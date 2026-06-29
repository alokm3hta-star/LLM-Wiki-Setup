#!/usr/bin/env python3
"""
add_frontmatter.py — prepend YAML frontmatter to wiki/pages/** for machine/Obsidian use.

Generates a draft frontmatter block (cluster, aliases, keywords, tags, summary, entities)
from each page's existing H1, **Summary**, body codes, and stem. Additive and idempotent:
a page that already starts with `---` is skipped. The body is left untouched.

  --dry-run            show the block for a few sample pages, write nothing
  --sample N           number of samples to print in dry-run (default 3)
  (no flag)            apply to every page lacking frontmatter

Sarah enriches aliases/keywords later; this just lays down the reviewed-quality draft.
Stdlib only.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGES = ROOT / "wiki" / "pages"

ENTITY_RE = re.compile(r"`([^`\s]{2,40})`")
SUMMARY_RE = re.compile(r"^\*\*Summary\*\*:\s*(.+)$", re.MULTILINE)
TITLE_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)

SOURCE_PREFIXES = ("btp-book-", "btp-docs-", "sap-build-", "wz-std-", "islm-",
                   "bi-", "adt-", "press-ilm-", "ilm-", "cloud-alm-")
STOP = {
    "the", "and", "for", "with", "from", "this", "that", "are", "via", "into",
    "sap", "use", "used", "uses", "using", "can", "all", "per", "its", "etc",
    "within", "across", "between", "such", "based", "provides", "provide",
    "supports", "support", "including", "each", "one", "two", "also", "which",
    "when", "where", "how", "not", "but", "any", "may", "must", "see", "set",
}
STOP_CODES = {"SAP", "API", "APIS", "URL", "ID", "UI", "OK", "REST", "HTTP",
              "HTTPS", "HTML", "XML", "JSON", "CSV", "PDF", "SQL", "GUI", "CLI"}


def is_code(tok: str) -> bool:
    if " " in tok or not re.match(r"^[A-Za-z0-9_/.\-]+$", tok):
        return False
    if not (re.search(r"[A-Z]", tok) or "_" in tok or "/" in tok):
        return False
    if re.match(r"^[A-Z][a-z]+$", tok) or tok.upper() in STOP_CODES:
        return False
    return True


def yaml_str(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').strip() + '"'


def yaml_list(items) -> str:
    return "[" + ", ".join(yaml_str(i) for i in items) + "]"


def deprefixed_alias(stem: str, title: str) -> str:
    s = stem
    for p in SOURCE_PREFIXES:
        if s.startswith(p):
            s = s[len(p):]
            break
    phrase = s.replace("-", " ").strip()
    return phrase if phrase and phrase.lower() != title.lower() else ""


def keywords_of(title: str, summary: str) -> list:
    words = re.findall(r"[a-z][a-z0-9]{2,}", f"{title} {summary}".lower())
    out, seen = [], set()
    for w in words:
        if w in STOP or w in seen:
            continue
        seen.add(w)
        out.append(w)
        if len(out) >= 10:
            break
    return out


def build_block(pf: Path) -> str:
    cluster = pf.parent.name
    text = pf.read_text(encoding="utf-8", errors="ignore")
    tm = TITLE_RE.search(text)
    title = tm.group(1).strip() if tm else pf.stem
    sm = SUMMARY_RE.search(text)
    summary = re.sub(r"\s+", " ", sm.group(1)).strip() if sm else ""
    entities = sorted({e for e in ENTITY_RE.findall(text) if is_code(e)})[:12]

    aliases = [title]
    alt = deprefixed_alias(pf.stem, title)
    if alt:
        aliases.append(alt)

    lines = ["---", f"cluster: {cluster}", f"aliases: {yaml_list(aliases)}",
             f"keywords: {yaml_list(keywords_of(title, summary))}",
             f"tags: {yaml_list([cluster])}"]
    if summary:
        lines.append(f"summary: {yaml_str(summary)}")
    if entities:
        lines.append(f"entities: {yaml_list(entities)}")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def main():
    dry = "--dry-run" in sys.argv
    sample = 3
    if "--sample" in sys.argv:
        sample = int(sys.argv[sys.argv.index("--sample") + 1])

    page_files = sorted(PAGES.rglob("*.md"))
    added, skipped, shown = 0, 0, 0
    for pf in page_files:
        text = pf.read_text(encoding="utf-8", errors="ignore")
        if text.lstrip().startswith("---"):
            skipped += 1
            continue
        block = build_block(pf)
        if dry:
            if shown < sample:
                print(f"\n===== {pf.relative_to(ROOT)} =====")
                print(block)
                shown += 1
            added += 1
            continue
        pf.write_text(block + text, encoding="utf-8")
        added += 1

    verb = "would add" if dry else "added"
    print(f"\n{verb} frontmatter to {added} pages; skipped {skipped} (already had it)")


if __name__ == "__main__":
    main()
