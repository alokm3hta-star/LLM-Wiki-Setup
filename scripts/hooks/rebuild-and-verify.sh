#!/usr/bin/env bash
# Stop / SubagentStop hook: when Tier-1 pages changed this turn (per-session dirty flag),
# rebuild the index and verify consistency, serialised across sessions via index.lock.
# Blocks finishing (exit 2) once if validate_wiki.py finds ERRORS. On lock contention
# it NEVER blocks the user: it leaves the flag set and lets the next Stop retry.
set -uo pipefail
input="$(cat)"
root="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
cd "$root" || exit 0

active="$(printf '%s' "$input" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("stop_hook_active",False))' 2>/dev/null || echo False)"
sid="$(printf '%s' "$input" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("session_id",""))' 2>/dev/null || echo '')"
flag_own="$root/wiki/.index-dirty.${sid:-unknown}"
flag_bare="$root/wiki/.index-dirty"

if [ -f "$flag_own" ] || [ -f "$flag_bare" ]; then
  python3 scripts/check_thresholds.py || true
else
  python3 scripts/check_thresholds.py --skip-generated || true
fi

# state-gc under ops.lock; short timeout, never blocks the turn.
python3 scripts/with_lock.py ops.lock --timeout 20 -- \
  python3 scripts/rotate_archives.py --state-gc || true

[ -f "$flag_own" ] || [ -f "$flag_bare" ] || exit 0   # this session changed no pages

out="$(python3 scripts/with_lock.py index.lock --timeout 120 -- \
       bash scripts/hooks/rebuild-core.sh "$flag_own" "$flag_bare" 2>&1)"; status=$?
case "$status" in
  0)
    printf '%s\n' "$out" | grep -E ' WARN ' >&2 || true
    exit 0 ;;
  75)
    echo "index.lock busy (another session rebuilding); dirty flag left in place, next Stop retries." >&2
    exit 0 ;;
  3)
    { echo "build_index.py FAILED — lookup.md was NOT rebuilt:"; printf '%s\n' "$out"; } >&2
    [ "$active" = "True" ] && exit 0
    exit 2 ;;
  4)
    { echo "Wiki verification FAILED after page changes — rework needed before finishing."
      echo "Invoke the validator (Dana / Sentinel) to review, fix the flagged pages, then continue."
      printf '%s\n' "$out"; } >&2
    [ "$active" = "True" ] && exit 0
    exit 2 ;;
  *)
    printf '%s\n' "$out" >&2
    exit 0 ;;
esac
