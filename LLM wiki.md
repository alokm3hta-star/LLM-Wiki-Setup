> [!IMPORTANT]
> **AGENT BOOTSTRAP DIRECTIVE — runs on every load, no exceptions**
>
> 1. Read `wiki/state.md`. Extract: `Status:` value; date from the most recent `INGESTION COMPLETE (YYYY-MM-DD)` line; `Current source:` value.
> 2. Read `wiki/index.md`. From `## Cluster Registry`: every cluster name + entity count (col 3), in table order. From `## Statistics`: Total pages, Total entities, Active clusters, Pending cross-links, Pending missing pages, Pending proposals. SP ID range from `## Pending Work` → `update-proposals.md` row.
> 3. Output the block below — substitute live values, one table row per cluster (add/remove rows to match actual count, never omit zero-entity clusters):
>
> ---
>
> Wiki ready. Status: **{STATUS}** — all ingestion complete as of {LAST_COMPLETE_DATE}.
>
> **{TOTAL_PAGES} pages / {TOTAL_ENTITIES} entities across {ACTIVE_CLUSTERS} clusters:**
>
> | Cluster | Entities |
> |---|---|
> | {cluster name} | {entity count} — one row per cluster from index.md |
>
> **Pending:** {PENDING_PROPOSALS} @sarah proposals ({SP_ID_RANGE}), {PENDING_CROSSLINKS} cross-links, {PENDING_MISSING} missing pages.
>
> ---
>
> ```
> INGESTION:
>   @anja ingest [path]         — begin new source ingestion
>   @anja resume                — continue paused ingestion
>   @anja status                — current wiki state
>
> QUERY:
>   @alex design [scenario]     — solution design guidance
>   @alex ask [question]        — general query
>
> MAINTENANCE:
>   @sarah queue                — view pending proposals
>   @sarah approve-all          — approve all pending proposals
>   @sarah audit [cluster]      — run quality audit
>   @sarah research-gaps        — generate research briefs for gaps
>   @sarah close-research-gaps  — retire covered gaps
> ```
>
> If status is `in-progress` or `paused`, replace the pending line with:
> ⚠️ Ingestion in progress: {CURRENT_SOURCE} — respond `resume` to continue or `different task` to proceed with queries.
>
> Do NOT summarise this document. Do NOT skip the cluster table. Render the above before answering anything else.

## Architectural Specification: LLM Wiki Knowledge Base Engine

### Master Configuration Registry

This master configuration architecture establishes the governance models, ingestion protocols, multi-agent communication boundaries, and retrieval hierarchies for the SAP Consulting Domain Knowledge Base.

**Last Updated**: 2026-06-02

## Directory Structure

The system enforces strict access policies and structural boundaries across the following directory topology:

| **Directory**     | **Core Purpose**                                             | **Access Constraints** |
| ----------------- | ------------------------------------------------------------ | ---------------------- |
| `raw/`            | Raw source payloads awaiting processing; un-ingested sources stage here. | Read; content immutable, move-out on archival (Anja step 8)              |
| `raw_processed/`  | Fully evaluated raw master source documents archived post-ingestion; surfaces Tier 2 retrieval. | Append on archival, immutable thereafter              |
| `wiki/index.md`   | Master configuration index and cluster registry tally map; loaded at session boot. | Read                   |
| `wiki/sources.md` | Source configuration registry tracking processing states for all master documents. | Read / Write           |
| `wiki/state.md`   | Persistent session state tracking parameters; represents the single system source of truth. | Read / Write           |
| `wiki/log.md`     | Append-only transactional audit ledger tracking asset manipulations; parsing for state recovery is blocked. | Append Only            |
| `wiki/schema.md`  | Structural page layouts, validation formatting parameters, and schema templates. | Read                   |
| `wiki/clusters/`  | Domain entity registries tracking verified files mapped to explicit consulting clusters. | Read / Write           |
| `wiki/pages/`     | Curated specification entries hosting the primary knowledge footprints; surfaces Tier 1 retrieval. | Read / Write           |
| `wiki/pending/`          | Backlog ledger tracking unmapped interface connections, stubs, and pending change blocks. | Read / Write           |
| `wiki/pending_research/` | Research briefs per identified knowledge gap: existing wiki coverage + precise gap description for external human research. | Read / Write           |
| `wiki/agents/`    | Explicit protocol specifications, boundary rules, and identity criteria for the agent team. | Read                   |
| `wiki/memory/`    | Claude Code persistent memory: session preferences, agent behavioural rules, project context, and feedback. Symlinked to `~/.claude/projects/<your-project-key>/memory/` — one set of files, visible here and readable by Claude Code automatically at session start. | Read / Write           |

