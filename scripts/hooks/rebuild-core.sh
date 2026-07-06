#!/usr/bin/env bash
# Critical section for rebuild-and-verify.sh. Invoked ONLY via with_lock.py index.lock.
# Exit codes: 0 = rebuilt+valid or nothing to do; 3 = build failed; 4 = validate failed.
set -uo pipefail
flag_own="$1"; flag_bare="$2"
# Re-check under the lock: a concurrent holder may have already rebuilt and cleared.
[ -f "$flag_own" ] || [ -f "$flag_bare" ] || exit 0
if ! build_out="$(python3 scripts/build_index.py 2>&1)"; then
    printf '%s\n' "$build_out"
    exit 3
fi
printf '%s\n' "$build_out"
report="$(python3 scripts/validate_wiki.py 2>&1)"; rc=$?
printf '%s\n' "$report"
if [ "$rc" -eq 0 ]; then
    rm -f "$flag_own" "$flag_bare"
    exit 0
fi
exit 4
