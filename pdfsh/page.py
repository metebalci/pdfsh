# Copyright (C) 2024 Mete Balci
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
page
"""

import logging

from .exceptions import PdfConformanceException
from .objects import PdfName


logger = logging.getLogger(__name__)


class Page:
    """Page"""

    def __init__(self, document, ref):
        self.document = document
        self.ref = ref
        self.kids = []
        self.dictionary = self.document.get_object_by_ref(self.ref)
        assert PdfName("Type") in self.dictionary, "page node does not have Type"
        self.page_type = self.dictionary[PdfName("Type")]
        if self.page_type == PdfName("Pages"):
            logger.info("not a leaf page")
            if PdfName("Kids") not in self.dictionary:
                raise PdfConformanceException("Page [%s] does not specify Kids")
            if PdfName("Count") not in self.dictionary:
                raise PdfConformanceException("Page [%s] does not specify Count")
            assert PdfName("Kids") in self.dictionary, "page node does not have Kids"
            assert PdfName("Count") in self.dictionary, "page node does not have Count"
        elif self.page_type == PdfName("Page"):
            logger.info("a leaf page")
        elif self.page_type == PdfName("Template"):
            logger.info("Template")
        else:
            raise PdfConformanceException(f"unknown page node type: {self.page_type}")

        if self.is_pages():
            self.kids = []
            for kid_ref in self.dictionary[PdfName("Kids")]:
                logger.debug("page kid: %s", kid_ref)
                page = Page(self.document, kid_ref)
                self.kids.append(page)
        elif self.is_page():
            self.document.add_leaf_page(self)

    def is_page(self):
        """returns True if page is a Page (leaf node)"""
        return self.page_type == PdfName("Page")

    def is_pages(self):
        """returns True if page is a Pages (intermediate node)"""
        return self.page_type == PdfName("Pages")

    def is_template(self):
        """returns True if page is a Template"""
        return self.page_type == PdfName("Template")

    def repl_cat(self):
        """repl cat support"""
        if self.is_page():
            pass

    def repl_ls(self):
        """repl ls support"""
        nodes = []
        nodes.append((self.dictionary, "dictionary"))
        if self.is_pages():
            for kid in self.kids:
                nodes.append(
                    (kid, f"{kid.ref.object_number}.{kid.ref.generation_number}")
                )

        return nodes
