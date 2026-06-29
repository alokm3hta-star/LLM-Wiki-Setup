"""Strip copyright notices and normalise heading hierarchy in a Markdown file (in-place).

Usage: python3 clean_markdown.py <filepath>

Prints the number of copyright blocks removed to stdout.
"""
import re
import sys


# ── Copyright / boilerplate patterns ────────────────────────────────────────

COPYRIGHT_PATTERNS = [
    # Standard copyright line
    r'©\s*\d{4}[^\n]*',
    r'Copyright\s*©?\s*\d{4}[^\n]*',
    r'All rights reserved\.?[^\n]*',
    # SAP-specific
    r'SAP SE or an SAP affiliate company\.?[^\n]*',
    r'Proprietary and confidential\.?[^\n]*',
    r'PUBLIC\s*$',
    r'What\'s New\s*\|\s*PUBLIC[^\n]*',
    r'Document Version:\s*[^\n]+',
    # PDF artifact headers/footers
    r'\d{1,2}/\d{1,2}/\d{2,4},\s*\d{1,2}:\d{2}\s*(?:AM|PM)[^\n]*',  # "3/9/26, 4:04 PM"
    r'This is custom documentation\.[^\n]*',
    r'For more information, please visit SAP Help Portal\.?[^\n]*',
    r'Generated on:\s*[^\n]+',
    # Repeated document title footers (e.g., "What's New in SAP S/4HANA ... Content")
    r'Content\s*$',
]

_COMPILED = [re.compile(p, re.MULTILINE | re.IGNORECASE) for p in COPYRIGHT_PATTERNS]


def strip_copyright(content):
    removed = 0
    for pattern in _COMPILED:
        new, n = pattern.subn("", content)
        removed += n
        content = new
    # Collapse runs of 3+ blank lines to 2
    content = re.sub(r'\n{3,}', '\n\n', content)
    return content, removed


# ── Heading normalisation ────────────────────────────────────────────────────

_HEADING_RE = re.compile(r'^(#{1,6})(\s+.*)$', re.MULTILINE)


def normalize_headings(content):
    lines = content.split('\n')
    heading_lines = [(i, len(m.group(1))) for i, line in enumerate(lines)
                     if (m := _HEADING_RE.match(line))]

    if not heading_lines:
        return content

    min_level = min(lvl for _, lvl in heading_lines)
    shift = min_level - 1  # promote so top heading becomes H1

    first_h1_seen = False
    result = []
    for i, line in enumerate(lines):
        m = _HEADING_RE.match(line)
        if m:
            new_level = len(m.group(1)) - shift
            new_level = max(1, min(6, new_level))
            # Ensure only one H1 in the document
            if new_level == 1:
                if first_h1_seen:
                    new_level = 2
                else:
                    first_h1_seen = True
            result.append('#' * new_level + m.group(2))
        else:
            result.append(line)

    return '\n'.join(result)


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 clean_markdown.py <filepath>", file=sys.stderr)
        sys.exit(1)

    filepath = sys.argv[1]
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    content, removed = strip_copyright(content)
    content = normalize_headings(content)
    content = content.strip() + '\n'

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"Removed {removed} copyright/boilerplate block(s).")


if __name__ == '__main__':
    main()
