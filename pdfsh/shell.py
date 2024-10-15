# Copyright (C) 2024 Mete Balci
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
shell
"""

from __future__ import annotations

import logging
import sys
from typing import Callable, List

from .cmdline import Cmdline
from .exceptions import PossibleBugException
from .objects import PdfName, PdfNull, PdfBoolean
from .objects import PdfIntegerNumber, PdfRealNumber
from .objects import PdfLiteralString, PdfHexadecimalString
from .objects import PdfArray, PdfDictionary, PdfStream
from .objects import PdfIndirectReference, PdfDirectObject
from .document import Document


logger = logging.getLogger(__name__)


_obj_types_as_str = {
    PdfBoolean: "a boolean object",
    PdfIntegerNumber: "an integer object",
    PdfRealNumber: "a real object",
    PdfLiteralString: "a literal string object",
    PdfHexadecimalString: "a hexadecimal string object",
    PdfName: "a name object",
    PdfArray: "an array object",
    PdfDictionary: "a dictionary object",
    PdfStream: "a stream object",
    PdfNull: "a null object",
    PdfIndirectReference: "an indirect reference",
}


def _generate_node_output(obj):
    # most objects are a direct subclass
    v = _obj_types_as_str.get(obj.__class__, None)
    # some are subclasses of subclasses of PdfDirectObject
    if v is None:
        for k, v in _obj_types_as_str.items():
            if isinstance(obj, k):
                return v

        return f"unknown {obj.__class__.__name__}"

    return v


# pylint: disable=too-many-return-statements
def _generate_cat_output(obj, level=1, stop=None):
    if level is None or level == 0:
        raise ValueError()

    if isinstance(
        obj,
        (
            PdfBoolean,
            PdfIntegerNumber,
            PdfRealNumber,
            PdfLiteralString,
            PdfHexadecimalString,
            PdfNull,
            PdfIndirectReference,
        ),
    ):
        return f"{str(obj)}"

    if isinstance(obj, PdfName):
        return f"{str(obj)[1:]}"

    if isinstance(obj, PdfStream):
        # cat only shows the stream dictionary
        # use cats or catsx to see the stream data
        return _generate_cat_output(obj.stream_dictionary, level, level + 1)

    if isinstance(obj, PdfArray):
        if stop is not None and level >= stop:
            return "[...]"

        s = ""
        for i, array_element in enumerate(obj):
            if i == 0:
                s = f"{_generate_cat_output(array_element, level+1, stop)}"

            else:
                s = f"{s}, {_generate_cat_output(array_element, level+1, stop)}"

        return f"[{s}]"

    if isinstance(obj, PdfDictionary):
        if stop is not None and level >= stop:
            return "{...}"

        s = []
        items = obj.items()
        for i, (k, v) in enumerate(items):
            comma = "," if i < (len(items) - 1) else ""
            # pylint: disable=consider-using-f-string
            s.append(
                "%s%s: %s%s"
                % (
                    "  " * level,
                    _generate_cat_output(k, level, stop),
                    _generate_cat_output(v, level + 1, stop),
                    comma,
                )
            )

        # pylint: disable=consider-using-f-string
        return "{\n\r%s\n\r%s}" % ("\n\r".join(s), "  " * (level - 1))

    raise PossibleBugException()


# pylint: disable=missing-function-docstring
class ShellNode:
    """ShellNode"""

    def __init__(self, name: str, data: PdfDirectObject, parent: ShellNode):
        if name is None or len(name) == 0:
            raise ValueError
        if data is None:
            raise ValueError
        self.name = name
        self.data = data
        self.parent = parent
        self._childs = []
        if self.parent is not None:
            self.parent._childs.append(self)

    def __str__(self):
        parent_name = self.parent.name if self.parent is not None else ""
        return f"ShellNode({self.name}, t:<{self.data.__class__.__name__}>, p:{parent_name})"

    def __repr__(self):
        return str(self)

    def is_container(self) -> bool:
        return isinstance(self.data, (PdfArray, PdfDictionary))

    def is_ref(self) -> bool:
        return isinstance(self.data, PdfIndirectReference)

    def is_leaf(self) -> bool:
        return not self.is_container()

    @property
    def childs(self):
        # special handling for document
        if isinstance(self.data, Document):
            childs = []
            childs.append(ShellNode("header", self.data.header, self))
            childs.append(ShellNode("body", self.data.body, self))
            childs.append(ShellNode("xrt", self.data.xrt, self))
            childs.append(ShellNode("trailer", self.data.trailer, self))
            childs.append(ShellNode("objects", self.data.objects, self))
            return childs

        # special handling for PdfArray
        if isinstance(self.data, PdfArray):
            childs = []
            for i, array_element in enumerate(self.data):
                childs.append(ShellNode(f"{i}", array_element, self))
            return childs

        # special handling for PdfDictionary
        if isinstance(self.data, PdfDictionary):
            childs = []
            for k, v in self.data.items():
                # k is PdfName for sure and
                # str(PdfName) starts with /
                childs.append(ShellNode(f"{str(k)[1:]}", v, self))
            return childs

        def sort_nodes(node):
            if node.is_container():
                return node.name

            return f"{'~'*10}{node.name}"

        return sorted(self._childs, key=sort_nodes)


# pylint: disable=missing-function-docstring
class ShellTree:
    """ShellTree"""

    def __init__(self, root: ShellNode):
        self.root = root
        self.current = root

    @property
    def current_path(self) -> str:
        if self.current == self.root:
            return "/"

        path_elements = []
        n = self.current
        while n != self.root:
            path_elements.append(n.name)
            n = n.parent

        return f"/{'/'.join(path_elements[::-1])}"

    def node_at_path(self, path: str) -> ShellNode:
        logger.debug("node_at_path: %s", path)
        if path[0] == "/":
            node = self.root

        else:
            node = self.current

        path_elements = path.split("/")
        for path_element in path_elements:
            if len(path_element) == 0:
                continue

            if path_element == ".":
                continue

            if path_element == "..":
                # when / is reached, behaves like nothing happens with ..
                if node.parent is not None:
                    node = node.parent
                    continue

            found = False
            logger.debug("path_element: %s", path_element)
            for child_node in node.childs:
                logger.debug("child_node.name: %s", child_node.name)
                if child_node.name == path_element:
                    logger.debug("found: %s", child_node)
                    node = child_node
                    found = True
                    break

            if not found:
                return None

        return node

    def go_up(self) -> bool:
        """navigates up to the parent"""
        if self.current is not self.root:
            self.current = self.current.parent
            return True

        logger.debug("cannot go_up, current node=%s is root", self.current)
        return False

    def go_down(self, node: ShellNode) -> bool:
        """navigates into the child node node"""
        for child_node in self.current.childs:
            if child_node == node:
                self.current = child_node
                return True

        logger.debug("cannot go_down, %s is not a child of current node=%s",
                    node,
                    self.current)
        return False


# pylint: disable=missing-function-docstring
class Shell(Cmdline):
    """Shell"""

    colors = {
        "prompt": "\033[0;37m",  # white
        "normal": "\033[2;37m",  # gray (faint white)
        "ref": "\033[0;36m",  # cyan
        "container": "\033[0;34m",  # blue
    }

    def __init__(
        self,
        ref2nodefn: Callable[[PdfIndirectReference], PdfDirectObject],
        root: PdfDirectObject,
        prompt_prefix: str | None,
    ) -> None:
        Cmdline.__init__(self)
        self.ref2nodefn = ref2nodefn
        self.tree = ShellTree(ShellNode(".", root, None))
        self.prompt_prefix = prompt_prefix

    def get_cmdline_prompt(self) -> str:
        return f"{self.prompt_prefix}:{self.tree.current_path} $ "

    def set_cmdline_color(self) -> None:
        if not self.raw:
            self.print(Shell.colors["prompt"])

    # pylint: disable=too-many-branches
    def complete_cmdline(self, cmdline: str) -> str:
        completion = ""
        t_cmdline = "".join(cmdline)
        t_cmdline_words = t_cmdline.strip().split(" ")
        if len(t_cmdline_words) == 2:
            t_cmd = t_cmdline_words[0].strip()
            t_path = t_cmdline_words[1].strip()
            logger.debug("t_cmd=%s t_path=%s", t_cmd, t_path)
            idx = t_path.rfind("/")
            # if there is no /, it is a simple path
            # starting node is current node
            if idx == -1:
                start_node = self.tree.current
                part = t_path

            # if there is a /, find the starting node (it is a path)
            else:
                start_node = self.tree.node_at_path(t_path[0:idx])
                part = t_path[idx + 1 :]

            # if this is a complex path, possible to print alternatives
            if idx >= 0 and len(part) == 0:

                # cd completion is containers only
                if t_cmd == "cd":
                    childs = list(filter(lambda x: x.is_container(), start_node.childs))

                # other completions can be anything
                else:
                    childs = start_node.childs

                # newline is needed because this is an inline completion
                self.newline()
                self.print_ls_childs(childs)

            else:
                matching_nodes = []
                for node in start_node.childs:
                    if t_cmd == "cd":
                        # if node is leaf, it cannot be cd'ed
                        if node.is_leaf() and not node.is_ref():
                            continue

                    if node.name.startswith(part):
                        matching_nodes.append(node)

                if (
                    len(matching_nodes) == 1
                    and matching_nodes[0].is_container()
                    and t_path[-1] != "/"
                ):

                    completion = f"{matching_nodes[0].name[len(part):]}/"

                elif len(matching_nodes) > 0:
                    minimum_matching_node = matching_nodes[0]
                    for node in matching_nodes:
                        if len(node.name) < len(minimum_matching_node.name):
                            minimum_matching_node = node

                    completion = minimum_matching_node.name[len(part) :]

        return completion

    def process_cmdline(self, cmdline: str) -> None:
        logger.debug("process cmdline=%s", self.cmdline)
        cmdline_words = cmdline.strip().split(" ")
        assert len(cmdline_words) <= 2
        cmd = None
        path = None

        if len(cmdline_words) >= 1:
            cmd = cmdline_words[0].strip()

        if len(cmdline_words) >= 2:
            path = cmdline_words[1].strip()

        if len(cmd) > 0:
            self.process_command(cmd, path)

    def set_container_color(self):
        if not self.raw:
            self.print(Shell.colors["container"])

    def set_ref_color(self):
        if not self.raw:
            self.print(Shell.colors["ref"])

    def set_normal_color(self):
        if not self.raw:
            self.print(Shell.colors["normal"])

    def print_ls_childs(self, childs: List[ShellNode]) -> None:
        for node in childs:
            postfix = ""
            if node.is_container():
                self.set_container_color()
                postfix = "/"

            elif node.is_ref():
                self.set_ref_color()
                postfix = "*"

            else:
                self.set_normal_color()

            self.println(f"{node.name}{postfix}")

    def command_ls(self, path: str | None) -> None:
        # ls means ls .
        if path is None:
            path = "."

        start_node = self.tree.node_at_path(path)
        if start_node is None:
            self.error(f"no such path {path}")

        elif start_node.is_leaf():
            self.error(f"{path} is not a container")

        else:
            # ls <path>
            self.print_ls_childs(start_node.childs)

    def command_cd(self, path: str | None) -> None:
        # cd means cd $HOME and $HOME is / in pdfsh
        if path is None:
            path = "/"

        node = self.tree.node_at_path(path)

        if node is None:
            self.error(f"no such path {path}")

        elif node.is_leaf():
            self.error(f"{path} is not a container")

        else:
            self.tree.current = node

    def command_cat(self, path: str) -> None:
        # cat requires a path
        if path is None:
            self.error("usage: cat <path>")

        # cat <path>
        else:
            node = self.tree.node_at_path(path)
            if node is None:
                self.error(f"no such path {path}")

            else:
                self.set_normal_color()
                self.println(_generate_cat_output(node.data, 1, 10))

    # pylint: disable=too-many-branches
    def command_cats(self, path: str, cmd: str) -> None:
        # cats/catsx
        if path is None:
            self.error(f"usage: {cmd} <path_to_stream>")

        # cats/catsx <path>
        else:
            node = self.tree.node_at_path(path)
            if node is None:
                self.error(f"no such path {path}")

            elif not isinstance(node.data, PdfStream):
                self.error(f"{path} is not a stream")

            else:
                self.set_normal_color()

                if cmd == "cats":
                    self.println(f"{node.data.stream_data.decode('utf-8', 'replace')}")

                elif cmd == "catsx":
                    self.println(f"{node.data.stream_data.hex()}")

                elif cmd == "catsb.decoded":
                    if not self.raw:
                        self.error("this command can only be run with -c option")

                    else:
                        sys.stdout.buffer.write(node.data.stream_data)
                        sys.stdout.flush()

                elif cmd == "catsb.encoded":
                    if not self.raw:
                        self.error("this command can only be run with -c option")

                    else:
                        sys.stdout.buffer.write(node.data.encoded_stream_data)
                        sys.stdout.flush()

                else:
                    raise PossibleBugException()

    def command_node(self, path: str) -> None:
        # node
        if path is None:
            self.error("usage: node <path>")

        # node <path>
        else:
            node = self.tree.node_at_path(path)
            if node is None:
                self.error(f"no such path {path}")

            else:
                self.set_normal_color()
                self.println(f"{node.name} is {_generate_node_output(node.data)}")

    def command_help(self) -> None:
        self.set_normal_color()
        self.println("ls <path>        list current context")
        self.println("cd <path>        change current context to path")
        self.println("cat <path>       show the contents of path")
        self.println(
            "cats <path>      show the contents of the stream data of node"
            " at path as ascii string"
        )
        self.println(
            "catsx <path>     show the contents of the stream data of node "
            "at path as hexadecimal string"
        )
        self.println("node <path>      show the type of node at path")
        self.println("? or help        show this help")
        self.println("q                quit pdfsh")

    def process_command(self, cmd, path):
        # ls
        if cmd == "ls":
            self.command_ls(path)

        # cd | .. | <node>
        elif cmd == "cd":
            self.command_cd(path)

        # cat <node>
        elif cmd == "cat":
            self.command_cat(path)

        # cats <node>
        elif cmd in ("cats", "catsx", "catsb.decoded", "catsb.encoded"):
            self.command_cats(path, cmd)

        # node <node>
        elif cmd == "node":
            self.command_node(path)

        # ? or help
        elif cmd in ("?", "help"):
            self.command_help()

        # q
        elif cmd == "q":
            self.terminate()

        # unknown command
        else:
            self.error("no such command")
