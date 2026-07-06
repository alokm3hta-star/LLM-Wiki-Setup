# Wiki Operations — Rotation & Health

Single reference for keeping the wiki's operational files small and fast.

## Active rotation targets

| File | Soft threshold | Rotation rule | Where it goes |
|---|---|---|---|
| `wiki/pending/update-proposals.md` | 200 lines / 100 pending | rows with status `executed` or `deferred` | `wiki/archive/<quarter>/update-proposals-executed.md` |
| `wiki/state.md` | 100 lines | self-pruning every Stop (see below); quarterly sweep keeps 5 newest as backstop | `wiki/archive/state-history.md` (Stop) / `wiki/archive/<quarter>/state-history.md` (quarterly) |
| `wiki/log.md` | 400 lines | rows dated before the cutoff (first day of next quarter) | `wiki/archive/<quarter>/log.md` |
| `wiki/pending/cross-links.md` | 400 lines / 30 resolved | first-table rows with status `resolved` (annotated forms accepted) | `wiki/archive/<quarter>/cross-links-resolved.md` |
| `wiki/pending/gap-log.md` | 200 lines | rows dated before the cutoff (first day of next quarter) | `wiki/archive/<quarter>/gap-log.md` |
| `wiki/pending/retrieval-log.md` | 200 lines | rows dated before the cutoff (first day of next quarter) | `wiki/archive/<quarter>/retrieval-log.md` |

Threshold breaches are surfaced as soft warnings by `scripts/check_thresholds.py`, which runs in the Stop/SubagentStop hook chain (`scripts/hooks/rebuild-and-verify.sh`). Warnings never block Stop.

## `state.md` self-pruning (status-keyed GC)

`wiki/state.md` is read in full at every session boot, so it is pruned continuously rather than only on the quarterly sweep. `scripts/rotate_archives.py --state-gc` runs on the Stop hook and archives completed Stage Plan / INGESTION blocks to `wiki/archive/state-history.md`, keying on the `## Current State → Status` field (the only reliable "pending" signal; per-block headers and `Dana: pending` prose drift):

- `Status: idle` → keep the single newest block (the boot reads its `INGESTION COMPLETE` date); archive the rest.
- `Status: in-progress` / `paused` → keep the active `Current source` block (the resume payload) **and** the newest; archive the rest.

It never archives the active/resumable block, is idempotent (no-op when already lean), and has no calendar dependency, so it sidesteps the quarterly in-progress guard. The quarterly `rotate_archives.py <quarter>` run still covers `state.md` as a backstop (keep 5 newest), alongside `update-proposals.md`, `log.md`, and `cross-links.md`. Run it manually once after deploying the GC to clear any pre-existing backlog: `python3 scripts/rotate_archives.py --state-gc`.

## Running rotation

The `quarter` argument names the quarter being archived (a just-ended quarter). Run AT or AFTER the quarter's last day.

```bash
python3 scripts/rotate_archives.py --dry-run 2026-q2     # preview
python3 scripts/rotate_archives.py 2026-q2               # apply (refuses if quarter is still in progress)
python3 scripts/rotate_archives.py --force 2026-q2       # override the in-progress guard
```

After rotation, the script appends one summary row to `wiki/log.md` and creates `wiki/archive/<quarter>/` populated with one file per target. State-rotation is a no-op if `state.md` has fewer than 10 dated blocks (file is already small).

## Measuring health

