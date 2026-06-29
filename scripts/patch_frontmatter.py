"""Set a key:value pair in a file's YAML frontmatter block (in-place).

Usage: python3 patch_frontmatter.py <filepath> <key> <value>

If the key already exists in the frontmatter, its value is replaced.
If it does not exist, it is appended before the closing ---.
The file must begin with a --- frontmatter block.
"""
import sys
import re


def patch(filepath, key, value):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    if not content.startswith("---"):
        print(f"ERROR: {filepath} does not start with YAML frontmatter", file=sys.stderr)
        sys.exit(1)

    # Find frontmatter bounds
    end_idx = content.index("---", 3)  # second ---
    fm_block = content[3:end_idx]      # content between the two ---
    body = content[end_idx:]           # from closing --- onward

    # Sanitise value (escape internal quotes)
    safe_value = value.replace('"', '\\"')
    new_line = f'{key}: "{safe_value}"'
    key_re = re.compile(rf'^{re.escape(key)}\s*:.*$', re.MULTILINE)

    if key_re.search(fm_block):
        fm_block = key_re.sub(new_line, fm_block)
    else:
        # Append before closing ---
        fm_block = fm_block.rstrip("\n") + f"\n{new_line}\n"

    new_content = "---" + fm_block + body

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(new_content)


def main():
    if len(sys.argv) < 4:
        print("Usage: python3 patch_frontmatter.py <filepath> <key> <value>", file=sys.stderr)
        sys.exit(1)
    filepath, key, value = sys.argv[1], sys.argv[2], sys.argv[3]
    patch(filepath, key, value)


if __name__ == "__main__":
    main()
