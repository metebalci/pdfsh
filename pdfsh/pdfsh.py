# Copyright (C) 2024 Mete Balci
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
pdfsh
"""

import argparse
from importlib.metadata import version
import logging
import sys
import traceback

from .document import Document
from .shell import Shell


logger = logging.getLogger(__name__)


def run():
    """pdfsh run loop"""
    try:
        parser = argparse.ArgumentParser(prog="pdfsh", description="", epilog="")
        parser.add_argument("file", help="pdf file")
        parser.add_argument("--version", action="version", version=version("pdfsh"))
        parser.add_argument(
            "-c", "--cmdline", help="execute CMDLINE and send output to stdout"
        )
        parser.add_argument(
            "-v",
            "--verbose",
            action="count",
            help="enable VERBOSE/DEBUG logging",
            default=0,
        )
        parser.add_argument(
            "--log-file",
            default="pdfsh.log",
            help="output logs to LOG_FILE (defaults: pdfsh.log) or - for stderr",
        )
        args = parser.parse_args()

        logging_format = "%(levelname)5s:%(filename)15s: %(message)s"

        if args.log_file is None or args.log_file == "-":
            logging.basicConfig(level=logging.WARNING, format=logging_format)

        elif args.log_file is not None:
            logging.basicConfig(
                filename=args.log_file, level=logging.WARNING, format=logging_format
            )

        logging_level = logging.WARNING
        parser_logging_level = logging.WARNING
        tokenizer_logging_level = logging.WARNING

        if args.verbose >= 1:
            logging_level = logging.DEBUG if args.verbose >= 2 else logging.INFO
            parser_logging_level = logging.DEBUG if args.verbose >= 3 else logging.INFO
            tokenizer_logging_level = (
                logging.DEBUG if args.verbose >= 4 else logging.INFO
            )

        logging.getLogger("pdfsh").setLevel(logging_level)
        logging.getLogger("pdfsh.parser").setLevel(parser_logging_level)
        logging.getLogger("pdfsh.tokenizer").setLevel(tokenizer_logging_level)
        logger.info(args)

        with open(args.file, "rb") as f:
            document = Document(f.read())
            if args.cmdline is None:
                print("pdfsh  Copyright (C) 2024  Mete Balci")
                print("License GPLv3+: GNU GPL version 3 or later")
                logger.debug("platform: %s", sys.platform)
                if not sys.platform.startswith("linux"):
                    print("WARNING: pdfsh is only tested on Linux")

            shell = Shell(document.get_object_by_ref, document, f"{args.file}")
            if args.cmdline:
                shell.raw = True
                shell.process_cmdline(args.cmdline)

            else:
                shell.run()

        return 0

    # pylint: disable=broad-exception-caught
    except Exception:
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(run())
