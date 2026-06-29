#!/usr/bin/env python3
"""
check_thresholds.py — soft warnings on operational-file growth.

Wired into the Stop / SubagentStop hook chain after validate_wiki.py. Prints
WARNING lines (one per crossed threshold) to stderr but ALWAYS exits 0 — never
blocks Stop. The agent sees the warnings at session end and can act when
convenient (typically by running scripts/rotate_archives.sh).

Thresholds match the documented rotation cadence in wiki/operations.md and the
revisit triggers in wiki/pending/deferred-optimisations.md. Tweak in one place
(the THRESHOLDS table below).
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# (label, path-relative-to-root, kind, threshold, suggested-action)
# kind ∈ {"lines", "status:<value>"}
THRESHOLDS = [
    ("update-proposals.md (active size)", "wiki/pending/update-proposals.md", "lines", 200,
     "rotate executed/deferred rows to wiki/archive/: `python3 scripts/rotate_archives.py <quarter>`"),
    ("state.md (active size)",            "wiki/state.md",                    "lines", 100,
     "compact stale stage plans: `python3 scripts/rotate_archives.py <quarter>` (state-rotation guard requires ≥10 blocks)"),
    ("log.md (active size)",              "wiki/log.md",                      "lines", 400,
     "archive prior-quarter rows: `python3 scripts/rotate_archives.py <quarter>`"),
    ("cross-links.md (resolved rows)",    "wiki/pending/cross-links.md",      "status:resolved", 30,
     "archive resolved rows: `python3 scripts/rotate_archives.py <quarter>`"),
    ("cross-links.md (active size)",      "wiki/pending/cross-links.md",      "lines", 400,
     "rotate resolved rows: `python3 scripts/rotate_archives.py <quarter>`"),
    ("update-proposals.md (pending)",     "wiki/pending/update-proposals.md", "status:pending", 100,
     "queue is large — consider triaging or revisit DEF-002 in wiki/pending/deferred-optimisations.md (SQLite for queues)"),
    ("lookup.md (lines)",                 "wiki/lookup.md",                   "lines", 15000,
     "revisit DEF-001 in wiki/pending/deferred-optimisations.md (partition by cluster)"),
    ("tier2-sections.md (lines)",         "wiki/tier2-sections.md",           "lines", 25000,
     "revisit DEF-003 in wiki/pending/deferred-optimisations.md (partition by cluster)"),
]


# Large auto-generated indexes: their line counts only change on a rebuild, so the Stop
# hook skips them (--skip-generated) on turns that did not touch wiki/pages/.
GENERATED = {"wiki/lookup.md", "wiki/tier2-sections.md"}


def measure(path: Path, kind: str) -> int:
    if not path.exists():
        return 0
    if kind == "lines":
        return sum(1 for _ in path.open())
    if kind.startswith("status:"):
        target = kind.split(":", 1)[1]
        return sum(1 for line in path.open() if line.rstrip().endswith(f"| {target} |"))
    return 0


def main():
    skip_generated = "--skip-generated" in sys.argv
    warnings = []
    for label, relpath, kind, threshold, action in THRESHOLDS:
        if skip_generated and relpath in GENERATED:
            continue
        value = measure(ROOT / relpath, kind)
        if value > threshold:
            warnings.append(f"  - {label}: {value} > threshold {threshold} → {action}")

    if not warnings:
        return  # silent success

    print(
        "WARN (wiki/operations): the following active files have crossed their soft rotation thresholds:",
        file=sys.stderr,
    )
    for w in warnings:
        print(w, file=sys.stderr)
    print(
        "  → none of these blocks Stop; act when convenient (see wiki/operations.md).",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