`scripts/measure_health.py` prints a YAML-style snapshot of every operational metric and appends it (with today's date header) to `wiki/pending/health-history.md`. Use the history file to spot trends and compare against the baselines in [`wiki/pending/deferred-optimisations.md`](pending/deferred-optimisations.md).

```bash
python3 scripts/measure_health.py                # print + append to history
python3 scripts/measure_health.py --no-history   # print only
```

Run after any significant ingestion / curation pass, or weekly on a schedule.

## Maintenance sweep (pull at boot)

`scripts/maintenance_sweep.sh` bundles the deterministic health checks into one dated digest at
`wiki/pending/maintenance-sweep.md`: `measure_health.py` (snapshot + history append), `check_thresholds.py --skip-generated`,
`rotate_archives.py --state-gc --dry-run`, `scripts/detect_stale.py` (pages whose `**Last updated**:` line is
older than 12 months, plus forward-looking / dated titles that should be re-checked), and
`scripts/check_def_triggers.py` (consolidated status of every machine-checkable deferred-optimisation revisit trigger;
CROSSED lines are surfaced as WARN). No model, no network, no Claude usage.

Triggering is **pull-at-boot**, never scheduled: the session-start sequence (`CLAUDE.md` step 7) reads the digest and, if
it is missing or its `generated:` date is more than 7 days old, runs the sweep inline once, then surfaces the sweep date,
threshold warnings, and staleness counts in the ready card. The digest is advisory; act on it with `@sarah research-gaps`,
`@sarah stale`, or a rotation pass when warranted. Re-run by hand any time: `bash scripts/maintenance_sweep.sh`.

## Deferred optimisations

When a future plan decides not to take an optimisation now, record it in [`wiki/pending/deferred-optimisations.md`](pending/deferred-optimisations.md) with the current baseline metrics from `measure_health.py` and the trigger conditions that should make us revisit. Future-you reads that file, runs `measure_health.py`, diffs, and acts only where a trigger crossed.

## Multi-session operation

Multiple Claude sessions can operate on this wiki at once. Contention is removed by construction, not by hoping writers take turns; locks are only a thin safety net on the one irreducibly serial step (the global index rebuild). This section states the model.

### Three-class file model

Every shared file falls into one of three classes, each handled differently:

1. **Generated / derived** — `lookup.md`, `tier2-sections.md`, `index.md` statistics, cluster-header counts. Never edited by hand; rebuilt whole and written via `wikilib.atomic_write` (temp file in the same directory + `os.replace`). A concurrent `grep` sees the old file or the new file, never a torn one (OPT-002).
2. **Queue tables** — proposals, cross-links, gaps, and the append-only ledgers. Writers **create files, they do not edit shared tables**: one file per proposal (`wiki/pending/proposals/SP-NNNN.md`, atomic `O_EXCL` create = ID allocation, OPT-005); inbox drops for cross-link markers and gaps (OPT-006, see below); ledger rows appended through `scripts/append_row.py` (single `O_APPEND` write, OPT-007). Only the curation sweep consolidates, under a lock.
3. **Single registers** — `wiki/state.md`, `wiki/pending/handoff.md`, `wiki/pending/action-items.md`. Semantically single-writer; see the session policy below.

### Locks

`scripts/with_lock.py` wraps a command in an `fcntl.flock` on `wiki/.locks/<lockname>`:
`python3 scripts/with_lock.py <lockname> [--timeout N] -- <cmd...>` (exit 75 on timeout). Two locks exist:

- `index.lock` — the rebuild pipeline (build + validate + flag-clear on the Stop hook, OPT-003).
- `ops.lock` — `state.md` GC, quarterly rotation, cross-link consolidation, health-history writes.

**Locks are `fcntl.flock` on the fd, never file-existence checks.** A leftover file in `wiki/.locks/` is harmless — the kernel releases the lock when the holder exits; there is no stale-lockfile cleanup to do and a leftover file must never be read as "locked".

### Per-session dirty flags

Each page-changing session marks `wiki/.index-dirty.<session_id>` (the bare `wiki/.index-dirty` is kept as a fail-closed fallback when the session id cannot be parsed). A session's Stop hook rebuilds/validates only its own batch (its own flag + the bare flag), so session B is never blocked by session A's half-written pages (OPT-004). `maintenance_sweep.sh` reports flags older than 24 hours (crashed sessions) in its "Stale dirty flags" section.

### Inbox pattern (cross-links + gaps)

Writers never edit the shared `cross-links.md` table. For cross-link rows, a writer creates a unique-named drop file under `wiki/pending/cross-links-inbox/` (`<YYYY-MM-DD>-<source-id>.md`, one `| `-prefixed row per line); pure creation, zero contention. Sarah's `resolve links` sweep alone consolidates the inbox into the Active Pending Queue of `cross-links.md` via `scripts/consolidate_crosslinks.py` under `ops.lock`, then deletes the drops (OPT-006). Anja's usual output is in-page `[?INTEGRATION:]` markers (harvested by `build_index.py`), not direct rows; gap events append to `gap-log.md` through `append_row.py` (OPT-007). Either way, nobody edits `cross-links.md` outside the consolidation sweep.

### Atomic-rename guarantee

Because every generated file is written to a temp file and atomically renamed, a reader's `grep` never blocks and never sees a partial index — it observes either the previous complete file or the next one.

### Cross-session collision log (DEF-010/011)

If you observe a suspected cross-session collision (a torn file, a duplicate ID, a lost row), log it:
`python3 scripts/append_row.py wiki/log.md "| <UTC-ISO> | collision | <files involved> | <what happened> |"`
`check_def_triggers.py` counts rows tagged `collision` for the DEF-010/011 revisit triggers.

### Session policy (OPT-009)

Concurrent sessions supported: any number of read-only query sessions; at most ONE ingestion session; at most ONE curation session; Paul sessions unlimited (he writes only to external code workspaces; write-backs serialise through Alex → Anja). `wiki/state.md`, `wiki/pending/handoff.md`, `wiki/pending/action-items.md` are single-writer registers: only the ingestion session (state) and the main thread (handoff, action-items) write them. Parallel ingestion is deliberately unsupported until DEF-009's trigger is met.

### Validator / sweep ignore paths

`scripts/validate_wiki.py` and `scripts/detect_stale.py` scan only `wiki/pages/` (`PAGES.rglob("*.md")` / `os.walk(PAGES)`), so the operational paths `wiki/.locks/`, `wiki/.index-dirty.*`, `wiki/pending/proposals/`, and `wiki/pending/cross-links-inbox/` are never mistaken for pages — no explicit excludes are required. Keep this true: any future page walker must root at `wiki/pages/`, not `wiki/` broadly.

## Curation backlog burn-down

Ingestion manufactures resolution debt — `[?INTEGRATION:]` markers (→ `pending/cross-links.md`) and Dana semantic advisories (→ `pending/update-proposals.md`) — faster than ad-hoc curation clears it. Left alone the backlog grows silently: unresolved cross-links leave the index `## Edges` traversal incomplete (multi-cluster queries under-retrieve), and unapplied proposals leave pages at as-ingested quality.

Cadence: run a burn-down pass every ~3–5 ingestions, or whenever `check_thresholds.py` warns —

- `@sarah resolve links` to clear the `cross-links.md` worklist, and
- `@sarah queue` triage + `@sarah approve-all` (LOW/MEDIUM proceed automatically, HIGH held) to drain `update-proposals.md`.

`check_thresholds.py` already warns at 100 pending proposals and 30 resolved-but-unrotated cross-links; treat either warning as the trigger to run the pass rather than deferring further.

## Spec hygiene — no embedded wiki-state

Agent specs (`wiki/agents/*.md`) and governance docs must state *what to check and how to verdict*, never *the current answer*. Do not write point-in-time state into a spec — e.g. "cluster X is currently empty", "not yet grounded", "X is a research brief". Such claims drift silently as the wiki grows and mis-prime the agents (an analyst told "expect KNOWLEDGE GAP" under-retrieves on a topic the wiki now covers); the completeness-sweep protocol already returns `KNOWLEDGE GAP` correctly when something is genuinely absent, so the embedded answer is redundant as well as fragile. Likewise, do not hand-maintain counts, ID ranges, or file rosters that a script owns — point at the script-owned source instead. `validate_wiki.py` enforces the highest-value case (a cluster flagged "pending" in `index.md` while its `wiki/pages/<cluster>/` folder is populated).

## Dev-card convention

Paul's craft-rules cache (Clean ABAP / OOP-SOLID / TDD / design-pattern rules) is a hand-authored,
optional artefact split across four files: a slim always-loaded core (`wiki/agents/paul-dev-card.md` —
pack index and loading rules, precedence, enforcement, task classification, checklist) plus three
lazily-loaded phase packs under `wiki/agents/paul-card-packs/` (`pack-1-tdd.md`,
`pack-2-structure-patterns.md`, `pack-3-naming-readability.md`) holding the verbatim rule bodies. None of
these are Tier-1 wiki pages and none are covered by the normal ingestion pipeline. `scripts/validate_wiki.py`
checks the whole set, ERROR-tier, whenever the core card exists: every `[[wikilink]]` in the core or any
pack must resolve to a real page stem; every backtick-wrapped `` `grep ...` `` recipe line must return at
least one hit against the live corpus (a recipe returning zero hits means the "where to look next"
guidance has gone stale); every pack listed in the core's Pack Index must exist on disk; and no rule ID
may be defined in more than one file. The check is a no-op if the core card is absent.

Rule IDs are stable forever: never renumbered, never reused. A retired ID is documented at its merge
target (the surviving rule carries "(supersedes X)") or, for the ATC-delegated CA-FORMAT block, in the
core's Enforcement section, which serves as the tombstone for those IDs.

To regenerate the card set from source: dispatch one Sonnet distiller per rule family (Clean ABAP,
OOP-SOLID, TDD, design patterns) in parallel, each returning verbatim-quoted rules tagged with a rule ID
and source page; run a single Dana pass that verifies every quote is a literal substring of its cited page
(programmatic check, not semantic judgement); rework any flagged quote with its originating batch, max 3
rounds; assemble the verified batches into the four-file layout (core + three packs), preserving existing
rule IDs and tombstones. See `wiki/pending/deferred-optimisations.md` → DEF-007 for the
compiler-vs-hand-authored trade-off this process currently defers.

## `.mcp.json` mirror exclusion

`.mcp.json` (project root) holds the ADT MCP Server's connection config, including a bearer token — a
secret. It must never be committed to a public remote, logged, or echoed in any agent hand-off (see
`wiki/agents/paul-dev.md` → Guardrails, token hygiene). When mirroring the framework engine into
`LLM Wiki Setup`, exclude `.mcp.json` from the sync alongside the existing `client-dev-context` cluster
exclusion (`wiki/clusters/client-dev-context.md`) — check for its presence and drop it from the mirror
payload every time a framework sync runs, the same way the confidential cluster row is checked and dropped.

The **personalisation stores** are confidential too and join the same exclusion: `wiki/profile/` (the user
engagement card) and `wiki/agents/lessons/` (per-agent lesson files) hold user-specific context and
corrections that are not portable across customers. Drop both directories from the mirror payload on every
framework sync, alongside `.mcp.json` and the `client-dev-context` row. The scaffolding is fine to ship;
seed the mirror's `wiki/profile/engagement.md` empty and leave the lesson files at "None yet".

The **runtime operational artefacts** are session-local and must also be dropped from the mirror payload:
`wiki/.locks/` (flock targets) and `wiki/.index-dirty.*` (per-session dirty flags). They carry no portable
content and are recreated on demand; exclude them the same way, alongside `.mcp.json`.

**Exclusion vs. scaffolding: which is which.** `wiki/pending/proposals/`, `wiki/pending/cross-links-inbox/`,
`wiki/archive/`, and `wiki/.locks/` are safe to drop from the mirror payload with no placeholder, because
their owning script creates the directory on first use (`ACTIVE.mkdir(parents=True, exist_ok=True)` in
`new_proposal.py`; the inbox is written via ordinary file creation, tolerant of absence on read in
`consolidate_crosslinks.py`; `ARCHIVE.mkdir(...)` / `qdir.mkdir(...)` in `rotate_archives.py`;
`LOCK_DIR.mkdir(...)` in `with_lock.py`); a fresh clone with the directory missing self-heals on first
write. `wiki/pending_research/_resolved/` is different: it is filled by Sarah archive-moving closed research
briefs per her spec, a prose instruction to an LLM agent rather than a script-guaranteed `mkdir`, so it does
**not** self-heal the same way. Ship it in the mirror with the same placeholder convention as
`raw/`/`raw_processed/`/`other_sources/` (a tracked `README.md`, real `.md` content gitignored) rather than
excluding it outright. When adding a future mirror exclusion, check which category it falls into before
choosing "just gitignore it" vs. "gitignore the content but ship a placeholder."

**Cluster registries must be reset to the fresh-install stub, never carried over live.** `wiki/clusters/*.md`
are tracked (unlike `wiki/pages/`), so a sync that copies them verbatim from the live wiki carries over
every accumulated entity row, including real page filenames, real summaries, and real source citations
(publisher name, book title, chapter/part) for whatever has actually been ingested. Every cluster registry
in the mirror must show `Entity count: 0` and an empty entity table (header + divider row only, matching a
genuinely fresh install), the same as the zero-pages rule for `wiki/pages/`. Check this for **every**
cluster on every sync, not just the ones that look client-specific: a generic public-domain topic sourced
from a named commercial publication is exactly as unsafe to carry over as a confidential one, because the
leak is the *publisher citation and accumulated entity detail*, not the topic's sensitivity.

**Genericise specific regulation/publisher naming in the mirror's illustrative text.** Independent of the
registries above, the mirror's own documentation (README walkthroughs, schema examples, cluster one-line
descriptions) should describe capability areas in generic product terms (e.g. "privacy-driven data
destruction" rather than naming a specific regional data-protection regulation by acronym) and should never
name a specific commercial publisher or cite a book/chapter/part in illustrative examples. This is a
documentation-style rule (avoid inviting the next sync to reintroduce a specific name as "just an example"),
separate from the registry-reset rule above, which is about real accumulated data.

**No em-dashes or en-dashes in shipped documentation.** CLAUDE.md's style rule (use semicolons, colons, or
new sentences instead) applies to every file the mirror ships, not just README.md: this operations file,
schema.md, agent specs, anything a sync writes or edits. Sweep before every sync with
`git grep -n '—\|–' -- '*.md'`; treat any hit inside text this sync is writing or editing as a fix-before-push
item. Pre-existing hits in untouched content are a separate, larger cleanup, not a per-sync blocker.

