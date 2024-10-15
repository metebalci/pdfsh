# Copyright (C) 2024 Mete Balci
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
objects
"""

import base64
from collections.abc import MutableMapping, MutableSequence
import functools
import logging
from typing import Any, Dict, List, Optional
import zlib

from .exceptions import NotSupportedException, PossibleBugException
from pdfsh.pdfminer import ccitt
from pdfsh.pdfminer import lzw
from pdfsh.pdfminer.utils import apply_png_predictor


logger = logging.getLogger(__name__)


# pylint: disable=too-few-public-methods
class PdfObject:
    """base class for all Pdf object types"""


# ISO 32000-2:2020
# There are nine "Objects" defined in PDF
# booleans, integers, real numbers, strings, names, arrays, dictionaries,
# streams and null
# indirect reference seems to be not considered an object
# but it can be stored in arrays and dictionaries ?!

# below I call these pdf objects subclasses of PdfDirectObject
# PdfIndirectObject is a wrapper of a PdfDirectObject with object number and
# generation number. The PdfDirectObject is stored in self.value attribute.

# Object Comparison of PdfDirectObjects are done according to Annex J


# in all PdfDirectObject subclasses
# self.p holds the Python representation of PdfDirectObject
# self.p can be: bool, int, float, bytes, list, dict, None
# pylint: disable=too-few-public-methods
class PdfDirectObject(PdfObject):
    """PdfDirectObject"""


# PDF: true or false
# Python: bool
class PdfBoolean(PdfDirectObject):
    """PdfBoolean"""

    def __init__(self, value) -> None:
        assert isinstance(value, bool), value
        self.p = value

    def __str__(self) -> str:
        return "True" if self.p else "False"

    def __repr__(self) -> str:
        return str(self)

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, PdfBoolean):
            return self.p == other.p

        return NotImplemented

    def __hash__(self) -> int:
        return hash(self.p)


# Integer or Real
# pylint: disable=too-few-public-methods
class PdfNumber(PdfDirectObject):
    """base class for Pdf number types"""


# PDF: 123
# Python: int
class PdfIntegerNumber(PdfNumber):
    """PdfIntegerNumber"""

    def __init__(self, value) -> None:
        assert isinstance(value, int), value
        self.p = value

    def __str__(self) -> str:
        return f"{self.p}"

    def __repr__(self) -> str:
        return str(self)

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, PdfIntegerNumber):
            return self.p == other.p

        if isinstance(other, PdfRealNumber):
            return float(self.p) == other.p

        return NotImplemented

    def __hash__(self) -> int:
        return hash(self.p)


# PDF: 34.5
# Python: float
class PdfRealNumber(PdfNumber):
    """PdfRealNumber"""

    def __init__(self, value) -> None:
        assert isinstance(value, float), value
        self.p = value

    def __str__(self) -> str:
        return f"{self.p}"

    def __repr__(self) -> str:
        return str(self)

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, PdfIntegerNumber):
            return self.p == float(other.p)

        if isinstance(other, PdfRealNumber):
            return self.p == other.p

        return NotImplemented

    def __hash__(self) -> int:
        return hash(self.p)


# Literal or Hexadecimal
class PdfString(PdfDirectObject):
    """base class for Pdf string types"""

    def __init__(self, value: bytes) -> None:
        self.p = value

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, (PdfLiteralString, PdfHexadecimalString)):
            return self.p == other.p

        return NotImplemented

    def __hash__(self) -> int:
        return hash(self.p)


# PDF: (This is a string)
# Python: bytes
class PdfLiteralString(PdfString):
    """PdfLiteralString"""

    def __init__(self, value: bytes | str) -> None:
        if isinstance(value, str):
            value = value.encode("utf-8")
        assert isinstance(value, bytes), value
        super(PdfLiteralString, self).__init__(value)

    def __str__(self) -> str:
        try:
            return f"{self.p.decode('utf-8')}"
        except UnicodeError:
            s = []
            for b in self.p:
                if 0x20 <= b <= 0x7E:
                    s.append(chr(b))

                else:
                    s.append(f"\\x{b:%02x}")

            return f"{''.join(s)}"

    def __repr__(self) -> str:
        return str(self)


# PDF: <4E6F762073686D6F7A206B6120706F702E>
# Python: bytes
class PdfHexadecimalString(PdfString):
    """PdfHexadecimalString"""

    def __init__(self, value: bytes) -> None:
        assert isinstance(value, bytes), value
        super(PdfHexadecimalString, self).__init__(value)

    def __str__(self) -> str:
        if len(self.p) <= 16:
            return f"<{self.p.hex()}>"

        return f"<{self.p[0:16].hex()}... (len={len(self.p)})>"

    def __repr__(self) -> str:
        return f"<{self.p.hex()}>"


# PDF: /Name1
# Python: bytes (without / symbol)
@functools.total_ordering
class PdfName(PdfDirectObject):
    """PdfName"""

    def __init__(self, value: str | bytes) -> None:
        if isinstance(value, str):
            value = value.encode("ascii")
        assert isinstance(value, bytes), value
        self.p = value

    def __str__(self) -> str:
        s = "/"
        for b in self.p:
            if b == ord("#"):
                s = f"{s}#23"

            elif 0x20 <= b <= 0x7E:
                s = f"{s}{chr(b)}"

            else:
                s = f"{s}#{b}"

        return s

    def __repr__(self) -> str:
        return str(self)

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, PdfName):
            return str(self) == str(other)

        return NotImplemented

    def __hash__(self) -> int:
        return hash(str(self))

    def __lt__(self, other) -> int:
        if isinstance(other, PdfName):
            return str(self) < str(other)

        return NotImplemented


# PDF: [549 3.14 false (Ralph) /SomeName]
# Python: array of PdfDirectObject entries
class PdfArray(MutableSequence[PdfDirectObject], PdfDirectObject):
    """PdfArray"""

    def __init__(self) -> None:
        self.p = []

    def __str__(self) -> str:
        return str(self.p)

    def __repr__(self) -> str:
        return repr(self.p)

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, PdfArray):
            return self.p == other.p

        return NotImplemented

    def __hash__(self) -> int:
        return hash(self.p)

    def __getitem__(self, idx: int) -> PdfDirectObject:
        return self.p[idx]

    def __setitem__(self, idx: int, value: PdfDirectObject) -> None:
        self.p[idx] = value

    def __delitem__(self, idx: int) -> None:
        del self.p[idx]

    def __len__(self) -> int:
        return len(self.p)

    def insert(self, index: int, value: PdfDirectObject) -> None:
        self.p.insert(index, value)


# PDF: <</Key Value>>
# Python: dict of (PdfName, PdfDirectObject) entries
class PdfDictionary(MutableMapping[PdfName, PdfDirectObject], PdfDirectObject):
    """PdfDictionary"""

    def __init__(self) -> None:
        self.p = {}

    def __str__(self) -> str:
        return str(self.p)

    def __repr__(self) -> str:
        return repr(self.p)

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, PdfDictionary):
            return self.p == other.p

        return NotImplemented

    def __hash__(self) -> int:
        return hash(self.p)

    def __getitem__(self, key: PdfName) -> PdfDirectObject:
        if not isinstance(key, PdfName):
            raise PossibleBugException()

        return self.p[key]

    def __setitem__(self, key: PdfName, value: PdfDirectObject):
        if not isinstance(key, PdfName):
            raise PossibleBugException()

        self.p[key] = value

    def __delitem__(self, key: PdfName):
        if not isinstance(key, PdfName):
            raise PossibleBugException()

        del self.p[key]

    def __iter__(self):
        return iter(self.p)

    def __len__(self) -> int:
        return len(self.p)


# PDF:
# << dictionary >>
# stream
# ... bytes ...
# endstream
# Python: bytes
class PdfStream(PdfDirectObject):
    """PdfStream"""

    def __init__(self, stream_dictionary: PdfDictionary, stream_data: bytes):
        self.stream_dictionary = stream_dictionary
        self.encoded_stream_data = stream_data
        self.stream_data = PdfStream.__decode_encoded_stream(
            stream_dictionary, stream_data
        )

    def __str__(self) -> str:
        if self.stream_data is None:
            return "stream[None]"

        return f"stream[{len(self.stream_data)}]"

    def __repr__(self) -> str:
        return str(self)

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, PdfStream):
            return (self.stream_dictionary == other.stream_dictionary) and (
                self.encoded_stream_data == other.encoded_stream_data
            )

        return NotImplemented

    def __hash__(self) -> int:
        return hash((self.stream_dictionary, self.encoded_stream_data))

    # pylint: disable=too-many-branches
    @staticmethod
    def __decode_encoded_stream(
        stream_dictionary: PdfDictionary, stream_data: bytes
    ) -> bytes:
        stream_filter = stream_dictionary.get(PdfName("Filter"), None)
        decode_parms = stream_dictionary.get(PdfName("DecodeParms"), None)
        # stream_filters will contain PdfName's of filters
        stream_filters: List[PdfName] = []
        # decode_params_list will contain decode_params for each filter
        # in stream_filters
        # it will be an empty dictionary
        decode_params_list: List[Dict[PdfName, PdfDirectObject]] = []
        if stream_filter is not None:
            if isinstance(stream_filter, PdfName):
                stream_filters.append(stream_filter)
                if decode_parms is None:
                    decode_params_list.append({})

                else:
                    # .p to get python dict from PdfDictionary
                    decode_params_list.append(decode_parms.p)

            elif isinstance(stream_filter, PdfArray):
                for i, stream_filter_element in enumerate(stream_filter):
                    assert isinstance(
                        stream_filter_element, PdfName
                    ), "stream filter array should contain PdfName entries"
                    stream_filters.append(stream_filter_element)
                    if decode_parms is None:
                        decode_params_list.append({})

                    else:
                        # .p to get python dict from PdfDictionary
                        decode_params_list.append(decode_parms[i].p)

                assert False, "stream filter should be PdfName or PdfArray"

        if len(stream_filters) == 0:
            logger.debug("stream without any filter")
            return stream_data

        for i, stream_filter in enumerate(stream_filters):
            decode_params = decode_params_list[i]
            logger.debug("part %d/%d", i + 1, len(stream_filters))
            logger.debug("stream_filter=%s", str(stream_filter))
            logger.debug("decode_params=%s", str(decode_params))
            # all stream filters defined in ISO 32000-2
            if stream_filter == PdfName("ASCIIHexDecode"):
                # pylint: disable=fixme
                # TODO: should append 0 if len(stream_data) is odd
                return base64.b16decode(stream_data)

            if stream_filter == PdfName("ASCII85Decode"):
                return base64.a85decode(stream_data, adobe=True)

            # 7.4.4.4 LZW and Flate predictor functions
            # Table 10 (Predictor Value - Meaning)
            #  1: No prediction (default value, only the algorithm lzw or zlib)
            #  2: TIFF Predictor 2
            # 10: PNG prediction (on encoding, PNG None on all rows)
            # 11: PNG prediction (on encoding, PNG Sub on all rows)
            # 12: PNG prediction (on encoding, PNG Up on all rows)
            # 13: PNG prediction (on encoding, PNG Average on all rows)
            # 14: PNG prediction (on encoding, PNG Paeth on all rows)
            # 15: PNG prediction (on encoding, PNG optimum)

            def reverse_predictor(data, predictor):
                if predictor == 1:
                    return data

                if 10 <= predictor <= 15:
                    colors = decode_params.get(PdfName("Colors"), PdfIntegerNumber(1))
                    columns = decode_params.get(PdfName("Columns"), PdfIntegerNumber(1))
                    bits_per_component = decode_params.get(
                        PdfName("BitsPerComponent"), PdfIntegerNumber(8)
                    )
                    return apply_png_predictor(
                        predictor, colors.p, columns.p, bits_per_component.p, data
                    )

                raise UnsupportedException(f"predictor={predictor} not supported")

            if stream_filter == PdfName("LZWDecode"):
                predictor = decode_params.get(PdfName("Predictor"), PdfIntegerNumber(1))
                return reverse_predictor(lzw.lzwdecode(stream_data), predictor.p)

            if stream_filter == PdfName("FlateDecode"):
                predictor = decode_params.get(PdfName("Predictor"), PdfIntegerNumber(1))
                return reverse_predictor(zlib.decompress(stream_data), predictor.p)

            if stream_filter == PdfName("CCITTFaxDecode"):
                assert (
                    False
                ), f"stream filter {stream_filter.decode('ascii')} not implemented yet"
                # default values below are taken from PDF spec
                params = {
                    "K": decode_params.get(PdfName("K"), PdfIntegerNumber(0)),
                    "Columns": decode_params.get(
                        PdfName("Columns"), PdfIntegerNumber(1728)
                    ),
                    "EncodedByteAlign": decode_params.get(
                        PdfName("EncodedByteAlign"), "false"
                    )
                    == "true",
                    "BlackIs1": decode_params.get(PdfName("BlackIs1"), "false")
                    == "true",
                }
                return ccitt.ccittfaxdecode(stream_data, params)

            if stream_filter in (
                b"RunLengthDecode",
                b"JBIG2Decode",
                b"DCTDecode",
                b"JPXDecode",
                b"Crypt",
            ):
                raise NotSupportedException(
                    f"stream filter {stream_filter.decode('ascii')} not implemented yet"
                )

            raise NotSupportedException(
                f"unknown stream filter {stream_filter.decode('ascii', 'replace')}"
            )


# PDF: null
# Python: None
class PdfNull(PdfDirectObject):
    """PdfNull"""

    def __init__(self) -> None:
        self.p = None

    def __str__(self) -> str:
        return "null"

    def __repr__(self) -> str:
        return str(self)

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, PdfNull):
            return True

        return NotImplemented

    def __hash__(self) -> int:
        return hash(self.p)


# not sure if this is explicitly called a Pdf Object
# but it is used as values in Dictionary etc., so it has to be a Pdf Object
# PDF: 12 0 R
# Python: tuple (object_number, generation_number)
class PdfIndirectReference(PdfDirectObject):
    """PdfIndirectReference"""

    def __init__(self, object_number: int, generation_number: int):
        self.object_number = object_number
        self.generation_number = generation_number

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, PdfIndirectReference):
            return (
                self.object_number == other.object_number
                and self.generation_number == other.generation_number
            )

        return NotImplemented

    def __hash__(self) -> int:
        return hash((self.object_number, self.generation_number))

    def __str__(self) -> str:
        return f"({self.object_number}, {self.generation_number}, R)"

    def __repr__(self) -> str:
        return str(self)


# PdfIndirectObject is just wrapping a PdfDirectObject
# giving it an object number and generation number
# PDF:
# 12 0 obj
# (Brillig)
# endobj
# Python: tuple (object_number, generation_number, PdfDirectObject)
class PdfIndirectObject:
    """PdfIndirectObject"""

    def __init__(
        self, object_number: int, generation_number: int, value: PdfDirectObject
    ):
        self.object_number = object_number
        self.generation_number = generation_number
        self.value = value

    def __eq__(self, other: Any) -> bool:
        if isinstance(self, PdfIndirectObject):
            return (
                (self.object_number == other.object_number)
                and (self.generation_number == other.generation_number)
                and (self.value == other.value)
            )

        return NotImplemented

    def __hash__(self) -> int:
        return hash((self.object_number, self.generation_number, self.value))

    def __str__(self) -> str:
        return f"({self.object_number}, \
                 {self.generation_number}, \
                 {self.value.__class__.__name__})"

    def __repr__(self) -> str:
        return str(self)

    def indirect_reference(self):
        """returns indirect reference to this object"""
        return PdfIndirectReference(self.object_number, self.generation_number)
