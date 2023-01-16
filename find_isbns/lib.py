"""Library that has useful functions for building other ebook management tools.

This is a Python port of `find-isbns.sh` and `lib.sh`_ from `ebook-tools` written in shell by
`na--`.

Ref.: 
- https://github.com/na--/ebook-tools/blob/master/find-isbns.sh
- https://github.com/na--/ebook-tools/blob/master/lib.sh
"""
import ast
import logging
import mimetypes
import os
import re
import shlex
import shutil
import string
import subprocess
import tempfile
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace

from find_isbns import __version__

# import ipdb

logger = logging.getLogger('find_lib')
logger.setLevel(logging.CRITICAL + 1)


# =====================
# Default config values
# =====================

# convert_to_txt options
# ======================
DJVU_CONVERT_METHOD = 'djvutxt'
EPUB_CONVERT_METHOD = 'epubtxt'
MSWORD_CONVERT_METHOD = 'textutil'  # not supported in script `find_isbns`
PDF_CONVERT_METHOD = 'pdftotext'

# Finding ISBNs options
# =====================
ISBN_REGEX = '(?<![0-9])(-?9-?7[789]-?)?((-?[0-9]-?){9}[0-9xX])(?![0-9])'
ISBN_BLACKLIST_REGEX = '^(0123456789|([0-9xX])\\2{9})$'
ISBN_DIRECT_FILES = '^text/(plain|xml|html)$'
ISBN_IGNORED_FILES = '^(image/(gif|svg.+)|application/(x-shockwave-flash|CDFV2|vnd.ms-opentype|x-font-ttf|x-dosexec|' \
                     'vnd.ms-excel|x-java-applet)|audio/.+|video/.+)$'
# False to disable the functionality or (first_lines,last_lines) to enable it
ISBN_REORDER_FILES = [400, 50]
ISBN_RET_SEPARATOR = '\n'
# NOTE: If you use Calibre versions that are older than 2.84, it's required to
# manually set the following option to an empty string
# ISBN_METADATA_FETCH_ORDER = ['Goodreads', 'Amazon.com', 'Google', 'ISBNDB', 'WorldCat xISBN', 'OZON.ru']

# Logging options
# ===============
LOGGING_FORMATTER = 'only_msg'
LOGGING_LEVEL = 'info'

# OCR options
# ===========
OCR_ENABLED = 'false'
OCR_COMMAND = 'tesseract_wrapper'
OCR_ONLY_FIRST_LAST_PAGES = (7, 3)


class Result:
    def __init__(self, stdout='', stderr='', returncode=None, args=None):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode
        self.args = args

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return f'stdout={str(self.stdout).strip()}, ' \
               f'stderr={str(self.stderr).strip()}, ' \
               f'returncode={self.returncode}, args={self.args}'


# ------
# Colors
# ------
COLORS = {
    'GREEN': '\033[0;36m',  # 32
    'RED': '\033[0;31m',
    'YELLOW': '\033[0;33m',  # 32
    'BLUE': '\033[0;34m',  #
    'VIOLET': '\033[0;35m',  #
    'BOLD': '\033[1m',
    'NC': '\033[0m',
}
_COLOR_TO_CODE = {
    'g': COLORS['GREEN'],
    'r': COLORS['RED'],
    'y': COLORS['YELLOW'],
    'b': COLORS['BLUE'],
    'v': COLORS['VIOLET'],
    'bold': COLORS['BOLD']
}


def color(msg, msg_color='y', bold_msg=False):
    msg_color = msg_color.lower()
    colors = list(_COLOR_TO_CODE.keys())
    assert msg_color in colors, f'Wrong color: {msg_color}. Only these ' \
                                f'colors are supported: {msg_color}'
    msg = bold(msg) if bold_msg else msg
    msg = msg.replace(COLORS['NC'], COLORS['NC']+_COLOR_TO_CODE[msg_color])
    return f"{_COLOR_TO_CODE[msg_color]}{msg}{COLORS['NC']}"


def blue(msg):
    return color(msg, 'b')


def bold(msg):
    return color(msg, 'bold')


def green(msg):
    return color(msg, 'g')


def red(msg):
    return color(msg, 'r')


def violet(msg):
    return color(msg, 'v')


def yellow(msg):
    return color(msg)


def catdoc(input_file, output_file):
    cmd = f'catdoc "{input_file}"'
    args = shlex.split(cmd)
    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # Everything on the stdout must be copied to the output file
    if result.returncode == 0:
        with open(output_file, 'w') as f:
            f.write(result.stdout)
    return convert_result_from_shell_cmd(result)


