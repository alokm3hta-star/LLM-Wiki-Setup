#!/usr/bin/env python3
"""
build_index.py — generate the grep-only retrieval index for the LLM Wiki.

Scans wiki/pages/** (read-only) and emits:
  - wiki/lookup.md            : the query-time index (Pages / Entities / Edges)
  - wiki/pending/index-report.md : broken links, near-duplicate titles, counts

Also reconciles entity counts into each wiki/clusters/<cluster>.md header and the
wiki/index.md statistics block (skip with --no-counts; preview with --dry-run).

Design: the agent GREPs lookup.md (never full-reads it) and reads only the pages
it points to — so it scales as the corpus grows. Stdlib only; re-run after every
ingestion/curation.
"""

import os
import re
import sys
import datetime as _dt
from pathlib import Path
from collections import defaultdict

# ROOT defaults to the project root (scripts/..); a WIKI_ROOT env override lets the smoke
# tests (scripts/test_wiki_scripts.py) build the index against a fixture tree. Default unchanged.
ROOT = Path(os.environ.get("WIKI_ROOT") or Path(__file__).resolve().parent.parent).resolve()
PAGES = ROOT / "wiki" / "pages"
CLUSTERS = ROOT / "wiki" / "clusters"
LOOKUP = ROOT / "wiki" / "lookup.md"
INDEX = ROOT / "wiki" / "index.md"
REPORT = ROOT / "wiki" / "pending" / "index-report.md"

ENTITY_RE = re.compile(r"`([^`\s]{2,40})`")
FIORI_RE = re.compile(r"\b(F\d{4,5})\b")
WIKILINK_RE = re.compile(r"\[\[([^\]|]+?)(?:\|[^\]]+)?\]\]")
INTEG_RE = re.compile(r"\[\?INTEGRATION:\s*(.+?)\]", re.DOTALL)
CLUSTER_LINE_RE = re.compile(r"^\*\*Cluster\*\*:\s*\[\[([^\]]+)\]\]", re.MULTILINE)
SUMMARY_RE = re.compile(r"^\*\*Summary\*\*:\s*(.+)$", re.MULTILINE)
FM_BLOCK_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)

# generic acronyms that add noise rather than signal to the entity index
STOP_CODES = {
    "SAP", "API", "APIS", "URL", "URI", "ID", "IDS", "UI", "UX", "OK", "REST",
    "HTTP", "HTTPS", "HTML", "XML", "JSON", "CSV", "PDF", "SQL", "GUI", "CLI",
    "SDK", "IDE", "OS", "VM", "IP", "FAQ", "ETC",
}

MAX_LINE_ENTITIES = 18      # signature entities shown on a Pages line (full set is in Entities index)
SUMMARY_CAP = 160


def slugify(text: str) -> str:
    text = re.sub(r"\.md$", "", text.strip().lower())
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def is_code(tok: str) -> bool:
    """A technical identifier: T-code, table, report, BAdI, FM, CDS view, API path, etc."""
    if " " in tok or not re.match(r"^[A-Za-z0-9_/.\-]+$", tok):
        return False
    if not (re.search(r"[A-Z]", tok) or "_" in tok or "/" in tok):
        return False
    if re.match(r"^[A-Z][a-z]+$", tok):          # plain Titlecase word, e.g. `Configuration`
        return False
    if tok.upper() in STOP_CODES:
        return False
    return True


def title_of(text: str, fallback: str) -> str:
    m = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    return m.group(1).strip() if m else fallback


def fm_terms(text: str) -> list:
    """Aliases + keywords from the YAML frontmatter (flow lists), for richer index matching."""
    m = FM_BLOCK_RE.match(text)
    if not m:
        return []
    block, terms = m.group(1), []
    for key in ("aliases", "keywords"):
        lm = re.search(rf"^{key}:\s*\[(.*?)\]\s*$", block, re.MULTILINE)
        if lm:
            terms += [t.strip().strip('"') for t in lm.group(1).split(",") if t.strip()]
    seen, out = set(), []
    for t in terms:
        if t.lower() not in seen:
            seen.add(t.lower())
            out.append(t)
    return out


