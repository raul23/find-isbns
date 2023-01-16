"""
The script find_isbns.py finds ISBNs from ebooks (pdf, djvu, epub) or any string
given as input to the script .

It is based on the great ebook-tools which is written in shell by na--.

Ref.: https://github.com/na--/ebook-tools
"""
import argparse
import codecs
import logging
import os

from find_isbns import __version__
from find_isbns.lib import (find, namespace_to_dict, setup_log, blue, green, red, yellow,
                            DJVU_CONVERT_METHOD, EPUB_CONVERT_METHOD, PDF_CONVERT_METHOD,
                            ISBN_REGEX, ISBN_BLACKLIST_REGEX, ISBN_DIRECT_FILES,
                            ISBN_IGNORED_FILES, ISBN_REORDER_FILES, ISBN_RET_SEPARATOR,
                            OCR_ENABLED, OCR_ONLY_FIRST_LAST_PAGES,
                            LOGGING_FORMATTER, LOGGING_LEVEL)

# import ipdb

logger = logging.getLogger('find_script')

# =====================
# Default config values
# =====================

# Misc options
# ============
QUIET = False
OUTPUT_FILE = 'output.txt'


class ArgumentParser(argparse.ArgumentParser):

    def error(self, message):
        print_(self.format_usage().splitlines()[0])
        self.exit(2, red(f'\nerror: {message}\n'))


class MyFormatter(argparse.HelpFormatter):
    """
    Corrected _max_action_length for the indenting of subactions
    """

    def add_argument(self, action):
        if action.help is not argparse.SUPPRESS:

            # find all invocations
            get_invocation = self._format_action_invocation
            invocations = [get_invocation(action)]
            current_indent = self._current_indent
            for subaction in self._iter_indented_subactions(action):
                # compensate for the indent that will be added
                indent_chg = self._current_indent - current_indent
                added_indent = 'x' * indent_chg
                invocations.append(added_indent + get_invocation(subaction))
            # print_('inv', invocations)

            # update the maximum item length
            invocation_length = max([len(s) for s in invocations])
            action_length = invocation_length + self._current_indent
            self._action_max_length = max(self._action_max_length,
                                          action_length)

            # add the item to the list
            self._add_item(self._format_action, [action])

    # Ref.: https://stackoverflow.com/a/23941599/14664104
    def _format_action_invocation(self, action):
        if not action.option_strings:
            metavar, = self._metavar_formatter(action, action.dest)(1)
            return metavar
        else:
            parts = []
            # if the Optional doesn't take a value, format is:
            #    -s, --long
            if action.nargs == 0:
                parts.extend(action.option_strings)

            # if the Optional takes a value, format is:
            #    -s ARGS, --long ARGS
            # change to
            #    -s, --long ARGS
            else:
                default = action.dest.upper()
                args_string = self._format_args(action, default)
                for option_string in action.option_strings:
                    # parts.append('%s %s' % (option_string, args_string))
                    parts.append('%s' % option_string)
                parts[-1] += ' %s'%args_string
            return ', '.join(parts)


class OptionsChecker:
    def __init__(self, add_opts, remove_opts):
        self.add_opts = init_list(add_opts)
        self.remove_opts = init_list(remove_opts)

    def check(self, opt_name):
        return not self.remove_opts.count(opt_name) or \
               self.add_opts.count(opt_name)


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


# General options
def add_general_options(parser, add_opts=None, remove_opts=None,
                        program_version=__version__,
                        title='General options'):
    checker = OptionsChecker(add_opts, remove_opts)
    parser_general_group = parser.add_argument_group(title=title)
    if checker.check('help'):
        parser_general_group.add_argument('-h', '--help', action='help',
                                          help='Show this help message and exit.')
    if checker.check('version'):
        parser_general_group.add_argument(
            '-v', '--version', action='version',
            version=f'%(prog)s v{program_version}',
            help="Show program's version number and exit.")
    if checker.check('quiet'):
        parser_general_group.add_argument(
            '-q', '--quiet', action='store_true',
            help='Enable quiet mode, i.e. nothing will be printed.')
    if checker.check('verbose'):
        parser_general_group.add_argument(
            '--verbose', action='store_true',
            help='Print various debugging information, e.g. print traceback '
                 'when there is an exception.')
    if checker.check('log-level'):
        parser_general_group.add_argument(
            '--log-level', dest='logging_level',
            choices=['debug', 'info', 'warning', 'error'], default=LOGGING_LEVEL,
            help='Set logging level.' + get_default_message(LOGGING_LEVEL))
    if checker.check('log-format'):
        parser_general_group.add_argument(
            '--log-format', dest='logging_formatter',
            choices=['console', 'only_msg', 'simple',], default=LOGGING_FORMATTER,
            help='Set logging formatter.' + get_default_message(LOGGING_FORMATTER))
    return parser_general_group