# Ref.: https://stackoverflow.com/a/28909933
def command_exists(cmd):
    return shutil.which(cmd) is not None


def convert_result_from_shell_cmd(old_result):
    new_result = Result()

    for attr_name, new_val in new_result.__dict__.items():
        old_val = getattr(old_result, attr_name)
        if old_val is None:
            shell_args = getattr(old_result, 'args', None)
            # logger.debug(f'result.{attr_name} is None. Shell args: {shell_args}')
        else:
            if isinstance(new_val, str):
                try:
                    new_val = old_val.decode('UTF-8')
                except (AttributeError, UnicodeDecodeError) as e:
                    if type(e) == UnicodeDecodeError:
                        # old_val = b'...'
                        new_val = old_val.decode('unicode_escape')
                    else:
                        # `old_val` already a string
                        # logger.debug('Error decoding old value: {}'.format(old_val))
                        # logger.debug(e.__repr__())
                        # logger.debug('Value already a string. No decoding necessary')
                        new_val = old_val
                try:
                    new_val = ast.literal_eval(new_val)
                except (SyntaxError, ValueError) as e:
                    # NOTE: ValueError might happen if value consists of [A-Za-z]
                    # logger.debug('Error evaluating the value: {}'.format(old_val))
                    # logger.debug(e.__repr__())
                    # logger.debug('Aborting evaluation of string. Will consider
                    # the string as it is')
                    pass
            else:
                new_val = old_val
        setattr(new_result, attr_name, new_val)
    return new_result


# Tries to convert the supplied ebook file into .txt. It uses calibre's
# ebook-convert tool. For optimization, if present, it will use pdftotext
# for pdfs, catdoc for word files and djvutxt for djvu files.
# Ref.: https://bit.ly/2HXdf2I
def convert_to_txt(input_file, output_file, mime_type,
                   djvu_convert_method=DJVU_CONVERT_METHOD,
                   epub_convert_method=EPUB_CONVERT_METHOD,
                   msword_convert_method=MSWORD_CONVERT_METHOD,
                   pdf_convert_method=PDF_CONVERT_METHOD, **kwargs):
    if mime_type.startswith('image/vnd.djvu') \
         and djvu_convert_method == 'djvutxt' and command_exists('djvutxt'):
        logger.debug('The file looks like a djvu, using djvutxt to extract the text')
        result = djvutxt(input_file, output_file)
    elif mime_type.startswith('application/epub+zip') \
            and epub_convert_method == 'epubtxt' and command_exists('unzip'):
        logger.debug('The file looks like an epub, using epubtxt to extract the text')
        result = epubtxt(input_file, output_file)
    elif mime_type == 'application/msword' \
            and msword_convert_method in ['catdoc', 'textutil'] \
            and (command_exists('catdoc') or command_exists('textutil')):
        msg = 'The file looks like a doc, using {} to extract the text'
        if command_exists('catdoc'):
            logger.debug(msg.format('catdoc'))
            result = catdoc(input_file, output_file)
        else:
            logger.debug(msg.format('textutil'))
            result = textutil(input_file, output_file)
    elif mime_type == 'application/pdf' and pdf_convert_method == 'pdftotext' \
            and command_exists('pdftotext'):
        logger.debug('The file looks like a pdf, using pdftotext to extract the text')
        result = pdftotext(input_file, output_file)
    elif (not mime_type.startswith('image/vnd.djvu')) \
            and mime_type.startswith('image/'):
        msg = f'The file looks like a normal image ({mime_type}), skipping ' \
              'ebook-convert usage!'
        logger.debug(msg)
        return convert_result_from_shell_cmd(Result(stderr=msg, returncode=1))
    else:
        logger.debug(f"Trying to use calibre's ebook-convert to convert the {mime_type} file to .txt")
        result = ebook_convert(input_file, output_file)
    return result


def djvutxt(input_file, output_file, pages=None):
    pages = f'--page={pages}' if pages else ''
    cmd = f'djvutxt "{input_file}" "{output_file}" {pages}'
    args = shlex.split(cmd)
    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return convert_result_from_shell_cmd(result)


def ebook_convert(input_file, output_file):
    cmd = f'ebook-convert "{input_file}" "{output_file}"'
    args = shlex.split(cmd)
    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return convert_result_from_shell_cmd(result)


def epubtxt(input_file, output_file):
    cmd = f'unzip -c "{input_file}"'
    args = shlex.split(cmd)
    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if not result.stderr:
        text = str(result.stdout)
        with open(output_file, 'w') as f:
            f.write(text)
        result.stdout = text
    return convert_result_from_shell_cmd(result)


