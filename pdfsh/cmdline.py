# Copyright (C) 2024 Mete Balci
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
cmdline
"""

from __future__ import annotations

import logging
import sys
import termios
import tty
from typing import List

from .exceptions import PossibleBugException

logger = logging.getLogger(__name__)


# 1- subclass
# 2- call Cmdline.__init__(self)
# 3- override get_cmdline_prompt, set_cmdline_color, complete_cmdline
# and process_cmdline, all are optional
# 4- use self.print, self.println, self.newline and self.error to print
class Cmdline:
    """cmdline"""

    def __init__(self):
        self.running: bool = False
        # cursor position in cmdline
        self.pos: int = 0
        # cmdline contents as individual (unicode) chars
        self.cmdline: List[str] = []
        # history
        self.history: List[str] = []
        self.history_pos: int = 0
        self.last_up_down: bool = False
        self.raw = False

    def get_cmdline_prompt(self) -> str:
        """returns the prompt before the cmdline"""
        return ""

    def set_cmdline_color(self) -> None:
        """sets cmdline color with ANSI codes"""

    # pylint: disable=unused-argument
    def complete_cmdline(self, cmdline: str) -> str:
        """returns the cmdline completion (not the whole cmdline)"""
        return ""

    def process_cmdline(self, cmdline: str) -> None:
        """process cmdline"""

    def __insert(self, ch: str) -> None:
        """make an insert char"""
        cmdline = self.cmdline[0 : self.pos]
        cmdline.append(ch)
        if self.pos < len(self.cmdline):
            cmdline.extend(self.cmdline[self.pos :])

        self.cmdline = cmdline
        self.pos = self.pos + 1

    def __backspace(self) -> None:
        """make a backspace move"""
        if len(self.cmdline) > 0:
            cmdline = self.cmdline[0 : self.pos - 1]
            if self.pos < len(self.cmdline):
                cmdline.extend(self.cmdline[self.pos :])

            self.cmdline = cmdline
            self.pos = self.pos - 1

    def print(self, s: str) -> None:
        """prints without new line"""
        if not isinstance(s, str):
            raise ValueError()

        if s is None:
            raise ValueError()

        sys.stdout.write(s)
        sys.stdout.flush()

    def newline(self) -> None:
        """prints only new line/end of line"""
        self.print("\n\r")

    def println(self, s: str = "") -> None:
        """prints with new line"""
        if not isinstance(s, str):
            raise ValueError()

        if s is None:
            raise ValueError()

        self.print(s)
        self.newline()

    # pylint: disable=unused-private-member
    def error(self, s: str) -> None:
        """prints error"""
        if not isinstance(s, str):
            raise ValueError()

        if s is None:
            raise ValueError()

        self.println(f"error: {s}")

    def __new_cmdline(self) -> None:
        """creates a new cmdline prompt"""
        # move cursor to home
        self.print("\r")
        # erase line
        self.__ansi_erase_from_cursor_to_end_of_line()
        self.set_cmdline_color()
        prompt = self.get_cmdline_prompt()
        self.print(prompt)
        self.print("".join(self.cmdline))
        self.__ansi_move_cursor_to_beginning_of_line()
        self.__ansi_move_cursor_right(len(prompt) + self.pos)

    def __reset(self) -> None:
        """resets the current cmdline"""
        self.last_up_down = False
        self.cmdline = []
        self.pos = 0

    def __ansi_erase_from_cursor_to_end_of_line(self) -> None:
        self.print("\x1b[0K")

    def __ansi_move_cursor_right(self, n: int = 1) -> None:
        self.print(f"\x1b[{n}C")

    def __ansi_move_cursor_to_beginning_of_line(self) -> None:
        self.print("\x1b[0E")

    def __process_ctrlc(self) -> None:
        # ctrl-c is functions like escape
        self.__process_esc()

    def __process_ctrld(self) -> None:
        # ctrl-d does nothing, it may terminate but
        # it is easy to terminate terminal accidentally
        pass

    def __process_esc(self) -> None:
        # escape, ignore current input and restart
        self.__reset()

    def __process_tab(self) -> None:
        if self.pos == len(self.cmdline):
            self.cmdline.extend(self.complete_cmdline("".join(self.cmdline)))
            self.pos = len(self.cmdline)

    def __process_alphanumeric(self, ch: str) -> None:
        self.__insert(ch)

    def __process_space(self) -> None:
        # only one space is allowed
        for ch in self.cmdline:
            if ch == " ":
                return

        self.__insert(" ")

    def __process_backspace(self) -> None:
        if self.pos > 0:
            self.__backspace()

    def __process_enter(self) -> None:
        # enter
        self.print("\n\r")
        cmdline = "".join(self.cmdline)
        self.history.append(cmdline)
        self.process_cmdline(cmdline)
        self.__reset()

    def __process_ins(self) -> None:
        pass

    def __process_del(self) -> None:
        # del = right backspace
        if self.pos < len(self.cmdline):
            self.__process_right()
            self.__process_backspace()

    def __process_home(self) -> None:
        self.pos = 0

    def __process_end(self) -> None:
        self.pos = len(self.cmdline)

    def __process_pageup(self) -> None:
        pass

    def __process_pagedown(self) -> None:
        pass

    def __process_up(self) -> None:
        logger.debug("up %s", self.last_up_down)
        if len(self.history) == 0:
            return

        if self.last_up_down:
            if self.history_pos > 0:
                self.history_pos = self.history_pos - 1

            else:
                return

        else:
            self.history_pos = len(self.history) - 1

        self.cmdline = list(self.history[self.history_pos])
        self.pos = len(self.cmdline)

    def __process_down(self) -> None:
        logger.debug("down %s", self.last_up_down)
        if len(self.history) == 0:
            return
        # for down to work for history, an up should happen before
        if self.last_up_down:
            self.history_pos = self.history_pos + 1
            if self.history_pos >= len(self.history):
                self.history_pos = len(self.history)
                self.cmdline = []
                self.pos = 0

            else:
                self.cmdline = list(self.history[self.history_pos])
                self.pos = len(self.cmdline)

    def __process_left(self) -> None:
        if self.pos > 0:
            self.pos = self.pos - 1

    def __process_right(self) -> None:
        if self.pos < len(self.cmdline):
            self.pos = self.pos + 1

    # pylint: disable=too-many-branches, too-many-statements
    def __process_stdin(self, ch: bytes) -> None:
        is_up_down = False
        if len(ch) == 1:

            if ch[0] == 0x03:
                self.__process_ctrlc()

            elif ch[0] == 0x04:
                self.__process_ctrld()

            elif ch[0] == 0x0D:
                self.__process_enter()

            elif ch[0] == 0x1B:
                self.__process_esc()

            elif ch[0] == 0x09:
                self.__process_tab()

            elif ch[0] == 0x7F:
                self.__process_backspace()

            elif ch[0] == 0x20:
                self.__process_space()

            elif ch[0] >= 0x21 and ch[0] <= 0x7E:
                self.__process_alphanumeric(chr(ch[0]))

            logger.debug("process stdin ch=%s", ch)
            logger.debug("process stdin cmdline=%s", self.cmdline)
            logger.debug("process stdin pos=%s", self.pos)

        else:

            if ch[0] == 0x1B:

                # up
                if ch[1:] == b"[A":
                    logger.debug("process stdin: up")
                    self.__process_up()
                    is_up_down = True

                # down
                elif ch[1:] == b"[B":
                    logger.debug("process stdin: down")
                    self.__process_down()
                    is_up_down = True

                # right
                elif ch[1:] == b"[C":
                    logger.debug("process stdin: right")
                    self.__process_right()

                # left
                elif ch[1:] == b"[D":
                    logger.debug("process stdin: left")
                    self.__process_left()

                # ins
                elif ch[1:] == b"[2~":
                    logger.debug("process stdin: ins")
                    self.__process_ins()

                # del
                elif ch[1:] == b"[3~":
                    logger.debug("process stdin: del")
                    self.__process_del()

                # home
                elif ch[1:] == b"[H":
                    logger.debug("process stdin: home")
                    self.__process_home()

                # end
                elif ch[1:] == b"[F":
                    logger.debug("process stdin: end")
                    self.__process_end()

                # page up
                elif ch[1:] == b"[5~":
                    logger.debug("process stdin: page up")
                    self.__process_pageup()

                # page down
                elif ch[1:] == b"[6~":
                    logger.debug("process stdin: page down")
                    self.__process_pagedown()

            else:
                try:
                    logger.debug("process stdin: potentially alphanumeric")
                    chars = ch.decode("utf-8")
                    logger.debug("process stdin: chars=%s", chars)
                    self.__process_alphanumeric(chars)
                except UnicodeError:
                    logger.debug("UnicodeError: 0x%s", ch.hex())

        if is_up_down:
            self.last_up_down = True
        else:
            self.last_up_down = False

    def terminate(self) -> None:
        """terminates cmdline loop"""
        self.running = False

    def run(self) -> None:
        """starts and runs cmdline loop"""
        # slightly different raw settings than tty.setraw
        # CC.VMIN is set to 0 to not block when reading
        old_settings = termios.tcgetattr(sys.stdin)
        tty.setraw(sys.stdin)
        mode = termios.tcgetattr(sys.stdin)
        # do not block when reading, simply return 0
        mode[6][termios.VMIN] = 0
        mode[6][termios.VTIME] = 0
        termios.tcsetattr(sys.stdin, termios.TCSAFLUSH, mode)
        self.running = True
        redraw = True
        try:
            while self.running:
                if redraw:
                    self.__new_cmdline()
                    redraw = False

                ch = sys.stdin.buffer.raw.read()
                if len(ch) > 0:
                    logger.debug("%s", ch)
                    self.__process_stdin(ch)
                    redraw = True

        finally:
            termios.tcsetattr(sys.stdin, termios.TCSAFLUSH, old_settings)
