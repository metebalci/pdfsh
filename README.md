# pdfsh

[![CircleCI](https://dl.circleci.com/status-badge/img/gh/metebalci/pdfsh/tree/main.svg?style=svg)](https://dl.circleci.com/status-badge/redirect/gh/metebalci/pdfsh/tree/main)

`pdfsh` is a utility to investigate the PDF file structure in a shell-like interface. It allows one to "mount" a PDF file and use a simple shell-like interface to navigate inside the PDF file structurally.

Technically, `pdfsh` is a PDF processor, a PDF reader, but not a viewer that renders the page contents.

In `pdfsh`, similar to a file system, the PDF file is represented as a tree. All the nodes of the tree are PDF objects.

`pdfsh` has its own ISO 32000-2:2020 PDF-2.0 parser.

`pdfsh` uses ccitt and lzw filter implementations and png predictor implementation in [pdfminer.six](https://github.com/pdfminer/pdfminer.six). To minimize the dependency, I decided to add the implementations of these directly to the pdfsh code, so there is no dependency to pdfminer.six.

`pdfsh` assumes it is run under a ANSI capable terminal as it uses ANSI terminal features and colors. If strange behavior is observed, make sure the terminal emulation it is run is ANSI compatible.

## Usage

```
pip install pdfsh
```

which installs a `pdfsh` executable into the path.

When `pdfsh` is run as `pdfsh <pdf_file>`, the shell interface is loaded with the document at the root of structural tree. The root node has no name, and represented by a single `/`.

`pdfsh` shell interface have commands like `ls`, `cd` and `cat`. For paths, an autocomplete mechanism is implemented.

`pdfsh` has a simple prompt: `<filename>:<current_node> $`. The current node is given as a path separated by `/` like a UNIX filesystem path.

## Tutorial

For an introduction to PDF and a tutorial using `pdfsh`, please see my blog post [A Minimum Complete Tutorial of Portable Document Format (PDF) with pdfsh](https://metebalci.com/blog/a-minimum-complete-tutorial-of-pdf-with-pdfsh/).

## Notes

`pdfsh` supports both cross-reference tables and cross-reference streams as well as hybrid-reference files. However, because `pdfsh` eagerly constructs the cross-reference table, either the cross-reference table or cross-reference stream is read in a particular update section. Thus, an object that is not visible in cross-reference stream but visible in cross-reference table cannot be found. More information about this topic can be found in ISO 32000-2:2020 7.5.8.4. Compatibility with applications that do not support compressed reference streams.

## Changes

Version numbers are in `<year>.<positive_integer>` format. The `<positive_integer` monotonically increases in the same year but resets to `1` in the new year.

### 2024.4
- cross-reference streams support
- object streams support
- `--version` option added
- migrated from setup.py to pyproject.toml 

### 2024.3 is skipped

### 2024.2
- first public release

### 2024.1
- initial test release, not for public use

## External Licenses

### pdfminer.six

[pdfminer.six](https://github.com/pdfminer/pdfminer.six): [Copyright (c) 2004-2016  Yusuke Shinyama \<yusuke at shinyama dot jp\>](LICENSE.pdfminer.six)

- [ccitt.py](pdfminer/ccitt.py) and [lzw.py](pdfminer/lzw.py) are part of pdfminer.six
- [utils.py](pdfminer/utils.py) contains one function (`apply_png_predictor`) from the same source file (utils.py) from pdfminer.six.

# License

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
