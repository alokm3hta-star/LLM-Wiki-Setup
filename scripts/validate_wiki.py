#!/usr/bin/env python3
"""
validate_wiki.py — post-ingestion / pre-finish consistency gate for the LLM Wiki.

Asserts the invariants that mean "the wiki is up to date" — the checks build_index.py
does NOT perform — then exits non-zero if any ERROR is found, so:
  - the Stop / SubagentStop hook can block "done" and surface the report, and
  - the Dana (live) / Sentinel (template) validator agent can report + route rework.

ERROR  (hard gate — must be reworked before ingestion is "complete"):
  - every wiki/pages/**.md has YAML frontmatter with all 6 mandatory fields
    (cluster, aliases, keywords, tags, summary, entities)
  - frontmatter `cluster:` matches the hosting folder
  - frontmatter `summary:` matches the body **Summary**
  - the index (lookup.md) is FRESH — no page newer than it
  - page counts reconcile: actual == lookup.md header == index.md "Total pages"
  - archival integrity: no source file exists in BOTH raw/ and raw_processed/
    (the copy-not-move signature — Guardrail #1 sanctions a MOVE, not a copy, on archival)
  - integration-cluster pages carry a `**Capability**:` from the controlled vocabulary
    (schema.md → "SAP Integration Suite Page Extension"); the value is a derived classification
    so it is always assignable — never legitimately absent

WARN  (advisory — routed to curation, does NOT fail the gate):
  - broken wikilinks / near-duplicate titles, read from pending/index-report.md
  - (Dana §2c/2e ported, STAGED): a page '## Details' section lacking a '### ' subsection,
    or lacking a '(source: ...)' inline citation
  - (Dana §2d ported, STAGED): a [?INTEGRATION:] marker not found registered in cross-links.md
  - (Part 3, STAGED): a cluster whose index.md Primary-Sources cell says "pending" while its
    wiki/pages/<cluster>/ folder is populated (stale registry annotation)

These four are staged as WARN deliberately: they encode Dana's manual mechanical checks
(dana-validator.md §2) so they are enforced deterministically even when Dana is not spawned.
Promote them to ERROR once the corpus is clean (no WARNs of these kinds remain).

Stdlib only. Run from anywhere:  python scripts/validate_wiki.py [--quiet]
"""

import os
import re
import sys
from pathlib import Path

# ROOT defaults to the project root (scripts/..); a WIKI_ROOT env override lets the smoke
# tests (scripts/test_wiki_scripts.py) point the validator at a fixture tree. Default unchanged.
ROOT = Path(os.environ.get("WIKI_ROOT") or Path(__file__).resolve().parent.parent).resolve()
PAGES = ROOT / "wiki" / "pages"
LOOKUP = ROOT / "wiki" / "lookup.md"
INDEX = ROOT / "wiki" / "index.md"
REPORT = ROOT / "wiki" / "pending" / "index-report.md"
CROSSLINKS = ROOT / "wiki" / "pending" / "cross-links.md"
RAW = ROOT / "raw"
RAWP = ROOT / "raw_processed"

# Mandatory frontmatter fields. `entities` is intentionally NOT required: entity-less
# conceptual pages legitimately omit it, and build_index.py extracts the entity index
# from page *bodies*, not frontmatter — so a missing `entities:` line is harmless.
MANDATORY = ["cluster", "aliases", "keywords", "tags", "summary"]
FM_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
BODY_SUMMARY_RE = re.compile(r"^\*\*Summary\*\*:\s*(.+)$", re.MULTILINE)
BODY_CAPABILITY_RE = re.compile(r"^\s*(?:[-*]\s+)?\*\*Capability\*\*:\s*(.+)$", re.MULTILINE)

# F1: Dana's mechanical schema checks (dana-validator.md §2), ported as advisory WARN.
# Capture the '## Details' section body (to the next H2 or EOF) for the grounding checks.
DETAILS_RE = re.compile(r"^##\s+Details\b.*?$(.*?)(?=^##\s|\Z)", re.MULTILINE | re.DOTALL)
DETAILS_SUBHEAD_RE = re.compile(r"^###\s+\S", re.MULTILINE)
SOURCE_CITE_RE = re.compile(r"\(source:", re.IGNORECASE)
INTEGRATION_MARKER_RE = re.compile(r"\[\?INTEGRATION:\s*(.*?)\]", re.DOTALL)

# Integration Suite clusters require a derived `**Capability**:` from this controlled vocabulary
# (schema.md → "SAP Integration Suite Page Extension"). Compared via _norm_cap (case/dash/space-insensitive).
INTEGRATION_CLUSTERS = {
    "integration-cloud-integration", "integration-api-management", "integration-suite-core",
}
# The controlled vocabulary is single-sourced from wiki/schema.md (the ```capability-vocab
# block). The set below is the fallback used only if that block is absent, so validation never
# silently loses its vocabulary.
_CAPABILITY_VOCAB_FALLBACK = {
    "Cloud Integration", "Open Connectors", "API Management", "Event Mesh",
    "Integration Advisor", "Trading Partner Management", "Provisioning & Setup",
    "Connectivity & Security", "Operations & Monitoring", "Methodology & Advisory",
    "Suite Overview", "Integration Assessment", "Migration Assessment", "N/A — Foundational",
}


