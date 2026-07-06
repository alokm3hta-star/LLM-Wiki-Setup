#!/usr/bin/env bash
# maintenance_sweep.sh — deterministic wiki-health sweep. No model, no network, no Claude usage.
# Runs the read-only / soft health scripts and writes a dated digest to
# wiki/pending/maintenance-sweep.md, which the boot sequence surfaces in the ready card.
# Triggered at session start when the digest is stale (pull-at-boot); safe to run repeatedly by hand.
set -uo pipefail

ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
cd "$ROOT" || exit 1

DIGEST="wiki/pending/maintenance-sweep.md"
TMP="$DIGEST.tmp.$$"
TODAY="$(date +%F)"
PY="python3"

# Fresh digest header (overwrite, one live digest at a time).
{
    echo "---"
    echo "type: maintenance-sweep"
    echo "generated: $TODAY"
    echo "---"
    echo
    echo "# Maintenance Sweep — $TODAY"
    echo
    echo "Deterministic health digest (no model, no Claude usage). Surfaced in the ready card at the"
    echo "next session start. Re-run by hand: \`bash scripts/maintenance_sweep.sh\`."
    echo
} > "$TMP"

# run <heading> <cmd...> : capture stdout+stderr into the digest under a fenced heading.
run() {
    local label="$1"; shift
    {
        echo "## $label"
        echo '```'
        "$@" 2>&1 || echo "(script exited non-zero: $*)"
        echo '```'
        echo
    } >> "$TMP"
}

run "Health snapshot (measure_health.py)"                                   "$PY" scripts/measure_health.py
run "Threshold warnings (check_thresholds.py)"                              "$PY" scripts/check_thresholds.py --skip-generated
run "State.md rotation preview (rotate_archives.py --state-gc --dry-run)"   "$PY" scripts/rotate_archives.py --state-gc --dry-run
run "Staleness scan (detect_stale.py)"                                      "$PY" scripts/detect_stale.py
run "Deferred-trigger status (check_def_triggers.py)"                        "$PY" scripts/check_def_triggers.py

{
    echo "## Stale dirty flags (crashed sessions)"
    echo '```'
    find wiki -maxdepth 1 -name '.index-dirty*' -mmin +1440 2>/dev/null \
      | sed 's/^/STALE (>24h): /' || true
    echo '(heal: run `python3 scripts/build_index.py && python3 scripts/validate_wiki.py`, then delete the flag)'
    echo '```'
    echo
} >> "$TMP"

mv "$TMP" "$DIGEST"
echo "Maintenance sweep written to $DIGEST"
