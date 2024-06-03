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

class Trailer(PdfDictionary):

    offset_re = re.compile(r"^[0-9]+$")

    # ISO 32000-2:2020 7.5.5: File trailer
    #
    # The last line of the file shall contain only the end-of-file marker
    # %%EOF
    # The two preceding lines shall contain, one per line, and in order,
    # the keyword startxref and the byte offset from the beginning of the
    # PDF file to the beginning of the xref keyword in the last
    # cross-reference section.
    #
    # The startxref line shall be preceded by the trailer dictionary,
    # consisting of the keyword trailer followed by a series of key-value pairs
    # enclosed in double angle branches << >>.
    def __init__(self,
                 dictionary:PdfDictionary,
                 xref_section_byte_offset:int):

        if PdfName('Root') not in dictionary:
            raise PdfConformanceException('trailer has no Root')

        super().__init__()

        self[PdfName('dictionary')] = dictionary
        self[PdfName('startxref')] = PdfIntegerNumber(xref_section_byte_offset)
        if PdfName('Prev') in dictionary:
            self[PdfName('prev')] = dictionary[PdfName('Prev')]
