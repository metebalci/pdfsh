*** This is an ongoing project, pypi distribution is not released yet.***

# pdfsh

`pdfsh` is a utility to investigate the PDF file structure in a shell-like interface. The idea is similar to the pseudo file system sysfs in Linux. `pdfsh` allows one to "mount" a PDF file and use a simple shell-like interface to navigate inside the PDF file structurally.

Technically, `pdfsh` is a PDF processor, a PDF reader, but not a viewer that renders the page contents.

In `pdfsh`, similar to a file system, the PDF file is represented as a tree. All the nodes of the tree are PDF objects.

`pdfsh` has its own ISO 32000-2:2020 PDF-2.0 parser.

`pdfsh` uses ccitt and lzw filter implementations in [pdfminer.six](https://github.com/pdfminer/pdfminer.six). 

`pdfsh` assumes it is run under a ANSI capable terminal as it uses ANSI terminal features and colors. If strange behavior is observed, make sure the terminal emulation it is run is ANSI compatible.

## Installation and Requirements

```
pip install pdfsh
```

which installs a `pdfsh` executable into the path.

It can also be run as a module `python -m pdfsh`.

## Design

`pdfsh` does three things:

- tokenizes and parses a PDF file
- creates the PDF objects in the PDF file and the PDF document model also as PDF objects
- offers a shell-like interface to navigate inside the PDF objects

The tokenization is performed based on rules given in ISO 32000-2:2020 7.2 Lexical conventions. The tokenization is implemented in `pdfsh.tokenizer.Tokenizer` and the classes in `psdsh.tokens.*`.

Using the tokens emitted by the tokenizer, PDF is parsed to create PDF objects. Parsing is implemented in `pdfsh.parser.Parser` and the classes in `pdfsh.objects.*`.

Before parsing the objects, at the very beginning, the PDF file has to be read line by line to find the objects (starting from the end). The PDF document itself, header, trailer etc. are not represented as PDF objects in the PDF file but they have a rigid syntax. However, in `pdfsh`, these are also represented as PDF objects. Thus, starting from the document, `pdfsh.document.Document`, everything is a PDF object, including `pdfsh.header.Header`, `pdfsh.body.Body`, `pdfsh.xrt.CrossReferenceTable` (for cross-reference table) and `pdfsh.trailer.Trailer`. `Document`, `Header`, `Body` and `Trailer` are defined as a Dictionary, whereas `CrossReferenceTable` is defined as an Array. CrossReferenceTable also has other classes (Section, Subsection and Entry).

The cross-reference table is called `xrt` in `pdfsh`.

Finally, `pdfsh.shell.Shell` implements the shell-like interface. The command line handling is implemented in `pdfsh.cmdline.Cmdline`.

## Tutorial

For an introduction to PDF and a tutorial using `pdfsh`, please see my blog post (TBD).

## Usage

When `pdfsh` is run as `pdfsh <pdf_file>`, the shell interface is loaded with the document at the root of structural tree. The root node has no name, and represented by a single `/`.

A node can be:
 
- `leaf`: Boolean, Number (Integer and Real), String (Literal and Hexadecimal), Name, Stream, Null objects are leaf nodes.
- `container`: Array and Dictionary are container nodes. These "contain" multiple leaf or container nodes. Array elements are named as numbers starting from 0 (since array elements are indexed by numbers). Dictionary elements are named as their keys (Name objects).
- `ref`: Indirect reference is a ref node. This node points to another object like a symbolic link. Since the direct object pointed by an indirect reference can be an Array or Dictionary, a ref node can function as a container depending on what it points to.

`pdfsh` shell interface have commands like `ls`, `cd` and `cat`. For paths, an autocomplete mechanism is implemented.

`pdfsh` has a simple prompt: `<filename>:<current_node> $`. The current node is given as a path separated by `/` like a UNIX filesystem path.

### ls

`ls` can be used as `ls` or `ls <path>` to list the child nodes under the current node or under the node provided with the path.

### cd

`cd` can be used as `cd`, `cd ..` or `cd <path>`.

- `cd` returns back to the root, in a sense that `cd` assumes `$HOME` is `/`.

- `cd ..` goes up one level.

- `cd <path>` changes the current node to the container node given by the `<path>`. This node has to be a container. In addition to this, this node can be a ref node with a container node target.

### cat

`cat` is used as `cat <path>`.

When the path points to a leaf node, it displays the contents of a leaf node.

When the path points to a container node, (this is different than a traditional regular), it also displays the contents of the container node. This is limited to only a few levels (sub-sub-container elements are not shown).

If the path points to a ref node, it also displays the content of the ref node (not its target).

### cats and catsx

These are slight variation of `cat` specific to stream nodes. `cat` only displays the stream dictionary not its data. Whereas `cats` shows the stream data as text after it is decoded with `utf-8` (unknown characters are replaced) and `catsx` shows the stream data as a hex string.

### node

`node` command is similar to `file` command in BASH, it shows the type of the node.

### other commands

- `?` and `help`: displays the help
- `q`: quits from pdfsh

## Changes

Version numbers are in `<year>.<positive_integer>` format. The `<positive_integer` is monotonically increasing in a year but reset to `1` in a new year.

### 2024.2
- first public release

### 2024.1
- initial test release, not for public use

## External Licenses

- [ccitt.py](pdfminer/ccitt.py) and [lzw.py](pdfminer/lzw.py) are part of [pdfminer.six](https://github.com/pdfminer/pdfminer.six): [Copyright (c) 2004-2016  Yusuke Shinyama \<yusuke at shinyama dot jp\>](LICENSE.pdfminer.six)

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
