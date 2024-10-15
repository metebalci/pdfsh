# Copyright (C) 2024 Mete Balci
#
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
import re
from typing import List

from .exceptions import PdfConformanceException
from .parser import Parser
from .objects import PdfName, PdfBoolean
from .objects import PdfIntegerNumber
from .objects import PdfArray, PdfDictionary, PdfStream, PdfIndirectObject


logger = logging.getLogger(__name__)


class CrossReferenceTableEntry(PdfDictionary):

    entry_re = re.compile(r"^[0-9]{10} [0-9]{5} [fn][ ]?$")

    # ISO 32000-2 7.5.4: Cross-reference table
    # xref entry has a fixed format
    # nnnnnnnnnn ggggg fEOL
    # EOL is one of SP CR, SP LF, CR LF
    @staticmethod
    def load_from_xref_table(parser: Parser, object_number: int):
        line = parser.next_line().decode("ascii", "replace")
        if CrossReferenceTableEntry.entry_re.match(line) is None:
            raise PdfConformanceException(f"invalid CrossReferenceTableEntry: {line}")
        return CrossReferenceTableEntryUncompressed(
            object_number, int(line[0:10]), int(line[11:16]), line[17:18] == "f"
        )

    @staticmethod
    def load_from_xref_stream(object_number: int, fields: List[bytes]):
        def __bytes2int(b: bytes):
            v = 0
            factor = 1
            for e in reversed(b):
                v = v + e * factor
                factor = factor * 256
            return v

        entry_type = 0
        if len(fields[0]) == 0:
            entry_type = 1

        else:
            entry_type = __bytes2int(fields[0])

        if entry_type == 0:
            object_number_of_next_free_object = __bytes2int(fields[1])
            generation_number = 0
            if len(fields[2]) > 0:
                generation_number = __bytes2int(fields[2])

            return CrossReferenceTableEntryUncompressed(
                object_number,
                object_number_of_next_free_object,
                generation_number,
                True,
            )

        if entry_type == 1:
            byte_offset = 0
            generation_number = 0
            if len(fields[1]) > 0:
                byte_offset = __bytes2int(fields[1])

            if len(fields[2]) > 0:
                generation_number = __bytes2int(fields[2])

            return CrossReferenceTableEntryUncompressed(
                object_number,
                byte_offset,
                generation_number,
                False,
            )

        if entry_type == 2:

            object_stream_number = __bytes2int(fields[1])
            object_stream_index = __bytes2int(fields[2])

            return CrossReferenceTableEntryCompressed(
                object_number,
                object_stream_number,
                object_stream_index,
            )

        raise PdfConformanceException(f"unknown xref stream entry type={entry_type}")

    def __init__(
        self,
        is_compressed: bool,
        object_number: int,
        generation_number: int,
        is_free: bool,
    ):
        super().__init__()
        self[PdfName("is_compressed")] = PdfBoolean(is_compressed)
        self[PdfName("object_number")] = PdfIntegerNumber(object_number)
        self[PdfName("generation_number")] = PdfIntegerNumber(generation_number)
        self[PdfName("is_free")] = PdfBoolean(is_free)

    @property
    def is_compressed(self):
        return self[PdfName("is_compressed")].p

    @property
    def object_number(self):
        return self[PdfName("object_number")].p

    @property
    def generation_number(self):
        return self[PdfName("generation_number")].p

    @property
    def is_free(self):
        return self[PdfName("is_free")].p

    @property
    def is_in_use(self):
        return not self.is_free

    def __repr__(self):
        return str(self)

    def __hash__(self):
        return hash(f"{self.object_number}.{self.generation_number}")

    def __eq__(self, other):
        if isinstance(other, CrossReferenceTableEntry):
            return (self.object_number == other.object_number) and (
                self.generation_number == other.generation_number
            )

        return NotImplemented


class CrossReferenceTableEntryUncompressed(CrossReferenceTableEntry):

    def __init__(
        self,
        object_number: int,
        byte_offset: int,
        generation_number: int,
        is_free: bool,
    ):
        super().__init__(False, object_number, generation_number, is_free)

        self[PdfName("byte_offset")] = PdfIntegerNumber(byte_offset)

    @property
    def byte_offset(self):
        return self[PdfName("byte_offset")].p

    def __str__(self):
        flag = "f" if self.is_free else "n"
        return f"{self.byte_offset:010d} {self.generation_number:05d} {flag}"


