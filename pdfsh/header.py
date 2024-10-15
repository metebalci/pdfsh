# Copyright (C) 2024 Mete Balci
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
header
"""

import logging
import re

from .exceptions import PdfConformanceException
from .parser import Parser
from .objects import PdfDictionary, PdfName, PdfLiteralString

logger = logging.getLogger(__name__)


class Header(PdfDictionary):
    """PDF header"""

    version_re = re.compile(r"^%PDF-[12]\.[0-9]$")

    # ISO 32000-2:2020 7.5.2: File header
    # The PDF file begins with the 5 characters %PDF- and byte offsets shall be
    # calculated from the % sign
    # The file header shall consists of %PDF-1.n or %PDF-2.n followed by a
    # single EOL marker, where 'n' is a single digit number between 0 and 9
    @staticmethod
    def load(parser: Parser):
        """loads header from the parser"""
        line = parser.next_line()
        logger.info("header: %s", line.decode("ascii", "replace"))
        line = line[0:8].decode("ascii", "replace")
        if Header.version_re.match(line) is None:
            raise PdfConformanceException("PDF version is invalid")

        version = line[5:]
        logger.info("version: %s", version)
        return Header(line, version)

    def __init__(self, line: str, version: str):
        super().__init__()
        self[PdfName("line")] = PdfLiteralString(line)
        self[PdfName("version")] = PdfName(version)
