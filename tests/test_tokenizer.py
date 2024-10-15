# Copyright (C) 2024 Mete Balci
#
# SPDX-License-Identifier: GPL-3.0-or-later

import unittest

from pdfsh.tokenizer import Tokenizer
from pdfsh.tokens import *

from . import enable_debug_logging

class TestTokenizer(unittest.TestCase):

    def setUp(self):
        enable_debug_logging()

    def test_comment_dont_skip(self):
        buffer = '%'.encode('ascii')
        t = Tokenizer(buffer, skip_comments=False)
        self.assertIsInstance(t.next(), TokenComment)

    def test_comment(self):
        buffer = '% comment\n123'.encode('ascii')
        t = Tokenizer(buffer)
        self.assertIsInstance(t.next(), TokenLiteral)

    def test_solidus(self):
        buffer = '/'.encode('ascii')
        t = Tokenizer(buffer)
        self.assertIsInstance(t.next(), TokenSolidus)

    def test_dictionary_start(self):
        buffer = '<<'.encode('ascii')
        t = Tokenizer(buffer)
        self.assertIsInstance(t.next(), TokenDictionaryStart)

    def test_dictionary_end(self):
        buffer = '>>'.encode('ascii')
        t = Tokenizer(buffer)
        self.assertIsInstance(t.next(), TokenDictionaryEnd)

    def test_array_start(self):
        buffer = '['.encode('ascii')
        t = Tokenizer(buffer)
        self.assertIsInstance(t.next(), TokenArrayStart)

    def test_array_end(self):
        buffer = ']'.encode('ascii')
        t = Tokenizer(buffer)
        self.assertIsInstance(t.next(), TokenArrayEnd)

    def test_hex_string_start(self):
        buffer = '<'.encode('ascii')
        t = Tokenizer(buffer)
        self.assertIsInstance(t.next(), TokenHexStringStart)

    def test_hex_string_end(self):
        buffer = '>'.encode('ascii')
        t = Tokenizer(buffer)
        self.assertIsInstance(t.next(), TokenHexStringEnd)

    def test_literal_string_start(self):
        buffer = '('.encode('ascii')
        t = Tokenizer(buffer)
        self.assertIsInstance(t.next(), TokenLiteralStringStart)

    def test_literal_string_end(self):
        buffer = ')'.encode('ascii')
        t = Tokenizer(buffer)
        self.assertIsInstance(t.next(), TokenLiteralStringEnd)

    def test_literal(self):
        buffer = 'something'.encode('ascii')
        t = Tokenizer(buffer)
        self.assertIsInstance(t.next(), TokenLiteral)

    # example in ISO 32000-2 7.2.4
    def test_example_iso32000_2_7_2_4(self):
        buffer = 'abc%comment (/%) blah blah blah\n123'.encode('ascii')
        t = Tokenizer(buffer)
        t1 = t.next()
        t2 = t.next()
        self.assertIsInstance(t1, TokenLiteral)
        self.assertEqual(t1.as_ascii(), 'abc')
        self.assertIsInstance(t2, TokenLiteral)
        self.assertEqual(t2.as_ascii(), '123')

    def _test_EOL(self, marker):
        buffer = ('abc%sdef' % marker).encode('ascii')
        t = Tokenizer(buffer)
        t1 = t.next()
        t2 = t.next()
        self.assertEqual(t1.as_ascii(), 'abc')
        self.assertEqual(t2.as_ascii(), 'def')

    def test_EOL_LF(self):
        self._test_EOL('\n')

    def test_EOL_CR(self):
        self._test_EOL('\r')

    def test_EOL_CRLF(self):
        self._test_EOL('\r\n')