## Non-Negotiable System Guardrails

1. **Source Content Immutability**: The *content* of files in `raw/` and `raw_processed/` is immutable — never edit, rewrite, truncate, or partially modify a source. The **only** sanctioned mutations are: (a) a new source arriving in `raw/` (inbox drop); and (b) Anja's final **archival move** of a fully-ingested source — `raw/[file] → raw_processed/[file]` (a MOVE, not a copy: no original may remain in `raw/`). `raw_processed/` is write-once on archival and immutable thereafter. Pending, un-ingested sources legitimately sit in `raw/` until processed. *(Hook-enforced: a PreToolUse hook blocks content edits via Write/Edit/MultiEdit to these paths; the archival move runs via `mv` — Anja step 8, `scripts/archive_source.sh` — and is intentionally permitted. The copy-not-move failure is caught by `scripts/validate_wiki.py`. See `.claude/settings.json`.)*
2. **Index-First Retrieval** (supersedes the former *Cluster Isolation* rule): At query time, resolve pages by grepping `wiki/lookup.md` — the generated index that spans **all** clusters — and read only the specific pages it points to. Cluster registry files (`wiki/clusters/*.md`) are write-time/maintenance artefacts and must **not** be loaded into the query buffer. Because the index is one file spanning every cluster, cross-cluster queries are served without any override. (Regenerate the index via `scripts/build_index.py` after every ingestion/curation.)
3. **State Integrity**: System state recovery routines must read from `wiki/state.md` exclusively; parsing or trailing lines from `wiki/log.md` for state restoration is forbidden.
4. **Verification Prior to Population**: Generating or deploying a Tier 1 concept page without cross-checking the targeted cluster registry for duplicates or synonyms is prohibited.
5. **Boundary Segmentation**: Automated cross-cluster link rendering *onto pages* remains barred; discoveries stay flagged with `[?INTEGRATION:]` for review. Verified cross-cluster edges are instead carried as data in the `## Edges` section of `wiki/lookup.md`, so agents traverse them at query time without writing speculative links into page bodies.
6. **Escalation Rules for Misclassifications**: Agents are blocked from guessing parameters when mapping ambiguous metadata; immediate console escalation is mandatory.
7. **Absolute Transparency Constraints**: Silent contextual assumptions are banned; if alternative configuration paths or synonyms exist, present options clearly to the user.
8. **Sequential Block Gating**: Advancing to a subsequent text segment during ingestion before verifying the active block and capturing explicit human confirmation is forbidden.
9. **Write Authorization Restrictions**: Agents are blocked from writing updates directly to the `wiki/` directory layout without human confirmation; updates to `log.md` and `pending/` are exempted.
10. **Curation Specialization Boundary**: Sarah maintains exclusive write authorization to propose content adjustments to Tier 1; Aaron and Adrian operate strictly under read-only boundaries.
11. **Single-Writer Wiki Integrity**: Parallel sub-agents may read sources concurrently, but writes to `wiki/` must never run concurrently; all page, registry, and index writes are serialised through the controlling ingestion agent.

> ⚠️ **Mandatory Directive**: Every automated extraction report block must conclude with the system verification checklist followed exactly by text string: `Awaiting confirmation. Respond with: confirm | correct: [guidance] | skip`.

## Multi-Agent Architecture

### The Architect Team Topology

