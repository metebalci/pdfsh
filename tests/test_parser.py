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

import unittest

from pdfsh import Parser
from pdfsh.objects import *

class TestParser(unittest.TestCase):

    def test_boolean_false(self):
        buffer = 'false'.encode('ascii')
        p = Parser(buffer)
        self.assertEqual(p.next(), PdfBoolean(False))

    def test_boolean_true(self):
        buffer = 'true'.encode('ascii')
        p = Parser(buffer)
        self.assertEqual(p.next(), PdfBoolean(True))

    def _test_int(self, number):
        buffer = number.encode('ascii')
        p = Parser(buffer)
        self.assertEqual(p.next(), PdfIntegerNumber(int(number)))

    # the integer number samples below are from ISO 32000-2 7.3.3
    def test_integer_number_iso32000_2_7_3_3_example_1(self):
        self._test_int('123')
        self._test_int('43445')
        self._test_int('+17')
        self._test_int('-98')
        self._test_int('0')

    def _test_real(self, number):
        buffer = number.encode('ascii')
        p = Parser(buffer)
        self.assertEqual(p.next(), PdfRealNumber(float(number)))

    # the real number samples below are from ISO 32000-2 7.3.3
    def test_real_number_iso32000_2_7_3_3_example_2(self):
        self._test_real('34.5')
        self._test_real('-3.62')
        self._test_real('+123.6')
        self._test_real('4.')
        self._test_real('-.002')
        self._test_real('0.0')

    # options
    # s:ascii str, expected:None
    # s:ascii str, expected:ascii str
    # s:ascii str, expected:bytes
    # s:bytes, expected:bytes
    def _test_literal_string(self, s, expected=None):
        buffer = s
        if isinstance(buffer, str):
            buffer = buffer.encode('ascii')
            if expected is None:
                # default expected is without surrounding ( and )
                expected = s[1:-1].encode('ascii')
            elif isinstance(expected, str):
                expected = expected.encode('ascii')
        assert isinstance(buffer, bytes)
        assert isinstance(expected, bytes)
        p = Parser(buffer)
        self.assertEqual(p.next(), PdfLiteralString(expected))

    def test_literal_string_iso32000_2_7_3_4_2_example_1(self):
        self._test_literal_string('(This is a string)')
        self._test_literal_string('(Strings can contain newlines\nand such.)')
        self._test_literal_string('(Strings can contain balanced parentheses ()\nand special characters ( * ! & } ^ %and so on) .)')
        self._test_literal_string('(The following is an empty string .)')
        self._test_literal_string('()')
        self._test_literal_string('(It has zero (0) length.)')

    def test_literal_string_iso32000_2_7_3_4_2_example_2(self):
        buffer1 = '(These \\\ntwo strings \\\nare the same.)'.encode('ascii')
        buffer2 = '(These two strings are the same.)'.encode('ascii')
        p1 = Parser(buffer1)
        p2 = Parser(buffer2)
        self.assertEqual(p1.next(), p2.next())

    def test_literal_string_iso32000_2_7_3_4_2_example_3(self):
        self._test_literal_string('(This string has an end-of-line at the end of it.\n)')
        self._test_literal_string('(This string has an end-of-line at the end of it.\r)',
                                  'This string has an end-of-line at the end of it.\n')
        self._test_literal_string('(This string has an end-of-line at the end of it.\r\n)',
                                  'This string has an end-of-line at the end of it.\n')
        self._test_literal_string('(So does this one.\n)')
        self._test_literal_string('(So does this one.\r)',
                                  'So does this one.\n')
        self._test_literal_string('(So does this one.\r\n)',
                                  'So does this one.\n')

    def test_literal_string_iso32000_2_7_3_4_2_example_4(self):
        self._test_literal_string(b'(This string contains \245two octal characters\307.)',
                                  b'This string contains \xa5two octal characters\xc7.')

    def test_literal_string_iso32000_2_7_3_4_2_example_5(self):
        self._test_literal_string(b'(\\0053)', b'\x053')
        self._test_literal_string(b'(\\053)', b'+')
        self._test_literal_string(b'(\\53)', b'+')
        # the test below is not from ISO
        self._test_literal_string(b'(\\5)', b'\x05')

    def _test_hexadecimal_string(self, s, expected=None):
        buffer = s.encode('ascii')
        if expected is None:
            expected = bytes.fromhex(s[1:-1])
        elif isinstance(expected, str):
            expected = bytes.fromhex(expected)
        assert isinstance(buffer, bytes)
        assert isinstance(expected, bytes)
        p = Parser(buffer)
        self.assertEqual(p.next(), PdfHexadecimalString(expected))

    def test_hexadecimal_string_iso32000_2_7_3_4_3_example_1(self):
        self._test_hexadecimal_string('<4E6F762073686D6F7A206B6120706F702E>')

    def test_hexadecimal_string_iso32000_2_7_3_4_3_example_2(self):
        self._test_hexadecimal_string('<901FA3>')
        self._test_hexadecimal_string('<901FA>', '901FA0')

    def _test_name(self, s, expected=None):
        buffer = s.encode('ascii')
        if expected is None:
            expected = s[1:].encode('ascii')
        elif isinstance(expected, str):
            expected = expected.encode('ascii')
        assert isinstance(buffer, bytes)
        assert isinstance(expected, bytes)
        p = Parser(buffer)
        self.assertEqual(p.next(), PdfName(expected))

    def test_name_iso32000_2_7_3_5_table_4(self):
        self._test_name('/Name1')
        self._test_name('/ASomewhatLongerName')
        self._test_name('/A;Name_With-Various***Characters?')
        self._test_name('/1.2')
        self._test_name('/$$')
        self._test_name('/@pattern')
        self._test_name('/.notdef')
        self._test_name('/Lime#20Green', 'Lime Green')
        self._test_name('/paired#28#29parentheses', 'paired()parentheses')
        self._test_name('/The_Key_of_F#23_Minor', 'The_Key_of_F#_Minor')
        self._test_name('/A#42', 'AB')

    def test_array_iso32000_2_7_3_6_example(self):
        buffer = '[549 3.14 false (Ralph) /SomeName]'.encode('ascii')
        p = Parser(buffer)
        arr = p.next()
        self.assertIsInstance(arr, PdfArray)
        self.assertEqual(arr[0], PdfIntegerNumber(549))
        self.assertEqual(arr[1], PdfRealNumber(3.14))
        self.assertEqual(arr[2], PdfBoolean(False))
        self.assertEqual(arr[3], PdfLiteralString(b'Ralph'))
        self.assertEqual(arr[4], PdfName(b'SomeName'))

    def test_dictionary_iso32000_2_7_3_7_example(self):
        buffer = '''
<</Type /Example
        /Subtype /DictionaryExample
        /Version 0.01
        /IntegerItem 12
        /StringItem (a string)
        /Subdictionary <<
            /Item1 0.4
            /Item2 true
            /LastItem (not !)
            /VeryLastItem (OK)
        >>
>>'''
        buffer = buffer.encode('ascii')
        p = Parser(buffer)
        arr = p.next()
        self.assertIsInstance(arr, PdfDictionary)

    def test_null(self):
        buffer = 'null'.encode('ascii')
        p = Parser(buffer)
        self.assertEqual(p.next(), PdfNull())

    def test_indirect_object(self):
        buffer = '''
12 0 obj
(Brillig)
endobj
'''
        buffer = buffer.encode('ascii')
        p = Parser(buffer)
        obj = p.next()
        self.assertIsInstance(obj, PdfIndirectObject)
        self.assertEqual(obj.object_number, 12)
        self.assertEqual(obj.generation_number, 0)
        self.assertEqual(obj.p, PdfLiteralString(b'Brillig'))