def norm_title(t: str) -> str:
    """Normalised title for near-duplicate detection (lowercase, sorted significant words)."""
    t = re.sub(r"[^a-z0-9 ]", " ", t.lower())
    words = [w for w in t.split() if len(w) > 2 and w not in {"sap", "the", "and", "for"}]
    return " ".join(sorted(words))


def main():
    dry_run = "--dry-run" in sys.argv
    write_counts = "--no-counts" not in sys.argv

    page_files = sorted(PAGES.rglob("*.md"))
    # exclude dotfile dirs (e.g. .obsidian) so they don't count as a cluster
    cluster_names = {p.name for p in PAGES.iterdir() if p.is_dir() and not p.name.startswith(".")}

    pages = {}                       # stem -> dict(cluster, rel, title, summary, entities)
    stem_to_rel = {}                 # stem -> "cluster/stem.md"
    title_slug_to_stem = {}          # slugified title -> stem (links often use the title)
    entity_pages = defaultdict(set)  # ENTITY -> {rel, ...}
    inbound = defaultdict(int)       # stem -> inbound wikilink count
    edges = []                       # (src_rel, target) — resolved post-loop
    broken = []                      # (src_rel, raw target)
    raw_links = []                   # (stem, rel, [targets], cluster_target)
    raw_edges = []                   # (src_rel, src_cluster, hint) — resolved post-loop

    for pf in page_files:
        cluster = pf.parent.name
        stem = pf.stem
        rel = f"{cluster}/{pf.name}"
        text = pf.read_text(encoding="utf-8", errors="ignore")

        title = title_of(text, stem)
        sm = SUMMARY_RE.search(text)
        summary = re.sub(r"\s+", " ", sm.group(1)).strip() if sm else ""

        entities = {e for e in ENTITY_RE.findall(text) if is_code(e)}
        entities |= set(FIORI_RE.findall(text))

        pages[stem] = dict(cluster=cluster, rel=rel, title=title,
                           summary=summary, entities=sorted(entities),
                           kw=fm_terms(text))
        stem_to_rel[stem] = rel
        title_slug_to_stem.setdefault(slugify(title), stem)
        for e in entities:
            entity_pages[e].add(rel)

        # wikilinks (excluding the **Cluster**: line, which points at a cluster by design)
        cluster_link = CLUSTER_LINE_RE.search(text)
        cluster_target = slugify(cluster_link.group(1)) if cluster_link else None
        targets = [slugify(t) for t in WIKILINK_RE.findall(text)]
        raw_links.append((stem, rel, targets, cluster_target))

        # cross-cluster integration hints — resolved after every stem is known
        for hint in INTEG_RE.findall(text):
            raw_edges.append((rel, cluster, re.sub(r"\s+", " ", hint).strip()))

    # everything below resolves against the full page set (handles forward references)
    def resolve(target):
        if target in stem_to_rel:
            return stem_to_rel[target], target
        if target in title_slug_to_stem:
            s = title_slug_to_stem[target]
            return stem_to_rel[s], s
        return None, None

    # authority + broken links
    for stem, rel, targets, cluster_target in raw_links:
        for t in targets:
            r, s = resolve(t)
            if r:
                inbound[s] += 1
            elif t in cluster_names or t == cluster_target:
                pass  # cluster reference, not a page link
            else:
                broken.append((rel, t))

    # cross-cluster edges (best-effort: links, then named cluster, then raw hint)
    for rel, cluster, hint in raw_edges:
        links = [slugify(t) for t in WIKILINK_RE.findall(hint)]
        named = [c for c in cluster_names if c in hint and c != cluster]
        if links:
            for t in links:
                r, _ = resolve(t)
                edges.append((rel, r if r else f"?{t}"))
        elif named:
            for c in named:
                edges.append((rel, f"cluster:{c}"))
        else:
            edges.append((rel, f"?{hint[:70]}"))

    # near-duplicate titles + canonical marking (highest inbound authority wins)
    by_norm = defaultdict(list)
    for stem, p in pages.items():
        by_norm[norm_title(p["title"])].append(stem)
    canonical = set()
    dup_groups = []
    for norm, stems in by_norm.items():
        if len(stems) > 1:
            ranked = sorted(stems, key=lambda s: inbound[s], reverse=True)
            canonical.add(ranked[0])
            dup_groups.append(ranked)
    # also treat top-authority pages as canonical signal
    if inbound:
        hi = sorted(inbound.values(), reverse=True)
        thresh = hi[min(len(hi) // 5, len(hi) - 1)] if hi else 0
        for stem, c in inbound.items():
            if c >= max(thresh, 3):
                canonical.add(stem)

    # ---- emit lookup.md -------------------------------------------------
    per_cluster = defaultdict(int)
    for p in pages.values():
        per_cluster[p["cluster"]] += 1

    out = []
    out.append("# Wiki Lookup Index")
    out.append("")
    out.append("> GENERATED by `scripts/build_index.py` — do not hand-edit. "
               "GREP this file (never full-read it); then read only the pages it points to.")
    out.append(f"> {len(pages)} pages · {len(entity_pages)} entities · "
               f"{len(edges)} cross-cluster edges · {len(cluster_names)} clusters")
    out.append("")
    out.append("Per cluster: " + ", ".join(f"{c} {per_cluster[c]}" for c in sorted(per_cluster)))
    out.append("")
    out.append("## Pages")
    out.append("`cluster/page.md | ★canonical | Title | summary | entities: …`")
    out.append("")
    for stem in sorted(pages):
        p = pages[stem]
        star = "★" if stem in canonical else " "
        summ = p["summary"].replace("|", "/")[:SUMMARY_CAP]
        ents = ",".join(p["entities"][:MAX_LINE_ENTITIES])
        kw = ",".join(t.replace("|", "/") for t in p["kw"][:12])
        out.append(f"{p['rel']} | {star} | {p['title']} | {summ} | kw: {kw} | entities: {ents}")
    out.append("")
    out.append("## Entities")
    out.append("`ENTITY | page(s) where documented` — the inverted index for grounded/validation lookups")
    out.append("")
    for e in sorted(entity_pages):
        out.append(f"{e} | {', '.join(sorted(entity_pages[e]))}")
    out.append("")
    out.append("## Edges")
    out.append("`source-page --integration--> target` (cluster:X = whole cluster; ?text = unresolved hint)")
    out.append("")
    for src, tgt in sorted(set(edges)):
        out.append(f"{src} --integration--> {tgt}")
    out.append("")

    # ---- emit report ----------------------------------------------------
    rep = []
    rep.append("# Index Build Report")
    rep.append("")
    rep.append(f"- pages: {len(pages)}")
    rep.append(f"- distinct entities: {len(entity_pages)}")
    rep.append(f"- cross-cluster edges: {len(edges)}")
    rep.append(f"- broken wikilinks: {len(broken)}")
    rep.append(f"- near-duplicate title groups: {len(dup_groups)}")
    rep.append("")
    rep.append("## Per-cluster page counts")
    for c in sorted(per_cluster):
        rep.append(f"- {c}: {per_cluster[c]}")
    rep.append("")
    rep.append("## Near-duplicate title groups (canonical first)")
    for grp in sorted(dup_groups):
        rep.append(f"- {' | '.join(grp)}")
    rep.append("")
    rep.append("## Broken wikilinks (source → unresolved target)")
    for src, t in sorted(set(broken)):
        rep.append(f"- {src} → [[{t}]]")
    rep.append("")

    print(f"pages={len(pages)} entities={len(entity_pages)} edges={len(edges)} "
          f"broken={len(broken)} dup_groups={len(dup_groups)}")
    if dry_run:
        print("[dry-run] no files written")
        return

    LOOKUP.write_text("\n".join(out), encoding="utf-8")
    REPORT.write_text("\n".join(rep), encoding="utf-8")
    print(f"wrote {LOOKUP.relative_to(ROOT)} and {REPORT.relative_to(ROOT)}")

    if write_counts:
        reconcile_counts(per_cluster, len(pages), len(entity_pages), len(cluster_names))


def _count_status_rows(relpath, statuses):
    """Count table rows whose final cell is one of `statuses` (e.g. 'pending').

    Robust to the placeholder ('—') and status-definition rows in the pending files:
    only a real data row ends with '| <status> |' because the status is the last cell.
    """
    f = ROOT / relpath
    if not f.exists():
        return 0
    n = 0
    for line in f.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = line.rstrip()
        if any(s.endswith(f"| {st} |") for st in statuses):
            n += 1
    return n


def reconcile_counts(per_cluster, total, entity_total, cluster_total):
    """Single source of truth for every numeric the index reports.

    The index.md Statistics and Pending Work tables (and the pending-file headers) are
    otherwise hand-maintained and drift between regenerations; here build_index.py drives
    them all from live data so a rebuild self-heals the counts.
    """
    for c, n in per_cluster.items():
        cf = CLUSTERS / f"{c}.md"
        if cf.exists():
            txt = cf.read_text(encoding="utf-8")
            new = re.sub(r"(Entity count:\s*)\d+", rf"\g<1>{n}", txt, count=1)
            if new != txt:
                cf.write_text(new, encoding="utf-8")

    if not INDEX.exists():
        print("reconciled cluster-header counts (index.md absent)")
        return

    x_pending = _count_status_rows("wiki/pending/cross-links.md", ["pending"])
    p_pending = _count_status_rows("wiki/pending/update-proposals.md", ["pending"])
    m_pending = _count_status_rows("wiki/pending/missing-pages.md",
                                   ["identified", "Analysed", "Drafting", "proposed"])
    today = _dt.date.today().isoformat()

    txt = INDEX.read_text(encoding="utf-8")
    orig = txt
    # Statistics block
    txt = re.sub(r"(\|\s*Total pages\s*\|\s*)\d+",           rf"\g<1>{total}", txt)
    txt = re.sub(r"(\|\s*Total entities\s*\|\s*)\d+",        rf"\g<1>{entity_total}", txt)
    txt = re.sub(r"(\|\s*Active clusters\s*\|\s*)\d+",       rf"\g<1>{cluster_total}", txt)
    txt = re.sub(r"(\|\s*Pending cross-links\s*\|\s*)\d+",   rf"\g<1>{x_pending}", txt)
    txt = re.sub(r"(\|\s*Pending missing pages\s*\|\s*)\d+", rf"\g<1>{m_pending}", txt)
    txt = re.sub(r"(\|\s*Pending proposals\s*\|\s*)\d+",     rf"\g<1>{p_pending}", txt)
    # Pending Work table (third cell carries the live count, sometimes with a trailing word)
    txt = re.sub(r"(\|\s*Cross-links\s*\|[^|]*\|\s*)\d+(\s*pending)",      rf"\g<1>{x_pending}\g<2>", txt)
    txt = re.sub(r"(\|\s*Missing pages\s*\|[^|]*\|\s*)\d+",               rf"\g<1>{m_pending}", txt)
    txt = re.sub(r"(\|\s*Update proposals\s*\|[^|]*\|\s*)\d+(\s*pending)", rf"\g<1>{p_pending}\g<2>", txt)
    # per-cluster cell in the registry table
    for c, n in per_cluster.items():
        txt = re.sub(rf"(\|\s*{re.escape(c)}\s*\|[^|]*\|\s*)\d+(\s*\|)", rf"\g<1>{n}\g<2>", txt)
    # machine-owned freshness stamp (counts are now auto-reconciled)
    txt = re.sub(r"(\*\*Last Updated\*\*:\s*).*",
                 rf"\g<1>{today} (counts auto-reconciled by scripts/build_index.py)", txt, count=1)

    if txt != orig:
        INDEX.write_text(txt, encoding="utf-8")
        print(f"reconciled index.md: pages={total} entities={entity_total} clusters={cluster_total} "
              f"x-links_pending={x_pending} proposals_pending={p_pending} missing={m_pending}")
    else:
        print("index.md counts already current — no write")


if __name__ == "__main__":
    main()
