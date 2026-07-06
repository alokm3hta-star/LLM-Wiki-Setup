#!/usr/bin/env python3
"""append_row.py — atomic single-write append of one row/block to a ledger file.

Usage:
  python3 scripts/append_row.py <ledger-relpath> "row text"
  ... | python3 scripts/append_row.py <ledger-relpath> --stdin

One os.write on an O_APPEND fd: concurrent writers cannot interleave a row-sized
write on a local filesystem. Only the allow-listed ledgers may be targeted.
"""
import os
import sys
from pathlib import Path

ROOT = Path(os.environ.get("WIKI_ROOT")
            or Path(__file__).resolve().parent.parent)
ALLOWED = {
    "wiki/log.md",
    "wiki/pending/gap-log.md",
    "wiki/pending/retrieval-log.md",
    "wiki/pending/health-history.md",
}


def main():
    if len(sys.argv) < 3:
        sys.exit("usage: append_row.py <ledger-relpath> \"row\" | --stdin")
    rel = sys.argv[1]
    if rel not in ALLOWED:
        sys.exit(f"append_row: '{rel}' is not an allow-listed ledger {sorted(ALLOWED)}")
    text = sys.stdin.read() if sys.argv[2] == "--stdin" else sys.argv[2]
    if not text.endswith("\n"):
        text += "\n"
    fd = os.open(ROOT / rel, os.O_WRONLY | os.O_APPEND | os.O_CREAT)
    try:
        os.write(fd, text.encode("utf-8"))
    finally:
        os.close(fd)


if __name__ == "__main__":
    main()
