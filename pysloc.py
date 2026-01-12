##########################################################################################
#
# Script name: count_loc.py
#
# Description: Count Python SLOC (source lines of code) in a directory tree.
#
# Author: John Macdonald
#
##########################################################################################

import argparse
import logging
import sys
import os
from datetime import date
import re
import fnmatch

# ****************************************************************************************
# Global data and configuration
# ****************************************************************************************
# Set global variables here and log.debug them below

# Logging config
log = logging.getLogger(os.path.basename(sys.argv[0]))
log.setLevel(logging.DEBUG)

# File handler for logging
fh = logging.FileHandler('count_loc.log', mode='w')
fh.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)-15s [%(funcName)25s:%(lineno)-5s] %(levelname)-8s %(message)s')
fh.setFormatter(formatter)
log.addHandler(fh)  # Add file handler to logger


# ****************************************************************************************
# Exceptions
# ****************************************************************************************

class Error(Exception):
    '''
    Base class for exceptions in this module.
    '''
    pass


class RequestError(Error):
    '''
    Base class for exceptions related to external requests in this module.
    '''
    def __init__(self, url):
        self.message = f'Failed to fetch URL: {url}'
        super().__init__(self.message)


# ****************************************************************************************
# Functions
# ****************************************************************************************

def is_code_line(line):
    '''
    Determine whether a line is considered source code.

    Rules:
        - Ignore blank lines.
        - Ignore full-line comments beginning with "#".
        - Strip inline comments and count the line only if code remains.
    '''
    stripped = line.strip()
    if not stripped:
        return False
    if stripped.startswith('#'):
        return False

    code_part = stripped.split('#', 1)[0].strip()
    return bool(code_part)


def should_ignore(path, ignore_patterns, root_path, include_hidden=False):
    '''
    Return True if the given path should be ignored based on provided patterns.
    Patterns are matched against both the relative path from the root and the basename.
    '''
    abs_path = os.path.abspath(path)
    root_abs = os.path.abspath(root_path)
    try:
        rel = os.path.relpath(abs_path, root_abs)
    except ValueError:
        # Different drives on Windows or other relpath failures; fall back to abs path.
        rel = abs_path
    name = os.path.basename(path)

    if not include_hidden and name.startswith('.'):
        log.warning(f'Skipping hidden path: {path}')
        log.debug(f'Hidden path ignored: {path}')
        return True

    if not ignore_patterns:
        return False

    for pattern in ignore_patterns:
        # Expand matching candidates to cover absolute and relative forms.
        candidates = [pattern]
        if os.path.isabs(pattern):
            try:
                candidates.append(os.path.relpath(pattern, root_abs))
            except ValueError:
                pass
        else:
            candidates.append(os.path.abspath(os.path.join(root_abs, pattern)))

        for candidate in candidates:
            if (
                fnmatch.fnmatch(rel, candidate)
                or fnmatch.fnmatch(abs_path, candidate)
                or fnmatch.fnmatch(name, candidate)
            ):
                log.debug(f'Ignoring {path} (matched pattern "{pattern}")')
                return True
    return False


def iter_python_files(root_path, ignore_patterns=None, include_hidden=False):
    '''
    Walk a directory recursively and yield all Python (.py) files.

    Input:
        root_path: Root directory to scan.
        ignore_patterns: List of glob-style patterns to skip.
        include_hidden: If False, skip hidden files/directories (names starting with ".").

    Output:
        Generator yielding absolute paths to Python files.
    '''
    root_path = os.path.abspath(root_path)
    ignore_patterns = ignore_patterns or []
    log.debug(f'Walking Python files under root: {root_path}')

    for dirpath, dirnames, filenames in os.walk(root_path):
        # Prune ignored directories in-place to avoid descending into them.
        dirnames[:] = [
            d for d in dirnames
            if not should_ignore(
                os.path.join(dirpath, d),
                ignore_patterns,
                root_path,
                include_hidden=include_hidden)
        ]

        for name in filenames:
            full_path = os.path.join(dirpath, name)
            if should_ignore(full_path, ignore_patterns, root_path, include_hidden=include_hidden):
                continue
            if name.endswith('.py'):
                log.debug(f'Found Python file: {full_path}')
                yield full_path


def count_file_loc(path):
    '''
    Count SLOC for a single Python file.

    Input:
        path: Absolute path to a file.

    Output:
        Integer number of SLOC.
    '''
    loc = 0
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as fh:
            for raw_line in fh:
                if is_code_line(raw_line):
                    loc += 1
    except OSError as exc:
        log.warning(f'Failed to read {path}: {exc}')

    log.debug(f'File {path} has {loc} SLOC')
    return loc


