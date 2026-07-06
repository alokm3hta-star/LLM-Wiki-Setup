#!/usr/bin/env python3
"""detect_stale.py — surface wiki pages that may be out of date.

Read-only. Scans wiki/pages/**/*.md and flags:
  1. aged        — pages whose "**Last updated**: YYYY-MM-DD" line is older than --months (default 12).
  2. review-trigger — pages whose H1 title carries a reclassification trigger (future / roadmap /
                   outlook / current status / pre-GA / preview, or a past-year token). These are
                   forward-looking or dated pages that should be re-checked against fresh sources.
  3. no-date     — pages with no parseable "**Last updated**:" line.

Prints a concise, dated report to stdout for the maintenance digest. Never writes anything.
Stdlib only; mirrors the light frontmatter/body reading used by build_index.py / validate_wiki.py.
"""
from __future__ import annotations

import datetime as _dt
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGES = os.path.join(ROOT, "wiki", "pages")

DATE_RE = re.compile(r"^\*\*Last updated\*\*:\s*(\d{4}-\d{2}-\d{2})", re.MULTILINE)
H1_RE = re.compile(r"^#\s+(.*)$", re.MULTILINE)
# Staleness signals only. Deliberately narrow: a bare year token over-flags legitimately-named
# release pages (e.g. "S/4HANA 2025 — Asset Accounting"), so match forward-looking/uncertain
# markers instead — the terms that mean "re-check this against a fresher source".
TRIGGER_RE = re.compile(
    r"(future|roadmap|outlook|\bcurrent status\b|pre-?ga)",
    re.IGNORECASE,
)

TOP_N = 25


def _months_arg() -> int:
    if "--months" in sys.argv:
        try:
            return int(sys.argv[sys.argv.index("--months") + 1])
        except (IndexError, ValueError):
            pass
    return 12


def main() -> int:
    months = _months_arg()
    today = _dt.date.today()
    cutoff = today - _dt.timedelta(days=months * 30)

    aged: list[tuple[int, str, str]] = []       # (age_days, rel_path, date_str)
    triggered: list[tuple[str, str]] = []        # (rel_path, title)
    no_date: list[str] = []

    for dirpath, _dirs, files in os.walk(PAGES):
        for name in files:
            if not name.endswith(".md"):
                continue
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, ROOT)
            try:
                with open(full, encoding="utf-8") as fh:
                    text = fh.read()
            except OSError:
                continue

            m = DATE_RE.search(text)
            if m:
                try:
                    d = _dt.date.fromisoformat(m.group(1))
                    if d < cutoff:
                        aged.append(((today - d).days, rel, m.group(1)))
                except ValueError:
                    no_date.append(rel)
            else:
                no_date.append(rel)

            h1 = H1_RE.search(text)
            title = h1.group(1).strip() if h1 else name
            if TRIGGER_RE.search(title):
                triggered.append((rel, title))

    aged.sort(reverse=True)
    triggered.sort()

    print(f"# Staleness scan — {today.isoformat()} (threshold: {months} months; cutoff {cutoff.isoformat()})")
    print()
    print(f"- Aged pages (last updated before cutoff): {len(aged)}")
    print(f"- Review-trigger pages (forward-looking / dated titles): {len(triggered)}")
    print(f"- Pages with no parseable date line: {len(no_date)}")
    print()

    if aged:
        print(f"## Aged — oldest {min(TOP_N, len(aged))} of {len(aged)}")
        for age, rel, ds in aged[:TOP_N]:
            print(f"- {ds} ({age // 30} mo): {rel}")
        print()

    if triggered:
        print(f"## Review-trigger — first {min(TOP_N, len(triggered))} of {len(triggered)}")
        for rel, title in triggered[:TOP_N]:
            print(f"- {rel}  ·  {title}")
        print()

    if no_date:
        print(f"## No date line — first {min(TOP_N, len(no_date))} of {len(no_date)}")
        for rel in no_date[:TOP_N]:
            print(f"- {rel}")
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
