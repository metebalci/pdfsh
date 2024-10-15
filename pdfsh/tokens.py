# Copyright (C) 2024 Mete Balci
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
tokens
"""

from .exceptions import PossibleBugException


# pylint: disable=missing-function-docstring
# pylint: disable=missing-class-docstring


class Token:

    def __init__(self):
        self.stack = []

    def push(self, ch: int):
        if ch < 0 or ch > 0xFF:
            raise PossibleBugException("token character is not a byte")
        self.stack.append(ch)

    def as_bytes(self):
        return bytes(self.stack)

    def as_hex(self):
        return bytes(self.stack).hex()

    def as_ascii(self):
        return bytes(self.stack).decode("ascii")

    def __eq__(self, other):
        assert isinstance(other, Token)
        return self.as_bytes() == other.as_bytes()

    def __hash__(self):
        return hash(self.as_bytes())


class TokenComment(Token):

    def __repr__(self):
        return "Token.%"


class TokenSolidus(Token):

    def __repr__(self):
        return "Token./"


class TokenDictionaryStart(Token):

    def __repr__(self):
        return "Token.<<"


class TokenDictionaryEnd(Token):

    def __repr__(self):
        return "Token.>>"


class TokenArrayStart(Token):

    def __repr__(self):
        return "Token.["


class TokenArrayEnd(Token):

    def __repr__(self):
        return "Token.]"


class TokenHexStringStart(Token):

    def __repr__(self):
        return "Token.<"


class TokenHexStringEnd(Token):

    def __repr__(self):
        return "Token.>"


class TokenLiteralStringStart(Token):

    def __repr__(self):
        return "Token.("


class TokenLiteralStringEnd(Token):

    def __repr__(self):
        return "Token.)"


class TokenLiteral(Token):

    def __repr__(self):
        s = []
        for b in self.stack:
            if 0x20 <= b <= 0x7E:
                s.append(chr(b))

            else:
                s.append("\\x%02x" % b)

        return f"Token.\"{''.join(s)}\": 0x{self.as_hex()}"