def extract_archive(input_file, output_file):
    cmd = f'7z x -o"{output_file}" "{input_file}"'
    args = shlex.split(cmd)
    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return convert_result_from_shell_cmd(result)


def find(input_data, isbn_blacklist_regex=ISBN_BLACKLIST_REGEX,
         isbn_direct_files=ISBN_DIRECT_FILES,
         isbn_reorder_files=ISBN_REORDER_FILES,
         isbn_ignored_files=ISBN_IGNORED_FILES,
         isbn_regex=ISBN_REGEX,
         isbn_ret_separator=ISBN_RET_SEPARATOR,
         djvu_convert_method=DJVU_CONVERT_METHOD,
         epub_convert_method=EPUB_CONVERT_METHOD,
         pdf_convert_method=PDF_CONVERT_METHOD,
         ocr_command=OCR_COMMAND,
         ocr_enabled=OCR_ENABLED,
         ocr_only_first_last_pages=OCR_ONLY_FIRST_LAST_PAGES,
         **kwargs):
    if input_data is None:
        logger.warning(yellow('`input_data` is None!'))
        return 1
    func_params = locals().copy()
    # Check if input data is a file path or a string
    try:
        if Path(input_data).is_file():
            logger.debug(f'The input data is a file path')
            isbns = search_file_for_isbns(input_data, **func_params)
        else:
            logger.debug(f'The input data might be a string')
            isbns = find_isbns(input_data, **func_params)
    except OSError as e:
        # Happens for example if ebook-metas instead of ebook-meta ("No such file or directory: 'ebook-metas'")
        if e.args[0]:
            logger.debug(f'{e.args[1]}: the input data might be a string')
            isbns = find_isbns(input_data, **func_params)
        else:
            raise e
    if isbns:
        logger.info(f"Extracted ISBNs:\n{isbns}")
        return isbns
    else:
        logger.info("No ISBNs could be found!")
        return None


# Searches the input string for ISBN-like sequences and removes duplicates and
# finally validates them using is_isbn_valid() and returns them separated by
# `isbn_ret_separator`
# Ref.: https://bit.ly/2HyLoSQ
def find_isbns(input_str, isbn_blacklist_regex=ISBN_BLACKLIST_REGEX,
               isbn_regex=ISBN_REGEX, isbn_ret_separator=ISBN_RET_SEPARATOR,
               **kwargs):
    isbns = []
    # TODO: they are using grep -oP
    # Ref.: https://bit.ly/2HUbnIs
    # Remove spaces
    # input_str = input_str.replace(' ', '')
    matches = re.finditer(isbn_regex, input_str)
    for i, match in enumerate(matches):
        match = match.group()
        # Remove everything except numbers [0-9], 'x', and 'X'
        # NOTE: equivalent to UNIX command `tr -c -d '0-9xX'`
        # TODO 1: they don't remove \n in their code
        # TODO 2: put the following in a function
        del_tab = string.printable[10:].replace('x', '').replace('X', '')
        tran_tab = str.maketrans('', '', del_tab)
        match = match.translate(tran_tab)
        # Only keep unique ISBNs
        if match not in isbns:
            # Validate ISBN
            if is_isbn_valid(match):
                if re.match(isbn_blacklist_regex, match):
                    logger.debug(f'Wrong ISBN (blacklisted): {match}')
                else:
                    logger.debug(f'Valid ISBN found: {match}')
                    isbns.append(match)
            else:
                logger.debug(f'Invalid ISBN found: {match}')
        else:
            logger.debug(f'Non-unique ISBN found: {match}')
    if not isbns:
        msg = f'"{input_str}"' if len(input_str) < 100 else ''
        logger.debug(f'No ISBN found in the input string {msg}')
    return isbn_ret_separator.join(isbns)


