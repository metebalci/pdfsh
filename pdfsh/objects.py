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

import base64
from collections.abc import MutableMapping, MutableSequence
import functools
import logging
from typing import Any
import zlib

from .exceptions import *

from pdfminer import ccitt
from pdfminer import lzw

logger = logging.getLogger(__name__)

class PdfObject:
    pass

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
class PdfDirectObject(PdfObject):
    pass

# PDF: true or false
# Python: bool
class PdfBoolean(PdfDirectObject):

    def __init__(self, value) -> None:
        assert isinstance(value, bool), value
        self.p = value

    def __str__(self) -> str:
        return 'True' if self.p else 'False'

    def __repr__(self) -> str:
        return str(self)

    def __eq__(self, other:Any) -> bool:
        if isinstance(other, PdfBoolean):
            return self.p == other.p
        else:
            return NotImplemented

    def __hash__(self) -> int:
        return hash(self.p)

# Integer or Real
class PdfNumber(PdfDirectObject):
    pass

# PDF: 123
# Python: int
class PdfIntegerNumber(PdfNumber):

    def __init__(self, value) -> None:
        assert isinstance(value, int), value
        self.p = value

    def __str__(self) -> str:
        return '%d' % self.p

    def __repr__(self) -> str:
        return str(self)

    def __eq__(self, other:Any) -> bool:
        if isinstance(other, PdfIntegerNumber):
            return self.p == other.p
        elif isinstance(other, PdfRealNumber):
            return float(self.p) == other.p
        else:
            return NotImplemented

    def __hash__(self) -> int:
        return hash(self.p)

# PDF: 34.5
# Python: float
class PdfRealNumber(PdfNumber):

    def __init__(self, value) -> None:
        assert isinstance(value, float), value
        self.p = value

    def __str__(self) -> str:
        return '%g' % self.p

    def __repr__(self) -> str:
        return str(self)

    def __eq__(self, other:Any) -> bool:
        if isinstance(other, PdfIntegerNumber):
            return self.p == float(other.p)
        elif isinstance(other, PdfRealNumber):
            return self.p == other.p
        else:
            return NotImplemented

    def __hash__(self) -> int:
        return hash(self.p)

# Literal or Hexadecimal
class PdfString(PdfDirectObject):

    def __eq__(self, other:Any) -> bool:
        if (isinstance(other, PdfLiteralString) or
            isinstance(other, PdfHexadecimalString)):
            return self.p == other.p
        else:
            return NotImplemented

    def __hash__(self) -> int:
        return hash(self.p)

# PDF: (This is a string)
# Python: bytes
class PdfLiteralString(PdfString):

    def __init__(self, value:bytes | str) -> None:
        if isinstance(value, str):
            value = value.encode('utf-8')
        assert isinstance(value, bytes), value
        self.p = value

    def __str__(self) -> str:
        try:
            return '(%s)' % self.p.decode('utf-8')
        except UnicodeError:
            s = []
            for b in self.p:
                if (b >= 0x20) and (b <= 0x7E):
                    s.append(chr(b))
                else:
                    s.append('\\x%02x' % b)
            return '(%s)' % ''.join(s)

    def __repr__(self) -> str:
        return str(self)

# PDF: <4E6F762073686D6F7A206B6120706F702E>
# Python: bytes
class PdfHexadecimalString(PdfString):

    def __init__(self, value:bytes) -> None:
        assert isinstance(value, bytes), value
        self.p = value

    def __str__(self) -> str:
        if len(self.p) <= 16:
            return '<%s>' % self.p.hex()
        else:
            return '<%s... (len=%d)>' % (self.p[0:16].hex(), len(self.p))

    def __repr__(self) -> str:
        return '<%s>' % self.p.hex()

# PDF: /Name1
# Python: bytes (without / symbol)
@functools.total_ordering
class PdfName(PdfDirectObject):

    def __init__(self, value:str | bytes) -> None:
        if isinstance(value, str):
            value = value.encode('ascii')
        assert isinstance(value, bytes), value
        self.p = value

    def __str__(self) -> str:
        s = '/'
        for b in self.p:
            if b == ord('#'):
                s = '%s#23' % s
            elif (b >= 0x20) and (b <= 0x7E):
                s = '%s%s' % (s, chr(b))
            else:
                s = '%s#%d' % (s, b)
        return s

    def __repr__(self) -> str:
        return str(self)

    def __eq__(self, other:Any) -> bool:
        if isinstance(other, PdfName):
            return str(self) == str(other)
        else:
            return NotImplemented

    def __hash__(self) -> int:
        return hash(str(self))

    def __lt__(self, other) -> int:
        if isinstance(other, PdfName):
            return str(self) < str(other)
        else:
            return NotImplemented

