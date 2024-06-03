# Copyright (C) 2024 Mete Balci
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# pdfsh: a minimal shell to investigate PDF files
# Copyright (C) 2024 Mete Balci
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

from __future__ import annotations

import functools
import logging
import sys
import termios
from typing import Callable, List, Tuple

from .cmdline import Cmdline
from .objects import *
from .document import Document
from .header import Header
from .body import Body
from .xrt import CrossReferenceTable
from .trailer import Trailer

logger = logging.getLogger(__name__)

obj_types_as_str = {
    PdfBoolean:             'boolean object',
    PdfIntegerNumber:       'integer object',
    PdfRealNumber:          'real object',
    PdfLiteralString:       'literal string object',
    PdfHexadecimalString:   'hexadecimal string object',
    PdfName:                'name object',
    PdfArray:               'array object',
    PdfDictionary:          'dictionary object',
    PdfStream:              'stream object',
    PdfNull:                'null object',
    PdfIndirectReference:   'indirect reference'
}

def generate_node_output(obj):
    # most objects are a direct subclass
    v = obj_types_as_str.get(obj.__class__, None)
    # some are subclasses of subclasses of PdfDirectObject
    if v is None:
        for (k, v) in obj_types_as_str.items():
            if isinstance(obj, k):
                return v

    return 'unknown'

def generate_cat_output(obj, level=1, stop=None):
    if stop is not None and level > stop:
        return ''

    if (isinstance(obj, PdfBoolean) or
        isinstance(obj, PdfIntegerNumber) or
        isinstance(obj, PdfRealNumber) or
        isinstance(obj, PdfLiteralString) or
        isinstance(obj, PdfHexadecimalString) or
        isinstance(obj, PdfNull) or
        isinstance(obj, PdfIndirectReference)):
        return '%s' % str(obj)

    elif isinstance(obj, PdfName):
        return '%s' % str(obj.p)[1:]

    elif isinstance(obj, PdfStream):
        s1 = generate_cat_output(obj.stream_dictionary, level, stop)
        s2 = 'stream=[%d]' % (0 if obj.stream_data is None else len(obj.stream_data))
        return '%s\n\r%s' % (s1, s2)

    elif isinstance(obj, PdfArray):
        s = ''
        for i, array_element in enumerate(obj):
            if i == 0:
                s = '%s' % generate_cat_output(array_element,
                                               level+1,
                                               stop)

            else:
                s = '%s, %s' % (s,
                                generate_cat_output(array_element,
                                                    level+1,
                                                    stop))

        return '[%s]' % s

    elif isinstance(obj, PdfDictionary):
        s = []
        s.append('%s{' % (' ' * (level-1)))
        i = 0
        items = obj.items()
        for (k, v) in items:
            comma = ','
            i = i + 1
            if i == len(items):
                comma = ''
            if isinstance(v, PdfDictionary):
                s.append('%s%s:' % (' ' * level,
                                    generate_cat_output(k,
                                                        level,
                                                        stop)))
                s.append('%s%s' % (generate_cat_output(v,
                                                       level+1,
                                                       stop), comma))
            else:
                s.append('%s%s: %s%s' % (' ' * level,
                                         generate_cat_output(k, level, stop),
                                         generate_cat_output(v, level, stop),
                                         comma))

        s.append('%s}' % (' ' * (level-1)))
        return '\n\r'.join(s)

    else:
        raise PossibleBugException()

class ShellNode:

    def __init__(self,
                 name:str,
                 data:PdfDirectObject,
                 parent:ShellNode):
        if name is None or len(name) == 0:
            raise ValueError
        if data is None:
            raise ValueError
        self.name = name
        self.data = data
        self.parent = parent

    def __str__(self):
        return '%s p:%s' % (self.name,
                            self.parent.name if self.parent is not None else '')

    def __repr__(self):
        return str(self)

    def is_container(self) -> bool:
        return (isinstance(self.data, PdfArray) or
                isinstance(self.data, PdfDictionary))

    def is_ref(self) -> bool:
        return isinstance(self.data, PdfIndirectReference)

    def is_leaf(self) -> bool:
        return not self.is_container()

    @property
    def childs(self):
        childs = []
        # special handling for document
        if isinstance(self.data, Document):
            childs.append(ShellNode('header', self.data.header, self))
            childs.append(ShellNode('body', self.data.body, self))
            childs.append(ShellNode('xrt', self.data.xrt, self))
            childs.append(ShellNode('trailer', self.data.trailer, self))

        elif isinstance(self.data, PdfArray):
            for i, array_element in enumerate(self.data):
                childs.append(ShellNode('%d' % i,
                                        array_element,
                                        self))

        elif isinstance(self.data, PdfDictionary):
            for (k, v) in self.data.items():
                # k is PdfName for sure and
                # str(PdfName) starts with /
                childs.append(ShellNode('%s' % str(k)[1:],
                                        v,
                                        self))

        if isinstance(self.data, Document):
            return childs

        else:
            def sort_nodes(node):
                if node.is_container():
                    return node.name

                else:
                    return '%s%s' % ('~' * 10, node.name)

            return sorted(childs, key=sort_nodes)

