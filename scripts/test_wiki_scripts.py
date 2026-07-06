#!/usr/bin/env python3
"""
test_wiki_scripts.py — smoke tests for the two load-bearing, hook-enforced scripts
(build_index.py + validate_wiki.py). These sit on the Stop critical path: a silent
regression there corrupts wiki/lookup.md or lets a bad page through the gate.

Coverage:
  - validate_wiki.py PASSES a known-good fixture tree and FAILS a known-bad one
    (the canonical "flags a bad page, passes a good one" guard).
  - build_index.py emits a wiki/lookup.md with the correct page count on a fixture.
  - the pure helpers in both scripts (slugify / is_code / title_of / norm / _norm_cap)
    behave as the index and validator rely on.

Fixture tests use the WIKI_ROOT env override so the real wiki is never touched.
Stdlib only. Run:  python3 scripts/test_wiki_scripts.py
"""

import os
import re
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import datetime
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
BUILD = SCRIPTS / "build_index.py"
VALIDATE = SCRIPTS / "validate_wiki.py"
WITH_LOCK = SCRIPTS / "with_lock.py"
NEW_PROPOSAL = SCRIPTS / "new_proposal.py"
APPEND_ROW = SCRIPTS / "append_row.py"

GOOD_PAGE = """\
---
cluster: demo
aliases: ["Demo Page", "demo concept"]
keywords: [demo, smoke, test, fixture]
tags: [demo]
summary: "A demo page for smoke testing."
entities: ["FPL9"]
---

# Demo Page

**Summary**: A demo page for smoke testing.

**Cluster**: [[demo]]

**Sources**:
- demo-source.md

**Last updated**: 2026-06-23

## Overview

A demo concept used only by the smoke test.

## Details

### Demo Subsection

Demo details with a grounded citation. (source: demo-source.md)
"""

# Same folder (demo) but frontmatter cluster says something else -> known-bad (cluster mismatch).
BAD_PAGE = """\
---
cluster: wrongcluster
aliases: ["Bad Page"]
keywords: [bad, fixture]
tags: [demo]
summary: "A deliberately inconsistent page."
---

# Bad Page

**Summary**: A deliberately inconsistent page.

**Cluster**: [[demo]]

## Overview

x

## Details

### S

y (source: z.md)
"""


def _make_tree(tmp: Path, pages: dict):
    """pages: {filename: content} written under wiki/pages/demo/."""
    (tmp / "wiki" / "pages" / "demo").mkdir(parents=True, exist_ok=True)
    (tmp / "wiki" / "pending").mkdir(parents=True, exist_ok=True)
    (tmp / "wiki" / "clusters").mkdir(parents=True, exist_ok=True)
    for name, content in pages.items():
        (tmp / "wiki" / "pages" / "demo" / name).write_text(content, encoding="utf-8")


def _write_card(tmp: Path, content: str):
    """Writes a fixture wiki/agents/paul-dev-card.md (the optional, hand-authored dev card)."""
    (tmp / "wiki" / "agents").mkdir(parents=True, exist_ok=True)
    (tmp / "wiki" / "agents" / "paul-dev-card.md").write_text(content, encoding="utf-8")


def _write_pack(tmp: Path, name: str, content: str):
    """Writes a fixture wiki/agents/paul-card-packs/<name> (a lazily-loaded phase pack)."""
    packs = tmp / "wiki" / "agents" / "paul-card-packs"
    packs.mkdir(parents=True, exist_ok=True)
    (packs / name).write_text(content, encoding="utf-8")


def _run(script: Path, root: Path, *args):
    env = dict(os.environ, WIKI_ROOT=str(root))
    return subprocess.run([sys.executable, str(script), *args],
                          capture_output=True, text=True, env=env)


def _build(root: Path):
    # --no-counts: emit lookup.md + index-report.md only; skip index.md/cluster reconciliation
    # (the fixture has no index.md to reconcile).
    r = _run(BUILD, root, "--no-counts")
    assert r.returncode == 0, f"build_index failed: {r.stdout}\n{r.stderr}"
    return r


