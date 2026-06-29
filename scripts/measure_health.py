#!/usr/bin/env python3
"""
measure_health.py — snapshot the wiki's operational metrics for trend tracking.

Reads sizes / row counts / cluster stats from the live wiki and emits a YAML-ish
record. Each invocation:
  - prints the snapshot to stdout
  - appends the snapshot (with a date header) to wiki/pending/health-history.md

Use the history file to compare today vs three months ago when deciding whether
the triggers in wiki/pending/deferred-optimisations.md have been crossed.

Stdlib only. Run after any significant ingestion or curation pass — or on a
schedule (cron / launchd) once weekly.
"""

import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PROPOSALS = ROOT / "wiki" / "pending" / "update-proposals.md"
CROSS_LINKS = ROOT / "wiki" / "pending" / "cross-links.md"
STATE = ROOT / "wiki" / "state.md"
LOG = ROOT / "wiki" / "log.md"
LOOKUP = ROOT / "wiki" / "lookup.md"
TIER2 = ROOT / "wiki" / "tier2-sections.md"
INDEX = ROOT / "wiki" / "index.md"
PAGES = ROOT / "wiki" / "pages"
CLUSTERS = ROOT / "wiki" / "clusters"
HISTORY = ROOT / "wiki" / "pending" / "health-history.md"


def lines(path: Path) -> int:
    return sum(1 for _ in path.open()) if path.exists() else 0


def bytes_(path: Path) -> int:
    return path.stat().st_size if path.exists() else 0


def count_pages() -> int:
    if not PAGES.exists():
        return 0
    return sum(1 for _ in PAGES.rglob("*.md"))


def parse_index_stats() -> dict:
    """Pull Total entities / Total pages / Pending counts from wiki/index.md statistics."""
    if not INDEX.exists():
        return {}
    text = INDEX.read_text()
    stats = {}
    for key in ("Total entities", "Total pages", "Active clusters",
                "Pending cross-links", "Pending missing pages", "Pending proposals"):
        m = re.search(rf"\|\s*{re.escape(key)}\s*\|\s*(\d+)\s*\|", text)
        if m:
            stats[key] = int(m.group(1))
    return stats


def count_status(path: Path, status: str) -> int:
    if not path.exists():
        return 0
    return sum(1 for line in path.open() if line.rstrip().endswith(f"| {status} |"))


def count_log_rows(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for line in path.open() if re.match(r"^\| \d{4}-\d{2}-\d{2}T", line))


def cluster_page_counts() -> dict:
    """Pages per cluster directory under wiki/pages/<cluster>/ (skipping hidden dirs)."""
    out = {}
    if not PAGES.exists():
        return out
    for d in sorted(PAGES.iterdir()):
        if d.is_dir() and not d.name.startswith("."):
            out[d.name] = sum(1 for _ in d.glob("*.md"))
    return out


def lookup_rows_per_cluster() -> dict:
    """Per-cluster row counts in lookup.md (for partition planning).
    The actual layout is a single ## Pages / ## Entities / ## Edges section; each
    row in ## Pages starts with `<cluster>/<page>.md | ...`. Count rows by prefix."""
    if not LOOKUP.exists():
        return {}
    counts = {}
    in_pages = False
    page_re = re.compile(r"^([a-z][a-z0-9\-]+)/[^|]+\|")
    for line in LOOKUP.open():
        if line.startswith("## Pages"):
            in_pages = True
            continue
        if line.startswith("## "):
            in_pages = False
            continue
        if not in_pages:
            continue
        m = page_re.match(line)
        if m:
            cluster = m.group(1)
            counts[cluster] = counts.get(cluster, 0) + 1
    return counts


def render_snapshot(date_str: str) -> str:
    idx = parse_index_stats()
    out = []
    out.append(f"## Snapshot {date_str}\n")
    out.append(f"corpus:")
    out.append(f"  pages: {idx.get('Total pages', count_pages())}")
    out.append(f"  entities: {idx.get('Total entities', '?')}")
    out.append(f"  clusters: {idx.get('Active clusters', '?')}")
    out.append(f"  pending_cross_links: {idx.get('Pending cross-links', '?')}")
    out.append(f"  pending_missing_pages: {idx.get('Pending missing pages', '?')}")
    out.append(f"  pending_proposals: {idx.get('Pending proposals', '?')}")
    out.append("")
    out.append("active_files:")
    out.append(f"  update-proposals.md: lines={lines(PROPOSALS)} bytes={bytes_(PROPOSALS)} "
               f"pending={count_status(PROPOSALS, 'pending')} "
               f"approved={count_status(PROPOSALS, 'approved')}")
    out.append(f"  cross-links.md:      lines={lines(CROSS_LINKS)} bytes={bytes_(CROSS_LINKS)} "
               f"pending={count_status(CROSS_LINKS, 'pending')} "
               f"approved={count_status(CROSS_LINKS, 'approved')} "
               f"resolved_in_file={count_status(CROSS_LINKS, 'resolved')}")
    out.append(f"  state.md:            lines={lines(STATE)} bytes={bytes_(STATE)}")
    out.append(f"  log.md:              lines={lines(LOG)} bytes={bytes_(LOG)} "
               f"dated_rows={count_log_rows(LOG)}")
    out.append(f"  lookup.md:           lines={lines(LOOKUP)} bytes={bytes_(LOOKUP)}")
    out.append(f"  tier2-sections.md:   lines={lines(TIER2)} bytes={bytes_(TIER2)}")
    out.append("")
    out.append("per_cluster:")
    cluster_pages = cluster_page_counts()
    lookup_rows = lookup_rows_per_cluster()
    for cluster in sorted(cluster_pages.keys()):
        out.append(f"  {cluster}: pages={cluster_pages[cluster]} "
                   f"lookup_rows={lookup_rows.get(cluster, '?')}")
    out.append("")
    return "\n".join(out)


def main():
    today = datetime.utcnow().strftime("%Y-%m-%d")
    snapshot = render_snapshot(today)
    print(snapshot)

    if "--no-history" in sys.argv:
        return

    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    if not HISTORY.exists():
        HISTORY.write_text(
            "## Specification Registry: Wiki Health History\n\n"
            "Time-series of operational metrics. Each snapshot is appended by "
            "`scripts/measure_health.py`. Compare against the baselines in "
            "[`wiki/pending/deferred-optimisations.md`](deferred-optimisations.md) "
            "to decide whether deferred decisions (partition lookup, migrate to SQLite, "
            "etc.) should now be acted on.\n\n"
        )
    with HISTORY.open("a") as f:
        f.write(snapshot)
        f.write("\n")


if __name__ == "__main__":
    main()
