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

import logging
import re

from .exceptions import *
from .parser import Parser
from .objects import *

logger = logging.getLogger(__name__)

class CrossReferenceTableEntry(PdfDictionary):

    entry_re = re.compile(r"^[0-9]{10} [0-9]{5} [fn][ ]?$")

    # ISO 32000-2 7.5.4: Cross-reference table
    # xref entry has a fixed format
    # nnnnnnnnnn ggggg fEOL
    # EOL is one of SP CR, SP LF, CR LF
    @staticmethod
    def load(parser:Parser, object_number:int):
        line = parser.next_line().decode('ascii', 'replace')
        if CrossReferenceTableEntry.entry_re.match(line) is None:
            raise PdfConformanceException('invalid CrossReferenceTableEntry: %s' % line)
        return CrossReferenceTableEntry(object_number,
                                        int(line[0:10]),
                                        int(line[11:16]),
                                        line[17:18] == 'f')

    def __init__(self,
                 object_number:int,
                 byte_offset:int,
                 generation_number:int,
                 is_free:bool):
        super().__init__()
        self[PdfName('object_number')] = PdfIntegerNumber(object_number)
        self[PdfName('byte_offset')] = PdfIntegerNumber(byte_offset)
        self[PdfName('generation_number')] = PdfIntegerNumber(generation_number)
        self[PdfName('is_free')] = PdfBoolean(is_free)

    @property
    def object_number(self):
        return self[PdfName('object_number')].p

    @property
    def byte_offset(self):
        return self[PdfName('byte_offset')].p

    @property
    def generation_number(self):
        return self[PdfName('generation_number')].p

    @property
    def is_free(self):
        return self[PdfName('is_free')].p

    @property
    def is_in_use(self):
        return not self.is_free

    def __str__(self):
        return '%010d %05d %s' % (self.byte_offset,
                                  self.generation_number,
                                  'f' if self.is_free else 'n')

    def __repr__(self):
        return str(self)

    def __hash__(self):
        return hash('%d.%d' % (self.object_number, self.generation_number))

    def __eq__(self, other):
        if isinstance(other, CrossReferenceTableEntry):
            return ((self.object_number == other.object_number) and
                    (self.generation_number == other.generation_number))
        else:
            return NotImplemented


class CrossReferenceTableSubsection(PdfDictionary):

    subsection_re = re.compile(r"^[0-9]+ [0-9]+$")

    # ISO 32000-2 7.5.4: Cross-reference table
    # first_obj_num num_entries
    # xref_entries* (see _read_xref_entry)
    @staticmethod
    def load(parser:Parser):
        saved_pos = parser.tell()
        line = parser.next_line().decode('ascii', 'replace')
        if CrossReferenceTableSubsection.subsection_re.match(line) is None:
            parser.seek(saved_pos)
            return None
        words = line.split(' ')
        first_object_number = int(words[0])
        number_of_entries = int(words[1])
        logger.debug('xref.first_obj_num: %d' % first_object_number)
        logger.debug('xref.num_entries: %d' % number_of_entries)
        if number_of_entries == 0:
            raise PdfConformanceException('Cross-reference table subsection number of entries cannot be 0')
        xrt_subsection = CrossReferenceTableSubsection(first_object_number)
        for object_number in range(first_object_number,
                                   first_object_number + number_of_entries):
            xrt_entry = CrossReferenceTableEntry.load(parser, object_number)
            logger.debug('xrt_entry: %s' % xrt_entry)
            xrt_subsection.append_entry(line, xrt_entry)
        return xrt_subsection

    def __init__(self, first_object_number:int):
        super().__init__()
        self[PdfName('first_object_number')] = PdfIntegerNumber(first_object_number)
        self[PdfName('entries')] = PdfArray()

    @property
    def first_object_number(self):
        return self[PdfName('first_object_number')].p

    @property
    def entries(self):
        return self[PdfName('entries')]

    def append_entry(self, line, entry):
        self.entries.append(entry)

    def get_object_byte_offset(self, object_number, generation_number=0):
        for i, entry in enumerate(self.entries):
            if (((self.first_object_number + i) == object_number) and
                (entry.generation_number == generation_number)):
                if entry.is_free:
                    return None
                else:
                    return entry.byte_offset

        return None

class CrossReferenceTableSection(PdfArray):

    # ISO 32000-2 7.5.4: Cross-reference table
    # xref
    # subsections+
    @staticmethod
    def load(parser:Parser):
        line = parser.next_line()
        if line != b'xref':
            raise PdfConformanceException('xref offset does not point to an xref')
        xrt_section = CrossReferenceTableSection()
        logger.debug('loading xrt_subsections...')
        while True:
            xrt_subsection = CrossReferenceTableSubsection.load(parser)
            if xrt_subsection is None:
                logger.debug('xrt_subsections loaded.')
                break

            else:
                logger.debug('xrt_subsection: %s' % xrt_subsection)
                xrt_section.append(xrt_subsection)

        return xrt_section

    def get_object_byte_offset(self, object_number, generation_number=0):
        for subsection in self:
            ref = subsection.get_object_byte_offset(object_number,
                                                    generation_number)
            if ref is not None:
                return ref

        return None

class CrossReferenceTable(PdfArray):

    def get_object_byte_offset(self, object_number, generation_number=0):
        for section in self:
            ref = section.get_object_byte_offset(object_number,
                                                 generation_number)
            if ref is not None:
                return ref

        return None
