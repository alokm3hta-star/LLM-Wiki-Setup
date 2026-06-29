"""Split a Markdown file into parts at H2 (or H3) boundaries.

Writes split files to --output-dir with YAML frontmatter.
Prints a JSON manifest to stdout.

Usage:
  python3 split_markdown.py \\
    --input /tmp/slug_full.md \\
    --slug s4hana-whats-new-2025 \\
    --source-file "WN_OP2025_EN.pdf" \\
    --output-dir raw/ \\
    --max-bytes 61440
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone


MAX_HARD = 81920  # 80 KB — absolute ceiling before hard-cutting


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--slug", required=True)
    p.add_argument("--source-file", required=True, dest="source_file")
    p.add_argument("--output-dir", required=True, dest="output_dir")
    p.add_argument("--max-bytes", type=int, default=61440, dest="max_bytes")
    return p.parse_args()


def detect_method(source_file):
    ext = os.path.splitext(source_file)[1].lower()
    if ext in (".pdf",):
        return "kylie-convert/pdf"
    if ext in (".pptx", ".ppt"):
        return "kylie-convert/pptx"
    return "kylie-convert/markdown"


def extract_sections(content, heading_prefix="## "):
    """Split content into (heading, body) tuples at the given heading level."""
    sections = []
    current_heading = None
    current_lines = []

    for line in content.splitlines(keepends=True):
        if line.startswith(heading_prefix) and heading_prefix.strip():
            if current_lines or current_heading is not None:
                sections.append((current_heading, "".join(current_lines)))
            current_heading = line.rstrip()
            current_lines = []
        else:
            current_lines.append(line)

    sections.append((current_heading, "".join(current_lines)))
    return sections


def reassemble(heading, body):
    if heading:
        return heading + "\n" + body
    return body


def split_large_section(heading, body, max_bytes):
    """If a single H2 section is too big, split it at H3 boundaries."""
    sub_sections = extract_sections(body, heading_prefix="### ")
    parts = []
    current_parts = []
    current_size = len((heading or "").encode("utf-8")) if heading else 0

    for h3_heading, h3_body in sub_sections:
        chunk = reassemble(h3_heading, h3_body)
        chunk_size = len(chunk.encode("utf-8"))

        if chunk_size > MAX_HARD:
            # Hard-cut: split every MAX_HARD bytes
            if current_parts:
                parts.append((heading, "".join(current_parts)))
                current_parts = []
                current_size = 0
            # Split the oversized chunk by bytes
            encoded = chunk.encode("utf-8")
            offset = 0
            while offset < len(encoded):
                slice_bytes = encoded[offset : offset + MAX_HARD]
                parts.append((heading if not parts else None, slice_bytes.decode("utf-8", errors="replace")))
                offset += MAX_HARD
        elif current_size + chunk_size > max_bytes and current_parts:
            parts.append((heading, "".join(current_parts)))
            current_parts = [chunk]
            current_size = chunk_size
        else:
            current_parts.append(chunk)
            current_size += chunk_size

    if current_parts:
        parts.append((heading, "".join(current_parts)))

    return parts


def group_into_parts(sections, max_bytes):
    """Combine sections into parts respecting max_bytes."""
    parts = []
    current_chunks = []
    current_size = 0

    for heading, body in sections:
        chunk = reassemble(heading, body)
        chunk_size = len(chunk.encode("utf-8"))

        if chunk_size > max_bytes:
            # Section too big — split at H3
            sub_parts = split_large_section(heading, body, max_bytes)
            for sub_heading, sub_body in sub_parts:
                sub_chunk = reassemble(sub_heading, sub_body)
                sub_size = len(sub_chunk.encode("utf-8"))
                if current_size + sub_size > max_bytes and current_chunks:
                    parts.append("".join(current_chunks))
                    current_chunks = [sub_chunk]
                    current_size = sub_size
                else:
                    current_chunks.append(sub_chunk)
                    current_size += sub_size
        elif current_size + chunk_size > max_bytes and current_chunks:
            parts.append("".join(current_chunks))
            current_chunks = [chunk]
            current_size = chunk_size
        else:
            current_chunks.append(chunk)
            current_size += chunk_size

    if current_chunks:
        parts.append("".join(current_chunks))

    return parts


def first_last_h2(content):
    """Return the first and last H2 heading text found in content."""
    headings = re.findall(r'^## (.+)$', content, re.MULTILINE)
    if not headings:
        headings = re.findall(r'^### (.+)$', content, re.MULTILINE)
    if not headings:
        return "", ""
    return headings[0].strip(), headings[-1].strip()


def build_frontmatter(source_file, total_parts, part_n, method, extra=""):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        "---",
        f'source_file: "{source_file}"',
        f"total_parts: {total_parts}",
        f"part: {part_n}",
        f'converted_at: "{ts}"',
        f'conversion_method: "{method}"',
        f'description: ""',
        "---",
        "",
    ]
    return "\n".join(lines)


def main():
    args = parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        content = f.read()

    method = detect_method(args.source_file)
    sections = extract_sections(content, heading_prefix="## ")
    raw_parts = group_into_parts(sections, args.max_bytes)

    total_parts = len(raw_parts)
    os.makedirs(args.output_dir, exist_ok=True)

    manifest = {
        "slug": args.slug,
        "total_parts": total_parts,
        "parts": [],
    }

    for i, part_content in enumerate(raw_parts, 1):
        filename = f"{args.slug}-{i:02d}.md"
        filepath = os.path.join(args.output_dir, filename)
        fm = build_frontmatter(args.source_file, total_parts, i, method)
        full_content = fm + part_content.strip() + "\n"

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(full_content)

        first_h2, last_h2 = first_last_h2(part_content)
        manifest["parts"].append(
            {
                "file": filepath,
                "first_h2": first_h2,
                "last_h2": last_h2,
                "bytes": len(full_content.encode("utf-8")),
            }
        )

    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
