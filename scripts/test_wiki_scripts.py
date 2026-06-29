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
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
BUILD = SCRIPTS / "build_index.py"
VALIDATE = SCRIPTS / "validate_wiki.py"

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


if __name__ == "__main__":
    unittest.main(verbosity=2)
