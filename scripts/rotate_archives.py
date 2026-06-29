#!/usr/bin/env python3
"""
rotate_archives.py — periodic rotation of the wiki's append-growing operational files.

Moves stale rows / blocks out of the active files into `wiki/archive/<quarter>/`
so the active files stay small and fast to read/edit. Idempotent: re-running for
the same quarter is a no-op.

Targets:
  - wiki/pending/update-proposals.md  → archive rows whose status is `executed`
                                         or `deferred` (regardless of date)
  - wiki/state.md                     → keep the 5 most-recent INGESTION COMPLETE
                                         entries / Stage Plan blocks; archive the rest
                                         (no-op if fewer than 10 dated blocks present)
  - wiki/log.md                       → archive entries dated before the cutoff
                                         (cutoff = first day of the quarter AFTER `quarter`)
  - wiki/pending/cross-links.md       → archive rows whose status is `resolved`
                                         (regardless of date)

The `quarter` argument names the quarter being archived (i.e., a just-ended quarter).
Run AT or AFTER the quarter's last day. Example: on 2026-07-01, run with arg `2026-q2`
to rotate everything dated within Q2 2026.

There is also a status-keyed, calendar-independent prune of state.md alone:
  - wiki/state.md (--state-gc)        → keep the newest block (idle) or the active
                                         `Current source` block + newest (in-progress);
                                         archive the rest to wiki/archive/state-history.md.
                                         Safe to run every session (e.g. from the Stop hook);
                                         never archives the active/resumable block.

Usage:
  python3 scripts/rotate_archives.py 2026-q2          # rotate Q2 → wiki/archive/2026-q2/
  python3 scripts/rotate_archives.py --dry-run 2026-q2
  python3 scripts/rotate_archives.py --state-gc       # prune state.md now (status-keyed)
  python3 scripts/rotate_archives.py --state-gc --dry-run

Stdlib only. Writes a single summary row to wiki/log.md at the end.
"""

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARCHIVE = ROOT / "wiki" / "archive"
PROPOSALS = ROOT / "wiki" / "pending" / "update-proposals.md"
STATE = ROOT / "wiki" / "state.md"
LOG = ROOT / "wiki" / "log.md"
CROSS_LINKS = ROOT / "wiki" / "pending" / "cross-links.md"

STAGE_PLAN_RE = re.compile(r"^## Stage Plan ")
INGESTION_RE = re.compile(r"^- \*\*INGESTION COMPLETE \((\d{4}-\d{2}-\d{2})\)\*\*")
LOG_ROW_RE = re.compile(r"^\| (\d{4})-(\d{2})-(\d{2})T")
PROPOSAL_ROW_RE = re.compile(r"^\| SP-\d+ \|.+\| (\w+) \|\s*$")
CROSSLINK_ROW_RE = re.compile(r"^\| .+\| (resolved|active|pending|approved) \|\s*$")
QUARTER_RE = re.compile(r"^(\d{4})-q([1-4])$")


def quarter_start(quarter: str) -> datetime:
    """Returns the first day of the named quarter."""
    m = QUARTER_RE.match(quarter)
    if not m:
        sys.exit(f"ERROR: quarter arg must be like '2026-q3', got '{quarter}'")
    year, q = int(m.group(1)), int(m.group(2))
    month = {1: 1, 2: 4, 3: 7, 4: 10}[q]
    return datetime(year, month, 1)


def next_quarter_start(quarter: str) -> datetime:
    """Returns the first day of the quarter AFTER the named quarter.
    This is the cutoff for date-based rotation (rows < cutoff are archived)."""
    m = QUARTER_RE.match(quarter)
    year, q = int(m.group(1)), int(m.group(2))
    next_q = q + 1
    next_year = year
    if next_q > 4:
        next_q = 1
        next_year += 1
    month = {1: 1, 2: 4, 3: 7, 4: 10}[next_q]
    return datetime(next_year, month, 1)