# Ref.: https://stackoverflow.com/a/5187097/14664104
def decode(value):
    return codecs.decode(value, 'unicode_escape')


def get_default_message(default_value):
    return green(f' (default: {default_value})')


def init_list(list_):
    return [] if list_ is None else list_


def print_(msg):
    global QUIET
    if not QUIET:
        print(msg)


# Ref.: https://stackoverflow.com/a/4195302/14664104
def required_length(nmin, nmax, is_list=True):
    class RequiredLength(argparse.Action):
        def __call__(self, parser, args, values, option_string=None):
            if isinstance(values, str):
                tmp_values = [values]
            else:
                tmp_values = values
            if not nmin <= len(tmp_values) <= nmax:
                if nmin == nmax:
                    msg = 'argument "{f}" requires {nmin} arguments'.format(
                        f=self.dest, nmin=nmin, nmax=nmax)
                else:
                    msg = 'argument "{f}" requires between {nmin} and {nmax} ' \
                          'arguments'.format(f=self.dest, nmin=nmin, nmax=nmax)
                raise argparse.ArgumentTypeError(msg)
            setattr(args, self.dest, values)
    return RequiredLength


def setup_argparser():
    width = os.get_terminal_size().columns - 5
    name_input = 'input_data'
    usage_msg = blue(f'%(prog)s [OPTIONS] {{{name_input}}}')
    desc_msg = 'Find valid ISBNs inside a file or in a string if no file was ' \
               'specified. \nSearching for ISBNs in files uses progressively more ' \
               'resource-intensive methods until some ISBNs are found.\n\n' \
               'This script is based on the great ebook-tools written in shell ' \
               'by na-- (See https://github.com/na--/ebook-tools).'
    parser = ArgumentParser(
        description="",
        usage=f"{usage_msg}\n\n{desc_msg}",
        add_help=False,
        formatter_class=lambda prog: MyFormatter(
            prog, max_help_position=50, width=width))
    general_group = add_general_options(
        parser,
        remove_opts=[],
        program_version=__version__,
        title=yellow('General options'))
    # ======================
    # Convert-to-txt options
    # ======================
    convert_group = parser.add_argument_group(title=yellow('Convert-to-txt options'))
    convert_group.add_argument(
        '--djvu', dest='djvu_convert_method',
        choices=['djvutxt', 'ebook-convert'], default=DJVU_CONVERT_METHOD,
        help='Set the conversion method for djvu documents.'
             + get_default_message(DJVU_CONVERT_METHOD))
    convert_group.add_argument(
        '--epub', dest='epub_convert_method',
        choices=['epubtxt', 'ebook-convert'], default=EPUB_CONVERT_METHOD,
        help='Set the conversion method for epub documents.'
             + get_default_message(EPUB_CONVERT_METHOD))
    convert_group.add_argument(
        '--pdf', dest='pdf_convert_method',
        choices=['pdftotext', 'ebook-convert'], default=PDF_CONVERT_METHOD,
        help='Set the conversion method for pdf documents.'
             + get_default_message(PDF_CONVERT_METHOD))
    # ==================
    # Find ISBNs options
    # ==================
    find_group = parser.add_argument_group(title=yellow('Find ISBNs options'))
    # TODO: add look-ahead and look-behind info, see https://bit.ly/2OYsY76
    find_group.add_argument(
        "-i", "--isbn-regex", dest='isbn_regex', default=ISBN_REGEX,
        help='''This is the regular expression used to match ISBN-like
            numbers in the supplied books.''' + get_default_message(ISBN_REGEX))
    find_group.add_argument(
        "--isbn-blacklist-regex", dest='isbn_blacklist_regex', metavar='REGEX',
        default=ISBN_BLACKLIST_REGEX,
        help='''Any ISBNs that were matched by the ISBN_REGEX above and pass
            the ISBN validation algorithm are normalized and passed through this
            regular expression. Any ISBNs that successfully match against it are
            discarded. The idea is to ignore technically valid but probably wrong
            numbers like 0123456789, 0000000000, 1111111111, etc..'''
             + get_default_message(ISBN_BLACKLIST_REGEX))
    find_group.add_argument(
        "--isbn-direct-files", dest='isbn_direct_files',
        metavar='REGEX', default=ISBN_DIRECT_FILES,
        help='''This is a regular expression that is matched against the MIME
            type of the searched files. Matching files are searched directly for
            ISBNs, without converting or OCR-ing them to .txt first.'''
             + get_default_message(ISBN_DIRECT_FILES))
    find_group.add_argument(
        "--isbn-ignored-files", dest='isbn_ignored_files', metavar='REGEX',
        default=ISBN_IGNORED_FILES,
        help='''This is a regular expression that is matched against the MIME
            type of the searched files. Matching files are not searched for ISBNs
            beyond their filename. By default, it tries to ignore .gif and .svg
            images, audio, video and executable files and fonts.'''
             + get_default_message(ISBN_IGNORED_FILES))
    find_group.add_argument(
        "--reorder-files", dest='isbn_reorder_files', nargs='+',
        action=required_length(1, 2), metavar='LINES', default=ISBN_REORDER_FILES,
        help='''These options specify if and how we should reorder the ebook
            text before searching for ISBNs in it. By default, the first 400 lines
            of the text are searched as they are, then the last 50 are searched in
            reverse and finally the remainder in the middle. This reordering is
            done to improve the odds that the first found ISBNs in a book text
            actually belong to that book (ex. from the copyright section or the
            back cover), instead of being random ISBNs mentioned in the middle of
            the book. No part of the text is searched twice, even if these regions
            overlap. Set it to `False` to disable the functionality or
            `first_lines last_lines` to enable it with the specified values.'''
             + get_default_message(str(ISBN_REORDER_FILES).strip('[|]').replace(',', '')))
    find_group.add_argument(
        '--irs', '--isbn-return-separator', dest='isbn_ret_separator',
        metavar='SEPARATOR', type=decode, default=ISBN_RET_SEPARATOR,
        help='''This specifies the separator that will be used when returning
                any found ISBNs.''' +
             get_default_message(repr(codecs.encode(ISBN_RET_SEPARATOR).decode('utf-8'))))
    # ===========
    # OCR options
    # ===========
    ocr_group = parser.add_argument_group(title=yellow('OCR options'))
    ocr_group.add_argument(
        "--ocr", "--ocr-enabled", dest='ocr_enabled',
        choices=['always', 'true', 'false'], default=OCR_ENABLED,
        help='Whether to enable OCR for .pdf, .djvu and image files. It is '
             'disabled by default.' + get_default_message(OCR_ENABLED))
    ocr_group.add_argument(
        "--ocrop", "--ocr-only-first-last-pages",
        dest='ocr_only_first_last_pages', metavar='PAGES', nargs=2,
        default=OCR_ONLY_FIRST_LAST_PAGES,
        help='''Value 'n m' instructs the script to convert only the
             first n and last m pages when OCR-ing ebooks.'''
             + get_default_message(str(OCR_ONLY_FIRST_LAST_PAGES).strip('(|)').replace(',', '')))
    # =====
    # Input
    # =====
    input_files_group = parser.add_argument_group(
        title=yellow('Input data'))
    input_files_group.add_argument(
        name_input, nargs='?',
        help='Can either be the path to a file or a string (enclose it within '
             'single or double quotes if it contains spaces). The input will be '
             'searched for ISBNs.')
    return parser