def count_loc(root_path, per_file=True, ignore_patterns=None, include_hidden=False):
    '''
    Count total SLOC for all Python files under a directory.

    Input:
        root_path: Directory to scan.
        per_file:  If True, return a dict of per-file SLOC.
        ignore_patterns: List of glob-style patterns to skip.
        include_hidden: If False, skip hidden files/directories (names starting with ".").

    Output:
        - If per_file=False: total SLOC
        - If per_file=True: (dict, total SLOC)
    '''
    total = 0
    per_file_dict = {}

    for path in iter_python_files(
            root_path,
            ignore_patterns=ignore_patterns,
            include_hidden=include_hidden):
        file_loc = count_file_loc(path)
        total += file_loc
        if per_file:
            per_file_dict[path] = file_loc

    log.info(f'Total SLOC under {root_path}: {total}')

    if per_file:
        return per_file_dict, total
    return total


def format_path_for_display(path, root_root):
    '''
    Return a human-friendly path, relative to the root when possible.
    '''
    try:
        return os.path.relpath(path, root_root)
    except ValueError:
        return path


def log_sloc_summary(root_abs, total, per_file_counts=None):
    '''
    Pretty-print the SLOC summary to the logger.
    '''
    log.info('=' * 70)
    if per_file_counts is not None:
        log.info(f'SLOC summary for {root_abs}')
        log.info('-' * 70)
        for path in sorted(per_file_counts):
            display_path = format_path_for_display(path, root_abs)
            log.info(f'{per_file_counts[path]:8d} | {display_path}')
        log.info('-' * 70)
        log.info(f'TOTAL SLOC: {total:,}')
    else:
        log.info(f'Total Python SLOC under {root_abs}: {total:,}')
    log.info('=' * 70)


# ****************************************************************************************
# Argument handling
# ****************************************************************************************

def handle_args():
    '''
    Parse command-line arguments and configure console logging.

    Returns:
        argparse.Namespace with parsed options.
    '''
    parser = argparse.ArgumentParser(
        description='Count Python source lines of code (SLOC).')

    parser.add_argument(
        'paths',
        nargs='*',
        default=['.'],
        help='Root directories/files to scan (default: current directory). Supports multiple paths.')

    parser.add_argument(
        '-i',
        '--ignore',
        action='append',
        nargs='+',
        default=[],
        metavar='PATTERN',
        help='File or directory patterns to ignore (supports glob wildcards). Can be repeated and may accept multiple patterns.')

    per_file_group = parser.add_mutually_exclusive_group()
    per_file_group.add_argument(
        '-p',
        '--per-file',
        dest='per_file',
        action='store_true',
        help='Show per-file SLOC (default).')
    per_file_group.add_argument(
        '--total-only',
        dest='per_file',
        action='store_false',
        help='Only show total SLOC.')
    parser.set_defaults(per_file=True)

    parser.add_argument(
        '--include-hidden',
        action='store_true',
        help='Include hidden files and directories (names starting with ".").')

    parser.add_argument(
        '-v',
        '--verbose',
        action='store_true',
        help='Verbose output.')

    parser.add_argument(
        '-q',
        '--quiet',
        action='store_true',
        help='Suppress non-error output.')

    args = parser.parse_args()

    # Configure stdout logging per template flow
    ch = logging.StreamHandler(sys.stdout)
    if args.verbose:
        ch.setLevel(logging.DEBUG)
    elif args.quiet:
        ch.setLevel(logging.ERROR)
    else:
        ch.setLevel(logging.INFO)

    ch.setFormatter(formatter)
    log.addHandler(ch)

    # Flatten ignore patterns (action='append', nargs='+') into a single list.
    args.ignore = [pattern for group in args.ignore for pattern in group]

    if args.ignore:
        log.debug(f'Ignore patterns: {args.ignore}')

    log.debug('Checking script requirements...')
    if not args.verbose and not args.quiet:
        log.debug('No output level specified. Defaulting to INFO.')

    log.info('++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++')
    log.info('             Starting Python SLOC Counting Tool             ')
    log.info('++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++')

    return args


# ****************************************************************************************
# Main
# ****************************************************************************************

def main():
    '''
    Entrypoint that wires together dependencies and launches the CLI loop.
    '''
    args = handle_args()
    overall_total = 0

    for target in args.paths:
        root_abs = os.path.abspath(target)

        if args.per_file:
            per_file_counts, total = count_loc(
                target,
                per_file=True,
                ignore_patterns=args.ignore,
                include_hidden=args.include_hidden)
            log_sloc_summary(root_abs, total, per_file_counts=per_file_counts)
        else:
            total = count_loc(target,
                              per_file=False,
                              ignore_patterns=args.ignore,
                              include_hidden=args.include_hidden)
            log_sloc_summary(root_abs, total, per_file_counts=None)

        overall_total += total

    if len(args.paths) > 1:
        log.info('=' * 70)
        log.info(
            f'Combined total across {len(args.paths)} paths: {overall_total:,}')
        log.info('=' * 70)


if __name__ == '__main__':
    main()
