========================================
Find ISBNs from ebooks (pdf, djvu, epub)
========================================
The script `find_isbns.py <./find_isbns/scripts/find_isbns.py>`_ finds ISBNs from ebooks (pdf, djvu, epub) or any string given as input 
to the script . 

It is based on the great `ebook-tools <https://github.com/na--/ebook-tools>`_ which is written in shell by `na-- <https://github.com/na-->`_:

 "Searching for ISBNs in files uses progressively more resource-intensive methods until some ISBNs are found."

Thus if the ebook is made up of images, then **OCR** is run on specific parts of the document to find its ISBNs.

`find_isbns <./find_isbns>`_ is a Python port of the parts of the shell scripts from ``ebook-tools`` that are 
related to finding ISBNs from ebooks.

|

`:star:` Other related projects that I ported from ``ebook-tools`` to Python:

- `convert-to-txt <https://github.com/raul23/convert-to-txt>`_: convert documents (pdf, djvu, epub, word) to txt
- `ocr <https://github.com/raul23/ocr>`_: OCR documents (pdf, djvu, and images)

.. contents:: **Contents**
   :depth: 3
   :local:
   :backlinks: top

Dependencies
============
This is the environment on which the script `find_isbns.py <./find_isbns/scripts/find_isbns.py>`_ was tested:

* **Platform:** macOS
* **Python**: version **3.7**
* `Tesseract <https://github.com/tesseract-ocr/tesseract>`_ for running OCR on books - version 4 gives 
  better results. 
  
  `:warning:` OCR is a slow resource-intensive process. Hence, by default only the first 7 and last 3 pages are OCRed through the option
  ``--ocr-only-first-last-pages``. More info at `Script options <#script-options>`_.
* `Ghostscript <https://www.ghostscript.com/>`_: ``gs`` converts *pdf* to *png* (useful for OCR)
* `DjVuLibre <http://djvu.sourceforge.net/>`_: 

  - it includes ``ddjvu`` for converting *djvu* to *tif* image (useful for OCR), and ``djvused`` to get number of pages from a *djvu* document
  - it includes ``djvutxt`` for converting *djvu* to *txt*
  
    `:warning:` 
  
    - To access the *djvu* command line utilities and their documentation, you must set the shell variable ``PATH`` and ``MANPATH`` appropriately. 
      This can be achieved by invoking a convenient shell script hidden inside the application bundle::
  
       $ eval `/Applications/DjView.app/Contents/setpath.sh`
   
      **Ref.:** ReadMe from DjVuLibre
    - You need to softlink ``djvutxt`` in ``/user/local/bin`` (or add it in ``$PATH``)
* `poppler <https://poppler.freedesktop.org/>`_: 

  - it includes ``pdftotext`` for converting *pdf* to *txt*
  - it includes ``pdfinfo`` to get number of pages from a *pdf* document if `mdls (macOS) <https://ss64.com/osx/mdls.html>`_ is not found.

`:information_source:` *epub* is converted to *txt* by using ``unzip -c {input_file}``

|

**Optionally:**

- `calibre <https://calibre-ebook.com/>`_: 

  - for converting {*pdf*, *djvu*, *epub*, *msword*} to *txt* by using calibre's own 
    `ebook-convert <https://manual.calibre-ebook.com/generated/en/ebook-convert.html>`_
  
    `:warning:` ``ebook-convert`` is slower than the other conversion tools (``textutil``, ``catdoc``, ``pdftotext``, ``djvutxt``)
  - for getting an ebook's metadata with ``ebook-metadata`` in order to search it for ISBNs

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
                                                     their filename. By default, it tries to ignore .gif and .svg images, 
                                                     audio, video and executable files and fonts. 
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
     input_data                                      Can either be the path to a file or a string (enclose it within single or double 
                                                     quotes if it contains spaces). The input will be searched for ISBNs.

`:information_source:` Explaining some of the options/arguments