## Paul write-back flow

Every Paul hand-off carries a mandatory `## Write-back requests` section (see `wiki/agents/paul-dev.md` →
Wiki Write-Back Duty). The flow: Paul emits write-back blocks → Alex relays exactly one
`@anja ingest paul-writebacks` call per hand-off (see `wiki/agents/alex-master.md` → "Paul Write-Back
Relay") → Anja classifies each block through the existing new/overlap/synonym delta logic, routing to a
general cluster or `client-dev-context` per the block's own stated routing → Dana verifies the resulting
pages/enrichments (same rework-loop discipline as any other ingestion) → the index rebuilds. To check
whether the loop is working, confirm a later Paul task cites a previously-written-back fact `[T1]` /
`[T1-client]` from `lookup.md` instead of re-running `[MCP]` introspection for the same fact.

## Files

- `scripts/rotate_archives.py` — quarterly rotation
- `scripts/measure_health.py` — operational snapshot
- `scripts/check_thresholds.py` — soft warnings (Stop hook)
- `scripts/check_def_triggers.py` — consolidated deferred-optimisation trigger status (maintenance sweep)
- `scripts/maintenance_sweep.sh` — pull-at-boot health digest → `wiki/pending/maintenance-sweep.md`
- `scripts/detect_stale.py` — staleness scan (aged / review-trigger / no-date pages)
- `scripts/scan_ingest.sh` — pull-at-boot ingest scan of `other_sources/` → `wiki/pending/ingest-queue.md`
- `scripts/wikilib.py` — shared helpers (`atomic_write`, status-row counting)
- `scripts/with_lock.py` — `fcntl.flock` command wrapper (`index.lock` / `ops.lock`)
- `scripts/new_proposal.py` — atomic `O_EXCL` proposal-file creation (ID allocation) → `wiki/pending/proposals/`
- `scripts/append_row.py` — atomic `O_APPEND` ledger-row writer (log / gap-log / retrieval-log / health-history)
- `scripts/consolidate_crosslinks.py` — folds `cross-links-inbox/` drops into `cross-links.md` (run under `ops.lock`)
- `wiki/.locks/` — flock lock files (session-local; mirror-excluded)
- `wiki/pending/proposals/` — one file per proposal (`SP-NNNN.md`)
- `wiki/pending/cross-links-inbox/` — writer drop-box for new cross-link rows (consolidated by Sarah)
- `wiki/archive/` — destination for rotated content
- `wiki/pending/deferred-optimisations.md` — decision log for deferred optimisations
- `wiki/pending/health-history.md` — time-series of `measure_health.py` snapshots
- `wiki/pending/maintenance-sweep.md` — latest maintenance digest (surfaced at boot)
- `wiki/profile/`, `wiki/agents/lessons/` — personalisation stores (confidential; mirror-excluded)
