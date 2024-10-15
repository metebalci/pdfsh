# Copyright (C) 2024 Mete Balci
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
exceptions
"""


class PdfConformanceException(Exception):
    """raised if Pdf does not conform to the spec"""


class PossibleBugException(Exception):
    """raised if an unexpected error occurs"""


class NotSupportedException(Exception):
    """raised for unsupported features"""
