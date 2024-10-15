# Copyright (C) 2024 Mete Balci
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
document
"""

import logging
import re

from .exceptions import PdfConformanceException
from .parser import Parser
from .objects import PdfName, PdfDictionary, PdfIndirectReference, PdfDirectObject
from .objects import PdfNull
from .header import Header
from .xrt import CrossReferenceTable, CrossReferenceTableSection
from .trailer import Trailer
from .body import Body, Objects


logger = logging.getLogger(__name__)


class Document(PdfDictionary):
    """represents a PDF document as a PdfDictionary"""

    __trailer_offset_re = re.compile(r"^[0-9]+$")

    def __init__(self, buffer: bytes):
        super().__init__()
        logger.debug("document buffer size = %0.2f MB", (len(buffer) / 1024.0 / 1024.0))
        self.parser = Parser(buffer)
        self.__load()

    @property
    def header(self):
        """header"""
        return self.get(PdfName("header"), None)

    @property
    def body(self):
        """body"""
        return self.get(PdfName("body"), None)

    @property
    def objects(self):
        """objects"""
        return self.get(PdfName("objects"), None)

    @property
    def xrt(self):
        """xrt"""
        return self.get(PdfName("xrt"), None)

    @property
    def trailer(self):
        """trailer"""
        return self.get(PdfName("trailer"), None)

    def get_object_by_ref(self, ref: PdfIndirectReference) -> PdfDirectObject:
        """returns an object pointed by ref"""
        assert ref is not None
        assert isinstance(ref, PdfIndirectReference)
        return self.get_object_by_number(ref.object_number, ref.generation_number)

    def get_object_by_number(
        self, object_number: int, generation_number: int = 0
    ) -> PdfDirectObject:
        """returns an object identified by object and generation number"""
        assert object_number is not None
        assert generation_number is not None
        entry = self.xrt.find_entry(object_number, generation_number)
        if entry is None:
            return PdfNull()

        if entry.is_compressed:
            object_stream = self.get_object_by_number(entry.object_stream_number)
            if object_stream is None:
                return PdfNull()

            stream_data = object_stream.stream_data
            parser = Parser(stream_data)
            for i in range(0, entry.object_stream_index - 1):
                parser.next()

            return parser.next()

        self.parser.seek(entry.byte_offset)
        obj = self.parser.next()
        if obj is None:
            return PdfNull()

        return obj.value

    def get_object_by_byte_offset(self, byte_offset: int) -> PdfDirectObject:
        """returns an object by byte offset"""
        self.parser.seek(byte_offset)
        obj = self.parser.next()
        if obj is None:
            return PdfNull()

        return obj.value

    def __load(self) -> None:
        self.__load_header()
        self.__load_xrt_sections_and_trailers()
        self.__load_body()

    def __load_header(self):
        logger.debug("__load_header")
        self.parser.seek(0)
        self[PdfName("header")] = Header.load(self.parser)

    def __load_xrt_sections_and_trailers(self):
        logger.debug("__load_xrt_sections_and_trailers")
        self[PdfName("xrt")] = CrossReferenceTable()
        xrt_section_byte_offset = self.__get_last_startxref_byte_offset()
        logger.debug(
            "last xrt section offset: 0x%x (%d)",
            xrt_section_byte_offset,
            xrt_section_byte_offset,
        )
        trailer = None
        last_trailer = None
        while True:
            self.parser.seek(xrt_section_byte_offset)
            trailer_dictionary, xrt_section = CrossReferenceTableSection.load(
                self.parser
            )
            self.xrt.append(xrt_section)
            if trailer_dictionary is None:
                while True:
                    trailer_keyword = self.parser.next_line()
                    if trailer_keyword is None:
                        raise PdfConformanceException("no trailer keyword found")

                    if trailer_keyword == b"trailer":
                        break

                trailer_dictionary = self.parser.next()
                if not isinstance(trailer_dictionary, PdfDictionary):
                    raise PdfConformanceException("trailer is not a dictionary")

            trailer = Trailer(trailer_dictionary, xrt_section_byte_offset)
            if self.trailer is None:
                self[PdfName("trailer")] = trailer

            logger.debug(
                "xrt section offset: 0x%x (%d)",
                xrt_section_byte_offset,
                xrt_section_byte_offset,
            )
            if last_trailer is None:
                last_trailer = trailer

            else:
                last_trailer.prev = trailer
                last_trailer = trailer

            xrt_section_byte_offset = trailer_dictionary.get(PdfName("Prev"), None)
            if xrt_section_byte_offset is None:
                break

            xrt_section_byte_offset = xrt_section_byte_offset.p

    def __get_last_startxref_byte_offset(self) -> int:
        self.parser.seek(self.parser.size() - 1)
        pos = self.parser.tell()
        while True:
            self.parser.seek_to_start_of_line()
            pos = self.parser.tell()
            line = self.parser.next_line()
            if line == b"startxref":
                offset_line = self.parser.next_line()
                if offset_line is None:
                    raise PdfConformanceException("startxref offset not found")

                offset_line = offset_line.decode("ascii", "replace")
                if Document.__trailer_offset_re.match(offset_line) is None:
                    raise PdfConformanceException("startxref offset is not a number ?")

                return int(offset_line)

            if pos == 0:
                break

            self.parser.seek(pos - 1)

        raise PdfConformanceException("startxref not found")

    def __load_body(self):
        logger.debug("__load_body")
        assert self.xrt is not None
        self[PdfName("body")] = Body()
        self[PdfName("objects")] = Objects()
        num_xrt_entries = 0
        for xrt_section in self.xrt:
            current_body = PdfDictionary()
            self.body.append(current_body)
            for xrt_subsection in xrt_section:
                for xrt_entry in xrt_subsection.entries:
                    num_xrt_entries = num_xrt_entries + 1
                    if xrt_entry.is_free:
                        continue

                    obj = self.get_object_by_number(xrt_entry.object_number,
                                                    xrt_entry.generation_number)
                    obj_id = f"{xrt_entry.object_number}.{xrt_entry.generation_number}"
                    obj_key = PdfName(obj_id)
                    current_body[obj_key] = obj
                    if obj_key not in self.objects:
                        self.objects[obj_key] = obj

        logger.info("%d xrt entries.", num_xrt_entries)
        logger.info("%d objects loaded.", len(self.body))