# PDF: [549 3.14 false (Ralph) /SomeName]
# Python: array of PdfDirectObject entries
class PdfArray(MutableSequence[PdfDirectObject],
               PdfDirectObject):

    def __init__(self) -> None:
        self.p = []

    def __str__(self) -> str:
        return str(self.p)

    def __repr__(self) -> str:
        return repr(self.p)

    def __eq__(self, other:Any) -> bool:
        if isinstance(other, PdfArray):
            return self.p == other.p
        else:
            return NotImplemented

    def __hash__(self) -> int:
        return hash(self.p)

    def __getitem__(self, idx:int) -> PdfDirectObject:
        return self.p[idx]

    def __setitem__(self, idx:int, value:PdfDirectObject) -> None:
        self.p[idx] = value

    def __delitem__(self, idx:int) -> None:
        del self.p[idx]

    def __len__(self) -> int:
        return len(self.p)

    def insert(self, idx:int, value:PdfDirectObject) -> None:
        self.p.insert(idx, value)

# PDF: <</Key Value>>
# Python: dict of (PdfName, PdfDirectObject) entries
class PdfDictionary(MutableMapping[PdfName, PdfDirectObject],
                    PdfDirectObject):

    def __init__(self) -> None:
        self.p = {}

    def __str__(self) -> str:
        return str(self.p)

    def __repr__(self) -> str:
        return repr(self.p)

    def __eq__(self, other:Any) -> bool:
        if isinstance(other, PdfDictionary):
            return self.p == other.p
        else:
            return NotImplemented

    def __hash__(self) -> int:
        return hash(self.p)

    def __getitem__(self, key:PdfName) -> PdfDirectObject:
        if not isinstance(key, PdfName):
            raise PossibleBugException()
        return self.p[key]

    def __setitem__(self, key:PdfName, value:PdfDirectObject):
        if not isinstance(key, PdfName):
            raise PossibleBugException()
        self.p[key] = value

    def __delitem__(self, key:PdfName):
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

    def __init__(self,
                 stream_dictionary:PdfDictionary,
                 stream_data:bytes):
        self.stream_dictionary = stream_dictionary
        self.encoded_stream_data = stream_data
        self.stream_data = PdfStream.__decode_encoded_stream(stream_dictionary,
                                                             stream_data)

    def __str__(self) -> str:
        if self.stream_data is None:
            return 'stream[None]'
        else:
            return 'stream[%d]' % len(self.stream_data)

    def __repr__(self) -> str:
        return str(self)

    def __eq__(self, other:Any) -> bool:
        if isinstance(other, PdfStream):
            return ((self.stream_dictionary == other.stream_dictionary) and
                    (self.encoded_stream_data == other.encoded_stream_data))
        else:
            return NotImplemented

    def __hash__(self) -> int:
        return hash((self.stream_dictionary, self.encoded_stream_data))

    @staticmethod
    def __decode_encoded_stream(stream_dictionary:PdfDictionary,
                                stream_data:bytes) -> bytes:
        stream_filter = stream_dictionary.get(PdfName('Filter'), None)
        decode_parms = stream_dictionary.get(PdfName('DecodeParms'), None)
        stream_filters = []
        decode_params = []
        if stream_filter is not None:
            if isinstance(stream_filter, PdfName):
                stream_filters.append(stream_filter.p)
                if decode_parms is None:
                    decode_params.append({})
                else:
                    decode_params.append(decode_parms.p)

            elif isinstance(stream_filter, PdfArray):
                for i in range(0, len(stream_filter)):
                    assert isinstance(stream_filter[i], PdfName), 'stream filter array should contain PdfName entries'
                    stream_filters.append(stream_filter[i].p)
                    if decode_parms is None:
                        decode_params.append({})
                    else:
                        decode_params.append(decode_parms[i].p.p)
                assert False, 'stream filter should be PdfName or PdfArray'

        if len(stream_filters) == 0:
            logger.debug('stream without any filter')
            return stream_data

        else:
            for i in range(0, len(stream_filters)):
                stream_filter = stream_filters[i]
                decode_param = decode_params[i]
                logger.debug('part %d/%d' % (i, len(stream_filters)))
                logger.debug('stream_filter=%s' % str(stream_filter))
                logger.debug('decode_param=%s' % str(decode_param))
                # all stream filters defined in ISO 32000-2
                if stream_filter == b'ASCIIHexDecode':
                    # TODO: should append 0 if len(stream_data) is odd
                    return base64.b16decode(stream_data)

                elif stream_filter == b'ASCII85Decode':
                    return base64.a85decode(stream_data, adobe=True)

                elif stream_filter == b'LZWDecode':
                    predictor = decode_param.get('Predictor', 1)
                    assert predictor == 1, "FlateDecode.Predictor != 1 but %d" % predictor
                    return lzw.lzwdecode(stream_data)

                elif stream_filter == b'FlateDecode':
                    predictor = decode_param.get('Predictor', 1)
                    assert predictor == 1, "FlateDecode.Predictor != 1 but %d" % predictor
                    return zlib.decompress(stream_data)

                elif stream_filter == b'CCITTFaxDecode':
                    assert False, 'stream filter %s not implemented yet' % stream_filter.decode('ascii')
                    # default values below are taken from PDF spec
                    params = {"K": decode_param.get('K', 0),
                            "Columns": decode_param.get('Columns', 1728) ,
                            "EncodedByteAlign": decode_param.get('EncodedByteAlign', 'false') == 'true',
                            "BlackIs1": decode_param.get('BlackIs1', 'false') == 'true'}
                    return ccitt.ccittfaxdecode(stream_data, params)

                elif (stream_filter == b'RunLengthDecode' or
                    stream_filter == b'JBIG2Decode' or
                    stream_filter == b'DCTDecode' or
                    stream_filter == b'JPXDecode' or
                    stream_filter == b'Crypt'):
                    raise NotSupportedException('stream filter %s not implemented yet' % stream_filter.decode('ascii'))

                else:
                    raise NotSupportedException('unknown stream filter %s' % stream_filter.decode('ascii', 'replace'))

