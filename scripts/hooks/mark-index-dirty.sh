#!/usr/bin/env bash
# PostToolUse(Write|Edit|MultiEdit): flag the index dirty when a Tier-1 page changes,
# so the Stop hook rebuilds + verifies exactly once per turn (not after every write).
#
# Fails CLOSED: if tool_input cannot be parsed (or yields no file_path), set the dirty flag
# anyway so the Stop hook rebuilds and validate_wiki.py establishes the true state, rather
# than silently skipping verification on a malformed payload.
set -uo pipefail
input="$(cat)"
root="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
fp="$(printf '%s' "$input" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("tool_input",{}).get("file_path",""))' 2>/dev/null || echo '__PARSE_ERROR__')"
if [ "$fp" = "__PARSE_ERROR__" ] || [ -z "$fp" ]; then
  touch "$root/wiki/.index-dirty"   # uncertain payload -> rebuild+verify will establish truth
  exit 0
fi
case "$fp" in
  */wiki/pages/*) touch "$root/wiki/.index-dirty" ;;
esac
exit 0
