# Copyright (C) 2024 Mete Balci
#
# SPDX-License-Identifier: GPL-3.0-or-later

import logging

from .exceptions import PdfConformanceException
from .objects import PdfName, PdfIntegerNumber, PdfDictionary


logger = logging.getLogger(__name__)


class Trailer(PdfDictionary):

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
    def __init__(self, dictionary: PdfDictionary, xref_section_byte_offset: int):

        if PdfName("Root") not in dictionary:
            raise PdfConformanceException("trailer has no Root")

        super().__init__()

        self[PdfName("dictionary")] = dictionary
        self[PdfName("startxref")] = PdfIntegerNumber(xref_section_byte_offset)

    @property
    def prev(self):
        return self[PdfName("prev")]

    @prev.setter
    def prev(self, new_prev: PdfDictionary):
        self[PdfName("prev")] = new_prev