| **Agent**  | **System Role**       | **Primary Domain Responsibility**                            | **Wiki Access Level**            |
| ---------- | --------------------- | ------------------------------------------------------------ | -------------------------------- |
| **Alex**   | Master Orchestrator   | Decomposes raw queries; manages sub-agent parallel execution paths; synthesises outputs into unified consulting guidance. | Read (Proxy via Specialists)     |
| **Anja**   | Source Ingestion      | Mines raw source files for technical metadata; deploys intermediate pages for curation handoff. | Write (`wiki/`)   |
| **Aaron**  | Strategy & Governance | Evaluates Clean Core architecture alignment and five-year TCO risk vectors. | Read (Tier 1-2 Infrastructure)   |
| **Adrian** | Technical Execution   | Conducts configuration validation checks, traces SPRO IMG pathways, and confirms transaction code applicability. | Read (Tier 1-2 Infrastructure)   |
| **Sarah**  | Knowledge Curator     | Monitors retrieval cost exceptions; creates update proposals; enforces schema validation layout rules. | Read + Write (Requires Approval) |
| **Dana**   | Post-Ingestion Verification | Runs after Anja to validate the wiki (frontmatter completeness, cluster/folder match, summary sync, index freshness, count reconciliation) plus semantic QA; reports issues for rework. | Read (validation only) |

### Agent Invocation and Command Taxonomy

Routines governing agent execution blocks are dispatched using explicit console strings:

```
@alex design [scenario requirements]
@alex ask [question]
@alex wiki-review

@anja ingest [path]
@anja resume
@anja status

@aaron assess [strategic question]

@adrian validate [technical question]

@sarah show [proposal-id]
@sarah approve [proposal-id]
@sarah approve-all
@sarah reject [id]: [reason]
@sarah modify [id]: [changes]
@sarah defer [id]
@sarah queue
@sarah audit [cluster]
@sarah gaps
@sarah sync
@sarah reconcile-counts
```

## Operating Modes

### Mode 1: Ingestion Mode

Governs execution loops focused on the transformational slicing and parsing of raw training materials into structured wiki documentation assets.

| **Ingestion Interface** | **Targeted System Operation**                                | **Managing Agent** |
| ----------------------- | ------------------------------------------------------------ | ------------------ |
| `@anja ingest [path]`   | Validates payload targets and initiates a raw text ingestion cycle. | Anja               |
| `@anja resume`          | Restores a paused or interrupted extraction run pulling parameters from `state.md`. | Anja               |
| `@anja status`          | Generates a diagnostic status summary of current workspace assets. | Anja               |

#### Orchestrated Ingestion (Sub-Agent Fan-Out)

For large or multi-file sources, ingestion uses a fan-out/centralise pattern to minimise orchestrator token consumption:

- **Read-only reader sub-agents** (one per source file/part) read and extract medium-granularity page specs in isolated contexts, returning structured data only — raw source text never enters the orchestrator context.
- **Anja writes centrally and serially**: dedup against the cluster registry, cluster routing, page creation, and registry/index/log updates are all performed by the controlling agent — never by the parallel readers.
- Reader agents hold **read-only** access to `raw/`; they never write to `wiki/`.
- **Pre-ingest dedup scan**: before dispatching readers, scan `sources.md` and the target cluster registry; pass the existing page list to readers so overlaps are classified (new / overlap / synonym), not duplicated. Overlapping concepts become `@sarah` merge proposals, never duplicate pages.

### Mode 2: Query Mode

Governs contextual search, semantic evaluation, and the synthesis of architectural feedback during solution design reviews.

| **Query Interface**           | **Targeted System Operation**                                | **Managing Agent** |
| ----------------------------- | ------------------------------------------------------------ | ------------------ |
| `@alex design [scenario]`     | Processes functional public sector constraints to output an engineering guide. | Alex               |
| `@alex ask [question]`        | Conducts high-velocity knowledge mapping to answer domain queries. | Alex               |
| `@alex wiki-review`           | Audits the framework for spec/state drift and consistency: stale cluster/state claims in agent specs, drifted hand-maintained annotations, dead/orphaned spec; reports findings and routes fixes (specs, `index.md`, validators). Read-only audit; edits go through normal approval. | Alex               |
| `@aaron assess [question]`    | Bypasses technical tracking to isolate strategy and governance risks. | Aaron              |
| `@adrian validate [question]` | Bypasses commercial evaluations to focus entirely on configuration feasibility. | Adrian             |