def get_all_isbns_from_archive(
        file_path, isbn_blacklist_regex=ISBN_BLACKLIST_REGEX,
        isbn_direct_files=ISBN_DIRECT_FILES,
        isbn_reorder_files=ISBN_DIRECT_FILES,
        isbn_ignored_files=ISBN_IGNORED_FILES, isbn_regex=ISBN_REGEX,
        isbn_ret_separator=ISBN_RET_SEPARATOR, ocr_command=OCR_COMMAND,
        ocr_enabled=OCR_ENABLED,
        ocr_only_first_last_pages=OCR_ONLY_FIRST_LAST_PAGES, **kwargs):
    func_params = locals().copy()
    func_params.pop('file_path')
    all_isbns = []
    tmpdir = tempfile.mkdtemp()
    logger.debug(f"Trying to decompress '{os.path.basename(file_path)}' and "
                 "recursively scan the contents")
    logger.debug(f"Decompressing '{file_path}' into tmp folder '{tmpdir}'")
    result = extract_archive(file_path, tmpdir)
    if result.stderr:
        logger.debug('Error extracting the file (probably not an archive)! '
                     'Removing tmp dir...')
        logger.debug(result.stderr)
        remove_tree(tmpdir)
        return ''
    logger.debug(f"Archive extracted successfully in '{tmpdir}', scanning "
                 f"contents recursively...")
    # TODO: Ref.: https://stackoverflow.com/a/2759553
    # TODO: ignore .DS_Store
    for path, dirs, files in os.walk(tmpdir, topdown=False):
        # TODO: they use flag options for sorting the directory contents
        # see https://github.com/na--/ebook-tools#miscellaneous-options [FILE_SORT_FLAGS]
        for file_to_check in files:
            # TODO: add debug_prefixer
            file_to_check = os.path.join(path, file_to_check)
            isbns = search_file_for_isbns(file_to_check, **func_params)
            if isbns:
                logger.debug(f"Found ISBNs\n{isbns}")
                # TODO: two prints, one for stderror and the other for stdout
                logger.debug(isbns.replace(isbn_ret_separator, '\n'))
                for isbn in isbns.split(isbn_ret_separator):
                    if isbn not in all_isbns:
                        all_isbns.append(isbn)
            logger.debug(f'Removing {file_to_check}...')
            remove_file(file_to_check)
        if len(os.listdir(path)) == 0 and path != tmpdir:
            os.rmdir(path)
        elif path == tmpdir:
            if len(os.listdir(tmpdir)) == 1 and '.DS_Store' in tmpdir:
                remove_file(os.path.join(tmpdir, '.DS_Store'))
    logger.debug(f"Removing temporary folder '{tmpdir}' (should be empty)...")
    if is_dir_empty(tmpdir):
        remove_tree(tmpdir)
    return isbn_ret_separator.join(all_isbns)


def get_ebook_metadata(file_path):
    # TODO: add `ebook-meta` in PATH, right now it is only working for mac
    cmd = f'ebook-metas "{file_path}"'
    args = shlex.split(cmd)
    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return convert_result_from_shell_cmd(result)


# Using Python built-in module mimetypes
def get_mime_type(file_path):
    return mimetypes.guess_type(file_path)[0]


# Return number of pages in a djvu document
def get_pages_in_djvu(file_path):
    cmd = f'djvused -e "n" "{file_path}"'
    args = shlex.split(cmd)
    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return convert_result_from_shell_cmd(result)


