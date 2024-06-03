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

import argparse
import logging
import sys
import traceback

from .document import Document
from .shell import Shell

logger = logging.getLogger(__name__)

def run():
    try:

        parser = argparse.ArgumentParser(
            prog='pdfsh',
            description='',
            epilog='')
        parser.add_argument('file',
                            help='pdf file')
        parser.add_argument('-v', '--verbose',
                            action='store_true',
                            help='enable general verbose/INFO logging')
        parser.add_argument('-d', '--debug',
                            action='store_true',
                            help='enable general DEBUG logging and verbose/INFO for parser and tokenizer)')
        parser.add_argument('--log-file',
                            default='pdfsh.log',
                            help='output logs to LOG_FILE')
        args = parser.parse_args()

        loggingFormat = '%(levelname)s/%(filename)s: %(message)s'

        if args.log_file is not None:
            logging.basicConfig(filename=args.log_file,
                                format=loggingFormat)
        else:
            logging.basicConfig(format=loggingFormat)

        if args.debug:
            print(args)
            logging.getLogger('pdfsh').setLevel(logging.DEBUG)
        elif args.verbose:
            logging.getLogger('pdfsh').setLevel(logging.INFO)
        else:
            logging.getLogger('pdfsh').setLevel(logging.WARNING)

        with open(args.file, 'rb') as f:
            document = Document(f.read())
            print('pdfsh  Copyright (C) 2024  Mete Balci')
            print('License GPLv3+: GNU GPL version 3 or later')
            logger.debug('platform: %s' % sys.platform)
            if not sys.platform.startswith('linux'):
                print('WARNING: pdfsh is only tested on Linux')
            Shell(document.get_object_by_ref,
                  document,
                  '%s' % args.file).run()

    except Exception as e:
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(run())