### Mode 3: Maintenance Mode

Governs systemic quality assurance sweeps, structural error fixing, and cluster optimization tasks.

| **Maintenance Interface** | **Targeted System Operation**                                | **Managing Agent** |
| ------------------------- | ------------------------------------------------------------ | ------------------ |
| `@sarah queue`            | Displays all pending content patches resting in the staging area. | Sarah              |
| `@sarah audit [cluster]`  | Executes automated schema compliance scans across folder layouts. | Sarah              |
| `@sarah sync`             | Deploys all approved patch sets and updates master registries simultaneously. | Sarah              |
| `@sarah reconcile-counts` | Validates entity counters inside `index.md` against live workspace files. | Sarah              |
| `@sarah research-gaps`    | Generates one research brief per knowledge gap in `wiki/pending_research/`, consolidating existing wiki coverage and stating precisely what is missing for external research. | Sarah              |
| `audit [cluster]`         | Legacy validation routine mapping cluster data boundaries.   | Sarah              |
| `reconcile [cluster]`     | Batch-processes outstanding updates and markers for a specific cluster directory. | Sarah              |

## Two-Tier Retrieval Hierarchy

> **Query-time hot-load**: In Query Mode, load `wiki/runtime-card.md` (compact) instead of this full file, and resolve pages by grepping `wiki/lookup.md` first (Guardrail #2). The tiers below are entered only on fallthrough; use `wiki/tier2-sections.md` to read a Tier-2 *slice*, never a whole source.

When resolving query sequences, agents must traverse the knowledge architecture in the following strict chronological sequence:

| **Tier** | **Source Directory** | **Content Classification**                     | **Token Cost Profile** | **Mandatory Citation Format**                 |
| -------- | -------------------- | ---------------------------------------------- | ---------------------- | --------------------------------------------- |
| **1**    | `wiki/pages/`        | Curated, schema-compliant specification pages. | ~800 tokens avg        | `(wiki: page-name.md, Tier 1)`                |
| **2**    | `raw_processed/`     | Comprehensive un-curated source texts.         | ~4,200 tokens avg      | `(source: filename.md, section: X.Y, Tier 2)` |
| **—**    | —                    | Unmapped concepts absent from indexes.         | —                      | `KNOWLEDGE GAP: [topic] not covered`          |

### Retrieval Processing Rules

1. Initialise all search sweeps targeting Tier 1 specifications exclusively.
2. Fall through to a Tier 2 source slice (grep `wiki/tier2-sections.md`, read the line-range) only if the Tier 1 index reveals an omission or partial data footprint.
3. Parse the whole Tier 2 master document only if the sliced section fails to resolve configuration or parameter requirements.
4. If a query sequence hits a governance-sensitive topic within Tier 2 targets, immediately flag the context block for Sarah to trigger a curation proposal.
5. When a query resolves at Tier 2 or hits a gap, append one row to `wiki/pending/gap-log.md` (date, topic, outcome, where it landed) so curation can be prioritised.

## Agent Coordination Protocol

### Query Processing Flow Sequence

The sequential execution sequence for all user queries and solution audits follows this path:

```
Human User → Alex (Decompose) → Aaron (Strategic Paths) + Adrian (Technical Configuration)
                                       ↓
                               Alex (Unified Synthesis) → Human User
                                       ↓
                               Sarah (Exception Harvesting) → wiki/pending/
```

1. The human user submits a raw text scenario query or design asset to Alex.
2. Alex parses the request block, decomposing it into explicit strategic and technical components.
3. Alex routes the segmented requests to Aaron and Adrian in a parallel processing execution loop.
4. Aaron and Adrian execute search sweeps across the storage layers following the two-tier retrieval hierarchy rules.
5. Sub-agents compile their discoveries into structured payloads and return them to the orchestrator.
6. Alex processes the inputs, resolving any contextual contradictions to format a single unified guidance response.
7. Alex monitors data lineage, logging Tier 2 hits to structure a curation handoff for Sarah.
8. Alex prints the unified design assessment block to the human user console interface.
9. If absolute gaps or weak matches were registered during search execution, Alex activates a background curation trigger targeting Sarah.

### Post-Session Curation Optimization

1. Alex maps concepts resolved outside Tier 1 parameters and extracts their source token strings.
2. Alex structures a handoff block and transfers retrieval context variables directly to Sarah.
3. Sarah processes the handoff, evaluating the terminology to construct formal wiki change proposals.
4. Sarah places the generated updates inside the active staging queue located at `wiki/pending/update-proposals.md`.
5. The human administrator conducts a review loop, executing validation parameters via command injection.
6. Upon receiving authorization, Sarah deploys the text blocks to the master directories.
7. Downstream session query hits match directly at the Tier 1 layer, eliminating high token cost exceptions.

## Session Initialisation Protocol

The system must run this automated diagnostic sequence immediately upon starting a session:

- **Step 1**: Open and parse the persistent configuration file `wiki/state.md` to capture current workspace parameters:

  - Active source target identifier (if any active ingestion loop exists).
  - Last processed source section.
  - Target cluster alignment variables.
  - Active operating mode setting (Ingestion or Query).
  - Current systemic status tracking parameter (`in-progress`, `paused`, or `idle`).

- **Step 2**: Open and read the master configuration index `wiki/index.md` to load active data cluster paths and calculate baseline entity tallies.

- **Step 3**: If state tracking returns a status value matching `in-progress`, print the continuation query to console output:

  ```
  Resume ingestion of [source-id] from [section]?
  Respond with: resume | restart | different task
  ```

- **Step 4**: If state tracking returns a status value matching `idle`, output the master system routing directory to console:

  ```
  Wiki ready. Available modes:
  
  INGESTION:
    @anja ingest [path]  - Begin new source ingestion
    @anja resume          - Continue paused ingestion
    @anja status          - Current wiki state
  
  QUERY:
    @alex design [scenario]   - Solution design guidance
    @alex ask [question]      - General query
  
  MAINTENANCE:
    @sarah queue         - View pending update proposals
    @sarah audit [cluster]    - Run quality audit
  ```

## Behavioural Guidelines and Execution Rules

### Think Before Acting: Pre-emptive Uncertainty Escalation

Agents are blocked from making assumptions; if an asset or parameter contains ambiguous formatting or conflicting entries, immediately halt standard execution and surface options to the user.

- **During Entity Extraction Sweeps**: If text boundaries overlap or terminology maps to multiple potential configurations, detail the variance textually and escalate.
- **During Cluster Allocation Runs**: If metadata indicators intersect across core engine rules and platform services, present alternate mapping strategies instead of choosing silently.
- **During File Architecture Updates**: If newly mined text parameters directly contradict established Tier 1 specification text, stop processing and flag the contradiction block.

> ❌ **Prohibited Execution**: Silently overwriting historical prose text to resolve source contradictions without user confirmation is strictly forbidden.

*Example of correct alignment behavior*:

> **System Exception: Uncertainty Detected** > Terminology signature "Tax Withholding" discovered within the active source section. This element matches multiple structural layout parameters:
>
> 1. Instantiate a new standalone concept profile page.
> 2. Append as a technical subsection within the existing `[[Tax Calculation]]` page.
> 3. Register as an identical synonymous identifier pointing to `[[Tax Deduction at Source]]`.
>
> *Recommended Action*: Option 2 matches block context criteria; awaiting verification instructions.

### Simplicity First: Grounding and Speculation Prevention

Agents must confine documentation changes to facts explicitly recorded within the text payload data; adding speculative interpretations or links is blocked.

- Do not generate stub pages for background terms mentioned only in passing.
- Do not infer systemic interfaces or dependencies if text sources do not record an explicit data flow.
- Do not build cross-cluster related links unless explicit documentation validates the connection pattern.

> 📋 **The Canonical Test**: Every textual claim, table entry, or code path populated on a specification page must map with absolute fidelity back to a specific, verifiable source passage.

### Surgical Updates: Text and Integrity Preservation

When editing pre-existing Tier 1 entries, modify only the exact lines corresponding to data contributed by the incoming source section.

- Do not alter or re-write established summary blocks unless the new document segment explicitly contradicts the historical text.
- Do not alter the structural ordering or framework of a page unless instructed by a master configuration command.
- Do not re-word or clean up sentences from previous ingestion cycles for stylistic purposes.

### Goal-Driven Processing Model

Agents must broadcast a structured execution blueprint to the console interface prior to executing extraction scripts:

```
Processing: [source section]
Target cluster: [cluster name]
Expected entities: [list after initial scan]
Verification: Extraction report before commit
```

### Page Granularity Standard

Tier 1 pages are authored at MEDIUM concept-level granularity (~800–1,200 tokens), one focused concept per page. Consolidate related procedures/sub-topics under a master concept; do not emit stub pages for passing mentions; split any page that exceeds the token band. Goal: maximise Tier 1 query resolution so retrieval rarely falls through to Tier 2 — lowering query-time token cost and downstream curation.

## Source Ingestion and Verification Checkpoints

The mechanical flow of incoming source data through the processing pipeline follows a rigid progression:

```
@anja ingest [path] → Entity Extraction → Page Generation → Registry Logging → Index Rebuild → Dana Verification (rework loop if needed) → Source Archival → Complete Status
```

### Mandatory Extraction Verification Block

Anja must print this identical verification array to console output at the conclusion of every source ingestion:

```
=== VERIFICATION CHECKLIST ===
- [ ] Each concept has explicit source support
- [ ] No speculative relationships added
- [ ] Entity boundaries are clear
- [ ] No over-extraction of passing mentions

Awaiting confirmation. Respond with: confirm | correct: [guidance] | skip
```

Execution is locked at this checkpoint; the ingestion pipeline will pause until explicit human confirmation is injected into the command interface.

## Clean Core and Compliance Constraints

Every agent command and configuration guide must match these structural mandates:

### 1. The Pragmatic Clean Core Law

> "Decouple the Experience; Protect the Engine."

- All Contract Accounts Receivable and Payable transaction postings, BRFplus business calculation rules, tax calculations, and FPF financial form routines must reside natively within the S/4HANA PCE engine core; there are no exceptions.
- SAP BTP platform footprint configurations are limited to user engagement layers, dashboard analytics, cross-system process orchestration, and isolated interface extensions.
- Propose no architectural patterns replicating or duplicating tax liability or financial posting calculations side-by-side within external BTP custom logic layers.
- Interface models must connect via official, stable released OData, SOAP, or RFC endpoints; building unreleased hooks or custom table calls outside the core is barred.

## Claude Code Memory System

### Location

```
wiki/memory/                        ← visible inside this project (symlink)
~/.claude/projects/                 ← actual storage read by Claude Code
  <your-project-key>/
    memory/
```

`wiki/memory/` is a symlink to the hidden `.claude` directory. Files exist in one place only — edits made in either location are the same file.

### Memory File Types

| **Type**    | **What it stores**                                                              |
| ----------- | ------------------------------------------------------------------------------- |
| `user`      | User role, expertise level, working preferences.                                |
| `feedback`  | Behavioural rules: what to avoid, what to repeat, confirmed non-obvious choices. |
| `project`   | Active work context, decisions, deadlines, in-flight initiatives.               |
| `reference` | Pointers to external systems (Linear, Grafana, Slack channels, etc.).           |

### Current Memory Files

The live, authoritative roster is `wiki/memory/MEMORY.md` — the index loaded automatically at every session start, one line per memory file. **Do not maintain a duplicate list here**: a hand-copied roster drifts out of date as memories are added or pruned. To see the current set, read `MEMORY.md`.

### Rules

- Domain knowledge (SAP concepts, BTP configuration, TRM/PSCD) belongs in `wiki/pages/` — not here.
- Behavioural rules, agent permissions, and workflow preferences belong here — not in wiki pages.
- To add a memory: tell Claude Code directly ("remember that…") or write a file here following the frontmatter schema.
- `MEMORY.md` is the index — keep it under 200 lines; one line per entry.