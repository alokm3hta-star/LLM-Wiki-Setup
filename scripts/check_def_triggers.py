#!/usr/bin/env python3
"""check_def_triggers.py — evaluate the machine-checkable revisit triggers from
wiki/pending/deferred-optimisations.md and print a consolidated status block.

Run by scripts/maintenance_sweep.sh (pull-at-boot cadence). One line per trigger:
CROSSED / ok / MANUAL (not machine-checkable; says where to look instead).
CROSSED lines are duplicated to stderr as WARN so the sweep digest and ready card
surface them. Always exits 0. Stdlib only.

Overlap with check_thresholds.py (lookup/tier2 line counts) is intentional: that
script fires at every Stop; this one is the consolidated DEF view at sweep cadence.
"""
import datetime
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
results = []


def lines(p: Path) -> int:
    return sum(1 for _ in p.open()) if p.exists() else 0


def add(def_id, label, crossed, detail):
    results.append((def_id, label, "CROSSED" if crossed else "ok", detail))


def manual(def_id, label, where):
    results.append((def_id, label, "MANUAL", where))


def main():
    today = datetime.date.today()
    q = (today.month - 1) // 3 + 1
    quarter_start = datetime.date(today.year, 3 * (q - 1) + 1, 1)

    lookup = ROOT / "wiki" / "lookup.md"
    tier2 = ROOT / "wiki" / "tier2-sections.md"
    log = ROOT / "wiki" / "log.md"
    prop_dir = ROOT / "wiki" / "pending" / "proposals"

    # ---- DEF-001 ----
    n = lines(lookup)
    add("DEF-001", "lookup.md lines > 15000", n > 15000, str(n))
    per, in_pages = {}, False
    if lookup.exists():
        page_re = re.compile(r"^([a-z][a-z0-9\-]+)/[^|]+\|")
        for line in lookup.open():
            if line.startswith("## Pages"):
                in_pages = True
                continue
            if line.startswith("## "):
                in_pages = False
                continue
            m = page_re.match(line) if in_pages else None
            if m:
                per[m.group(1)] = per.get(m.group(1), 0) + 1
    biggest = max(per.values()) if per else 0
    add("DEF-001", "largest per-cluster lookup slice > 6000 rows", biggest > 6000, str(biggest))
    # DEF-001 trigger 3 ("grep regularly > 200 lines") is captured further down via
    # the standardised retrieval-log rows (grep-lines= field), not left as manual.

    # ---- DEF-002 ----
    if prop_dir.exists():
        pending = sum(1 for f in prop_dir.glob("SP-*.md")
                      if re.search(r"^status:\s*pending\b",
                                   f.read_text(errors="ignore"), re.M))
    else:
        legacy = ROOT / "wiki" / "pending" / "update-proposals.md"
        pending = sum(1 for l in legacy.open()
                      if l.rstrip().endswith("| pending |")) if legacy.exists() else 0
    add("DEF-002", "pending proposals > 500", pending > 500,
        f"{pending} (full trigger needs 2 consecutive quarters; confirm trend in health-history.md)")

    # ---- DEF-003 ----
    n = lines(tier2)
    add("DEF-003", "tier2-sections.md lines > 25000", n > 25000, str(n))
    src = ROOT / "wiki" / "sources.md"
    nsrc = sum(1 for l in src.open() if l.startswith("| ")) if src.exists() else 0
    add("DEF-003", "sources.md rows > 600", nsrc > 600, str(nsrc))

    # ---- DEF-004 / DEF-005 (dry-run build = full parse+resolve, no writes) ----
    t0 = time.monotonic()
    subprocess.run([sys.executable, "scripts/build_index.py", "--dry-run"],
                   capture_output=True, cwd=ROOT)
    dt = time.monotonic() - t0
    add("DEF-004", "build_index.py dry-run wall time > 10s", dt > 10, f"{dt:.1f}s")
    pages_dir = ROOT / "wiki" / "pages"
    pages = sum(1 for _ in pages_dir.rglob("*.md")) if pages_dir.exists() else 0
    add("DEF-004/005", "corpus > 4000 pages", pages > 4000, str(pages))

    # ---- DEF-006 ----
    for spec in ("aaron-strategy", "adrian-technical"):
        n = lines(ROOT / "wiki" / "agents" / f"{spec}.md")
        add("DEF-006", f"{spec}.md > 800 lines", n > 800, str(n))

    # ---- DEF-007 (card-drift proposals filed this quarter) ----
    drift = 0
    pat = re.compile(r"paul-dev-card|paul-card-packs")
    if prop_dir.exists():
        for f in prop_dir.glob("SP-*.md"):
            t = f.read_text(errors="ignore")
            md = re.search(r"^date:\s*(\d{4}-\d{2}-\d{2})", t, re.M)
            if md and datetime.date.fromisoformat(md.group(1)) >= quarter_start \
               and pat.search(t):
                drift += 1
    qdir = ROOT / "wiki" / "archive" / f"{today.year}-q{q}" / "proposals"
    if qdir.exists():
        drift += sum(1 for f in qdir.glob("SP-*.md")
                     if pat.search(f.read_text(errors="ignore")))
    add("DEF-007", "card-drift proposals this quarter >= 3", drift >= 3, str(drift))
    manual("DEF-007", "second craft book enters scope",
           "event tripwire: kylie-convert/anja-ingest specs flag rulebook-style sources to the user")

    # ---- DEF-008 (Paul relay rate; requires tagged log rows, see operations.md) ----
    week_ago = today - datetime.timedelta(days=7)
    relays = 0
    if log.exists():
        for l in log.open():
            m = re.match(r"^\| (\d{4}-\d{2}-\d{2})T", l)
            if m and "paul-writeback-relay" in l \
               and datetime.date.fromisoformat(m.group(1)) >= week_ago:
                relays += 1
    add("DEF-008", "Paul write-back relays in last 7 days >= 5", relays >= 5,
        f"{relays} (counts rows tagged paul-writeback-relay in wiki/log.md)")

    # ---- DEF-008 trigger 2 (card-conformance audit findings) ----
    misses = 0
    if log.exists():
        misses = sum(1 for l in log.open() if "card-conformance-miss" in l)
    add("DEF-008", "card-conformance-miss audit findings >= 2", misses >= 2,
        f"{misses} (counts rows tagged card-conformance-miss in wiki/log.md)")

    # ---- DEF-009 / DEF-010 / DEF-011 ----
    manual("DEF-009", "ingestions queueing behind each other",
           "operator judgement; compare ingest-queue count vs state.md status")
    coll = 0
    if log.exists():
        coll = sum(1 for l in log.open() if "| collision" in l)
    add("DEF-010/011", "cross-session collision events logged >= 1", coll >= 1,
        f"{coll} (counts rows tagged collision in wiki/log.md)")

    # ---- DEF-001 trigger 3 / DEF-003 trigger 3 (retrieval-log standard rows) ----
    rlog = ROOT / "wiki" / "pending" / "retrieval-log.md"
    thirty_ago = today - datetime.timedelta(days=30)
    heavy_greps, tier2_yes, std_rows = 0, 0, 0
    if rlog.exists():
        for l in rlog.open():
            m = re.match(r"^\| (\d{4}-\d{2}-\d{2})T", l)
            if not (m and "grep-lines=" in l):
                continue
            if datetime.date.fromisoformat(m.group(1)) < thirty_ago:
                continue
            std_rows += 1
            gm = re.search(r"grep-lines=(\d+)", l)
            if gm and int(gm.group(1)) > 200:
                heavy_greps += 1
            if "tier2=yes" in l:
                tier2_yes += 1
    add("DEF-001", "retrieval greps >200 lines in last 30d >= 3", heavy_greps >= 3,
        f"{heavy_greps} of {std_rows} standardised rows")
    t2_share = (tier2_yes / std_rows) if std_rows else 0.0
    add("DEF-003", "tier2 fallthrough share > 10% (min 20 rows)",
        std_rows >= 20 and t2_share > 0.10,
        f"{tier2_yes}/{std_rows} = {t2_share:.0%}")

    print("Deferred-trigger status (see wiki/pending/deferred-optimisations.md):")
    for def_id, label, state, detail in results:
        print(f"  {state:8s} {def_id:12s} {label} — {detail}")
    crossed = [r for r in results if r[2] == "CROSSED"]
    if crossed:
        print("WARN (deferred-optimisations): revisit trigger(s) crossed:", file=sys.stderr)
        for def_id, label, _, detail in crossed:
            print(f"  - {def_id}: {label} ({detail})", file=sys.stderr)


if __name__ == "__main__":
    main()
