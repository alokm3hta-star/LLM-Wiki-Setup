#!/usr/bin/env bash
# archive_source.sh — the single sanctioned path for Anja's ingestion step 8 (Archival).
#
# Guardrail #1 sanctions a MOVE (never a copy) of a fully-ingested source out of raw/ into
# raw_processed/. This script guarantees move-not-copy: it is idempotent, refuses to clobber a
# DIFFERING archive, heals a prior copy-not-move, and appends one audit row to wiki/log.md.
# raw_processed/ is write-once on archival and immutable thereafter.
#
# Usage:  scripts/archive_source.sh "raw/<filename>.md"   (a bare basename is also accepted)
set -uo pipefail
root="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"

arg="${1:-}"
if [ -z "$arg" ]; then
  echo "usage: archive_source.sh \"raw/<filename>\"" >&2
  exit 2
fi

base="$(basename "$arg")"
src="$root/raw/$base"
dst="$root/raw_processed/$base"

result=""
if [ ! -f "$src" ]; then
  if [ -f "$dst" ]; then
    echo "OK: '$base' already archived (absent from raw/) — nothing to do."
    exit 0
  fi
  echo "ERROR: source not found in raw/: '$base'" >&2
  exit 1
elif [ -f "$dst" ]; then
  if cmp -s "$src" "$dst"; then
    rm -f "$src"
    result="healed prior copy — removed raw/ original (identical to archive)"
    echo "HEALED: '$base' — archive already identical; removed the raw/ original."
  else
    echo "ERROR: '$base' exists in raw_processed/ but DIFFERS from raw/." >&2
    echo "       Refusing to clobber the archive (immutable — Guardrail #1). Resolve manually." >&2
    exit 1
  fi
else
  mv "$src" "$dst"
  result="moved raw/ → raw_processed/"
  echo "ARCHIVED: moved '$base' raw/ → raw_processed/."
fi

# append-only audit row (log.md is exempt under Guardrail #9), matching the table format
printf '| %s | source-archived | %s | %s (archive_source.sh) |\n' \
  "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$base" "$result" >> "$root/wiki/log.md"
exit 0