- Since the program ``find_isbns`` is based on the shell suite of scripts `ebook-tools <https://github.com/na--/ebook-tools>`_, the descriptions for the options are from ``ebook-tools``.
- The input string must be enclosed within single or double quotes if it contains *spaces*, like so::

   $ find_isbns '978-159420172-1 978-1892391810 0000000000 0123456789 1111111111'

How the script ``find_isbns`` extracts ISBNs from an input file or string
=========================================================================
As stated from `ebook-tools <https://github.com/na--/ebook-tools>`_ (shell scripts from which ``find_isbns.py`` was ported)::

 "Searching for ISBNs in files uses progressively more resource-intensive methods until some ISBNs are found."

Here are the steps followed by ``find_isbns`` to find ISBNs in files or string:

1. If the input data is a string, it is searched for any ISBN-like sequences using a regex, duplicate ISBNs are removed and
   finally the found ISBNs are validated and returned separated by the user's specified separator or default one ('\\n').
2. If the input is a file, the situation is a lot more complex since different methods are used starting from simples
   ones and ending with more complicated ones:
   
   i. The filename is checked for ISBNs
   ii. The file metadata is searched for ISBNs with calibre's ``ebook-meta``
   iii. If the document is an archive, its files are extracted with ``7z`` and are each searched for ISBNs
   iv. If the document is not an archive, it is converted to *txt* and the data is searched for ISBNs
   v. If the conversion failed and OCR is enabled, OCR is run on the file and the resultant text file
      is searched for ISBNs
      
`:information_source:` Some details given

- When searching the content of an ebook, by default, the first 400 lines are searched for any
  ISBNs, then the last 50 lines **in reverse**, and finally the middle. This is done in order to maximize the chances that
  the extracted ISBNs are really related to the given ebook analyzed and not from other books mentioned in the middle of the text.
  
  The option `--reorder-files <#script-options>`_ controls the number of lines at the beginning and end of the document
  that will be searched for ISBNs.
- By default, only the first 7 and last 3 pages of a given document are OCRed. The option `--ocr-only-first-last-pages <#script-options>`_
  controls these numbers of pages.

For more details, see:

- The `documentation <https://github.com/na--/ebook-tools#searching-for-isbns-in-files>`_ for ``ebook-tools`` (shell scripts) or
- `search_file_for_isbns() <https://github.com/raul23/find-isbns/blob/926cbb49f8e97b6f71526bcaef5c810805ccad99/find_isbns/lib.py#L702>`_ 
  from ``lib.py`` (Python function where ISBNs search in files is implemented).

Examples
========
Find ISBNs in a string
----------------------
Through the script ``find_isbns.py``
""""""""""""""""""""""""""""""""""""
Find ISBNs in the string ``'978-159420172-1 978-1892391810 0000000000 0123456789 1111111111'``:

.. code-block:: terminal

   $ find_isbns '978-159420172-1 978-1892391810 0000000000 0123456789 1111111111'

If the input string contains *spaces*, it must be enclosed within single or double quotes.

**Output:**

.. code-block:: terminal

   Extracted ISBNs:
   9781594201721
   9781892391810

The other sequences ``'0000000000 0123456789 1111111111'`` are rejected because
they are matched with the regular expression `isbn_blacklist_regex <#script-options>`_.

By `default <#script-options>`__, the extracted ISBNs are separated by newlines, `\\n``.

|

`:information_source:` Multiple-lines string

If you want to search ISBNs in a **multiple-lines string**, e.g. you copied
many pages from a document, you must follow ``find_isbns`` with a
backslash ``\`` and enclose the string within **double quotes**, like so:

.. code-block:: terminal

   $ find_isbns \
   "
   978-159420172-1

   blablabla
   blablabla
   blablabla

   978-1892391810
   0000000000 0123456789 

   blablabla
   blablabla
   blablabla

   1111111111
   blablabla
   blablabla
   "
   
