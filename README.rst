========================================
Find ISBNs from ebooks (pdf, djvu, epub)
========================================
The script `find_isbns <./find_isbns/scripts/find_isbns.py>`_ finds ISBNs from ebooks (pdf, djvu, epub) or any string given as input 
to the script . 

It is based on the great `ebook-tools <https://github.com/na--/ebook-tools>`_ which is written in shell by `na-- <https://github.com/na-->`_:

 "Searching for ISBNs in files uses progressively more resource-intensive methods until some ISBNs are found."

Thus, `find_isbns <./find_isbns>`_ is a Python port of the parts of the shell scripts from ``ebook-tools`` that are 
related to finding ISBNs from ebooks.

.. contents:: **Contents**
   :depth: 3
   :local:
   :backlinks: top

Dependencies
============
TODO

Installation
============
To install the `find_isbns <./find_isbns/>`_ package::

 $ pip install git+https://github.com/raul23/find-isbns#egg=find-isbns
 
**Test installation**

1. Test your installation by importing ``find_isbns`` and printing its
   version::

   $ python -c "import find_isbns; print(find_isbns.__version__)"

2. You can also test that you have access to the ``find_isbns.py`` script by
   showing the program's version::

   $ find_isbns --version

Uninstall
=========
To uninstall the `find_isbns <./find_isbns/>`_ package::

 $ pip uninstall find_isbns

Script options
==============
To display the script `find_isbns.py <./find_isbns/scripts/find_isbns.py>`_ list of options and their descriptions::

   $ find_isbns -h
   usage: find_isbns [OPTIONS] {input_data}

   Find valid ISBNs inside a file or in a string if no file was specified. 
   Searching for ISBNs in files uses progressively more resource-intensive methods until some ISBNs are found.

   This script is based on the great ebook-tools written in Shell by na-- (See https://github.com/na--/ebook-tools).

   General options:
     -h, --help                                      Show this help message and exit.
     -v, --version                                   Show program's version number and exit.
     -q, --quiet                                     Enable quiet mode, i.e. nothing will be printed.
     --verbose                                       Print various debugging information, e.g. print traceback when there is an exception.
     --log-level {debug,info,warning,error}          Set logging level. (default: info)
     --log-format {console,only_msg,simple}          Set logging formatter. (default: only_msg)

   Convert-to-txt options:
     --djvu {djvutxt,ebook-convert}                  Set the conversion method for djvu documents. (default: djvutxt)
     --epub {epubtxt,ebook-convert}                  Set the conversion method for epub documents. (default: epubtxt)
     --pdf {pdftotext,ebook-convert}                 Set the conversion method for pdf documents. (default: pdftotext)

   Find ISBNs options:
     -i, --isbn-regex ISBN_REGEX                     This is the regular expression used to match ISBN-like numbers in the 
                                                     supplied books. 
                                                     (default: (?<![0-9])(-?9-?7[789]-?)?((-?[0-9]-?){9}[0-9xX])(?![0-9]))
     --isbn-blacklist-regex REGEX                    Any ISBNs that were matched by the ISBN_REGEX above and pass the ISBN 
                                                     validation algorithm are normalized and passed through this regular 
                                                     expression. Any ISBNs that successfully match against it are discarded. 
                                                     The idea is to ignore technically valid but probably wrong numbers 
                                                     like 0123456789, 0000000000, 1111111111, etc.. 
                                                     (default: ^(0123456789|([0-9xX])\2{9})$)
     --isbn-direct-files REGEX                       This is a regular expression that is matched against the MIME type of 
                                                     the searched files. Matching files are searched directly for ISBNs, 
                                                     without converting or OCR-ing them to .txt first. 
                                                     (default: ^text/(plain|xml|html)$)
     --isbn-ignored-files REGEX                      This is a regular expression that is matched against the MIME type of 
                                                     the searched files. Matching files are not searched for ISBNs beyond 
                                                     their filename. By default, it tries to make the subcommands ignore 
                                                     .gif and .svg images, audio, video and executable files and fonts. 
                                                     (default: ^(image/(gif|svg.+)|application/(x-shockwave-flash|CDFV2|
                                                               vnd.ms-opentype|x-font-ttf|x-dosexec|vnd.ms-excel|
                                                               x-java-applet)|audio/.+|video/.+)$)
     --reorder-files LINES [LINES ...]               These options specify if and how we should reorder the ebook text before 
                                                     searching for ISBNs in it. By default, the first 400 lines of the text 
                                                     are searched as they are, then the last 50 are searched in reverse and 
                                                     finally the remainder in the middle. This reordering is done to improve 
                                                     the odds that the first found ISBNs in a book text actually belong to 
                                                     that book (ex. from the copyright section or the back cover), instead of 
                                                     being random ISBNs mentioned in the middle of the book. No part of the 
                                                     text is searched twice, even if these regions overlap. Set it to `False` 
                                                     to disable the functionality or `first_lines last_lines` to enable it with 
                                                     the specified values. (default: 400 50)
     --irs, --isbn-return-separator SEPARATOR        This specifies the separator that will be used when returning any found 
                                                     ISBNs. (default: '\n')

   OCR options:
     --ocr, --ocr-enabled {always,true,false}        Whether to enable OCR for .pdf, .djvu and image files. It is disabled by default. 
                                                     (default: false)
     --ocrop, --ocr-only-first-last-pages PAGES PAGES
                                                     Value 'n m' instructs the script to convert only the first n and last m pages 
                                                     when OCR-ing ebooks. (default:7 3)

   Input data:
     input_data                                      Can either be the path to a file or a string. The input will be searched for ISBNs.

`:information_source:` Since the program ``find_isbns`` is based on the shell suite of scripts 
`ebook-tools <https://github.com/na--/ebook-tools>`_, the descriptions for the options are from ``ebook-tools``.

How the script ``find_isbns`` finds ISBN
========================================
For more details, see:

- The `documentation <https://github.com/na--/ebook-tools#searching-for-isbns-in-files>`_ for ``ebook-tools`` (shell scripts) or
- `search_file_for_isbns() <https://github.com/raul23/find-isbns/blob/926cbb49f8e97b6f71526bcaef5c810805ccad99/find_isbns/lib.py#L702>`_ 
  from ``lib.py`` (Python function where ISBNs search in files is implemented).

Examples
========
Find ISBNs in a string
----------------------
TODO

Find ISBNs in a pdf file
------------------------
TODO

Cases tested
============
TODO
