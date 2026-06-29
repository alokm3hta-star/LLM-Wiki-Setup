#!/usr/bin/env bash
# PreToolUse(Write|Edit|MultiEdit): enforce Guardrail #1 — raw source CONTENT is immutable.
# Denies content edits (Write/Edit/MultiEdit) whose target is under raw/ or raw_processed/.
# The sanctioned archival MOVE (raw/ -> raw_processed/) runs via `mv`
# (scripts/archive_source.sh, Anja step 8), which this Write-tool guard intentionally does
# not see; the copy-not-move failure is caught by scripts/validate_wiki.py.
#
# Fails CLOSED: if tool_input cannot be parsed to a file_path, the write is BLOCKED rather
# than allowed, so a malformed payload can never slip an edit past the guard.
set -uo pipefail
input="$(cat)"
fp="$(printf '%s' "$input" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("tool_input",{}).get("file_path",""))' 2>/dev/null || echo '__PARSE_ERROR__')"
if [ "$fp" = "__PARSE_ERROR__" ] || [ -z "$fp" ]; then
  echo "BLOCKED: could not determine a target file_path from tool_input; failing closed (Guardrail #1). Retry the edit; if this persists, inspect the hook input." >&2
  exit 2
fi
case "$fp" in
  */raw/*|raw/*|*/raw_processed/*|raw_processed/*)
    echo "BLOCKED: '$fp' is under an immutable source directory. Guardrail #1: source CONTENT in raw/, raw_processed/ must not be edited. To archive a processed source use scripts/archive_source.sh (a MOVE, not an edit); curate in wiki/pages/ instead." >&2
    exit 2 ;;
esac
exit 0