Through the API
"""""""""""""""
To find ISBNs in a string using the API:

.. code-block:: python

   from find_isbns.lib import find

   isbns = find('dsadasd9781892391810 sdafdf3143 978-159420172-1fdfd', isbn_ret_separator=' - ')
   # Do something with `isbns`

`:information_source:` The variable ``isbns`` will contain the two ISBNs found in the input string::

 '9781892391810 - 9781594201721'
 
By `default <#script-options>`_, the extracted ISBNs are separated by '\\n'. However, with the parameter ``isbn_ret_separator``
you can choose your own separator.

Signature of the function `find() <https://github.com/raul23/find-isbns/blob/7872ae9ead02d2976f4df81afa8e19755e451b1b/find_isbns/lib.py#L262>`_:

.. code-block:: python

   find(input_data, isbn_blacklist_regex=ISBN_BLACKLIST_REGEX,
        isbn_direct_files=ISBN_DIRECT_FILES,
        isbn_reorder_files=[400, 50],
        isbn_ignored_files=ISBN_IGNORED_FILES,
        isbn_regex=ISBN_REGEX,
        isbn_ret_separator='\n',
        djvu_convert_method=DJVU_CONVERT_METHOD,
        epub_convert_method=EPUB_CONVERT_METHOD,
        pdf_convert_method=PDF_CONVERT_METHOD,
        ocr_command=OCR_COMMAND,
        ocr_enabled='false',
        ocr_only_first_last_pages=(7, 3),
        **kwargs)

By default when using the API, the loggers are disabled. If you want to enable them, call the
function ``setup_log()`` (with the desired log level in all caps) at the beginning of your code before 
the conversion function ``convert()``:

.. code-block:: python

   from find_isbns.lib import find

   setup_log(logging_level='DEBUG')
   isbns = find('dsadasd9781892391810 sdafdf3143 978-159420172-1fdfd', isbn_ret_separator=' - ')
   # Do something with `isbns`

Find ISBNs in a pdf file
------------------------
Through the script ``find_isbns.py``
""""""""""""""""""""""""""""""""""""
.. code-block:: terminal

   $ find_isbns pdf_file.pdf
   
**Output:**

.. code-block:: terminal

   Searching file 'pdf_file.pdf' for ISBN numbers...
   Extracted ISBNs:
   9789580158448
   1000100111

The search for ISBNs starts in the first pages of the document to increase the
likelihood that the first extracted ISBN is the correct one. Then the last
pages are analyzed in reverse. Finally, the rest of the pages are searched.

Thus, in this example, the first extracted ISBN is the correct one
associated with the book since it was found in the first page. 

The last sequence ``1000100111`` was found in the middle of the document and is
not an ISBN even though it is a technically valid but wrong ISBN that the
regular expression `isbn_blacklist_regex <#script-options>`_ didn't catch.

`:information_source:` If the *pdf* file was made up of images, then the OCR can be applied like this::

 $ find_isbns ~/Data/convert/Book.pdf --ocr true

Through the API
"""""""""""""""
To find ISBNs in a given document using the API:

.. code-block:: python

   from find_isbns.lib import find
   
   isbns = find('/Users/test/Data/convert/Archive2.zip')
   # Do something with `isbns`

`:information_source:` Explaining the snippet of code

- The variable ``isbns`` will contain the ISBNs found in the input *zip* archive.
- If the *pdf* file was made up of images, then the OCR can be applied by setting the parameter ``ocr_enabled`` to 'true'
  for the ``find()`` function:

  .. code-block:: python

     from find_isbns.lib import find
   
     isbns = find('/Users/test/Data/convert/Book.pdf', ocr_enabled='true')
     # Do something with `isbns`

Cases tested
============
- *pdf* documents 
- *djvu* documents 
- *epub* documents
- *png* images using the ``--ocr true`` option
- *zip* archives with duplicate documents