class ValidateFixtureTests(unittest.TestCase):
    def test_passes_good_tree(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _make_tree(root, {"good.md": GOOD_PAGE})
            _build(root)
            r = _run(VALIDATE, root)
            self.assertEqual(r.returncode, 0, f"expected PASS, got:\n{r.stdout}\n{r.stderr}")
            self.assertIn("PASS", r.stdout)

    def test_flags_bad_page(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _make_tree(root, {"good.md": GOOD_PAGE, "bad.md": BAD_PAGE})
            _build(root)  # refresh lookup.md so the only ERROR is the cluster mismatch
            r = _run(VALIDATE, root)
            self.assertEqual(r.returncode, 1, f"expected FAIL, got:\n{r.stdout}")
            self.assertIn("FAIL", r.stdout)
            self.assertIn("!= hosting folder 'demo'", r.stdout)


class PaulCardFixtureTests(unittest.TestCase):
    """wiki/agents/paul-dev-card.md is optional (hand-authored); when present, every
    [[wikilink]] must resolve to a real page. No-card trees stay unaffected (no-op)."""

    def test_no_card_is_a_no_op(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _make_tree(root, {"good.md": GOOD_PAGE})
            _build(root)
            r = _run(VALIDATE, root)
            self.assertEqual(r.returncode, 0, f"expected PASS, got:\n{r.stdout}\n{r.stderr}")
            self.assertNotIn("paul-dev-card.md", r.stdout)

    def test_passes_card_with_resolving_link(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _make_tree(root, {"good.md": GOOD_PAGE})
            _build(root)
            _write_card(root, "# Paul Dev Card (fixture)\n\nSee [[good]] for an example.\n")
            r = _run(VALIDATE, root)
            self.assertEqual(r.returncode, 0, f"expected PASS, got:\n{r.stdout}\n{r.stderr}")
            self.assertIn("PASS", r.stdout)

    def test_flags_card_with_dangling_link(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _make_tree(root, {"good.md": GOOD_PAGE})
            _build(root)
            _write_card(root, "# Paul Dev Card (fixture)\n\nSee [[missing-page]] for an example.\n")
            r = _run(VALIDATE, root)
            self.assertEqual(r.returncode, 1, f"expected FAIL, got:\n{r.stdout}")
            self.assertIn("FAIL", r.stdout)
            self.assertIn("wikilink [[missing-page]] does not resolve to a page", r.stdout)


class PaulCardPackFixtureTests(unittest.TestCase):
    """wiki/agents/paul-card-packs/*.md are the dev-card's lazily-loaded phase packs.
    When the core card is present, every pack gets the same wikilink + grep-recipe checks,
    every pack path listed in the core's Pack Index table must exist on disk, and no rule
    ID may be defined in more than one file. No card -> the whole block (pack checks
    included) is a no-op."""

    @staticmethod
    def _core(*pack_names):
        rows = "".join(f"| `paul-card-packs/{n}` | fixture |\n" for n in pack_names)
        return ("# Paul Dev Card v2 (fixture)\n\n"
                "## Pack Index\n\n"
                "| Pack | Load when |\n"
                "|---|---|\n" + rows +
                "\nSee [[good]] for an example.\n")

    def test_passes_healthy_core_plus_packs(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _make_tree(root, {"good.md": GOOD_PAGE})
            _build(root)
            _write_card(root, self._core("pack-1-tdd.md", "pack-2-structure-patterns.md"))
            _write_pack(root, "pack-1-tdd.md",
                        "# Pack 1 — TDD (fixture)\n\n"
                        "- **TDD-DESIGN-01** Test first. See [[good]].\n"
                        "- **CA-TESTING-01** Write testable code.\n"
                        "\nRecipe: `grep -i demo wiki/lookup.md`\n")
            _write_pack(root, "pack-2-structure-patterns.md",
                        "# Pack 2 — structure (fixture)\n\n"
                        "- **OOP-SOLID-01** One reason to change.\n"
                        "- **DP-02 Factory** Centralise creation.\n")
            r = _run(VALIDATE, root)
            self.assertEqual(r.returncode, 0, f"expected PASS, got:\n{r.stdout}\n{r.stderr}")
            self.assertIn("PASS", r.stdout)

    def test_flags_pack_with_dangling_link(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _make_tree(root, {"good.md": GOOD_PAGE})
            _build(root)
            _write_card(root, self._core("pack-1-tdd.md"))
            _write_pack(root, "pack-1-tdd.md",
                        "# Pack 1 (fixture)\n\nSee [[missing-page]] for an example.\n")
            r = _run(VALIDATE, root)
            self.assertEqual(r.returncode, 1, f"expected FAIL, got:\n{r.stdout}")
            self.assertIn("FAIL", r.stdout)
            self.assertIn("paul-card-packs/pack-1-tdd.md", r.stdout)
            self.assertIn("wikilink [[missing-page]] does not resolve to a page", r.stdout)

    def test_flags_missing_listed_pack(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _make_tree(root, {"good.md": GOOD_PAGE})
            _build(root)
            _write_card(root, self._core("pack-9-ghost.md"))
            r = _run(VALIDATE, root)
            self.assertEqual(r.returncode, 1, f"expected FAIL, got:\n{r.stdout}")
            self.assertIn("FAIL", r.stdout)
            self.assertIn("paul-card-packs/pack-9-ghost.md", r.stdout)
            self.assertIn("does not exist on disk", r.stdout)

    def test_flags_duplicate_rule_id_across_files(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _make_tree(root, {"good.md": GOOD_PAGE})
            _build(root)
            _write_card(root, self._core("pack-1-tdd.md"))
            _write_pack(root, "pack-1-tdd.md",
                        "# Pack 1 (fixture)\n\n- **CA-TESTING-01** Write testable code.\n")
            _write_pack(root, "pack-2-structure-patterns.md",
                        "# Pack 2 (fixture)\n\n- **CA-TESTING-01** Copied, not moved.\n")
            r = _run(VALIDATE, root)
            self.assertEqual(r.returncode, 1, f"expected FAIL, got:\n{r.stdout}")
            self.assertIn("FAIL", r.stdout)
            self.assertIn("rule ID CA-TESTING-01 defined in more than one file", r.stdout)
            self.assertIn("wiki/agents/paul-card-packs/pack-1-tdd.md", r.stdout)
            self.assertIn("wiki/agents/paul-card-packs/pack-2-structure-patterns.md", r.stdout)

    def test_no_card_skips_pack_checks_too(self):
        # A broken pack with NO core card present must not fail — the absent-card no-op
        # contract covers the whole block, pack checks included.
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _make_tree(root, {"good.md": GOOD_PAGE})
            _build(root)
            _write_pack(root, "pack-1-tdd.md",
                        "# Pack 1 (fixture)\n\nSee [[missing-page]].\n")
            r = _run(VALIDATE, root)
            self.assertEqual(r.returncode, 0, f"expected PASS, got:\n{r.stdout}\n{r.stderr}")
            self.assertNotIn("pack-1-tdd.md", r.stdout)


class BuildIndexFixtureTests(unittest.TestCase):
    def test_emits_lookup_with_page_count(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _make_tree(root, {"good.md": GOOD_PAGE})
            _build(root)
            lookup = root / "wiki" / "lookup.md"
            self.assertTrue(lookup.exists(), "build_index did not emit lookup.md")
            head = lookup.read_text(encoding="utf-8")[:500]
            self.assertIn("1 pages", head, f"lookup.md header missing expected count: {head!r}")


class PureHelperTests(unittest.TestCase):
    def setUp(self):
        sys.path.insert(0, str(SCRIPTS))
        import build_index, validate_wiki  # noqa: E402
        self.bi = build_index
        self.vw = validate_wiki

    def test_build_index_helpers(self):
        self.assertEqual(self.bi.slugify("Clearing Control FICA.md"), "clearing-control-fica")
        self.assertTrue(self.bi.is_code("FPL9"))
        self.assertTrue(self.bi.is_code("DFKKOP"))
        self.assertFalse(self.bi.is_code("Configuration"))   # plain Titlecase word
        self.assertFalse(self.bi.is_code("SAP"))             # stop-code
        self.assertEqual(self.bi.title_of("# Account Balance\n\nbody", "fb"), "Account Balance")
        self.assertEqual(self.bi.title_of("no heading here", "fallback"), "fallback")

    def test_validate_helpers(self):
        # a double-quoted frontmatter value compares equal to the plain body text it mirrors
        self.assertEqual(self.vw.norm('"A demo page."'), self.vw.norm("A demo page."))
        # capability normalisation is case/dash/space tolerant
        self.assertEqual(self.vw._norm_cap("API Management"), self.vw._norm_cap("api management"))
        self.assertEqual(self.vw._norm_cap("N/A — Foundational"), self.vw._norm_cap("N/A - Foundational"))
        # the ported Details/marker regexes match as intended
        self.assertTrue(self.vw.SOURCE_CITE_RE.search("text (source: x.md)"))
        self.assertEqual(self.vw.INTEGRATION_MARKER_RE.findall("see [?INTEGRATION: Foo Bar]"), ["Foo Bar"])
        self.assertTrue(self.vw.DETAILS_SUBHEAD_RE.search("## Details\n\n### Sub\nbody"))


class StateGcTests(unittest.TestCase):
    """Status-keyed state.md GC: idle keeps the newest block; in-progress also keeps the
    active (Current source) block; never evicts the resumable block; idempotent."""

    def setUp(self):
        sys.path.insert(0, str(SCRIPTS))
        import rotate_archives  # noqa: E402
        self.ra = rotate_archives
        self._orig_state = self.ra.STATE
        self._tmp = tempfile.TemporaryDirectory()
        self.state = Path(self._tmp.name) / "state.md"
        self.ra.STATE = self.state  # redirect module-level STATE at the source

    def tearDown(self):
        self.ra.STATE = self._orig_state
        self._tmp.cleanup()

    def _write(self, status, current_source, blocks):
        """blocks: list of (source, date). The active source's header reads '(started …)'
        when not idle, mirroring a real in-progress block; the rest read '(completed …)'."""
        lines = [
            "# Session State", "",
            "## Current State", "",
            f"- **Current source**: {current_source}",
            f"- **Status**: {status}", "",
        ]
        plain_source = current_source.split(" (")[0]
        for src, date in blocks:
            verb = "started" if (status != "idle" and src == plain_source) else "completed"
            lines += [
                f"## Stage Plan — {src} ({verb} {date})",
                f"- **INGESTION COMPLETE ({date})**: {src} — fixture body text.",
                "Files: 1", "",
            ]
        self.state.write_text("\n".join(lines) + "\n")

    def test_idle_keeps_newest_only(self):
        self._write("idle", "c (complete)",
                    [("a", "2026-06-01"), ("b", "2026-06-02"), ("c", "2026-06-03")])
        active, archived = self.ra.gc_state_by_status()
        txt, arc = "\n".join(active), "\n".join(archived)
        self.assertIn("## Current State", txt)        # header preserved
        self.assertIn("Stage Plan — c", txt)          # newest kept
        self.assertNotIn("Stage Plan — a", txt)
        self.assertNotIn("Stage Plan — b", txt)
        self.assertIn("Stage Plan — a", arc)          # older archived
        self.assertIn("Stage Plan — b", arc)

    def test_in_progress_keeps_active_and_newest(self):
        # The active/resumable source is the OLDEST block; it must survive with the newest.
        self._write("in-progress", "a",
                    [("a", "2026-06-01"), ("b", "2026-06-02"), ("c", "2026-06-03")])
        active, _ = self.ra.gc_state_by_status()
        txt = "\n".join(active)
        self.assertIn("Stage Plan — a", txt)          # active block never evicted
        self.assertIn("Stage Plan — c", txt)          # newest kept
        self.assertNotIn("Stage Plan — b", txt)

    def test_idempotent_no_op_second_run(self):
        self._write("idle", "c (complete)",
                    [("a", "2026-06-01"), ("b", "2026-06-02"), ("c", "2026-06-03")])
        active, archived = self.ra.gc_state_by_status()
        self.assertTrue([l for l in archived if l.strip()])
        self.state.write_text("\n".join(active) + "\n")
        _, archived2 = self.ra.gc_state_by_status()
        self.assertEqual([l for l in archived2 if l.strip()], [])

    def test_read_current_state_strips_parenthetical(self):
        self._write("idle", "bdc-foo (complete)", [("bdc-foo", "2026-06-03")])
        header, *_ = self.ra._decompose_state(self.state.read_text())
        status, source = self.ra._read_current_state(header)
        self.assertEqual(status, "idle")
        self.assertEqual(source, "bdc-foo")


class ParallelBuildTests(unittest.TestCase):
    """OPT-002/020: concurrent build_index.py runs (atomic_write) must leave lookup.md
    intact and fully parseable — never a torn file, never .tmp litter."""

    def test_four_concurrent_builds_leave_lookup_intact(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _make_tree(root, {"good.md": GOOD_PAGE})
            env = dict(os.environ, WIKI_ROOT=str(root))
            procs = [subprocess.Popen([sys.executable, str(BUILD), "--no-counts"],
                                      env=env, stdout=subprocess.DEVNULL,
                                      stderr=subprocess.DEVNULL) for _ in range(4)]
            rcs = [p.wait() for p in procs]
            self.assertTrue(all(rc == 0 for rc in rcs), f"rcs={rcs}")
            lookup = root / "wiki" / "lookup.md"
            text = lookup.read_text(encoding="utf-8")
            self.assertIn("1 pages", text[:500])   # header intact
            self.assertIn("## Pages", text)          # structure parseable
            litter = list((root / "wiki").glob("lookup.md.tmp.*"))
            self.assertEqual(litter, [], f"atomic_write left tmp litter: {litter}")


class WithLockTests(unittest.TestCase):
    """OPT-001: fcntl.flock wrapper — uncontended runs and propagates rc; a contender
    that cannot acquire within --timeout exits 75."""

    def _env(self, d):
        (Path(d) / "wiki" / ".locks").mkdir(parents=True, exist_ok=True)
        return dict(os.environ, CLAUDE_PROJECT_DIR=str(d))

    def test_uncontended_runs_and_propagates_rc(self):
        with tempfile.TemporaryDirectory() as d:
            env = self._env(d)
            r = subprocess.run([sys.executable, str(WITH_LOCK), "t.lock", "--", "true"],
                               env=env, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0)
            r2 = subprocess.run([sys.executable, str(WITH_LOCK), "t.lock", "--", "false"],
                                env=env, capture_output=True, text=True)
            self.assertEqual(r2.returncode, 1)   # child rc propagated

    def test_contended_times_out_75(self):
        with tempfile.TemporaryDirectory() as d:
            env = self._env(d)
            holder = subprocess.Popen(
                [sys.executable, str(WITH_LOCK), "t.lock", "--",
                 sys.executable, "-c", "import time; time.sleep(2)"], env=env)
            time.sleep(0.5)   # let the holder acquire
            r = subprocess.run(
                [sys.executable, str(WITH_LOCK), "t.lock", "--timeout", "1", "--", "true"],
                env=env, capture_output=True, text=True)
            self.assertEqual(r.returncode, 75, f"stderr={r.stderr}")
            self.assertIn("timeout", r.stderr)
            holder.wait()


class NewProposalTests(unittest.TestCase):
    """OPT-005: O_EXCL atomic ID allocation — N parallel claims yield N unique IDs/files."""

    def test_five_parallel_claims_are_unique(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            env = dict(os.environ, WIKI_ROOT=str(root))
            procs = [subprocess.Popen([sys.executable, str(NEW_PROPOSAL),
                                       "--title", f"t{i}"], env=env,
                                      stdout=subprocess.PIPE, text=True) for i in range(5)]
            outs = [p.communicate()[0].strip() for p in procs]
            self.assertTrue(all(p.returncode == 0 for p in procs))
            ids = [o for o in outs if o.startswith("SP-")]
            self.assertEqual(len(set(ids)), 5, f"non-unique ids: {ids}")
            files = list((root / "wiki" / "pending" / "proposals").glob("SP-*.md"))
            self.assertEqual(len(files), 5)


class AppendRowTests(unittest.TestCase):
    """OPT-007: O_APPEND single write — 10 parallel writers, all rows present, none torn."""

    def test_ten_parallel_writers_no_torn_rows(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "wiki" / "pending").mkdir(parents=True)
            (root / "wiki" / "pending" / "retrieval-log.md").write_text("# hdr\n")
            env = dict(os.environ, WIKI_ROOT=str(root))
            procs = [subprocess.Popen(
                [sys.executable, str(APPEND_ROW),
                 "wiki/pending/retrieval-log.md", f"| GATE {i} |"], env=env)
                for i in range(10)]
            [p.wait() for p in procs]
            lines = (root / "wiki" / "pending" / "retrieval-log.md").read_text().splitlines()
            gate = [l for l in lines if l.startswith("| GATE ")]
            self.assertEqual(len(gate), 10)
            self.assertTrue(all(re.fullmatch(r"\| GATE \d+ \|", l) for l in gate),
                            f"torn/interleaved rows: {gate}")


class CountStatusRowsTests(unittest.TestCase):
    """OPT-008: annotated status cells count (last cell startswith the token)."""

    def setUp(self):
        sys.path.insert(0, str(SCRIPTS))
        import wikilib  # noqa: E402
        self.wl = wikilib

    def test_annotated_status_rows_counted(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "cl.md"
            f.write_text(
                "| **A** | **Status** |\n| --- | --- |\n"
                "| x | pending |\n"
                "| x | pending - awaiting Sarah |\n"
                "| x | resolved 2026-06-21 [[p]] |\n"
                "| x | gap - no target |\n")
            self.assertEqual(self.wl.count_status_rows(f, ["pending"]), 2)
            self.assertEqual(self.wl.count_status_rows(f, ["resolved"]), 1)
            self.assertEqual(self.wl.count_status_rows(f, ["gap"]), 1)


class SplitDatedLedgerTests(unittest.TestCase):
    """OPT-011: date-cutoff ledger split — old dated rows archive; every non-row line
    (headers, column headers, blanks) stays in the active file."""

    def setUp(self):
        sys.path.insert(0, str(SCRIPTS))
        import rotate_archives  # noqa: E402
        self.ra = rotate_archives

    def test_archives_old_rows_keeps_structure(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "gap-log.md"
            f.write_text(
                "# Gap Log\n\n## Section\n\n| Date | X |\n| --- | --- |\n"
                "| 2026-06-04 | old |\n"
                "| 2026-08-01 | new |\n")
            active, archived = self.ra.split_dated_ledger(
                f, self.ra.LEDGER_ROW_RE, datetime(2026, 7, 1))
            self.assertIn("| 2026-06-04 | old |", archived)
            self.assertNotIn("| 2026-08-01 | new |", archived)
            self.assertIn("| 2026-08-01 | new |", active)
            # non-row lines never migrate to the archive
            self.assertIn("## Section", active)
            self.assertIn("| Date | X |", active)
            self.assertNotIn("## Section", archived)
            self.assertNotIn("| Date | X |", archived)


if __name__ == "__main__":
    unittest.main(verbosity=2)