class CrossReferenceTableEntryCompressed(CrossReferenceTableEntry):

    def __init__(
        self, object_number: int, object_stream_number: int, object_stream_index: int
    ):
        # compressed objects always have generation number = 0
        # and they are always used, never free
        super().__init__(True, object_number, 0, False)

        self[PdfName("object_stream_number")] = PdfIntegerNumber(object_stream_number)
        self[PdfName("object_stream_index")] = PdfIntegerNumber(object_stream_index)

    @property
    def object_stream_number(self):
        return self[PdfName("object_stream_number")].p

    @property
    def object_stream_index(self):
        return self[PdfName("object_stream_index")].p

    def __str__(self):
        return f"{self.object_stream_index}@{self.object_stream_number}"


class CrossReferenceTableSubsection(PdfDictionary):

    subsection_re = re.compile(r"^[0-9]+ [0-9]+$")

    # ISO 32000-2 7.5.4: Cross-reference table
    # first_obj_num num_entries
    # xref_entries* (see _read_xref_entry)
    @staticmethod
    def load_from_xref_table(parser: Parser):
        saved_pos = parser.tell()
        line = parser.next_line().decode("ascii", "replace")
        if CrossReferenceTableSubsection.subsection_re.match(line) is None:
            parser.seek(saved_pos)
            return None
        words = line.split(" ")
        first_object_number = int(words[0])
        number_of_entries = int(words[1])
        logger.debug("xref.first_obj_num: %d", first_object_number)
        logger.debug("xref.num_entries: %d", number_of_entries)
        if number_of_entries == 0:
            raise PdfConformanceException(
                "Cross-reference table subsection number of entries cannot be 0"
            )
        xrt_subsection = CrossReferenceTableSubsection(first_object_number)
        for object_number in range(
            first_object_number, first_object_number + number_of_entries
        ):
            xrt_entry = CrossReferenceTableEntry.load_from_xref_table(
                parser, object_number
            )
            logger.debug("xrt_entry (table)=%s", xrt_entry)
            xrt_subsection.append_entry(xrt_entry)
        return xrt_subsection

    @staticmethod
    def load_from_xref_stream(
        first_object_number: int,
        number_of_entries: int,
        w: List[int],
        stream_data: bytes,
    ):
        xrt_subsection = CrossReferenceTableSubsection(first_object_number)
        xrt_subsection_entries = xrt_subsection[PdfName("entries")]
        offset = 0
        for i in range(0, number_of_entries):
            object_number = first_object_number + i
            fields = []
            for field_size in w:
                field_data = stream_data[offset : offset + field_size]
                fields.append(field_data)
                offset = offset + field_size

            logger.debug(
                "loading obj=%d/%d from fields=%s",
                object_number,
                first_object_number + number_of_entries,
                fields,
            )
            xrt_entry = CrossReferenceTableEntry.load_from_xref_stream(
                object_number, fields
            )
            logger.debug("xrt_entry (stream)=%s", xrt_entry)
            xrt_subsection_entries.append(xrt_entry)

        return xrt_subsection

    def __init__(self, first_object_number: int):
        super().__init__()
        self[PdfName("first_object_number")] = PdfIntegerNumber(first_object_number)
        self[PdfName("entries")] = PdfArray()

    @property
    def first_object_number(self):
        return self[PdfName("first_object_number")].p

    @property
    def entries(self):
        return self[PdfName("entries")]

    def append_entry(self, entry):
        self.entries.append(entry)

    def get_number_of_entries(self):
        return len(self.entries)


