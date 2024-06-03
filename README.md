*** This is an ongoing project, pypi distribution is not released yet.***

# pdfsh

`pdfsh` is a utility to investigate the PDF file structure in a shell-like interface. The idea is similar to the pseudo file system sysfs in Linux. `pdfsh` allows one to "mount" a PDF file and use a simple shell-like interface to navigate inside the PDF file structurally (not visually, `pdfsh` is not a PDF reader).

In `pdfsh`, similar to a file system, PDF file is represented as a tree. All the nodes of this tree are PDF objects.

`pdfsh` has its own ISO 32000-2:2020 PDF-2.0 parser.

`pdfsh` uses ccitt and lzw filter implementations in [pdfminer.six](https://github.com/pdfminer/pdfminer.six). 

## Installation

```
pip install pdfsh
```

which installs a `pdfsh` executable into the path.

It can also be run as a module `python -m pdfsh`.

## Design

`pdfsh` does three things:

- tokenizes and parses a PDF file
- creates PDF objects and a PDF document model also as PDF objects
- offers a shell-like interface to navigate in PDF objects

The tokenization is performed based on rules given in ISO 32000-2:2020 7.2 Lexical conventions. The tokenization is implemented in `pdfsh.tokenizer.Tokenizer` and Token* classes in `psdsh.tokens.*`.

Using the tokens emitted by the tokenizer, PDF is parsed to create PDF objects. Parsing is implemented in `pdfsh.parser.Parser` and Pdf* classes in `pdfsh.objects.*`.

Before parsing the objects, at the very beginning, the PDF file has to be read line by line to find the objects (starting from the end). The PDF document itself, header, trailer etc. are not given as PDF objects but they have a rigid syntax. However, in `pdfsh`, these are also represented as PDF objects. Thus, starting from the document, `pdfsh.document.Document`, everything is a PDF object, including `pdfsh.header.Header`, `pdfsh.body.Body`, `pdfsh.xrt.CrossReferenceTable` (for cross-reference table) and `pdfsh.trailer.Trailer`. `Document`, `Header`, `Body` and `Trailer` are defined as a Dictionary, whereas `CrossReferenceTable` are defined as an Array. CrossReferenceTable also has other classes (Section, Subsection and Entry).

The cross-reference table is called `xrt` in `pdfsh`.

Finally, `pdfsh.shell.Shell` implements the shell-like interface that can be used with `pdfsh` program when installed with `pip` or by running the module by `python -m pdfsh`.

## Usage

For an introduction to PDF and a tutorial using `pdfsh`, please see my blog post [](https://metebalci.com/blog/).

### PDF Objects

According to ISO 32000-2:2020 7.3 Objects, PDF objects are:

- Boolean
- Numeric: Integer (32-bit signed) and Real (single or double, implementation defined)
- String: Literal and Hexadecimal (no size limit)
- Name (recommended to have a length of less than 127 bytes)
- Array (no size limit)
- Dictionary (no size limit)
- Stream (no size limit)
- Null
- Indirect

An object without a label (label can be thought as variable name) is called a direct object. All but Indirect above are direct objects. When a direct object is defined with a label, it becomes an indirect object. Since it has a label, an indirect object can be referenced from other objects (Array and Dictionary).

```
For example:

- true, is a (direct) Boolean object
- my_label true, is an (indirect) Boolean object with label my_label
- a dictionary can refer this object using my_label
```

A label is actually two numbers, an object number and a generation number. An indirect reference is given like `(1 2 R)` where object number is 1, generation number is 2. This object (lets say it is a Boolean) is defined as:

```
1 2 obj
true
endobj
```

I find it strange that Indirect object is categorized as a PDF object in the specification. I think actually indirect reference is a PDF object, because an indirect object cannot be stored in an array or dictionary but indirect reference can be stored.

## Shell

When `pdfsh` is run with `pdfsh <pdf_file>`, the shell interface is loaded with the document at the root of structural tree. The root node has no name, and represented by a single `/`.

A node can be:
 
- `leaf`: Boolean, Number (Integer and Real), String (Literal and Hexadecimal), Name, Stream, Null objects are leaf nodes.
- `container`: Array and Dictionary are container nodes. These can provide leaf nodes. Array leaf nodes are named as numbers (since array elements are indexed by numbers starting from 0). Dictionary leaf nodes are named as their keys (Name objects).
- `ref`: Indirect reference is a ref node. This node points to another object like a symbolic link. Since the direct object pointed by an indirect reference can be an Array or Dictionary, a ref node can function as a container depending on what it points to.

`pdfsh` shell interface have `ls`, `cd`, `cat` and `node` commands. For `cd`, `cat` and `node` commands, a simple autocomplete mechanism is provided.

`pdfsh` has a simple prompt: `<filename>:<current_node> $`. The current node is given as a path separated by `/` like a UNIX filesystem path.

### ls

`ls` can only be used as `ls` to list the child nodes under the current node.

`ls` does not support listing the child nodes of a far node like `ls a/b/c`.

### cd

`cd` can be used in four ways:

- `cd` returns back to the root. Similar to `cd /` or `cd` assuming `HOME=/` in BASH.

- `cd ..` goes up one level.

- `cd <container_node>` changes the current node to the given `<container_node>`. This node has to be a container not surprisingly to have child nodes. `PdfArray` and `PdfDictionary` are container nodes.

- `cd <ref_node>` changes the current node to the target of given `<ref_node>`. This is very useful for example when a dictionary contains indirect references. Naturally, this only makes sense if the target is an Array or a Dictionary.

### cat

`cat` can be used in one way but it can also be considered two ways:

- `cat <leaf_node>` displays the contents of a leaf node. For example, if it is a `PdfIntegerNumber`, it shows the value of this node.

- `cat <container_node>` displays the contents of a container node. This is different than BASH, since `cat <dir>` does not work. The idea here is, for some cases, it is much easier to see the contents of `PdfArray` and `PdfDictionary` directly, rather than the entering inside and checking each element individually.

- `cat <ref_node>` displays the content (reference) of a reference node, a `PdfIndirectReference`, such as `(10 0 R)`.

### node

`node` command is similar to `file` command in BASH, it shows the type of the node.

### other commands

- `?` and `help`: displays the help
- `exit` and `quit`: exits from pdfsh
- `ctrl-c` and `ctrl-d`: also exits from pdfsh
- `show w` and `show c`: displays parts of GNU GPL 3.0 license

## Tutorial

It is assumed that `pdfsh` is installed with `pip`.

### PDF 101

These are the very basics of Portable Data Format (PDF).

An object in PDF is identified by two numbers, object number (positive integer, no upper limit) and generation number (non-negative integer, maximum value 65535). It is not a must to have all objects to have an identification (a label). If an object has a label, it is called an indirect object (thus ones without a label a direct object). An indirect object can be referenced from other objects with an indirect reference. An array or a dictionary can contain any type of direct objects or an indirect reference. An indirect object has to be declared stand-alone.

A minimal PDF file consists of 4 parts:

- header: single line consisting of file version
- body: consists of all (direct and indirect) objects
- cross-reference table: information about indirect objects
- trailer: special information including trailer dictionary and startxref

Although the actual content in PDF is formed by objects, and PDF is essentially a binary format, there is a need for line-by-line text processing when parsing a PDF file initially. Because the special structures, header, part of trailer (startxref) and cross-reference table are not stored as PDF objects. Trailer dictionary is stored as a dictionary object.

I will call cross-reference table as xrt in this document and also in pdfsh. This is not a standard term.

A PDF file can be incrementally updated. Incremental means the original content of the file is left intact, but the updates are added at the end of the file. An incremental update has another body, cross-reference table and trailer. Thus, when a PDF file is created, it contains:

- header, body, xrt, trailer

when it is updated, it will contain:

- header, body, xrt, trailer, body_updated, xrt_updated, trailer_updated

with every update, more body, xrt and trailer sections are added to the end.

With an update:

- new objects can be introduced
- old objects can be marked as deleted (free) (but actually still stays in the file)
- special information in trailer can be changed

Cross-reference table in general refers to the final merged table of all cross-reference tables in a PDF file due to incremental updates. For example, an object with object number 1 generation number 0 is deleted with an update, the cross-reference table that is added with the update contains an entry object number 1 generation number 1 deleted. Thus, the final merged cross-reference table is created from backwards, from the last cross-reference table to the first.


#### trailer

The trailer (the last part of the file) has to be read first in a PDF file, before reading the body. The trailer in this file is (I use -A 8 only because I know there are 8 lines after trailer line):

```
$ grep -A 8 '^trailer' Simple\ PDF\ 2.0\ file.pdf 
trailer
<<
  /Size 10
  /Root 1 0 R
  /ID [ <31c7a8a269e4c59bc3cd7df0dabbf388><31c7a8a269e4c59bc3cd7df0dabbf388> ]
>>
startxref
4851
%%EOF
```

Lets look at the `trailer` now.

```
Simple PDF 2.0 file.pdf:/ $ cd trailer
Simple PDF 2.0 file.pdf:/trailer $ ls
dictionary/
startxref
Simple PDF 2.0 file.pdf:/trailer $ node startxref
startxref is a integer object
Simple PDF 2.0 file.pdf:/trailer $ cat startxref
4851
Simple PDF 2.0 file.pdf:/trailer $ cat dictionary
{
 'Size': 10,
 'Root': (1, 0, R),
 'ID': [<31c7a8a269e4c59bc3cd7df0dabbf388>, <31c7a8a269e4c59bc3cd7df0dabbf388>]
}
```

`trailer` has two (very important) childs: `dictionary` and `startxref`. 

`startxref` is an integer number object containing the byte offset of cross-reference table.

`dictionary` contains the trailer dictionary. Because the trailer dictionary contains an indirect reference (Root) and an array (ID), it is also possible to `cd` into this dictionary.

```
Simple PDF 2.0 file.pdf:/trailer/dictionary $ cd dictionary
Simple PDF 2.0 file.pdf:/trailer/dictionary $ ls
ID/
Root*
Size
Simple PDF 2.0 file.pdf:/trailer/dictionary $ node ID
ID is a array object
Simple PDF 2.0 file.pdf:/trailer/dictionary $ node Root
Root is a indirect reference
```

Trailer dictionary should at minimum contain Size and Root (and ID in PDF 2.0). Size indicates the size (number of in-use objects) of the cross-reference table, and Root is an indirect reference to the "catalog dictionary".

#### xrt, cross-reference table

After the trailer is read (thus startxref), the cross-reference table (xrt) can be read. xrt is not just a single table, it contains sections, sections contain subsections and finally subsections contain entries. Each cross-reference table entry contains the byte offset (10 digit number), generation number (5 digit number) and a free/in-use flag (f or n). Cross-reference table section starts with a line containing `xref` (hence the name startxref in trailer), then a subsection starts with the first object number and number of objects. Thus, the subsection knows which entry is for which object number. The section (pointed by startxref) in this PDF file contains this:

```
$ grep -A 11 '^xref' Simple\ PDF\ 2.0\ file.pdf 
xref
0 10
0000000000 65535 f
0000000016 00000 n
0000000096 00000 n
0000002547 00000 n
0000002619 00000 n
0000002782 00000 n
0000003587 00000 n
0000003811 00000 n
0000003972 00000 n
0000004524 00000 n
```

Altought cross-reference section has a very rigid structure and not stored as objects, `pdfsh` represents it as objects. Particularly, the cross-reference table and the section is represented as arrays, and the subsections are represented as dictionaries (because subsection also has first_object_number in addition to entries).

Lets now see xrt:

```
Simple PDF 2.0 file.pdf:/ $ cd xrt
Simple PDF 2.0 file.pdf:/xrt $ ls
0/
Simple PDF 2.0 file.pdf:/xrt $ node 0
0 is a array object
Simple PDF 2.0 file.pdf:/xrt $ cd 0
Simple PDF 2.0 file.pdf:/xrt/0 $ ls
0/
Simple PDF 2.0 file.pdf:/xrt/0 $ node 0
0 is a dictionary object
Simple PDF 2.0 file.pdf:/xrt/0 $ cd 0
Simple PDF 2.0 file.pdf:/xrt/0/0 $ ls
entries/
first_object_number
Simple PDF 2.0 file.pdf:/xrt/0/0 $ cat first_object_number
0
```

This PDF file (Simple PDF 2.0 file.pdf) is not (incrementally) updated, hence there is only one cross-reference table section (index=0) and it also has one subsection (index=0). The subsection has two childs: `entries` and `first_object_number`. The `first_object_number` is 0, entries start from object number 0.

`entries` is a dictionary with object numbers used as keys. 

Keep in mind that cross-reference table, including entries, are not stored as objects in a PDF file. However, `pdfsh` represents them as objects. An actual entry looks like this (this is the object number 1 in this PDF):

```
```

Lets look at the first and the second entry, object number 0 and 1 (because the subsection's first_object_number is 0, the object number of first entry is 0 and the second is 1).

```
Simple PDF 2.0 file.pdf:/xrt/0/0 $ cd entries
Simple PDF 2.0 file.pdf:/xrt/0/0/entries $ ls
0/
1/
2/
3/
4/
5/
6/
7/
8/
9/
Simple PDF 2.0 file.pdf:/xrt/0/0/entries $ cat 0
{
 'object_number': 0,
 'byte_offset': 0,
 'generation_number': 65535,
 'is_free': True
}
Simple PDF 2.0 file.pdf:/xrt/0/0/entries $ cat 1
{
 'object_number': 1,
 'byte_offset': 16,
 'generation_number': 0,
 'is_free': False
}
```

In ISO 32000-2:2020 7.3.10 Indirect objects, it says the object identifier consists of two parts:

- "A positive integer object number. Indirect objects may be numbered sequentially within a PDF file, but this is not required; object numbers may be assigned in any arbitrary order."

- "A non-negative integer generation number. In a newly created file, all indirect objects shall have generation numbers of 0. Non-zero generation numbers may be introduced when the file is later updated;...".

In ISO 32000-2:2020 7.5.4 Cross-reference table (page 57), it is said that generation number can be maximum 65535 (16-bit unsigned integer). In the same page, it is also said that the cross-reference table should contain an entry for each object from object number 0 to the maximum object number used in the PDF file. Thus, it is possible to skip some object numbers but cross-reference table should still contain an entry for them.

It does not seem like there is an upper bound for the object number.

So, it does not make sense the first entry has and `object_number` of 0 (object number has to be > 0). This is another strange thing in the PDF spec. This is because there is a concept of free.

#### body

## Changes

### 0.1

- initial release

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
