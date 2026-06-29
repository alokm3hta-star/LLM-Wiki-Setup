# Session State

This file tracks current operational state; read at session start to determine resumption requirements.

## Current State

- **Current source**: none (fresh install)
- **Status**: idle

No ingestion has run yet. The first `@anja ingest` adds a Stage Plan block and an `INGESTION COMPLETE (YYYY-MM-DD)` line here, which the boot sequence reads.

## Status Values

- **idle**: No active operation; ready for new commands.
- **in-progress**: Ingestion active; resume with 'resume' command.
- **paused**: Ingestion paused by user; resume with 'resume' command.

## Session History

| Session Start | Operation | Source | Chunks Processed | Outcome |
| ------------- | --------- | ------ | ---------------- | ------- |