class CrossReferenceTableSection(PdfArray):
    """
    CrossReferenceTableSection is a PdfArray holding CrossReferenceTableSubsection(s).
    A section can be a cross-reference table or a cross-reference stream.
    """

    __directobject_re = re.compile(r"^[0-9]+ [0-9]+ obj$")

    # ISO 32000-2 7.5.4: Cross-reference table
    # ISO 32000-2 7.5.8: Cross-reference streams
    @staticmethod
    def load(parser: Parser):
        pos = parser.tell()
        line = parser.next_line()
        logger.debug("line: %s", line)
        # if startxref points to a `xref` line, it is a table
        if line == b"xref":
            logger.debug("xref as table")
            return None, CrossReferenceTableSection.__load_from_xref_table(parser)

        # if startxref points to an indirect object, which contains a stream
        # whose type is XRef, then it is a stream
        parser.seek(pos)
        obj = parser.next()
        if isinstance(obj, PdfIndirectObject):
            if isinstance(obj.value, PdfStream):
                if obj.value.stream_dictionary[PdfName("Type")] == PdfName("XRef"):
                    logger.debug("xref as stream")
                    return (
                        obj.value.stream_dictionary,
                        CrossReferenceTableSection.__load_from_xref_stream(obj.value),
                    )

                raise PdfConformanceException(
                    "startxref points to a stream but its Type is not XRef"
                )

            raise PdfConformanceException(
                "startxref points to an indirect object but it is not a stream"
            )

        raise PdfConformanceException(
            "startxref does not point to an xref or to an indirect object"
        )

    @staticmethod
    def __load_from_xref_table(parser: Parser):
        xrt_section = CrossReferenceTableSection()
        logger.debug("loading xrt_subsections from xref table...")
        while True:
            xrt_subsection = CrossReferenceTableSubsection.load_from_xref_table(parser)
            if xrt_subsection is None:
                logger.debug("xrt_subsections loaded.")
                break

            logger.debug("xrt_subsection: %s", xrt_subsection)
            xrt_section.append(xrt_subsection)

        return xrt_section

    @staticmethod
    def __load_from_xref_stream(stream: PdfStream):
        xrt_section = CrossReferenceTableSection()
        logger.debug("loading xrt_subsections from xref stream...")
        logger.debug("xref_stream dictionary: %s", stream.stream_dictionary)
        size = stream.stream_dictionary[PdfName("Size")]
        assert isinstance(size, PdfIntegerNumber)
        index = stream.stream_dictionary.get(PdfName("Index"), None)
        # the default of Index is [0 Size]
        if index is None:
            index = PdfArray()
            index.append(PdfIntegerNumber(0))
            index.append(size)

        # make index a List[int]
        index = list(map(lambda x: x.p, index))
        assert (len(index) % 2) == 0
        w = stream.stream_dictionary[PdfName("W")]
        assert isinstance(w, PdfArray)
        # make w a List[int]
        w = list(map(lambda x: x.p, w))

        size_of_one_entry = 0
        for single_w in w:
            size_of_one_entry = size_of_one_entry + single_w

        index_offset = 0
        stream_data_offset = 0
        logger.debug("stream_data: %s", stream.stream_data)
        while index_offset < len(index):
            first_object_number = index[index_offset]
            number_of_entries = index[index_offset + 1]
            logger.debug(
                "xref subsection %d %d", first_object_number, number_of_entries
            )
            index_offset = index_offset + 2
            next_stream_data_offset = (
                stream_data_offset + size_of_one_entry * number_of_entries
            )
            xrt_subsection = CrossReferenceTableSubsection.load_from_xref_stream(
                first_object_number,
                number_of_entries,
                w,
                stream.stream_data[stream_data_offset:next_stream_data_offset],
            )
            xrt_section.append(xrt_subsection)
            stream_data_offset = next_stream_data_offset

        return xrt_section

    def get_number_of_entries(self):
        cnt = 0
        for subsection in self:
            cnt = cnt + subsection.get_number_of_entries()
        return cnt


class CrossReferenceTable(PdfArray):
    """
    CrossReferenceTable is a PdfArray holding CrossReferenceTableSection(s).
    """

    def find_entry(self, object_number, generation_number=0):
        for section in self:
            for subsection in section:
                for entry in subsection.entries:
                    if (
                        entry.object_number == object_number
                        and entry.generation_number == generation_number
                    ):
                        return entry

        return None

    def get_number_of_entries(self):
        cnt = 0
        for section in self:
            cnt = cnt + section.get_number_of_entries()
        return cnt
