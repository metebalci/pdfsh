# Copyright (C) 2024 Mete Balci
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
PDF body representation
"""

import logging

from .objects import PdfArray, PdfDictionary

logger = logging.getLogger(__name__)


class Body(PdfArray):
    """PDF body"""


class Objects(PdfDictionary):
    """PDF objects"""
