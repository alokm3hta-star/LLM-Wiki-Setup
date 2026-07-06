#!/usr/bin/env bash
# scan_ingest.sh — pull-at-boot ingest scan. Lists other_sources/ and writes
# wiki/pending/ingest-queue.md so the boot sequence can surface a "N files awaiting @kylie convert"
# line in the ready card. Deterministic: no conversion, no ingestion, no writes to raw/. bash 3.2 safe.
set -uo pipefail

ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
cd "$ROOT" || exit 1

QUEUE="wiki/pending/ingest-queue.md"
TODAY="$(date +%F)"
SRC="other_sources"

count="$(find "$SRC" -maxdepth 1 -type f ! -name '.*' 2>/dev/null | wc -l | tr -d ' ')"

{
    echo "---"
    echo "type: ingest-queue"
    echo "generated: $TODAY"
    echo "count: $count"
    echo "---"
    echo
    echo "# Ingest Queue — $TODAY"
    echo
    if [ "$count" -eq 0 ]; then
        echo "\`other_sources/\` is empty. Nothing awaiting conversion."
    else
        echo "$count file(s) in \`other_sources/\` awaiting \`@kylie convert\` (then \`@anja ingest\`):"
        echo
        find "$SRC" -maxdepth 1 -type f ! -name '.*' 2>/dev/null | sort | while IFS= read -r f; do
            sz="$(du -h "$f" 2>/dev/null | cut -f1 | tr -d ' ')"
            printf -- '- `%s` (%s)\n' "$f" "$sz"
        done
        echo
        echo "Run \`@kylie convert\` to stage into \`raw/\`, then \`@anja ingest raw/<file>\`. Nothing is converted automatically."
    fi
} > "$QUEUE.tmp.$$"
mv "$QUEUE.tmp.$$" "$QUEUE"

echo "Ingest queue written to $QUEUE ($count file(s))."