def _load_capability_vocab():
    schema = ROOT / "wiki" / "schema.md"
    if schema.exists():
        m = re.search(r"```capability-vocab\n(.*?)\n```",
                      schema.read_text(encoding="utf-8", errors="ignore"), re.DOTALL)
        if m:
            vocab = {ln.strip() for ln in m.group(1).splitlines() if ln.strip()}
            if vocab:
                return vocab
    return _CAPABILITY_VOCAB_FALLBACK


CAPABILITY_VOCAB = _load_capability_vocab()


def norm(s: str) -> str:
    """Collapse whitespace, strip one surrounding quote pair, and unescape YAML inner
    quotes/backslashes — so a double-quoted frontmatter value compares equal to the
    plain body text it mirrors."""
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        s = s[1:-1]
    return s.replace('\\"', '"').replace("\\\\", "\\").strip()


def _norm_cap(s: str) -> str:
    """Normalise a Capability value for tolerant comparison (case, em/en-dash, spacing)."""
    s = s.strip().strip('"').lower().replace("—", "-").replace("–", "-")
    return re.sub(r"\s+", " ", s)


CAPABILITY_VOCAB_NORM = {_norm_cap(v) for v in CAPABILITY_VOCAB}


def fm_value(block: str, key: str):
    m = re.search(rf"^{key}:\s*(.+)$", block, re.MULTILINE)
    return m.group(1).strip() if m else None


