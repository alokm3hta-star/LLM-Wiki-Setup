#!/usr/bin/env python3
"""new_proposal.py — atomically allocate the next SP ID and create its proposal file.

Usage:
  python3 scripts/new_proposal.py --title "..." --type "..." --target "..." \
      --cluster "..." --trigger "..." --priority Low --raised-by alex \
      [--body "text" | --body-file path]

Creates wiki/pending/proposals/SP-<n>.md with O_CREAT|O_EXCL — the file creation IS
the ID allocation, so two concurrent callers can never receive the same ID.
Prints the allocated ID (e.g. SP-301). IDs are unpadded, continuing the existing
SP-NNN sequence; never renumbered or reused.
"""
import argparse
import datetime
import os
import re
import sys
from pathlib import Path

ROOT = Path(os.environ.get("WIKI_ROOT")
            or Path(__file__).resolve().parent.parent)
ACTIVE = ROOT / "wiki" / "pending" / "proposals"
ARCHIVE = ROOT / "wiki" / "archive"
LEGACY = ROOT / "wiki" / "pending" / "update-proposals.md"


def max_existing_id() -> int:
    mx = 0
    if ACTIVE.exists():
        for p in ACTIVE.glob("SP-*.md"):
            m = re.match(r"SP-(\d+)$", p.stem)
            if m:
                mx = max(mx, int(m.group(1)))
    scan = [LEGACY]
    if ARCHIVE.exists():
        scan += list(ARCHIVE.rglob("update-proposals*.md"))
        for d in ARCHIVE.rglob("proposals"):
            if d.is_dir():
                for p in d.glob("SP-*.md"):
                    m = re.match(r"SP-(\d+)$", p.stem)
                    if m:
                        mx = max(mx, int(m.group(1)))
    for f in scan:
        if f.exists():
            for m in re.finditer(r"\bSP-(\d+)\b", f.read_text(errors="ignore")):
                mx = max(mx, int(m.group(1)))
    return mx


def main():
    ap = argparse.ArgumentParser()
    for opt in ("--title", "--type", "--target", "--cluster", "--trigger",
                "--priority", "--raised-by"):
        ap.add_argument(opt, required=(opt == "--title"), default="")
    ap.add_argument("--body", default="")
    ap.add_argument("--body-file", default="")
    a = ap.parse_args()
    body = a.body
    if a.body_file:
        body = Path(a.body_file).read_text()

    ACTIVE.mkdir(parents=True, exist_ok=True)
    n = max_existing_id() + 1
    while True:
        path = ACTIVE / f"SP-{n}.md"
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except FileExistsError:
            n += 1
    today = datetime.date.today().isoformat()
    content = (
        "---\n"
        f"id: SP-{n}\n"
        f"date: {today}\n"
        f"type: {a.type}\n"
        f"target: {a.target}\n"
        f"cluster: {a.cluster}\n"
        f"trigger: {a.trigger}\n"
        f"priority: {a.priority or 'Low'}\n"
        "status: pending\n"
        f"raised-by: {a.raised_by}\n"
        "---\n\n"
        f"# SP-{n} — {a.title}\n\n"
        f"{body}\n"
    )
    os.write(fd, content.encode("utf-8"))
    os.close(fd)
    print(f"SP-{n}")


if __name__ == "__main__":
    main()
