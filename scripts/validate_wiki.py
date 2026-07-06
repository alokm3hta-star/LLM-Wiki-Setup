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
import shlex
import subprocess
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
CROSSLINKS_ARCHIVE_GLOB = "wiki/archive/*/cross-links-resolved.md"
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
# Marker text can legitimately contain nested [[wikilink]] syntax (e.g.
# "[?INTEGRATION: documented in [[grants-management-psm-gm]] pending review]"). A naive
# non-greedy `.*?]` stops at the wikilink's own closing `]]`'s first `]`, truncating the
# capture mid-link. Treat `[[...]]` as an atomic unit first (matched and consumed as a
# whole token) so the outer marker capture runs to the marker's own closing `]` — i.e. the
# LAST `]` on the line/marker span, not the first one encountered.
INTEGRATION_MARKER_RE = re.compile(
    r"\[\?INTEGRATION:\s*((?:\[\[.*?\]\]|[^\[\]]|\[(?!\?INTEGRATION:))*)\]",
    re.DOTALL,
)
# Extracts the target page(s) referenced inside a marker's own [[wikilink]] tokens, so the
# registration check can confirm the specific (source page, target page) pair — not just
# that some token from the marker string appears somewhere in cross-links.md.
WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]*)?\]\]")

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

    # F1: cross-links registry rows for the [?INTEGRATION:] registration check.
    # Parsed per-row (not as one loose blob) so registration is verified on the specific
    # (source page, target page) pair, not a substring match against the whole file —
    # a generic page-name token repeated across many historical rows would otherwise
    # produce false "already registered" positives for an unrelated pair.
    def _crosslink_rows_from_text(text):
        rows = []
        for line in text.splitlines():
            line = line.strip()
            if not line.startswith("|") or line.startswith("| **") or line.startswith("| -"):
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) < 3:
                continue
            source_cell = cells[0]
            # Source Page cell may list several files separated by ';' (consolidated rows).
            source_stems = {
                re.sub(r"\.md\b.*$", "", s.strip()).lower()
                for s in source_cell.split(";") if s.strip()
            }
            if not source_stems:
                continue
            row_norm = re.sub(r"\s+", " ", line).lower()
            rows.append((source_stems, row_norm))
        return rows

    # list of (source_page_stems: set[str], row_text_norm: str)
    crosslinks_rows = []
    if CROSSLINKS.exists():
        crosslinks_rows += _crosslink_rows_from_text(
            CROSSLINKS.read_text(encoding="utf-8", errors="ignore"))
    # Rotation (rotate_archives.py) moves resolved rows out of the active file into
    # wiki/archive/<quarter>/cross-links-resolved.md — a resolved-then-archived marker is
    # still registered, so the registration check must also see archived rows, not just
    # the active queue (otherwise rotation silently breaks a previously-passing check).
    for arch in ROOT.glob(CROSSLINKS_ARCHIVE_GLOB):
        crosslinks_rows += _crosslink_rows_from_text(
            arch.read_text(encoding="utf-8", errors="ignore"))

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
        # Registration requires the SPECIFIC (source page, target page) pair to co-occur within a
        # single cross-links.md row — not a loose token search across the whole file. The source
        # page is this page's own filename stem; the target page is read from the marker's own
        # [[wikilink]] token(s) where present. Markers with no wikilink target (prose-only, e.g.
        # naming a cluster generically) fall back to a same-row token match scoped to rows whose
        # Source Page cell already names this page — still pair-scoped, never file-wide.
        page_stem = pf.stem.lower()
        rows_for_this_page = [row_norm for stems, row_norm in crosslinks_rows if page_stem in stems]
        for marker in INTEGRATION_MARKER_RE.findall(text):
            m = re.sub(r"\s+", " ", marker).strip()
            if not m:
                continue
            targets = [re.sub(r"\s+", " ", t).strip().lower() for t in WIKILINK_RE.findall(m)]
            if targets:
                registered = any(
                    any(t in row_norm for t in targets) for row_norm in rows_for_this_page
                )
            elif rows_for_this_page:
                m_lower = m.lower()
                toks = set(re.findall(r"[a-z0-9][a-z0-9-]{7,}", m_lower))
                # Whitespace-tolerant fallback: short multi-word targets (e.g. "SAP Event Mesh")
                # have no single 8+ char token, so also check 2- and 3-word phrases.
                words = re.findall(r"[a-z0-9]+", m_lower)
                for n in (2, 3):
                    for i in range(len(words) - n + 1):
                        phrase = " ".join(words[i:i + n])
                        if len(phrase) >= 6:
                            toks.add(phrase)
                registered = any(any(t in row_norm for t in toks) for row_norm in rows_for_this_page) if toks else False
            else:
                registered = False
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
        # ignore hidden OS/editor cruft (.DS_Store, ._*) and the starter-kit README.md
        # placeholders that legitimately live in both dirs (kept via .gitignore un-ignore
        # rules) — never real sources, so flagging them would make this a false-positive gate.
        _skip = {"README.md"}
        raw_top = {p.name for p in RAW.iterdir() if p.is_file() and not p.name.startswith(".") and p.name not in _skip}
        archived = {p.name for p in RAWP.iterdir() if p.is_file() and not p.name.startswith(".") and p.name not in _skip}
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

    # Paul dev-card + phase-pack checks (ERROR-tier). The hand-authored dev-card core
    # (wiki/agents/paul-dev-card.md) plus every pack under wiki/agents/paul-card-packs/
    # gets the same two checks: (1) every [[wikilink]] resolves to a real page stem, and
    # (2) every backtick-wrapped `grep ...` recipe line returns >=1 hit against the live
    # corpus (a recipe that stops matching means the "where to look next" guidance has
    # gone stale). Two structural checks on top: (3) every pack path listed in the core's
    # Pack Index table (any markdown table row referencing paul-card-packs/) must exist on
    # disk — a listed-but-missing pack would silently drop rules at load time; (4) no rule
    # ID may be DEFINED (a `- **<ID>**` bullet) in more than one file — IDs are stable
    # forever, so a duplicate definition means a rule was copied, not moved. No-op if the
    # card is absent — it's an optional, hand-maintained artefact, not a mandatory wiki
    # structure; with no card, the pack checks are skipped too.
    CARD = ROOT / "wiki" / "agents" / "paul-dev-card.md"
    PACKS_DIR = ROOT / "wiki" / "agents" / "paul-card-packs"
    if CARD.exists():
        card_files = [CARD]
        if PACKS_DIR.is_dir():
            card_files.extend(sorted(PACKS_DIR.glob("*.md")))
        page_stems = {p.stem for p in pages}
        rule_id_re = re.compile(r"^- \*\*((?:CA|OOP|TDD)-[A-Z]+-[0-9]+|DP-[0-9]+)\b", re.MULTILINE)
        pack_path_re = re.compile(r"paul-card-packs/([A-Za-z0-9._-]+\.md)")
        rule_defs = {}  # rule ID -> [rel paths of files that define it]

        for cf in card_files:
            cf_text = cf.read_text(encoding="utf-8", errors="ignore")
            cf_rel = cf.relative_to(ROOT).as_posix()

            for link in WIKILINK_RE.findall(cf_text):
                target = link.strip()
                if target and target not in page_stems:
                    errors.append(f"{cf_rel}: wikilink [[{target}]] does not resolve to a page")

            for line in cf_text.splitlines():
                gm = re.search(r"`(grep\s+.+?)`", line)
                if not gm:
                    continue
                recipe = gm.group(1)
                try:
                    argv = shlex.split(recipe)
                except ValueError as e:
                    errors.append(f"{cf_rel}: grep recipe unparsable ({e}): {recipe}")
                    continue
                try:
                    result = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=10)
                except (FileNotFoundError, subprocess.TimeoutExpired):
                    errors.append(f"{cf_rel}: grep recipe failed to run: {recipe}")
                    continue
                if result.returncode == 1:
                    errors.append(f"{cf_rel}: grep recipe returns 0 hits: {recipe}")
                elif result.returncode not in (0, 1):
                    errors.append(f"{cf_rel}: grep recipe errored (exit {result.returncode}): {recipe}")

            # (4) collect rule-ID definitions for the cross-file uniqueness check below
            for rid in rule_id_re.findall(cf_text):
                files = rule_defs.setdefault(rid, [])
                if cf_rel not in files:
                    files.append(cf_rel)

            # (3) Pack Index integrity — core card only
            if cf == CARD:
                listed_packs = set()
                for line in cf_text.splitlines():
                    if line.lstrip().startswith("|"):
                        listed_packs.update(pack_path_re.findall(line))
                for pack_name in sorted(listed_packs):
                    if not (PACKS_DIR / pack_name).exists():
                        errors.append(f"{cf_rel}: Pack Index lists paul-card-packs/{pack_name} "
                                      f"but the file does not exist on disk")

        # (4) rule-ID uniqueness across core + packs
        for rid, files in sorted(rule_defs.items()):
            if len(files) > 1:
                errors.append(f"paul dev-card: rule ID {rid} defined in more than one file: "
                              f"{', '.join(files)}")

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
