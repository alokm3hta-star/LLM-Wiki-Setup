#!/usr/bin/env python3
"""wikilib.py — tiny shared helpers for the wiki's operational scripts.

Import style (works because sys.path[0] is scripts/ when any sibling script runs):
    from wikilib import atomic_write, count_status_rows, STATUS_TOKENS
Stdlib only.
"""
import os
import tempfile
from pathlib import Path

# Canonical leading status tokens for queue-table rows (last |-cell).
# A cell may carry an annotation after the token, e.g. "pending - Sarah's call".
STATUS_TOKENS = ("pending", "approved", "resolved", "executed", "deferred",
                 "rejected", "closed", "converted", "gap")


def atomic_write(path, text):
    """Write text to path atomically: temp file in the same directory + os.replace.
    Readers (grep) see the old or the new file, never a torn one."""
    path = Path(path)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".tmp.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _status_matches(last_cell, statuses):
    last = last_cell.strip().lower()
    for st in statuses:
        st = st.lower()
        if last == st or last.startswith(st + " ") or last.startswith(st + "-") \
           or last.startswith(st + " -") or last.startswith(st + ":"):
            return True
    return False


def count_status_rows(path, statuses):
    """Count table rows whose LAST |-cell starts with one of `statuses` (word-boundary:
    the token is followed by end, space, or hyphen). Tolerates annotated cells like
    'pending - awaiting Sarah' and 'resolved 2026-06-21 [[page]]'."""
    path = Path(path)
    if not path.exists():
        return 0
    n = 0
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = line.strip()
        if not (s.startswith("|") and s.endswith("|")):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if not cells:
            continue
        if _status_matches(cells[-1], statuses):
            n += 1
    return n


def count_status_rows_first_table(path, statuses):
    """Like count_status_rows, but scoped to only the FIRST status-bearing table (a line
    starting '|', containing '**' and 'Status') — everything after that table ends (a
    non-'|' non-blank line) is ignored. Some files (cross-links.md) carry a permanent
    Historical Resolution Ledger after the active queue; that table is reference data the
    rotation script deliberately never touches (see rotate_archives.py::split_cross_links),
    so a whole-file scan would count it as backlog forever. Use this variant wherever the
    question is "does the ACTIVE queue need rotation", not "how much history exists"."""
    path = Path(path)
    if not path.exists():
        return 0
    n = 0
    in_table = False
    table_done = False
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = line.strip()
        if table_done:
            break
        if not in_table and s.startswith("|") and "**" in s and "Status" in s:
            in_table = True
            continue
        if in_table and s.startswith("| ---"):
            continue
        if in_table and s.startswith("|") and s.endswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if cells and _status_matches(cells[-1], statuses):
                n += 1
            continue
        if in_table and not s.startswith("|") and s:
            table_done = True
    return n
