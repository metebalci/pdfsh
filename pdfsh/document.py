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

import collections
import functools
import logging
import re
import time
from typing import List, Tuple
import sys

from .exceptions import *
from .parser import Parser
from .objects import *
from .page import Page
from .header import Header
from .xrt import CrossReferenceTable, CrossReferenceTableSection
from .trailer import Trailer
from .body import Body

logger = logging.getLogger(__name__)

# represents a PDF document as a PdfDictionary
class Document(PdfDictionary):

    def __init__(self, buffer:bytes):
        super().__init__()
        logger.debug("document buffer size = %0.2f MB" % (len(buffer)/1024.0/1024.0))
        self.parser = Parser(buffer)
        self.__load()

    @property
    def header(self):
        return self.get(PdfName('header'), None)

    @property
    def body(self):
        return self.get(PdfName('body'), None)

    @property
    def xrt(self):
        return self.get(PdfName('xrt'), None)

    @property
    def trailer(self):
        return self.get(PdfName('trailer'), None)

    def get_object_by_ref(self,
                          ref:PdfIndirectReference) -> PdfDirectObject:
        assert ref is not None
        assert isinstance(ref, PdfIndirectReference)
        return self.get_object_by_number(ref.object_number,
                                         ref.generation_number)

    def get_object_by_number(self,
                             object_number:int,
                             generation_number:int=0) -> PdfDirectObject:
        assert object_number is not None
        assert generation_number is not None
        byte_offset = self.xrt.get_object_byte_offset(object_number,
                                                      generation_number)
        if byte_offset is None:
            return PdfNull()

        self.parser.seek(byte_offset)
        obj = self.parser.next()
        if obj is None:
            return PdfNull()
        else:
            return obj.value

    def __load(self) -> None:
        self.__load_header()
        self.__load_xrt_sections_and_trailers()
        self.__load_body()

    def __load_header(self):
        self.parser.seek(0)
        self[PdfName('header')] = Header.load(self.parser)

    def __load_xrt_sections_and_trailers(self):
        self[PdfName('xrt')] = CrossReferenceTable()
        xrt_section_byte_offset = self.__get_last_startxref_byte_offset()
        logger.debug('last xrt section offset: %x' % xrt_section_byte_offset)
        trailer = None
        last_trailer = None
        while True:
            self.parser.seek(xrt_section_byte_offset)
            xrt_section = CrossReferenceTableSection.load(self.parser)
            logger.debug('xrt_section: %s' % xrt_section)
            self.xrt.append(xrt_section)
            while True:
                trailer_keyword = self.parser.next_line()
                if trailer_keyword is None:
                    raise PdfConformanceError('no trailer keyword found')
                elif trailer_keyword == b'trailer':
                    break
            trailer_dictionary = self.parser.next()
            if not isinstance(trailer_dictionary, PdfDictionary):
                raise PdfConformanceException('trailer is not a dictionary')
            trailer = Trailer(trailer_dictionary, xrt_section_byte_offset)
            if self.trailer is None:
                self[PdfName('trailer')] = trailer
            logger.debug('xrt section offset: %x' % xrt_section_byte_offset)
            if last_trailer is None:
                last_trailer = trailer
            else:
                last_trailer.prev = trailer
                last_trailer = trailer
            xrt_section_byte_offset = trailer_dictionary.get(PdfName('Prev'),
                                                             None)
            if xrt_section_byte_offset is None:
                break
            else:
                xrt_section_byte_offset = xrt_section_byte_offset.p

    def __get_last_startxref_byte_offset(self) -> int:
        pos = self.parser.seek(self.parser.size() - 1)
        while True:
            self.parser.seek_to_start_of_line()
            pos = self.parser.tell()
            line = self.parser.next_line()
            if line == b'startxref':
                offset_line = self.parser.next_line()
                if offset_line is None:
                    PdfConformanceException('startxref offset not found')
                offset_line = offset_line.decode('ascii', 'replace')
                if Trailer.offset_re.match(offset_line) is None:
                    PdfConformanceException('startxref offset is not a number ?')
                return int(offset_line)

            else:
                if pos == 0:
                    break

                else:
                    self.parser.seek(pos - 1)

        raise PdfConformanceException('startxref not found')

    def __load_body(self):
        assert self.xrt is not None
        self[PdfName('body')] = Body()
        processed_entries = set()
        num_xrt_entries = 0
        for xrt_section in self.xrt:
            for xrt_subsection in xrt_section:
                for xrt_entry in xrt_subsection.entries:
                    num_xrt_entries = num_xrt_entries + 1
                    if xrt_entry in processed_entries:
                        continue

                    processed_entries.add(xrt_entry)
                    if xrt_entry.is_in_use:
                        obj = self.get_object_by_number(xrt_entry.object_number,
                                                        xrt_entry.generation_number)
                        self.body[PdfName('%d.%d' % (xrt_entry.object_number,
                                                     xrt_entry.generation_number))] = obj

        logger.info('%d xrt entries.' % num_xrt_entries)
        logger.info('%d objects loaded.' % len(self.body))