def split_proposals():
    """
    Returns (active_lines, archived_rows).
    Keeps everything before the table-body, the 3 column-header lines, and any row
    whose status (last `|`-separated cell) is NOT in {executed, deferred}.
    """
    lines = PROPOSALS.read_text().splitlines()
    active, archived = [], []
    in_queue = False
    for line in lines:
        if line.startswith("| **Proposal ID**"):
            active.append(line)
            in_queue = True
            continue
        if in_queue and line.startswith("| ---"):
            active.append(line)
            continue
        if in_queue and line.startswith("| SP-"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            status = cells[-1] if cells else ""
            if status in ("executed", "deferred"):
                archived.append(line)
            else:
                active.append(line)
            continue
        # leaving the table region
        if in_queue and not line.startswith("|") and line.strip():
            in_queue = False
        active.append(line)
    return active, archived


def _decompose_state(text: str):
    """
    Splits state.md into (header, history, tail, blocks).
      header  — lines before the first Stage Plan / INGESTION block
      history — the contiguous run of Stage Plan / INGESTION blocks
      tail    — any trailing non-block `## ` section (reference matter)
      blocks  — list of (date, start, end, source); start/end index into `history`.

    A Stage Plan header opens a block; a following INGESTION COMPLETE bullet stays
    inside it (and refines the block's date). A standalone INGESTION COMPLETE (no
    Stage Plan immediately before) opens its own block. Shared by the quarterly
    `split_state` and the status-keyed `gc_state_by_status`.
    """
    lines = text.splitlines()

    history_start = None
    for i, line in enumerate(lines):
        if STAGE_PLAN_RE.match(line) or INGESTION_RE.match(line):
            history_start = i
            break
    if history_start is None:
        return lines, [], [], []

    history_end = len(lines)
    for i in range(history_start, len(lines)):
        if lines[i].startswith("## ") and not STAGE_PLAN_RE.match(lines[i]):
            history_end = i
            break

    header = lines[:history_start]
    history = lines[history_start:history_end]
    tail = lines[history_end:]

    blocks = []
    current_start = 0
    current_date = "0000-00-00"
    current_kind = None  # "stage" or "ingest"
    current_source = None

    def close_block(end):
        if current_kind is not None:
            blocks.append((current_date, current_start, end, current_source))

    for i, line in enumerate(history):
        is_stage = STAGE_PLAN_RE.match(line)
        is_ingest = INGESTION_RE.match(line)
        if is_stage:
            close_block(i)
            current_start = i
            m = re.search(r"\((?:started|completed) (\d{4}-\d{2}-\d{2})", line)
            current_date = m.group(1) if m else "0000-00-00"
            sm = re.match(r"^## Stage Plan — (.+?) \((?:started|completed)", line)
            current_source = sm.group(1).strip() if sm else None
            current_kind = "stage"
        elif is_ingest:
            if current_kind == "stage":
                current_date = is_ingest.group(1)
            else:
                close_block(i)
                current_start = i
                current_date = is_ingest.group(1)
                current_kind = "ingest"
                current_source = None
    close_block(len(history))

    return header, history, tail, blocks


def _apply_keep(header, history, tail, blocks, keep_starts):
    """Returns (active_lines, archived_lines) keeping only blocks whose start index
    is in `keep_starts`; gap lines between kept blocks are archived."""
    keep_ranges = sorted([(b[1], b[2]) for b in blocks if b[1] in keep_starts])
    kept, archived = [], []
    last_end = 0
    for start, end in keep_ranges:
        archived.extend(history[last_end:start])
        kept.extend(history[start:end])
        last_end = end
    archived.extend(history[last_end:])
    return header + kept + tail, archived


def _read_current_state(header):
    """Extracts (status, current_source) from the `## Current State` header block.
    `status` is lower-cased; `current_source` has any trailing parenthetical
    (e.g. ' (complete)') stripped so it matches a Stage Plan header's source name."""
    status, source = "idle", None
    for line in header:
        ms = re.match(r"^- \*\*Status\*\*:\s*(.+?)\s*$", line)
        if ms:
            status = ms.group(1).strip().lower()
        mc = re.match(r"^- \*\*Current source\*\*:\s*(.+?)\s*$", line)
        if mc:
            source = mc.group(1).strip()
    if source:
        source = re.sub(r"\s*\(.*\)\s*$", "", source).strip()
    return status, source


def split_state(keep_most_recent: int = 5, min_blocks: int = 10):
    """
    Returns (active_lines, archived_lines).
    Keeps the `keep_most_recent` newest blocks by date; archives the rest.
    No-ops if fewer than `min_blocks` blocks are present (file is already small).
    """
    text = STATE.read_text()
    header, history, tail, blocks = _decompose_state(text)
    if not blocks or len(blocks) < min_blocks:
        return header + history + tail, []
    blocks_sorted = sorted(blocks, key=lambda b: b[0], reverse=True)
    keep_starts = {b[1] for b in blocks_sorted[:keep_most_recent]}
    return _apply_keep(header, history, tail, blocks, keep_starts)


def gc_state_by_status():
    """
    Status-keyed garbage collection of state.md. Returns (active_lines, archived_lines).

    The `## Current State → Status` field is the authority for what is "pending"
    (per-block headers and 'Dana: pending' prose are unreliable):
      - Status == idle               -> keep the single newest block; archive the rest.
      - Status in {in-progress, ...} -> keep the active (Current source) block AND the
                                        newest; archive the rest.

    Never archives the active/resumable block: the keep-set is keyed on Status +
    Current source, not date alone. No-op when nothing would be archived.
    """
    text = STATE.read_text()
    header, history, tail, blocks = _decompose_state(text)
    if not blocks:
        return header + history + tail, []

    status, current_source = _read_current_state(header)
    blocks_sorted = sorted(blocks, key=lambda b: b[0], reverse=True)

    keep_starts = {blocks_sorted[0][1]}  # always keep the newest block (boot reads its date)
    if status != "idle" and current_source:
        # Force-keep the active source's block(s) — the resume payload — regardless of date.
        for date, start, end, source in blocks:
            if source and (source == current_source
                           or current_source in source
                           or source in current_source):
                keep_starts.add(start)

    if len(keep_starts) >= len(blocks):
        return header + history + tail, []  # already lean
    return _apply_keep(header, history, tail, blocks, keep_starts)


def split_log(cutoff: datetime):
    """
    Returns (active_lines, archived_lines).
    Header lines (before the first dated table row) stay; table rows with date < cutoff
    move to archive; everything else (subsection headers etc.) goes with the row before it.
    """
    lines = LOG.read_text().splitlines()
    # find first dated row
    first_date_idx = None
    for i, line in enumerate(lines):
        if LOG_ROW_RE.match(line):
            first_date_idx = i
            break
    if first_date_idx is None:
        return lines, []
    header = lines[:first_date_idx]
    body = lines[first_date_idx:]

    active_body, archive_body = [], []
    current_bucket = None  # 'active' or 'archive'
    for line in body:
        m = LOG_ROW_RE.match(line)
        if m:
            row_date = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            current_bucket = "active" if row_date >= cutoff else "archive"
        # else: subsection header, blank, etc — stays with its preceding row's bucket
        if current_bucket == "archive":
            archive_body.append(line)
        else:
            active_body.append(line)
    return header + active_body, archive_body


def split_cross_links():
    """
    Returns (active_lines, archived_rows).
    Only targets the FIRST `Status`-bearing table (the Active Pending Queue) —
    subsequent tables (Historical Resolution Ledger, Reference matrices) are left
    alone since their rows are already retired or are reference data.
    Rows in the active queue with status `resolved` move to the archive.
    """
    if not CROSS_LINKS.exists():
        return [], []
    lines = CROSS_LINKS.read_text().splitlines()
    active, archived = [], []
    in_queue = False
    queue_done = False  # set once we've left the first table
    for line in lines:
        if not queue_done and not in_queue and line.startswith("|") and "**" in line and "Status" in line:
            active.append(line)
            in_queue = True
            continue
        if in_queue and line.startswith("| ---"):
            active.append(line)
            continue
        if in_queue and line.startswith("| "):
            cells = [c.strip() for c in line.strip("|").split("|")]
            status = cells[-1] if cells else ""
            if status.startswith("resolved"):  # tolerates "resolved — [[link]]"-style annotations
                archived.append(line)
                continue
        # leaving the first queue
        if in_queue and not line.startswith("|") and line.strip():
            in_queue = False
            queue_done = True
        active.append(line)
    return active, archived


def write_archive(path: Path, header: str, rows: list[str]) -> int:
    if not rows:
        return 0
    if path.exists():
        existing = path.read_text().splitlines()
    else:
        existing = header.splitlines()
    out = existing + rows
    path.write_text("\n".join(out) + "\n")
    return len(rows)


def append_log_row(message: str):
    """Append a single rotation summary row to wiki/log.md."""
    ts = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    row = f"| {ts}      | rotation-run      | rotate_archives.py | {message} |\n"
    with LOG.open("a") as f:
        f.write(row)


def run_state_gc(dry_run: bool = False) -> int:
    """One-shot status-keyed prune of state.md → wiki/archive/state-history.md.
    Returns the number of non-blank lines archived. Used both on the Stop hook
    (continuous leanness) and as a manual one-off. No calendar dependency."""
    active, archived = gc_state_by_status()
    archived_text = [ln for ln in archived if ln.strip()]
    n = len(archived_text)
    if dry_run:
        print(f"DRY-RUN: state-gc would archive {n} lines.")
        return n
    if n == 0:
        print("NO-OP: state.md already lean.")
        return 0
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    target = ARCHIVE / "state-history.md"
    header = (
        "## Specification Registry: Archived Session State History\n\n"
        "Rolling archive pruned from `wiki/state.md` by `rotate_archives.py --state-gc`.\n\n"
    )
    write_archive(target, header, archived_text)
    STATE.write_text("\n".join(active) + "\n")
    append_log_row(f"state-gc archived {n} lines to wiki/archive/state-history.md")
    print(f"STATE-GC: archived {n} lines to wiki/archive/state-history.md")
    return n


def main():
    ap = argparse.ArgumentParser(description="Rotate wiki append-growing files to wiki/archive/<quarter>/.")
    ap.add_argument("quarter", nargs="?", help="Target quarter, e.g. 2026-q3 (omit with --state-gc)")
    ap.add_argument("--dry-run", action="store_true", help="Report what would change; write nothing.")
    ap.add_argument("--force", action="store_true", help="Rotate even if the target quarter is still in progress (otherwise refuse).")
    ap.add_argument("--state-gc", action="store_true",
                    help="Status-keyed prune of state.md only (idle→keep newest; in-progress→keep active+newest). "
                         "No quarter arg needed; safe to run every session.")
    args = ap.parse_args()

    # Status-keyed state.md GC: independent of the quarterly calendar path.
    if args.state_gc:
        run_state_gc(dry_run=args.dry_run)
        return

    if not args.quarter:
        ap.error("quarter is required unless --state-gc is given")

    cutoff = next_quarter_start(args.quarter)
    qdir = ARCHIVE / args.quarter
    qdir.mkdir(parents=True, exist_ok=True)

    # Sanity check: refuse to rotate a quarter that is still in progress, unless --force.
    today = datetime.utcnow()
    qend = cutoff  # cutoff is the first day of the quarter AFTER the named one
    if today < qend and not args.dry_run:
        if not args.force:
            sys.exit(
                f"ERROR: {args.quarter} is still in progress (ends {qend:%Y-%m-%d}, "
                f"today is {today:%Y-%m-%d}). Wait until the quarter ends, or pass --force."
            )
        print(
            f"WARN: --force in effect; archiving in-progress {args.quarter}.",
            file=sys.stderr,
        )

    summary = {}

    # 1. update-proposals.md
    active, archived = split_proposals()
    if archived:
        target = qdir / "update-proposals-executed.md"
        header = (
            "## Specification Registry: Archived Update Proposals\n\n"
            f"Rotated from `wiki/pending/update-proposals.md` for {args.quarter}.\n\n"
            "| **Proposal ID** | **Date** | **Type** | **Target** | **Cluster** | **Trigger** | **Priority** | **Status** |\n"
            "| --------------- | -------- | -------- | ---------- | ----------- | ----------- | ------------ | ---------- |\n"
        )
        if not args.dry_run:
            write_archive(target, header, archived)
            PROPOSALS.write_text("\n".join(active) + "\n")
    summary["proposals"] = len(archived)

    # 2. state.md
    active, archived = split_state(keep_most_recent=5)
    if archived:
        target = qdir / "state-history.md"
        header = (
            "## Specification Registry: Archived Session State History\n\n"
            f"Rotated from `wiki/state.md` for {args.quarter}.\n\n"
        )
        archived_text = [ln for ln in archived if ln.strip()]
        if not args.dry_run and archived_text:
            write_archive(target, header, archived_text)
            STATE.write_text("\n".join(active) + "\n")
    summary["state"] = len([ln for ln in archived if ln.strip()])

    # 3. log.md
    active, archived = split_log(cutoff)
    if archived:
        target = qdir / "log.md"
        header = (
            "## Specification Registry: Archived Operation Log\n\n"
            f"Rotated from `wiki/log.md` for {args.quarter} (rows dated before {cutoff:%Y-%m-%d}).\n\n"
        )
        if not args.dry_run:
            write_archive(target, header, archived)
            LOG.write_text("\n".join(active) + "\n")
    summary["log"] = len([ln for ln in archived if LOG_ROW_RE.match(ln)])

    # 4. cross-links.md
    active, archived = split_cross_links()
    if archived:
        target = qdir / "cross-links-resolved.md"
        header = (
            "## Specification Registry: Archived Cross-Links (resolved)\n\n"
            f"Rotated from `wiki/pending/cross-links.md` for {args.quarter}.\n\n"
        )
        if not args.dry_run:
            write_archive(target, header, archived)
            CROSS_LINKS.write_text("\n".join(active) + "\n")
    summary["cross_links"] = len(archived)

    total = sum(summary.values())
    msg = (
        f"quarter={args.quarter} proposals={summary['proposals']} "
        f"state_lines={summary['state']} log_rows={summary['log']} "
        f"cross_links={summary['cross_links']} (dry-run={args.dry_run})"
    )

    if args.dry_run:
        print(f"DRY-RUN: would rotate {total} rows/blocks. {msg}")
        return

    if total == 0:
        print(f"NO-OP: nothing to rotate for {args.quarter}.")
        return

    append_log_row(f"rotated {total} rows; {msg}")
    print(f"ROTATED: {msg}")


if __name__ == "__main__":
    main()
