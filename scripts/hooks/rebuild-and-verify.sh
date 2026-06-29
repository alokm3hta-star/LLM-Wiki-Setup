#!/usr/bin/env bash
# Stop / SubagentStop hook: when Tier-1 pages changed this turn, rebuild the index and
# verify consistency. Blocks finishing (exit 2) once if validate_wiki.py finds ERRORS,
# surfacing the report so the model reworks + invokes the validator (Dana/Sentinel).
# `stop_hook_active` guards against an infinite stop loop.
set -uo pipefail
input="$(cat)"
root="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
flag="$root/wiki/.index-dirty"
cd "$root" || exit 0

active="$(printf '%s' "$input" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("stop_hook_active",False))' 2>/dev/null || echo False)"

# Soft-warning threshold check (never blocks; warnings go to stderr). On a clean turn (no
# page changes) skip the two large generated indexes (lookup.md, tier2-sections.md): they
# only grow on a rebuild, so there is nothing new to measure; the cheap operational-file
# checks (update-proposals, state, log, cross-links) still run because those can grow in
# sessions that never touch wiki/pages/.
if [ -f "$flag" ]; then
  python3 scripts/check_thresholds.py || true
else
  python3 scripts/check_thresholds.py --skip-generated || true
fi

# Status-keyed prune of state.md: archive completed Stage Plan blocks (keeping the active
# block when an ingestion is in-progress) so the next session's boot reads a lean file.
# Never blocks; archive move is reversible; no-op when already lean.
python3 scripts/rotate_archives.py --state-gc || true

[ -f "$flag" ] || exit 0          # no page changed this turn -> skip index rebuild

# Rebuild the index; surface failures instead of swallowing them (so a real build error is
# visible at its source, not later as a confusing "lookup.md missing").
build_out="$(python3 scripts/build_index.py 2>&1)"; build_status=$?
if [ "$build_status" -ne 0 ]; then
  {
    echo "build_index.py FAILED (exit $build_status) — lookup.md was NOT rebuilt:"
    echo "$build_out"
  } >&2
  [ "$active" = "True" ] && exit 0
  exit 2
fi

# Validate; surface advisory warnings rather than hiding them behind --quiet.
report="$(python3 scripts/validate_wiki.py 2>&1)"; status=$?

if [ "$status" -eq 0 ]; then
  rm -f "$flag"
  printf '%s\n' "$report" | grep -E ' WARN ' >&2 || true   # surface WARN lines even on PASS
  exit 0
fi

{
  echo "Wiki verification FAILED after page changes — rework needed before finishing."
  echo "Invoke the validator (Dana / Sentinel) to review, fix the flagged pages, then continue."
  echo "$report"
} >&2
[ "$active" = "True" ] && exit 0   # already prompted once this turn -> avoid an infinite loop
exit 2                              # block finishing; feed the report back to the model
