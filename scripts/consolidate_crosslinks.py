#!/usr/bin/env python3
"""consolidate_crosslinks.py — fold inbox drop-files into cross-links.md.

Reads every wiki/pending/cross-links-inbox/*.md (skipping README.md), collects the
`| `-prefixed rows, appends them to the END of the FIRST status-bearing table (the
Active Pending Queue) of wiki/pending/cross-links.md, writes atomically, and deletes
the consumed inbox files.

Contention-free by construction: writers only ever CREATE inbox files; this sweep is
the sole editor of cross-links.md and must run under ops.lock:
    python3 scripts/with_lock.py ops.lock -- python3 scripts/consolidate_crosslinks.py

Refuses (exit 1, no changes) if any non-blank inbox line is not a `| `-prefixed row.
Stdlib + wikilib only.
"""
import sys
from pathlib import Path

from wikilib import atomic_write

ROOT = Path(__file__).resolve().parent.parent
CROSS_LINKS = ROOT / "wiki" / "pending" / "cross-links.md"
INBOX = ROOT / "wiki" / "pending" / "cross-links-inbox"


def collect_rows():
    """Return (rows, consumed_files). Exit 1 if any inbox line is not a `| ` row."""
    rows, consumed = [], []
    if not INBOX.exists():
        return rows, consumed
    for f in sorted(INBOX.glob("*.md")):
        if f.name == "README.md":
            continue
        consumed.append(f)
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.strip() == "":
                continue
            if not line.startswith("| "):
                sys.exit(f"consolidate_crosslinks: refusing — '{f.name}' has a "
                         f"non-row line (not '| '-prefixed): {line!r}")
            rows.append(line)
    return rows, consumed


def first_table_last_index(lines):
    """Index of the last line belonging to the FIRST status-bearing table, or None.

    Mirrors rotate_archives.py::split_cross_links: the header row starts with `|`,
    contains `**` and `Status`; blank lines do NOT end the table; a non-blank
    non-`|` line does.
    """
    in_queue = False
    queue_done = False
    last_idx = None
    for i, line in enumerate(lines):
        if not queue_done and not in_queue and line.startswith("|") \
                and "**" in line and "Status" in line:
            in_queue = True
            last_idx = i
            continue
        if in_queue and line.startswith("|"):
            last_idx = i
            continue
        if in_queue and not line.startswith("|") and line.strip():
            in_queue = False
            queue_done = True
        # blank lines while in_queue fall through without ending the table
    return last_idx


def main():
    rows, consumed = collect_rows()
    if not rows:
        print("consolidate_crosslinks: no inbox rows to consolidate.")
        return
    if not CROSS_LINKS.exists():
        sys.exit(f"consolidate_crosslinks: {CROSS_LINKS} not found")

    text = CROSS_LINKS.read_text(encoding="utf-8")
    had_final_nl = text.endswith("\n")
    lines = text.splitlines()

    last_idx = first_table_last_index(lines)
    if last_idx is None:
        sys.exit("consolidate_crosslinks: no status-bearing table found in cross-links.md")

    new_lines = lines[:last_idx + 1] + rows + lines[last_idx + 1:]
    out = "\n".join(new_lines)
    if had_final_nl:
        out += "\n"
    atomic_write(CROSS_LINKS, out)

    for f in consumed:
        f.unlink()

    print(f"consolidate_crosslinks: appended {len(rows)} row(s) to the Active Pending "
          f"Queue; consumed {len(consumed)} inbox file(s).")


if __name__ == "__main__":
    main()
