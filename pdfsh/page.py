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
import collections
import logging
import time
import sys
import zlib

from .objects import *
from .parser import Parser

logger = logging.getLogger(__name__)

class Page:
    def __init__(self, document, ref):
        self.document = document
        self.ref = ref
        self.kids = []
        self.dictionary = self.document.get_object_by_ref(self.ref)
        assert PdfName('Type') in self.dictionary, 'page node does not have Type'
        self.page_type = self.dictionary[PdfName('Type')]
        if self.page_type == PdfName('Pages'):
            logger.info('not a leaf page')
            if PdfName('Kids') not in self.dictionary:
                raise PdfConformanceException('Page [%s] does not specify Kids')
            if PdfName('Count') not in self.dictionary:
                raise PdfConformanceException('Page [%s] does not specify Count')
            assert PdfName('Kids') in self.dictionary, 'page node does not have Kids'
            assert PdfName('Count') in self.dictionary, 'page node does not have Count'
        elif self.page_type == PdfName('Page'):
            logger.info('a leaf page')
        elif self.page_type == PdfName('Template'):
            logger.info('Template')
        else:
            raise PdfConformanceException('unknown page node type: %s' % self.page_type)

        if self.is_pages():
            self.kids = []
            for kid_ref in self.dictionary[PdfName('Kids')]:
                logger.debug('page kid: %s' % kid_ref)
                page = Page(self.document, kid_ref)
                self.kids.append(page)
        elif self.is_page():
            self.document.add_leaf_page(self)

    def is_page(self):
        return self.page_type == PdfName('Page')

    def is_pages(self):
        return self.page_type == PdfName('Pages')

    def is_template(self):
        return self.page_type == PdfName('Template')

    def repl_cat(self):
        if self.is_page():
            pass

    def repl_ls(self):
        nodes = []
        nodes.append((self.dictionary, 'dictionary'))
        if self.is_pages():
            for kid in self.kids:
                nodes.append((kid,
                              '%d.%d' % (kid.ref.object_number,
                                         kid.ref.generation_number)))
        return nodes

