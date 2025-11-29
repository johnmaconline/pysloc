# pysloc

Simple Python SLOC counter with per-file totals, ignore globs, and optional hidden-file scanning.

## Features
- Counts source lines of code in `.py` files, excluding blank lines and comments.
- Per-file output is enabled by default; `--total-only` switches to just a total.
- Glob-based ignore patterns (`-i/--ignore`) for files or directories; supports multiple patterns.
- Hidden files and directories are skipped by default and logged when ignored; `--include-hidden` opts them back in.
- Verbose/quiet logging controls.

## Usage
```bash
# Per-file summary (default) under the current directory
python3 pysloc.py .

# Totals only
python3 pysloc.py --total-only .

# Ignore tests and virtualenv contents
python3 pysloc.py ../my_project --ignore "../my_project/tests/*" "../my_project/.venv/*"

# Include hidden files/dirs as well
python3 pysloc.py ../my_project --include-hidden

# Verbose logging
python3 pysloc.py -v .
```

## Notes
- All output is emitted via logging (`count_loc.log` is written by default); adjust verbosity with `-v`/`-q`.
- Ignore matching happens against absolute, relative, and basename forms to play nicely with shell-expanded globs.