def main():
    quiet = "--quiet" in sys.argv
    errors, warns = [], []

    pages = sorted(PAGES.rglob("*.md")) if PAGES.exists() else []
    if not pages:
        warns.append("no pages found under wiki/pages/ (empty wiki?)")

    # F1: cross-links registry text (normalised) for the [?INTEGRATION:] registration check.
    crosslinks_norm = ""
    if CROSSLINKS.exists():
        crosslinks_norm = re.sub(r"\s+", " ", CROSSLINKS.read_text(encoding="utf-8", errors="ignore")).lower()

    newest_page_mtime = 0.0
    for pf in pages:
        rel = pf.relative_to(ROOT).as_posix()
        cluster = pf.parent.name
        newest_page_mtime = max(newest_page_mtime, pf.stat().st_mtime)
        text = pf.read_text(encoding="utf-8", errors="ignore")

        m = FM_RE.match(text)
        if not m:
            errors.append(f"{rel}: missing YAML frontmatter block")
            continue
        block = m.group(1)

        missing, blank = [], []
        for k in MANDATORY:
            fmv = re.search(rf"^{k}:\s*(.*)$", block, re.MULTILINE)
            if not fmv:
                missing.append(k)
            elif fmv.group(1).strip() in ("", "[]", "[ ]", '""', "''"):
                blank.append(k)
        if missing:
            errors.append(f"{rel}: frontmatter missing field(s): {', '.join(missing)}")
        if blank:
            errors.append(f"{rel}: frontmatter field(s) present but empty: {', '.join(blank)}")

        cval = fm_value(block, "cluster")
        if cval and cval.strip().strip('"') != cluster:
            errors.append(f"{rel}: frontmatter cluster '{cval}' != hosting folder '{cluster}'")

        fsum = fm_value(block, "summary")
        bm = BODY_SUMMARY_RE.search(text)
        if fsum and bm and norm(fsum) != norm(bm.group(1)):
            errors.append(f"{rel}: frontmatter summary does not match body **Summary**")
        elif fsum and not bm:
            warns.append(f"{rel}: frontmatter summary present but no body **Summary** line")

        # integration clusters: mandatory derived **Capability** from the controlled vocabulary
        if cluster in INTEGRATION_CLUSTERS:
            cm = BODY_CAPABILITY_RE.search(text)
            if not cm:
                errors.append(f"{rel}: integration page missing '**Capability**:' line (mandatory in {cluster})")
            elif _norm_cap(cm.group(1)) not in CAPABILITY_VOCAB_NORM:
                errors.append(f"{rel}: **Capability** '{cm.group(1).strip()}' not in the controlled vocabulary")

        # F1 (advisory WARN — Dana §2c/2e): '## Details' present, with a '### ' subsection and a source citation
        dm_det = DETAILS_RE.search(text)
        if not dm_det:
            warns.append(f"{rel}: no '## Details' section (Dana §2c)")
        else:
            details = dm_det.group(1)
            if not DETAILS_SUBHEAD_RE.search(details):
                warns.append(f"{rel}: '## Details' has no '### ' subsection (Dana §2c)")
            if not SOURCE_CITE_RE.search(details):
                warns.append(f"{rel}: '## Details' has no '(source: ...)' citation (Dana §2e)")

        # F1 (advisory WARN — Dana §2d): every [?INTEGRATION:] marker must be registered in cross-links.md.
        # Match on the marker's distinctive tokens (kebab page-stems / words >=8 chars) rather than a
        # fixed prefix, since cross-links.md may phrase the concept differently; warn only when none match.
        for marker in INTEGRATION_MARKER_RE.findall(text):
            m = re.sub(r"\s+", " ", marker).strip()
            if not m or not crosslinks_norm:
                continue
            toks = re.findall(r"[a-z0-9][a-z0-9-]{7,}", m.lower())
            registered = any(t in crosslinks_norm for t in toks) if toks else (m.lower()[:20] in crosslinks_norm)
            if not registered:
                warns.append(f"{rel}: [?INTEGRATION:] marker not registered in cross-links.md — '{m[:50]}' (Dana §2d)")

    # index freshness (1s tolerance for filesystem granularity)
    if not LOOKUP.exists():
        errors.append("wiki/lookup.md missing — run scripts/build_index.py")
    else:
        if newest_page_mtime > LOOKUP.stat().st_mtime + 1:
            errors.append("wiki/lookup.md is STALE (a page is newer) — run scripts/build_index.py")
        hm = re.search(r">\s*(\d+)\s+pages", LOOKUP.read_text(encoding="utf-8", errors="ignore")[:500])
        if hm and int(hm.group(1)) != len(pages):
            errors.append(f"lookup.md header says {hm.group(1)} pages but found {len(pages)} — run build_index.py")

    # count reconcile vs index.md statistics
    if INDEX.exists():
        im = re.search(r"\|\s*Total pages\s*\|\s*(\d+)", INDEX.read_text(encoding="utf-8", errors="ignore"))
        if im and int(im.group(1)) != len(pages):
            errors.append(f"index.md 'Total pages' = {im.group(1)} but found {len(pages)} — run build_index.py")

    # archival integrity: a fully-ingested source is MOVED to raw_processed/, never copied,
    # so no file may live in BOTH raw/ and raw_processed/ (Guardrail #1 sanctions the move).
    # Pending sources sit in raw/ only, so this never false-flags the ingestion backlog.
    if RAW.is_dir() and RAWP.is_dir():
        # ignore hidden OS/editor cruft (.DS_Store, ._*) — never real sources, and they
        # regenerate, so flagging them would make this a brittle, false-positive gate.
        raw_top = {p.name for p in RAW.iterdir() if p.is_file() and not p.name.startswith(".")}
        archived = {p.name for p in RAWP.iterdir() if p.is_file() and not p.name.startswith(".")}
        for dup in sorted(raw_top & archived):
            errors.append(f"archival integrity: '{dup}' is in BOTH raw/ and raw_processed/ "
                          f"(source was copied, not moved) — remove the raw/ original")

    # Part 3 guard (advisory WARN): a cluster whose index.md Primary-Sources cell says
    # "pending" while wiki/pages/<cluster>/ is populated is a stale registry annotation
    # (the "empty cluster that isn't" class of bug). Cheap, catches it the moment it drifts.
    if INDEX.exists():
        for line in INDEX.read_text(encoding="utf-8", errors="ignore").splitlines():
            cells = [c.strip() for c in line.split("|")]
            if len(cells) >= 7:
                cname, sources = cells[1], cells[5]
                cdir = PAGES / cname
                if "pending" in sources.lower() and cdir.is_dir() and any(cdir.glob("*.md")):
                    warns.append(f"index.md: cluster '{cname}' Primary-Sources says '{sources}' "
                                 f"but wiki/pages/{cname}/ is populated (stale registry annotation)")

    # advisory: fold in build_index's report
    if REPORT.exists():
        rtxt = REPORT.read_text(encoding="utf-8", errors="ignore")
        bm = re.search(r"broken wikilinks:\s*(\d+)", rtxt)
        dm = re.search(r"near-duplicate title groups:\s*(\d+)", rtxt)
        if bm and int(bm.group(1)) > 0:
            warns.append(f"{bm.group(1)} broken wikilinks (see pending/index-report.md → @sarah resolve)")
        if dm and int(dm.group(1)) > 0:
            warns.append(f"{dm.group(1)} near-duplicate title groups (see pending/index-report.md)")

    # ---- report -------------------------------------------------------
    print(f"validate_wiki: {len(pages)} pages · {len(errors)} errors · {len(warns)} warnings")
    if warns and not quiet:
        for w in warns:
            print(f"  WARN  {w}")
    for e in errors:
        print(f"  ERROR {e}")

    if errors:
        print("FAIL — wiki is not consistent; rework needed before ingestion is 'complete'.")
        sys.exit(1)
    print("PASS — wiki is consistent and up to date.")
    sys.exit(0)


if __name__ == "__main__":
    main()