# PDF: null
# Python: None
class PdfNull(PdfDirectObject):

    def __init__(self) -> None:
        self.p = None

    def __str__(self) -> str:
        return 'null'

    def __repr__(self) -> str:
        return str(self)

    def __eq__(self, other:Any) -> bool:
        if isinstance(other, PdfNull):
            return True
        else:
            return NotImplemented

    def __hash__(self) -> int:
        return hash(self.p)

# not sure if this is explicitly called a Pdf Object
# but it is used as values in Dictionary etc., so it has to be a Pdf Object
# PDF: 12 0 R
# Python: tuple (object_number, generation_number)
class PdfIndirectReference(PdfDirectObject):

    def __init__(self,
                 object_number:int,
                 generation_number:int):
        self.object_number = object_number
        self.generation_number = generation_number

    def __eq__(self, other:Any) -> bool:
        if isinstance(other, PdfIndirectReference):
            return (self.object_number == other.object_number and
                    self.generation_number == other.generation_number)
        else:
            return NotImplemented

    def __hash__(self) -> int:
        return hash((self.object_number, self.generation_number))

    def __str__(self) -> str:
        return '(%d, %d, R)' % (self.object_number,
                                self.generation_number)

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

    def __init__(self,
                 object_number:int,
                 generation_number:int,
                 value:PdfDirectObject):
        self.object_number = object_number
        self.generation_number = generation_number
        self.value = value

    def __eq__(self, other:Any) -> bool:
        if isinstance(self, PdfIndirectObject):
            return ((self.object_number == other.object_number) and
                    (self.generation_number == other.generation_number) and
                    (self.value == other.value))
        else:
            return NotImplemented

    def __hash__(self) -> int:
        return hash((self.object_number,
                     self.generation_number,
                     self.value))

    def __str__(self) -> str:
        return '(%d, %d, %s)' % (self.object_number,
                                 self.generation_number,
                                 self.value.__class__.__name__)

    def __repr__(self) -> str:
        return str(self)

    def indirect_reference(self):
        return PdfIndirectReference(self.object_number,
                                    self.generation_number)
