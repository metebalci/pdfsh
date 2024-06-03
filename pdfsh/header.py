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

class Header(PdfDictionary):

    version_re = re.compile(r"^%PDF-[12]\.[0-9]$")

    # ISO 32000-2:2020 7.5.2: File header
    # The PDF file begins with the 5 characters %PDF- and byte offsets shall be
    # calculated from the % sign
    # The file header shall consists of %PDF-1.n or %PDF-2.n followed by a
    # single EOL marker, where 'n' is a single digit number between 0 and 9
    @staticmethod
    def load(parser):
        line = parser.get_line(0)
        logger.info('header: %s' % line.decode('ascii', 'replace'))
        line = line[0:8].decode('ascii', 'replace')
        if Header.version_re.match(line) is None:
            raise PdfConformanceException('PDF version is invalid')

        version = line[5:]
        logger.info('version: %s' % version)
        return Header(line, version)

    def __init__(self, line:str, version:str):
        super().__init__()
        self[PdfName('line')] = PdfLiteralString(line)
        self[PdfName('version')] = PdfLiteralString(version)