# Return number of pages in a pdf document
def get_pages_in_pdf(file_path, cmd='mdls'):
    assert cmd in ['mdls', 'pdfinfo']
    if command_exists(cmd) and cmd == 'mdls':
        cmd = f'mdls -raw -name kMDItemNumberOfPages "{file_path}"'
        args = shlex.split(cmd)
        result = subprocess.run(args, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        if '(null)' in str(result.stdout):
            return get_pages_in_pdf(file_path, cmd='pdfinfo')
    else:
        cmd = f'pdfinfo "{file_path}"'
        args = shlex.split(cmd)
        result = subprocess.run(args, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        if result.returncode == 0:
            result = convert_result_from_shell_cmd(result)
            result.stdout = int(re.findall('^Pages:\s+([0-9]+)',
                                           result.stdout,
                                           flags=re.MULTILINE)[0])
            return result
    return convert_result_from_shell_cmd(result)


# Checks if directory is empty
# Ref.: https://stackoverflow.com/a/47363995
def is_dir_empty(path):
    return next(os.scandir(path), None) is None


# Validates ISBN-10 and ISBN-13 numbers
# Ref.: https://bit.ly/2HO2lMD
def is_isbn_valid(isbn):
    # TODO: there is also a Python package for validating ISBNs (but dependency)
    # Remove whitespaces (space, tab, newline, and so on), '-', and capitalize all
    # characters (ISBNs can consist of numbers [0-9] and the letters [xX])
    isbn = ''.join(isbn.split())
    isbn = isbn.replace('-', '')
    isbn = isbn.upper()

    sum = 0
    # Case 1: ISBN-10
    if len(isbn) == 10:
        for i in range(len(isbn)):
            if i == 9 and isbn[i] == 'X':
                number = 10
            else:
                number = int(isbn[i])
            sum += (number * (10 - i))
        if sum % 11 == 0:
            return True
    # Case 2: ISBN-13
    elif len(isbn) == 13:
        if isbn[0:3] in ['978', '979']:
            for i in range(0, len(isbn), 2):
                sum += int(isbn[i])
            for i in range(1, len(isbn), 2):
                sum += (int(isbn[i])*3)
            if sum % 10 == 0:
                return True
    return False


def isalnum_in_file(file_path):
    with open(file_path, 'r', encoding="utf8", errors='ignore') as f:
        isalnum = False
        for line in f:
            for ch in line:
                if ch.isalnum():
                    isalnum = True
                    break
            if isalnum:
                break
    return isalnum


def namespace_to_dict(ns):
    namspace_classes = [Namespace, SimpleNamespace]
    # TODO: check why not working anymore
    # if isinstance(ns, SimpleNamespace):
    if type(ns) in namspace_classes:
        adict = vars(ns)
    else:
        adict = ns
    for k, v in adict.items():
        # if isinstance(v, SimpleNamespace):
        if type(v) in namspace_classes:
            v = vars(v)
            adict[k] = v
        if isinstance(v, dict):
            namespace_to_dict(v)
    return adict


# OCR on a pdf, djvu document or image
# NOTE: If pdf or djvu document, then first needs to be converted to image and then OCR
def ocr_file(file_path, output_file, mime_type,
             ocr_command=OCR_COMMAND,
             ocr_only_first_last_pages=OCR_ONLY_FIRST_LAST_PAGES, **kwargs):
    # Convert pdf to png image
    def convert_pdf_page(page, input_file, output_file):
        cmd = f'gs -dSAFER -q -r300 -dFirstPage={page} -dLastPage={page} ' \
              '-dNOPAUSE -dINTERPOLATE -sDEVICE=png16m ' \
              f'-sOutputFile="{output_file}" "{input_file}" -c quit'
        args = shlex.split(cmd)
        result = subprocess.run(args, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        return convert_result_from_shell_cmd(result)

    # Convert djvu to tif image
    def convert_djvu_page(page, input_file, output_file):
        cmd = f'ddjvu -page={page} -format=tif "{input_file}" "{output_file}"'
        args = shlex.split(cmd)
        result = subprocess.run(args, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        return convert_result_from_shell_cmd(result)

    if mime_type.startswith('application/pdf'):
        result = get_pages_in_pdf(file_path)
        num_pages = result.stdout
        logger.debug(f"Result of '{get_pages_in_pdf.__name__}()' on '{file_path}':\n{result}")
        page_convert_cmd = convert_pdf_page
    elif mime_type.startswith('image/vnd.djvu'):
        result = get_pages_in_djvu(file_path)
        num_pages = result.stdout
        logger.debug(f"Result of '{get_pages_in_djvu.__name__}()' on '{file_path}':\n{result}")
        page_convert_cmd = convert_djvu_page
    elif mime_type.startswith('image/'):
        logger.debug(f"Running OCR on file '{file_path}' and with mime type '{mime_type}'...")
        if ocr_command in globals():
            result = eval(f'{ocr_command}("{file_path}", "{output_file}")')
            logger.debug(f"Result of '{ocr_command}':\n{result}")
            return 0
        else:
            msg = red("Function '{ocr_command}' doesn't exit.")
            logger.error(f'{msg}')
            return 1
    else:
        logger.error(f"{red('Unsupported mime type')} '{mime_type}'!")
        return 1

    if result.returncode == 1:
        err_msg = result.stdout if result.stdout else result.stderr
        msg = "Couldn't get number of pages:"
        logger.error(f"{red(msg)} '{str(err_msg).strip()}'")
        return 1

    if ocr_command not in globals():
        msg = red("Function '{ocr_command}' doesn't exit.")
        logger.error(f'{msg}')
        return 1

    logger.debug(f"The file '{file_path}' has {num_pages} page{'s' if num_pages > 1 else ''}")
    logger.debug(f'mime type: {mime_type}')

    # Pre-compute the list of pages to process based on ocr_only_first_last_pages
    if ocr_only_first_last_pages:
        ocr_first_pages, ocr_last_pages = [int(i) for i in ocr_only_first_last_pages.split(',')]
        pages_to_process = [i for i in range(1, ocr_first_pages + 1)]
        pages_to_process.extend([i for i in range(num_pages + 1 - ocr_last_pages, num_pages + 1)])
    else:
        # ocr_only_first_last_pages is False
        logger.debug('ocr_only_first_last_pages is False')
        logger.warning(f"{yellow('OCR will be applied to all ({pages}) pages of the document')}")
        pages_to_process = [i for i in range(1, num_pages+1)]
    logger.debug(f'Pages to process: {pages_to_process}')

    text = ''
    for i, page in enumerate(pages_to_process, start=1):
        logger.debug(f'Processing page {i} of {len(pages_to_process)}')
        # Make temporary files
        tmp_file = tempfile.mkstemp()[1]
        tmp_file_txt = tempfile.mkstemp(suffix='.txt')[1]
        logger.debug(f'Running OCR of page {page}...')
        logger.debug(f'Using tmp files {tmp_file} and {tmp_file_txt}')
        # doc(pdf, djvu) --> image(png, tiff)
        result = page_convert_cmd(page, file_path, tmp_file)
        if result.returncode == 0:
            logger.debug(f"Result of {page_convert_cmd.__name__}():\n{result}")
            # image --> text
            logger.debug(f"Running the '{ocr_command}'...")
            result = eval(f'{ocr_command}("{tmp_file}", "{tmp_file_txt}")')
            if result.returncode == 0:
                logger.debug(f"Result of '{ocr_command}':\n{result}")
                with open(tmp_file_txt, 'r') as f:
                    data = f.read()
                    # logger.debug(f"Text content of page {page}:\n{data}")
                text += data
            else:
                msg = red(f"Image couldn't be converted to text: {result}")
                logger.error(f'{msg}')
                logger.error(f'Skipping current page ({page})')
        else:
            msg = red(f"Document couldn't be converted to image: {result}")
            logger.error(f'{msg}')
            logger.error(f'Skipping current page ({page})')
        # Remove temporary files
        logger.debug('Cleaning up tmp files')
        remove_file(tmp_file)
        remove_file(tmp_file_txt)
    # Everything on the stdout must be copied to the output file
    logger.debug('Saving the text content')
    with open(output_file, 'w') as f:
        f.write(text)
    return 0


def pdftotext(input_file, output_file, first_page_to_convert=None, last_page_to_convert=None):
    first_page = f'-f {first_page_to_convert}' if first_page_to_convert else ''
    last_page = f'-l {last_page_to_convert}' if last_page_to_convert else ''
    pages = f'{first_page} {last_page}'.strip()
    cmd = f'pdftotext "{input_file}" "{output_file}" {pages}'
    args = shlex.split(cmd)
    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return convert_result_from_shell_cmd(result)


def remove_file(file_path):
    # Ref.: https://stackoverflow.com/a/42641792
    try:
        os.remove(file_path)
        return 0
    except OSError as e:
        logger.error(red(f'{e.filename} - {e.strerror}.'))
        return 1


# Recursively delete a directory tree, including the parent directory
# Ref.: https://stackoverflow.com/a/186236
def remove_tree(file_path):
    try:
        shutil.rmtree(file_path)
        return 0
    except Exception as e:
        logger.error(f'Error: {e.filename} - {e.strerror}.')
        return 1


# If `isbn_reorder_files` is enabled, reorders the specified file
# according to the values of `isbn_rf_scan_first` and
# `isbn_rf_reverse_last`
# Ref.: https://bit.ly/2JuaEKw
# TODO: order params and other places
def reorder_file_content(
        file_path,
        isbn_reorder_files=ISBN_REORDER_FILES, **kwargs):
    if isbn_reorder_files:
        isbn_rf_scan_first = isbn_reorder_files[0]
        isbn_rf_reverse_last = isbn_reorder_files[1]
        logger.debug('Reordering input file (if possible), read first '
                     f'{isbn_rf_scan_first} lines normally, then read '
                     f'last {isbn_rf_reverse_last} lines in reverse and '
                     'then read the rest')
        # TODO: try out with big file, more than 800 pages (approx. 73k lines)
        # TODO: see alternatives for reading big file @
        # https://stackoverflow.com/a/4999741 (mmap),
        # https://stackoverflow.com/a/24809292 (linecache),
        # https://stackoverflow.com/a/42733235 (buffer)
        with open(file_path, 'r') as f:
            # Read whole file as a list of lines
            # TODO: do we remove newlines? e.g. with f.read().rstrip("\n")
            data = f.readlines()
            # Read the first ISBN_GREP_RF_SCAN_FIRST lines of the file text
            first_part = data[:isbn_rf_scan_first]
            del data[:isbn_rf_scan_first]
            # Read the last part and reverse it
            last_part = data[-isbn_rf_reverse_last:]
            if last_part:
                last_part.reverse()
                del data[-isbn_rf_reverse_last:]
            # Read the middle part of the file text
            middle_part = data
            # TODO: try out with large lists, if efficiency is a concern then
            # check itertools.chain
            # ref.: https://stackoverflow.com/a/4344735
            # Concatenate the three parts: first, last part (reversed), and
            # middle part
            data = first_part + last_part + middle_part
            data = "".join(data)
    else:
        logger.debug('Since `isbn_reorder_file`s is False, input file will '
                     'not be reordered')
        with open(file_path, 'r') as f:
            # TODO: do we remove newlines? e.g. with f.read().rstrip("\n")
            # Read whole content of file as a string
            data = f.read()
    return data


# Tries to find ISBN numbers in the given ebook file by using progressively
# more "expensive" tactics.
# These are the steps:
# 1. Check the supplied file name for ISBNs (the path is ignored)
# 2. If the MIME type of the file matches `isbn_direct_files`, search the
#    file contents directly for ISBNs
# 3. If the MIME type matches `isbn_ignored_files`, the function returns early
#    with no results
# 4. Check the file metadata from calibre's `ebook-meta` for ISBNs
# 5. Try to extract the file as an archive with `7z`; if successful,
#    recursively call search_file_for_isbns for all the extracted files
# 6. If the file is not an archive, try to convert it to a .txt file
#    via convert_to_txt()
# 7. If OCR is enabled and convert_to_txt() fails or its result is empty,
#    try OCR-ing the file. If the result is non-empty but does not contain
#    ISBNs and OCR_ENABLED is set to "always", run OCR as well.
# Ref.: https://bit.ly/2r28US2
def search_file_for_isbns(
        file_path, isbn_blacklist_regex=ISBN_BLACKLIST_REGEX,
        isbn_direct_files=ISBN_DIRECT_FILES,
        isbn_reorder_files=ISBN_REORDER_FILES,
        isbn_ignored_files=ISBN_IGNORED_FILES, isbn_regex=ISBN_REGEX,
        isbn_ret_separator=ISBN_RET_SEPARATOR, ocr_command=OCR_COMMAND,
        djvu_convert_method=DJVU_CONVERT_METHOD,
        epub_convert_method=EPUB_CONVERT_METHOD,
        pdf_convert_method=PDF_CONVERT_METHOD,
        ocr_enabled=OCR_ENABLED,
        ocr_only_first_last_pages=OCR_ONLY_FIRST_LAST_PAGES, **kwargs):
    func_params = locals().copy()
    func_params.pop('file_path')
    basename = os.path.basename(file_path)
    logger.info(f"Searching file '{basename}' for ISBN numbers...")
    # Step 1: check the filename for ISBNs
    # TODO: make sure that we return an empty string when we can't find ISBNs
    logger.debug('check the filename for ISBNs')
    isbns = find_isbns(basename, **func_params)
    if isbns:
        logger.debug("Extracted ISBNs '{}' from the file name!".format(
            isbns.replace('\n', '; ')))
        return isbns

    # Steps 2-3: (2) if valid MIME type, search file contents for ISBNs and
    # (3) if invalid MIME type, exit without results
    mime_type = get_mime_type(file_path)
    if re.match(isbn_direct_files, mime_type):
        logger.debug('Ebook is in text format, trying to find ISBN directly')
        data = reorder_file_content(file_path, **func_params)
        isbns = find_isbns(data, **func_params)
        if isbns:
            logger.debug(f"Extracted ISBNs from the text file contents:\n{isbns}")
        else:
            logger.debug('Did not find any ISBNs')
        return isbns
    elif re.match(isbn_ignored_files, mime_type):
        logger.info('The file type is in the blacklist, ignoring...')
        return isbns

    # Step 4: check the file metadata from calibre's `ebook-meta` for ISBNs
    logger.debug("check the file metadata from calibre's `ebook-meta` for ISBNs")
    if command_exists('ebook-metadata'):
        ebookmeta = get_ebook_metadata(file_path)
        logger.debug(f'Ebook metadata:\n{ebookmeta.stdout}')
        isbns = find_isbns(ebookmeta.stdout, **func_params)
        if isbns:
            logger.debug(f"Extracted ISBNs from calibre ebook metadata:\n{isbns}'")
            return isbns
    else:
        logger.debug("`ebook-metadata` is not found!")

    # Step 5: decompress with 7z
    logger.debug('decompress with 7z')
    if not mime_type.startswith('application/epub+zip'):
        isbns = get_all_isbns_from_archive(file_path, **func_params)
        if isbns:
            logger.debug(f"Extracted ISBNs from the archive file:\n{isbns}")
            return isbns

    # Step 6: convert file to .txt
    try_ocr = False
    tmp_file_txt = tempfile.mkstemp(suffix='.txt')[1]
    logger.debug(f"Converting ebook to text format...")
    logger.debug(f"Temp file: {tmp_file_txt}")

    # TODO: important, takes a long time for pdfs (not djvu)
    result = convert_to_txt(file_path, tmp_file_txt, mime_type, **func_params)
    if result.returncode == 0:
        logger.debug('Conversion to text was successful, checking the result...')
        with open(tmp_file_txt, 'r') as f:
            data = f.read()
        if not re.search('[A-Za-z0-9]+', data):
            logger.debug('The converted txt with size '
                         f'{os.stat(tmp_file_txt).st_size} bytes does not seem '
                         'to contain text')
            logger.debug(f'First 1000 characters:\n{data[:1000]}')
            try_ocr = True
        else:
            data = reorder_file_content(tmp_file_txt, **func_params)
            isbns = find_isbns(data, **func_params)
            if isbns:
                logger.debug(f"Text output contains ISBNs:\n{isbns}")
            elif ocr_enabled == 'always':
                logger.debug('We will try OCR because the successfully converted '
                             'text did not have any ISBNs')
                try_ocr = True
            else:
                logger.debug('Did not find any ISBNs and will NOT try OCR')
    else:
        logger.warning(yellow('There was an error converting the book to txt format:'))
        logger.warning(yellow(result.stderr))
        try_ocr = True

    # Step 7: OCR the file
    if not isbns and ocr_enabled != 'false' and try_ocr:
        logger.debug('Trying to run OCR on the file...')
        if ocr_file(file_path, tmp_file_txt, mime_type, **func_params) == 0:
            logger.debug('OCR was successful, checking the result...')
            data = reorder_file_content(tmp_file_txt, **func_params)
            isbns = find_isbns(data, **func_params)
            if isbns:
                logger.debug(f"Text output contains ISBNs {isbns}!")
            else:
                logger.debug('Did not find any ISBNs in the OCR output')
        else:
            logger.info('There was an error while running OCR!')

    logger.debug(f'Removing {tmp_file_txt}...')
    remove_file(tmp_file_txt)

    if isbns:
        logger.debug(f"Returning the found ISBNs:\n{isbns}")
    else:
        logger.debug(f'Could not find any ISBNs in {file_path} :(')

    return isbns


def setup_log(quiet=False, verbose=False, logging_level=LOGGING_LEVEL,
              logging_formatter=LOGGING_FORMATTER):
    if not quiet:
        for logger_name in ['find_script', 'find_lib']:
            logger_ = logging.getLogger(logger_name)
            if verbose:
                logger_.setLevel('DEBUG')
            else:
                logging_level = logging_level.upper()
                logger_.setLevel(logging_level)
            # Create console handler and set level
            ch = logging.StreamHandler()
            ch.setLevel(logging.DEBUG)
            # Create formatter
            if logging_formatter:
                formatters = {
                    'console': '%(name)-10s | %(levelname)-8s | %(message)s',
                    # 'console': '%(asctime)s | %(levelname)-8s | %(message)s',
                    'only_msg': '%(message)s',
                    'simple': '%(levelname)-8s %(message)s',
                    'verbose': '%(asctime)s | %(name)-10s | %(levelname)-8s | %(message)s'
                }
                formatter = logging.Formatter(formatters[logging_formatter])
                # Add formatter to ch
                ch.setFormatter(formatter)
            # Add ch to logger
            logger_.addHandler(ch)
        # =============
        # Start logging
        # =============
        logger.debug("Running {} v{}".format(__file__, __version__))
        logger.debug("Verbose option {}".format("enabled" if verbose else "disabled"))


# OCR: convert image to text
def tesseract_wrapper(input_file, output_file):
    cmd = f'tesseract "{input_file}" stdout --psm 12'
    args = shlex.split(cmd)
    result = subprocess.run(args,
                            stdout=open(output_file, 'w'),
                            stderr=subprocess.PIPE,
                            encoding='utf-8',
                            bufsize=4096)
    return convert_result_from_shell_cmd(result)


# macOS equivalent for catdoc
# See https://stackoverflow.com/a/44003923/14664104
def textutil(input_file, output_file):
    cmd = f'textutil -convert txt "{input_file}" -output "{output_file}"'
    args = shlex.split(cmd)
    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return convert_result_from_shell_cmd(result)


def touch(path, mode=0o666, exist_ok=True):
    logger.debug(f"Creating file: '{path}'")
    Path(path).touch(mode, exist_ok)
    logger.debug("File created!")
