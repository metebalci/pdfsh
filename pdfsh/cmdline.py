# SPDX-FileCopyrightText: 2024 Mete Balci
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

import logging
import sys
import termios
import tty
from typing import List

logger = logging.getLogger(__name__)

# 1- subclass
# 2- call Cmdline.__init__(self)
# 3- override get_cmdline_prompt, set_cmdline_color, complete_cmdline
# and process_cmdline, all are optional
# 4- use self.print, self.println, self.newline and self.error to print
class Cmdline:

    def __init__(self):
        # cursor position in cmdline
        self.pos:Int = 0
        # cmdline contents as individual (unicode) chars
        self.cmdline:List[str] = []
        # history
        self.history:List[str] = []
        self.history_pos:Int = 0
        self.last_up_down:bool = False

    # return the prompt before the cmdline
    def get_cmdline_prompt(self) -> str:
        return ''

    # set with ANSI codes the cmdline color
    def set_cmdline_color(self) -> None:
        pass

    # complete cmdline and return the completion (not whole cmdline)
    def complete_cmdline(Self, cmdline:str) -> str:
        return ''

    # enter pressed, process cmdline
    def process_cmdline(self, cmdline:str) -> None:
        pass

    def insert(self, ch:str) -> None:
        cmdline = self.cmdline[0:self.pos]
        cmdline.append(ch)
        if self.pos < len(self.cmdline):
            cmdline.extend(self.cmdline[self.pos:])
        self.cmdline = cmdline
        self.pos = self.pos + 1

    def backspace(self) -> None:
        if len(self.cmdline) > 0:
            cmdline = self.cmdline[0:self.pos-1]
            if self.pos < len(self.cmdline):
                cmdline.extend(self.cmdline[self.pos:])
            self.cmdline = cmdline
            self.pos = self.pos - 1

    # print without new line
    def print(self, s:str) -> None:
        if not isinstance(s, str):
            raise ValueError()
        if s is None:
            raise ValueError()
        sys.stdout.write(s)
        sys.stdout.flush()

    # print only new line
    def newline(self) -> None:
        self.print('\n\r')

    def println(self, s:str='') -> None:
        if not isinstance(s, str):
            raise ValueError()
        if s is None:
            raise ValueError()
        self.print(s)
        self.newline()

    def error(self, s:str) -> None:
        if not isinstance(s, str):
            raise ValueError()
        if s is None:
            raise ValueError()
        self.println('error: %s' % s)

    def new_cmdline(self) -> None:
        # move cursor to home
        self.print('\r')
        # erase line
        self.__ansi_erase_from_cursor_to_end_of_line()
        self.set_cmdline_color()
        prompt = self.get_cmdline_prompt()
        self.print(prompt)
        self.print(''.join(self.cmdline))
        self.__ansi_move_cursor_to_beginning_of_line()
        self.__ansi_move_cursor_right(len(prompt) + self.pos)

    def reset(self) -> None:
        self.last_up_down = False
        self.cmdline = []
        self.pos = 0

    def __ansi_erase_from_cursor_to_end_of_line(self) -> None:
        self.print('\x1b[0K')

    def __ansi_move_cursor_right(self, n:Int=1) -> None:
        self.print('\x1b[%dC' % n)

    def __ansi_move_cursor_to_beginning_of_line(self) -> None:
        self.print('\x1b[0E')

    def process_ctrlc(self) -> None:
        # ctrl-c is functions like escape
        self.process_esc()

    def process_ctrld(self) -> None:
        # ctrl-d does nothing, it may terminate but
        # it is easy to terminate terminal accidentally
        pass

    def process_esc(self) -> None:
        # escape, ignore current input and restart
        self.reset()

    def process_tab(self) -> None:
        if self.pos == len(self.cmdline):
            self.cmdline.extend(self.complete_cmdline(''.join(self.cmdline)))
            self.pos = len(self.cmdline)

    def process_alphanumeric(self, ch:str) -> None:
        self.insert(ch)

    def process_space(self) -> None:
        # only one space is allowed
        for ch in self.cmdline:
            if ch == ' ':
                return

        self.insert(' ')

    def process_backspace(self) -> None:
        if self.pos > 0:
            self.backspace()

    def process_enter(self) -> None:
        # enter
        self.print('\n\r')
        cmdline = ''.join(self.cmdline)
        self.history.append(cmdline)
        self.process_cmdline(cmdline)
        self.reset()

    def process_ins(self) -> None:
        pass

    def process_del(self) -> None:
        # del = right backspace
        if self.pos < len(self.cmdline):
            self.process_right()
            self.process_backspace()

    def process_home(self) -> None:
        self.pos = 0

    def process_end(self) -> None:
        self.pos = len(self.cmdline)

    def process_pageup(self) -> None:
        pass

    def process_pagedown(self) -> None:
        pass

    def process_up(self) -> None:
        logger.debug('up %s' % self.last_up_down)
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

    def process_down(self) -> None:
        logger.debug('down %s' % self.last_up_down)
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

    def process_left(self) -> None:
        if self.pos > 0:
            self.pos = self.pos - 1

    def process_right(self) -> None:
        if self.pos < len(self.cmdline):
            self.pos = self.pos + 1

    def process_stdin(self, ch:bytes) -> None:
        is_up_down = False
        if len(ch) == 1:

            if ch[0] == 0x03:
                self.process_ctrlc()

            elif ch[0] == 0x04:
                self.process_ctrld()

            elif ch[0] == 0x0d:
                self.process_enter()

            elif ch[0] == 0x1b:
                self.process_esc()

            elif ch[0] == 0x09:
                self.process_tab()

            elif ch[0] == 0x7f:
                self.process_backspace()

            elif ch[0] == 0x20:
                self.process_space()

            elif (ch[0] >= 0x21 and ch[0] <= 0x7e):
                self.process_alphanumeric(chr(ch[0]))

            logger.debug('process stdin ch=%s' % ch)
            logger.debug('process stdin cmdline=%s' % self.cmdline)
            logger.debug('process stdin pos=%s' % self.pos)

        else:

            if ch[0] == 0x1b:

                # up
                if ch[1:] == b'[A':
                    logger.debug('process stdin: up')
                    self.process_up()
                    is_up_down = True

                # down
                elif ch[1:] == b'[B':
                    logger.debug('process stdin: down')
                    self.process_down()
                    is_up_down = True

                # right
                elif ch[1:] == b'[C':
                    logger.debug('process stdin: right')
                    self.process_right()

                # left
                elif ch[1:] == b'[D':
                    logger.debug('process stdin: left')
                    self.process_left()

                # ins
                elif ch[1:] == b'[2~':
                    logger.debug('process stdin: ins')
                    self.process_ins()

                # del
                elif ch[1:] == b'[3~':
                    logger.debug('process stdin: del')
                    self.process_del()

                # home
                elif ch[1:] == b'[H':
                    logger.debug('process stdin: home')
                    self.process_home()

                # end
                elif ch[1:] == b'[F':
                    logger.debug('process stdin: end')
                    self.process_end()

                # page up
                elif ch[1:] == b'[5~':
                    logger.debug('process stdin: page up')
                    self.process_pageup()

                # page down
                elif ch[1:] == b'[6~':
                    logger.debug('process stdin: page down')
                    self.process_pagedown()

            else:
                try:
                    logger.debug('process stdin: potentially alphanumeric')
                    chars = ch.decode('utf-8')
                    logger.debug('process stdin: chars=%s' % chars)
                    self.process_alphanumeric(chars)
                except UnicodeError:
                    logger.debug('UnicodeError: 0x%s' % ch.hex())

        if is_up_down:
            self.last_up_down = True
        else:
            self.last_up_down = False

    def terminate(self) -> None:
        self.running = False

    def run(self) -> None:
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
                    self.new_cmdline()
                    redraw = False
                ch = sys.stdin.buffer.raw.read()
                if len(ch) > 0:
                    logger.debug('%s' % ch)
                    self.process_stdin(ch)
                    redraw = True
        finally:
            termios.tcsetattr(sys.stdin, termios.TCSAFLUSH, old_settings)