class ShellTree:

    def __init__(self, root:ShellNode):
        self.root = root
        self.current = root

    @property
    def current_path(self) -> str:
        if self.current == self.root:
            return '/'
        else:
            path_elements = []
            n = self.current
            while n != self.root:
                path_elements.append(n.name)
                n = n.parent
            return '/%s' % '/'.join(path_elements[::-1])

    def node_at_path(self, path:str) -> ShellNode:
        if path[0] == '/':
            node = self.root

        else:
            node = self.current

        path_elements = path.split('/')
        for path_element in path_elements:
            if len(path_element) == 0:
                continue

            elif path_element == '.':
                continue

            elif path_element == '..':
                # when / is reached, behaves like nothing happens with ..
                if node.parent is not None:
                    node = node.parent

            else:
                found = False
                for child_node in node.childs:
                    if child_node.name == path_element:
                        node = child_node
                        found = True
                        break

                if not found:
                    return None

        return node

    def go_up(self) -> bool:
        if self.current is not self.root:
            self.current = self.current.parent
            return True
        return False

    def go_down(self, node:ShellNode) -> bool:
        for child_node in self.current.childs:
            if child_node == node:
                self.current = child_node
                return True
        return False

class Shell(Cmdline):

    colors = {
        'prompt': '\033[0;37m',     # white
        'normal': '\033[2;37m',     # gray (faint white)
        'ref': '\033[0;36m',        # cyan
        'container': '\033[0;34m'   # blue
    }

    def __init__(self,
                 ref2nodefn:Callable[[PdfIndirectReference], PdfDirectObject],
                 root:PdfDirectObject,
                 prompt_prefix: str | None) -> None:
        Cmdline.__init__(self)
        self.ref2nodefn = ref2nodefn
        self.tree = ShellTree(ShellNode('.', root, None))
        self.prompt_prefix = prompt_prefix

    def get_cmdline_prompt(self) -> str:
        return '%s:%s $ ' % (self.prompt_prefix, self.tree.current_path)

    def set_cmdline_color(self) -> None:
        self.print(Shell.colors['prompt'])

    def complete_cmdline(self, cmdline:str) -> str:
        completion = ''
        t_cmdline = ''.join(cmdline)
        t_cmdline_words = t_cmdline.strip().split(' ')
        if len(t_cmdline_words) == 2:
            t_cmd   = t_cmdline_words[0].strip()
            t_path  = t_cmdline_words[1].strip()
            logger.debug('t_cmd=%s t_path=%s' % (t_cmd, t_path))
            idx     = t_path.rfind('/')
            # if there is no /, it is a simple path
            # starting node is current node
            if idx == -1:
                start_node = self.tree.current
                part = t_path

            # if there is a /, find the starting node (it is a path)
            else:
                start_node = self.tree.node_at_path(t_path[0:idx])
                part = t_path[idx+1:]

            # if this is a complex path, possible to print alternatives
            if (idx >= 0 and
                len(part) == 0):

                # cd completion is containers only
                if t_cmd == 'cd':
                    childs = list(filter(lambda x:x.is_container(),
                                         start_node.childs))

                # other completions can be anything
                else:
                    childs = start_node.childs

                # newline is needed because this is an inline completion
                self.newline()
                self.print_ls_childs(childs)

            else:
                matching_nodes = []
                for node in start_node.childs:
                    if t_cmd == 'cd':
                        # if node is leaf, it cannot be cd'ed
                        if (node.is_leaf() and
                            not node.is_ref()):
                            continue

                    if node.name.startswith(part):
                        matching_nodes.append(node)

                if (len(matching_nodes) == 1 and
                    matching_nodes[0].is_container() and
                    t_path[-1] != '/'):

                    completion = '%s/' % matching_nodes[0].name[len(part):]

                elif len(matching_nodes) > 0:
                    minimum_matching_node = matching_nodes[0]
                    for node in matching_nodes:
                        if len(node.name) < len(minimum_matching_node.name):
                            minimum_matching_node = node

                    completion = minimum_matching_node.name[len(part):]

        return completion

    def process_cmdline(self, cmdline:str) -> None:
        logger.debug('process cmdline=%s' % self.cmdline)
        cmdline_words = cmdline.strip().split(' ')
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
        self.print(Shell.colors['container'])

    def set_ref_color(self):
        self.print(Shell.colors['ref'])

    def set_normal_color(self):
        self.print(Shell.colors['normal'])

    def print_ls_childs(self, childs:List[ShellNode]) -> None:
        for node in childs:
            prefix = ''
            postfix = ''
            if node.is_container():
                self.set_container_color()
                postfix = '/'

            elif node.is_ref():
                self.set_ref_color()
                postfix = '*'

            else:
                self.set_normal_color()

            self.println('%s%s' % (node.name, postfix))

    def command_ls(self, path:str | None) -> None:
        # ls means ls .
        if path is None:
            path = '.'

        start_node = self.tree.node_at_path(path)
        if start_node is None:
            self.error('no such path %s' % path)

        elif start_node.is_leaf():
            self.error('%s is not a container' % path)

        else:
            # ls <path>
            self.print_ls_childs(start_node.childs)

    def command_cd(self, path:str | None) -> None:
        # cd means cd $HOME and $HOME is / in pdfsh
        if path is None:
            path = '/'

        node = self.tree.node_at_path(path)

        if node is None:
            self.error('no such path %s' % path)

        elif node.is_leaf():
            self.error('%s is not a container' % path)

        else:
            self.tree.current = node

    def command_cat(self, path:str) -> None:
        # cat requires a path
        if path is None:
            self.error('usage: cat <path>')

        # cat <path>
        else:
            node = self.tree.node_at_path(path)
            if node is None:
                self.error('no such path %s' % path)

            else:
                self.set_normal_color()
                self.println(generate_cat_output(node.data))

    def command_cats_catsx(self, path:str, ascii:bool) -> None:
        # cats/catsx
        if path is None:
            self.error('usage: %s <path_to_stream>' % 'cats' if ascii else 'catsx')

        # cats/catsx <path>
        else:
            node = self.tree.node_at_path(path)
            if node is None:
                self.error('no such path %s' % path)

            elif isinstance(node.data, PdfStream):
                self.error('%s is not a stream' % path)

            else:
                self.set_normal_color()
                if ascii:
                    self.println('%s' % node.data.stream_data.decode('ascii',
                                                                     'replace'))
                else:
                    self.println('%s' % node.data.stream_data.hex())

    def command_node(self, path:str) -> None:
        # node
        if path is None:
            self.error('usage: node <path>')

        # node <path>
        else:
            node = self.tree.node_at_path(path)
            if node is None:
                self.error('no such path %s' % path)

            else:
                self.set_normal_color()
                self.println('%s is a %s' % (node.name,
                                             generate_node_output(node.data)))

    def command_help(self) -> None:
        self.set_normal_color()
        self.println('ls <path>        list current context')
        self.println('cd <path>        change current context to path')
        self.println('cat <path>       show the contents of path')
        self.println('cats <path>      show the contents of the stream data of node at path as ascii string')
        self.println('catsx <path>     show the contents of the stream data of node at path as hexadecimal string')
        self.println('node <path>      show the type of node at path')
        self.println('? or help        show this help')
        self.println('q                quit pdfsh')

    def process_command(self, cmd, path):
        # ls
        if cmd == 'ls':
            self.command_ls(path)

        # cd | .. | <node>
        elif cmd == 'cd':
            self.command_cd(path)

        # cat <node>
        elif cmd == 'cat':
            self.command_cat(path)

        # cats <node>
        elif cmd == 'cats':
            self.command_cats_catsx(path, True)

        # catsx <node>
        elif cmd == 'catsx':
            self.command_cats_catsx(path, False)

        # node <node>
        elif cmd == 'node':
            self.command_node(path)

        # ? or help
        elif cmd == '?' or cmd == 'help':
            self.command_help()

        # q
        elif cmd == 'q':
            self.terminate()

        # unknown command
        else:
            self.error('no such command')