def show_exit_code(exit_code):
    msg = f'Program exited with {exit_code}'
    if exit_code == 1:
        logger.error(red(f'{msg}'))
    else:
        logger.debug(msg)


def main():
    global QUIET
    try:
        parser = setup_argparser()
        args = parser.parse_args()
        QUIET = args.quiet
        setup_log(args.quiet, args.verbose, args.logging_level, args.logging_formatter)
        # Actions
        error = False
        args_dict = namespace_to_dict(args)
        if len(args.isbn_reorder_files) == 1:
            if args.isbn_reorder_files[0] == 'False':
                args_dict['isbn_reorder_files'] = False
            else:
                logger.error(f"{red(f'error: invalid choice for reorder-files: ')}"
                             f"'{args.isbn_reorder_files[0]}' (choose from 'False' or two integers)")
                exit_code = 1
                error = True
        else:
            args_dict['isbn_reorder_files'][0] = int(args_dict['isbn_reorder_files'][0])
            args_dict['isbn_reorder_files'][1] = int(args_dict['isbn_reorder_files'][1])
        if not error:
            retval = find(**args_dict)
            exit_code = 0 if retval else retval
    except KeyboardInterrupt:
        print_(yellow('\nProgram stopped!'))
        exit_code = 2
    except Exception as e:
        print_(yellow('Program interrupted!'))
        logger.exception(e)
        exit_code = 1
    if __name__ != '__main__':
        show_exit_code(exit_code)
    return exit_code


if __name__ == '__main__':
    retcode = main()
    show_exit_code(retcode)
