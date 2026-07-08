# LLM Wiki: Starter Kit

A living, grounded SAP knowledge base powered by a team of specialised AI agents running inside Claude Code. Feed it your documents; ask it anything; trust every answer because every answer is cited.

## The Series

This project, and the thinking behind it, is documented in a five-part series:

- [Part 1: I built an AI that refuses to guess](https://www.linkedin.com/pulse/part-1-i-built-ai-refuses-guess-alok-mehta-epdue/)
- [Part 2: Seven AI agents and the harness that keeps them honest](https://www.linkedin.com/pulse/seven-ai-agents-harness-keeps-them-honest-alok-mehta-7nnye/)
- [Part 3: Texting my SAP knowledge base on WhatsApp](https://www.linkedin.com/pulse/part-3-texting-my-sap-knowledge-base-whatsapp-alok-mehta-rab4e/)
- [Part 4: I asked it for ABAP, and it refused to guess the BAPI](https://www.linkedin.com/pulse/part-4-i-asked-abap-refused-guess-bapi-alok-mehta-bbs1e/)
- [Part 5: Did anyone ask Joule for on-premises? I built the add-on that does similar](https://www.linkedin.com/pulse/part-5-did-anyone-ask-joule-on-premises-i-built-add-on-alok-mehta-8s97e/)

---

## Table of Contents

1. [What Is This?](#1-what-is-this)
2. [A Quick Word on Claude Code and AI Agents](#2-a-quick-word-on-claude-code-and-ai-agents)
3. [The Big Picture: How Everything Connects](#3-the-big-picture)
4. [Meet the Agent Team](#4-meet-the-agent-team)
5. [The Full Pipeline: From PDF to Answered Query](#5-the-full-pipeline)
6. [The Knowledge Clusters](#6-the-knowledge-clusters)
7. [Sarah's Curation Workflow](#7-sarahs-curation-workflow)
8. [How Alex Manages Aaron and Adrian](#8-how-alex-manages-aaron-and-adrian)
9. [The Guardrail System](#9-the-guardrail-system)
10. [The AI Harness](#10-the-ai-harness)
11. [The Scripts Engine](#11-the-scripts-engine)
12. [Integrations](#12-integrations)
13. [Folder Structure](#13-folder-structure)
14. [Command Reference](#14-command-reference)
15. [Getting Started](#15-getting-started)

---

## 1. What Is This?

The LLM Wiki is a **grounded knowledge base** for SAP consulting. "Grounded" means it will only tell you things it has actually read; it never invents answers from the AI's general training data. Every response is cited to a specific page and section.

It works like a very well-organised team of consultants who have read all your documents, remember everything, never hallucinate, and can be questioned at any time.

You feed it source material: SAP documentation, training transcripts, technical books, internal guides, community blogs, and policy documents. It reads them, extracts the knowledge into structured wiki pages, indexes everything for fast retrieval, and then answers questions and validates technical claims, all from what it has actually been shown and never from guesswork.

As of the reference build this starter kit was taken from, the wiki held **over 1,280 pages across 12 SAP knowledge clusters**, covering everything from TRM/PSCD tax processing to SAP Integration Suite, BTP platform services, ABAP Cloud development, ILM data archiving, Flexible Real Estate Management (RE-FX), and SAP's Joule AI capabilities.

---

## 2. A Quick Word on Claude Code and AI Agents

**If you are new to AI, start here.**

**Claude** is an AI assistant made by Anthropic. Think of it like a very capable consultant you can have a conversation with: you type questions or instructions and it responds.

**Claude Code** is the version of Claude that runs directly in your terminal or inside VS Code. Unlike a web chat interface, Claude Code can read files on your computer, run scripts, write new files, and take multi-step actions, all while you watch. It is the engine that powers this entire wiki.

**An AI agent** is Claude operating with a specific persona, a specific set of rules, and a specific job. Instead of one generic AI doing everything, you have multiple specialised agents, each trained on their role. One agent knows how to ingest documents. Another knows how to answer strategy questions. Another checks the quality of the first agent's work. They work as a team.

This wiki runs **eight agents**. They each have a name, a voice, a philosophy, and a clearly defined responsibility. They hand work to each other. They check each other's output. And they are all governed by guardrails that prevent them from making things up.

---

## 3. The Big Picture

Here is the entire system in one flow:

```
You have a document
        │
        ▼
┌───────────────┐
│  other_sources│  ← Drop PDFs, PPTXs, large Markdown files here
└───────┬───────┘
        │  @kylie convert [file]
        ▼
┌───────────────┐
│     raw/      │  ← Clean, split Markdown parts ready for ingest
└───────┬───────┘
        │  @anja ingest raw/[file] to cluster [name]
        ▼
┌─────────────────────────┐
│  wiki/pages/[cluster]/  │  ← Structured Tier-1 knowledge pages
│  wiki/clusters/*.md     │  ← Cluster registries updated
│  wiki/sources.md        │  ← Source registry updated
└───────┬─────────────────┘
        │  scripts/build_index.py (automatic)
        ▼
┌───────────────┐
│  wiki/lookup.md│  ← Master retrieval index (grep-only; never full-read)
└───────┬───────┘
        │  @dana verify (automatic after every ingest)
        ▼
┌───────────────┐
│  Dana: PASS?  │  ── FAIL ──► Anja reworks ──► repeat (max 3 rounds)
└───────┬───────┘
        │  PASS
        ▼
┌─────────────────────────────────────────────────┐
│  @alex ask                                      │
│  Alex → Aaron (strategy) + Adrian (technical)  │
│  → synthesised, cited answer back to you        │
└─────────────────────────────────────────────────┘
        │  Over time, Sarah monitors quality
        ▼
┌──────────────────────────────────────────────┐
│  @sarah audit / approve-all / research-gaps  │
│  Sarah enriches, links, and closes gaps      │
└──────────────────────────────────────────────┘
```

Every step is automated. Every agent hands off to the next. You interact mainly at the top (dropping in documents) and at the bottom (asking questions). Everything in between runs itself.

That covers the knowledge track. A second track runs in parallel for delivery: Paul reads the same `wiki/lookup.md` for grounding, but writes code, not pages, and never touches `wiki/pages/`.

```
┌───────────────┐
│  wiki/lookup.md│  ← Same master index Paul reads for grounding, step 1 of his ladder
└───────┬───────┘
        │  @paul scan [object] / a development task
        ▼
┌────────────────────────────────────────────┐
│  Paul's verification ladder                 │
│  lookup.md → live [MCP] introspection →     │
│  [SAP] published docs → extraction request  │
│  (never a guess)                            │
└───────────────────┬────────────────────────┘
                    │  write path (explicit; never a silent swap)
           ┌────────┴────────────────────┐
           ▼                             ▼
┌──────────────────────┐  ┌────────────────────────────┐
│ Path A (default)     │  │ Path B (bounded, opt-in)   │
│ ADT MCP Server, Dev  │  │ abapGit-serialised src +   │
│ only; in-system ABAP │  │ abaplint CI on the PR;     │
│ Unit / ATC / activate│  │ no MCP; in-system verify   │
│ (or local repo, CAP) │  │ PENDING a human pull       │
└──────────┬───────────┘  └──────────────┬─────────────┘
           └────────┬────────────────────┘
                    ▼
┌────────────────────────────────────────────┐
│  External code workspace                    │
│  Test-first ABAP/RAP/CAP; never wiki/pages/ │
└───────────────────┬────────────────────────┘
        │  newly-verified facts, every hand-off
        ▼
┌────────────────────────────────────────────┐
│  Write-back request → Alex relays it to     │
│  Anja → next task cites it from the wiki    │
│  instead of re-checking live                │
└────────────────────────────────────────────┘
```

The two tracks share only the wiki: the knowledge track writes it, Paul reads it, and Paul's write-backs are the one bridge back into the knowledge track; they are routed through Alex and Anja like any other source, never written by Paul directly.

---

## 4. Meet the Agent Team

### Alex: Master Orchestrator

**Role:** Alex is the senior partner. He never does deep analysis himself; he decomposes your question, decides which specialist to send it to, waits for their output, resolves any contradictions between them, and synthesises one coherent, cited answer.

**Voice:** Senior partner at a Big 4 consulting firm. Authoritative, collaborative, British English.

**Philosophy:** *"Strategy without execution is hallucination. Execution without strategy is chaos. We deliver both."*

**What Alex can never do:** Invent answers. If Aaron and Adrian both come back with a knowledge gap, Alex surfaces that gap to you and does not fill it with guesswork. Every claim Alex makes in a response must be cited to a specific wiki page and section. The AI's general training knowledge of SAP is explicitly forbidden as a source.

**You interact with Alex using:** `@alex ask`

---

### Aaron: Strategic Advisor

**Role:** Aaron holds the strategic lens. When Alex sends him a question, Aaron reads the relevant wiki pages and assesses the strategic dimension: Clean Core alignment, total cost of ownership, governance implications, and five-year programme risk. He is read-only; he never writes to the wiki.

**What Aaron is good at:** "Is this approach strategically sound?" / "What are the governance risks?" / "Does this align with SAP's Clean Core principles?"

---

### Adrian: Technical Validator

**Role:** Adrian holds the technical lens. He reads the same pages as Aaron but focuses on whether something is technically feasible: are the T-codes correct, is the API released, does the configuration path exist in IMG, is the integration pattern documented?

**What Adrian is good at:** "Will this actually work in the system?" / "Is this API publicly available?" / "Which T-code does this?" / "Is this a released or internal API?"

**The key difference between Aaron and Adrian:** Aaron tells you if the *strategy* is right. Adrian tells you if the *execution* is possible. Alex makes sure you hear both before deciding.

---

### Anja: Source Ingestion Specialist

**Role:** Anja is the archivist. She takes raw Markdown source files and transforms them into structured, indexed, cross-linked wiki pages. She is the engine of knowledge growth.

**Voice:** Methodical, precise, efficient. The clarity of a data engineer and the attention of an archivist.

**Philosophy:** *"Raw knowledge is potential. Structured knowledge is power. I bridge the gap."*

**Anja's nine-step ingest process:**

| Step | What happens |
|------|-------------|
| 1 | Read the source file |
| 2 | Analyse its content structure |
| 3 | Identify page-sized concept boundaries |
| 4 | Extract entities (T-codes, tables, BAdIs, role collections) |
| 5 | Write schema-compliant wiki pages to `wiki/pages/[cluster]/` |
| 6 | Update the cluster registry |
| 7 | Rebuild the retrieval index (`wiki/lookup.md`) |
| 8 | Archive the source file: `raw/` → `raw_processed/` (move, not copy) |
| 9 | Write a log entry to `wiki/log.md` |

Anja never copies source text verbatim. She extracts, structures, and paraphrases, producing Tier-1 knowledge pages that are dense, searchable, and precisely cited to their source.

---

### Kylie: Source Conversion Specialist

**Role:** Kylie is the preprocessor. She sits upstream of Anja. If your source is a PDF, a PowerPoint, or a very large Markdown file, Kylie converts it first (extracting text, normalising headings, stripping copyright boilerplate, and splitting it into appropriately sized parts) and then stages those parts in `raw/` for Anja to ingest.

**Voice:** Methodical, systematic, faithful. The precision of a technical writer and the discipline of a quality engineer.

**Philosophy:** *"Raw knowledge must be legible before it can be useful. I make it so."*

**What Kylie converts:**
- **PDF** → Clean Markdown (via `pymupdf4llm`)
- **PPTX** → Structured Markdown (via `python-pptx`)
- **Large Markdown** → Split parts at section boundaries

Kylie deletes the original from `other_sources/` after verifying all splits are correctly written, leaving no duplicates behind.

---

### Sarah: Curation Specialist

**Role:** Sarah is the editor and librarian. She is not involved in ingestion (that is Anja's job); she comes after, maintaining quality over time. She resolves cross-references, merges duplicate pages, enriches keyword metadata, acts on retrieval feedback, and generates research briefs for gaps that cannot be filled from existing sources.

**Voice:** Thoughtful, precise, quality-focused. The care of an editor and the rigour of a librarian.

**Philosophy:** *"Knowledge unreviewed is knowledge untrusted. I ensure every page earns its place."*

**Sarah's key capabilities:**

| Command | What Sarah does |
|---------|----------------|
| `@sarah queue` | Show all pending curation proposals waiting for your approval |
| `@sarah approve-all` | Execute all pending proposals (no per-item confirmation) |
| `@sarah audit [cluster]` | Deep quality audit of a specific cluster |
| `@sarah research-gaps` | Create research briefs for topics the wiki cannot answer yet |
| `@sarah close-research-gaps` | Check if recent ingestions have resolved any open research briefs |

**Sarah's proposal system:** Sarah never writes to the wiki unilaterally. Every change she wants to make is staged as a proposal (SP-001, SP-002, etc.) in `wiki/pending/update-proposals.md`. You review and approve. This keeps a human in the loop for all curation decisions. See Section 7 for the full workflow.

---

### Dana: Post-Ingestion Verification Agent

**Role:** Dana is the quality gate. Every time Anja finishes ingesting a source, Alex spawns Dana to verify the wiki is genuinely consistent before declaring ingestion complete.

**Voice:** Precise, checklist-driven, calm.

**Philosophy:** *"Ingestion isn't done when the pages are written; it's done when the wiki is verifiably consistent."*

**What Dana checks:**
- Every new page has all required frontmatter fields (`cluster`, `aliases`, `keywords`, `tags`, `summary`; `entities` is advisory, since the entity index is built from page bodies)
- The frontmatter `summary` matches the body `**Summary**` exactly
- The frontmatter `cluster` matches the folder the page is in
- The index counts reconcile (pages in `lookup.md` match `index.md`)
- Cluster extension blocks are present and complete for each page's type
- No near-duplicate titles or broken wikilinks exist

**If Dana fails:** She returns a detailed report. Anja reworks the flagged pages. Dana checks again. This cycle repeats up to three rounds. If it still fails after three rounds, it escalates to you rather than silently passing.

**Dana is strictly read-only.** She reports; she never fixes. All fixes go through Anja (page rework) or Sarah (curation proposals).

---

### Paul: TDD Development Agent

**Role:** Paul is the odd one out on purpose: everyone above is part of the knowledge pipeline (read sources in, answer questions out); Paul is the delivery track. He writes grounded, test-first ABAP, RAP, and CAP code, connecting live to SAP's official ADT MCP Server for ABAP/RAP by default, with a bounded, opt-in abapGit-serialised route (guarded by abaplint CI) as a fallback for estates without MCP reach, or a local repo for CAP. He reads the wiki read-only for grounding (Clean ABAP/OOP-SOLID/TDD/design-pattern rules, RAP/CAP best practice, domain facts) and never writes to `wiki/pages/`; his code goes to an external workspace supplied at invocation.

**Voice:** Disciplined, unshowy, allergic to guessing. The precision of a senior developer who has been burned by unverified assumptions before.

**Philosophy:** *"Code without a failing test first is a guess. An SAP signature without a live check is a second guess. I ship neither."*

**Paul's verification ladder:** rather than ever inventing an SAP method signature, table structure, or API shape, Paul works down a strict ladder until he finds ground truth:

| Step | Source | What it gives Paul |
|------|--------|---------------------|
| 1 | `wiki/lookup.md` | Previously-grounded facts, cited `[T1]`/`[T1-client]` |
| 2 | Live `[MCP]` introspection | Direct read of the real object via the ADT MCP Server |
| 3 | `[SAP]` published docs | Official documentation, cited by URL |
| 4 | Extraction request | If all three fail, Paul emits a structured request for a human to supply the fact; he never fabricates it |

**Write path:** Paul has two ABAP/RAP write paths, explicit and never silently swapped. **Path A (default)** connects through the ADT MCP Server, confirmed against a Dev destination every session (never Production); `integrations/claude-code-eclipse/` (an Eclipse plug-in bridging Claude Code to an ADT-open editor) is the supported connection in this repo, and it gives Paul the full in-system loop: ABAP Unit red-green, ATC, and activation. **Path B (bounded, opt-in)** is for abapGit-managed estates with no MCP reach: Paul serialises test-first ABAP to abapGit files and relies on abaplint CI on the pull request (see Section 12), a strictly weaker path with no in-system test or ATC run until a human pulls the code, so a Path B hand-off marks in-system verification as pending rather than claiming a pass. Path B is chosen explicitly, never as a silent fallback from a failed Path A. For ABAP/RAP he may create and assign transports but never release one; on Path B he commits but never pushes; for CAP he may commit inside the given workspace but never push.

**Wiki write-back duty:** every Paul hand-off includes a `## Write-back requests` section: newly-verified facts (a real signature, a real table structure) get relayed back through Alex to Anja, so the next task cites them from the wiki instead of re-running live introspection.

**You interact with Paul using:** describe the ABAP/RAP/CAP object you want built or reviewed and dispatch him via the Agent tool (see Section 14's Development commands for the one formally documented shorthand, `@paul scan [object]`, used for a TDD-conformance review of code that already exists).

---

## 5. The Full Pipeline

Here is a concrete, step-by-step example of how a source moves through the system.

### Starting point: You have a PDF

Say you have the SAP Help PDF for ILM. Here is exactly what happens.

**Step 1: Drop the PDF into `other_sources/`**

```
other_sources/SAP_ILM_Help.pdf
```

**Step 2: Ask Kylie to convert it**

```
@kylie convert SAP_ILM_Help.pdf
```

Kylie:
- Runs `scripts/convert_pdf.py` (uses `pymupdf4llm`)
- Reads the table of contents and first pages to derive a slug: `sap-ilm-help`
- Splits the content into parts of ~100 pages each (to stay within context limits)
- Writes: `raw/sap-ilm-help-01.md`, `raw/sap-ilm-help-02.md`, ... `raw/sap-ilm-help-23.md`
- Deletes the original PDF from `other_sources/`

**Step 3: Ask Anja to ingest**

```
@anja ingest raw/sap-ilm-help-01.md to cluster ilm
```

Anja reads the part, identifies concept boundaries (Archiving Objects, ILM Store, privacy-driven data deletion, etc.), and writes structured pages:

```
wiki/pages/ilm/ilm-archiving-objects-overview.md
wiki/pages/ilm/ilm-store-configuration.md
wiki/pages/ilm/ilm-data-destruction.md
...
```

Each page has this structure:
```yaml
---
cluster: ilm
aliases: ["ILM Store Configuration", "SAP ILM Store Setup", "how to configure ILM Store"]
keywords: [ilm, store, configuration, retention, archiving, privacy, worm, warehouse]
tags: [ilm]
summary: "ILM Store connects to certified WORM storage via ILM Object Store API..."
entities: ["IRMPAC", "SARE", "IF_ARCH_RAW_DATA_PROVIDER"]
---
```

Followed by a structured body with `**Summary**`, `**Cluster**`, `**Last updated**`, and domain-specific extension fields.

**Step 4: Index rebuilds automatically**

After Anja writes the pages, she runs `scripts/build_index.py`. This generates `wiki/lookup.md`, a flat, grep-optimised index with one line per page:

```
ilm/ilm-store-configuration.md | ★ | ILM Store Configuration | ILM Store connects to certified WORM storage... | kw: ilm store,worm,configuration,... | entities: IRMPAC,SARE,...
```

This file is the retrieval backbone. It is never read in full; it is grepped for keywords, T-codes, or concept names, and only the matching pages are then read in detail.

**Step 5: Dana verifies**

Alex automatically spawns Dana. Dana runs `scripts/validate_wiki.py`, checks every new page, and returns PASS or FAIL with a detailed report. If there are failures, Anja reworks them. If there are advisory findings (not errors), Alex routes those to Sarah as proposals.

**Step 6: Source is archived**

Once Dana passes, Anja runs `scripts/archive_source.sh "raw/sap-ilm-help-01.md"`, which moves (not copies) the file to `raw_processed/`. Sources in `raw_processed/` are immutable after this one-way move.

**Step 7: Repeat for all parts**

Parts 02 through 23 follow the same process. Some parts may yield no new pages if the content is already covered; in that case, Anja runs in delta mode, enriching existing pages rather than creating duplicates.

**Step 8: Query the result**

```
@alex ask What archiving objects are available for PSCD contract accounts, and what is the ILM Store retention configuration approach?
```

Alex:
1. Greps `wiki/lookup.md` for `pscd`, `contract`, `archiving`, `ilm store`
2. Reads the 2-3 most relevant pages
3. Dispatches to Adrian (technical: which specific artefacts, which T-codes)
4. Synthesises one response, citing every claim: `[T1: ilm-archiving-objects-overview.md § PSCD Archiving Objects]`

---

## 6. The Knowledge Clusters

The wiki is organised into 12 clusters. Each cluster covers a distinct SAP domain. Pages live in `wiki/pages/[cluster]/` and are registered in `wiki/clusters/[cluster].md`.

| Cluster | What it covers |
|---------|---------------|
| `trm-pscd-core` | SAP Tax and Revenue Management (TRM); Public Sector Collection and Disbursement (PSCD); FI-CA; form bundle processing; BRFplus tax rules |
| `abap-cloud` | Core ABAP; RAP (RESTful Application Programming); CDS views; ABAP Cloud model; Clean Core methodology; ADT tooling; design patterns; abapGit |
| `btp-platform` | SAP BTP platform services: Kyma, Cloud Foundry, identity (IAS/IPS/IAG), Work Zone, BAS, Datasphere, ETD, SAP ETD, connectivity |
| `btp-ai` | SAP AI services: Gen AI Hub, SAP AI Core, Behavioural Insights, Joule, Claude Code, MCP, autonomous enterprise strategy |
| `integration-cloud-integration` | SAP Integration Suite, Cloud Integration: iFlows, adapters (FTP, IDoc, JDBC, RFC, HTTP), mappings, EIP patterns, Edge Integration Cell |
| `integration-api-management` | SAP Integration Suite, API Management: proxies, policies (KVM, OAuth, CSRF, threat analytics), Developer Hub, Graph |
| `integration-suite-core` | SAP Integration Suite cross-cutting: provisioning, ISA-M methodology, B2B/Integration Advisor, Event Mesh, Migration Assessment |
| `ilm` | SAP Information Lifecycle Management: data archiving, privacy-driven data destruction, ILM Store, retention warehouse |
| `s4hana-lifecycle` | S/4HANA implementation: ACTIVATE methodology, Situation Handling, system conversion (DMO/SUM), migration tooling, output management |
| `cloud-alm` | SAP Cloud ALM: project management, test management, change management, operations monitoring |
| `cap-dev` | SAP Cloud Application Programming Model (CAP): Node.js/Java services, OData, multitenancy |
| `real-estate` | SAP Flexible Real Estate Management (RE-FX): portfolio and contract management, rental accounting, condition-based rent adjustment, service charge settlement, space management, implementation methodology |

Clusters are not rigid silos. The `[?INTEGRATION:]` marker system tracks relationships across clusters that cannot be confirmed without dedicated evidence. Sarah resolves these over time as more sources are ingested.

---

## 7. Sarah's Curation Workflow

Sarah is the quality conscience of the wiki. Here is her complete workflow.

### Proposals: The Change Management System

Sarah never edits wiki pages directly without leaving a trail. Every curation action is first staged as a **proposal** (format: SP-001, SP-002, etc.) in `wiki/pending/update-proposals.md`. Each proposal records:

- What needs changing and why
- Which page and cluster is affected
- What the trigger was (Dana finding, retrieval gap, user query)
- Priority and risk level

You review and approve the queue at your discretion.

### Common Sarah commands

**`@sarah queue`:** Inline command handled without spawning an agent. Shows you the current pending proposals in a quick table.

**`@sarah approve-all`:** Sarah spawns, reads every pending proposal, assesses risk, executes them in order, marks them as `executed`, and updates the index. Low-risk proposals (keyword enrichment, summary fixes) run automatically. Medium-risk proposals (structural cross-links, description updates) run with a brief justification. High-risk proposals (merges, deletions) are flagged for your confirmation before execution.

**`@sarah audit [cluster]`:** Sarah does a deep sweep of a cluster: schema compliance, alias richness, keyword quality, near-duplicate detection, and freshness of sources. Outputs a list of findings as new proposals.

**`@sarah research-gaps`:** Sarah reads `wiki/pending/gap-log.md` (the log of every query that could not be answered from Tier-1 pages) and creates research briefs in `wiki/pending_research/`. Each brief summarises what the wiki already knows about the topic and what is missing, so you know exactly what source to find and ingest next.

**`@sarah close-research-gaps`:** The inverse; Sarah sweeps all open research briefs and checks whether recent ingestions have already resolved them. Resolved briefs are archived to `wiki/pending_research/_resolved/`. Partially covered briefs are downgraded and annotated. This is usually run after a batch ingest.

### The retrieval gap log

Every time Alex fails to answer a query from Tier-1 pages, he appends a row to `wiki/pending/gap-log.md`. This is the primary signal that drives what gets ingested next. A topic that appears in the gap log repeatedly is a high-priority ingestion candidate. Sarah reads this log when generating research briefs.

---

## 8. How Alex Manages Aaron and Adrian

This is the core orchestration pattern. Understanding it shows why the wiki produces better answers than asking an AI directly.

### The problem with asking an AI directly

If you ask an AI "what are the risks of this SAP integration design?" it will answer confidently, drawing on its general training data, potentially citing things that have changed, confabulating details it is not certain of, and mixing strategic opinion with technical fact without making the distinction clear.

### What Alex does instead

When you send Alex a query, here is what actually happens:

**Step 1: Decomposition**

Alex reads your question and identifies two kinds of sub-questions hidden within it:

- *Strategic questions* (alignment, risk, governance, cost): these go to Aaron
- *Technical questions* (feasibility, configuration, specific artefacts): these go to Adrian

For a question like *"Is using the FI-CA payment run for PSCD direct debit a sound approach for a high-volume deployment?"*, Alex identifies:
- Aaron's work: governance alignment, volume/risk pattern, Clean Core stance
- Adrian's work: FI-CA payment run T-codes, batch scheduling parameters, SEPA mandate configuration, PSCD-specific adapter behaviour

**Step 2: Parallel dispatch**

Alex spawns Aaron and Adrian as sub-agents simultaneously. Each reads only the pages relevant to their assigned question, grepping `wiki/lookup.md` first and then reading the 1-3 highest-relevance pages.

**Step 3: Grounded responses only**

Both Aaron and Adrian are under the same grounding contract: if the wiki does not contain the answer, they must say `KNOWLEDGE GAP`, not fill it from training. They cite every claim with page and section.

**Step 4: Synthesis**

Alex receives both outputs and synthesises one response. He:
- Resolves any contradictions (e.g. if Aaron identifies a governance risk that Adrian's technical approach does not account for)
- Escalates genuine disagreements to you rather than silently choosing one
- Produces a single, coherent answer in his own voice; you see Alex rather than Aaron and Adrian separately
- Appends any knowledge gaps to `wiki/pending/gap-log.md`

**Step 5: The output you see**

A synthesised answer with every claim cited: `[T1: pscd-payment-run.md § SEPA Direct Debit Configuration]`. You can open the page and verify the claim yourself. The wiki is not a black box.

---

## 9. The Guardrail System

The wiki enforces quality automatically through a system of hooks: scripts that run at key moments and block bad outcomes.

### How hooks work

Claude Code allows you to attach shell scripts to events. These run automatically; no agent can bypass them. Four hooks protect this wiki:

---

**`guard-raw.sh`: Content immutability for source files**

Fires: *before* any Write or Edit operation on a file.

What it does: Blocks any attempt to edit the content of a file in `raw/` or `raw_processed/`. These directories are sacred; sources may not be rewritten, only read and moved. The one permitted write in `raw/` is Anja's incoming write of new split files. The one permitted mutation in `raw_processed/` is Anja's archive move. Everything else is blocked.

Why: If a source were silently edited after ingestion, the wiki pages derived from it would no longer match what the file actually says. Citation integrity would be broken.

---

**`rebuild-and-verify.sh`: Mandatory validation on every stop**

Fires: when any agent finishes its turn (Stop) and when any sub-agent finishes (SubagentStop).

What it does: If any wiki page was changed during the turn, runs `scripts/build_index.py` (to rebuild `lookup.md`) and then `scripts/validate_wiki.py` (to check consistency). If validation finds errors, it blocks the agent from declaring "done" and feeds the error report back to the model, forcing a rework before the turn ends.

Why: This means no ingestion cycle can complete with broken pages. The validation gate is automatic and non-negotiable.

---

**`mark-index-dirty.sh`: Change tracking**

Fires: after any Write or Edit.

What it does: Creates a flag file (`wiki/.index-dirty`) whenever a page is changed. The `rebuild-and-verify.sh` hook checks for this flag before deciding whether to run. This avoids re-validating the entire wiki when nothing has changed.

---

**`dispatch-subagent.sh`: @-command routing enforcement**

Fires: when you submit a message.

What it does: Checks whether your message contains an @-prefixed agent name (`@anja`, `@sarah`, `@kylie`, etc.). If it does, it ensures the correct sub-agent profile is used, preventing Alex from handling the task himself when a specialist should do it.

Why: Alex orchestrates; he does not do Anja's ingestion work himself. The hook enforces this even if Alex were inclined to try.

---

### The grounding contract

Beyond the hooks, every agent carries a non-negotiable grounding contract:

- **No training knowledge.** Responses must be derived from wiki pages only. The AI's general knowledge of SAP is not a permitted source.
- **Section-level citations required.** Citing a page is not enough; the specific section must be named.
- **KNOWLEDGE GAP logging is mandatory.** If a topic is not in the wiki, it must be logged. Silence is not permitted.
- **KNOWLEDGE GAP cannot be converted into a confident claim.** If Adrian says "I cannot confirm this from the wiki", Alex cannot synthesise it into a confident statement.

---

## 10. The AI Harness

### What is a harness?

Imagine you hired a brilliant but new consultant who knows everything about SAP but has never worked for your firm before. On day one, you give them a company handbook (your standards, your voice, your non-negotiable rules), a specific job description, a morning checklist, and a manager who reviews all client-facing output before it leaves the building.

That is a harness. In this wiki, the harness is the set of files, rules, and automated checks that take a general-purpose AI (Claude) and constrain it into behaving as this specific, grounded, multi-agent knowledge system.

Without the harness, Claude is a capable but unconstrained assistant: it will answer your SAP questions from its training data, mix facts with plausible-sounding invention, and forget everything when you close the session. With the harness, it is Alex, Anja, Sarah, and the rest of the team, each with a specific persona, specific responsibilities, specific things they are not allowed to do, and a persistent shared memory that survives across sessions.

The harness is the difference between "an AI that knows about SAP" and "a grounded knowledge system that only tells you what it has actually read".

---

### The five components of the harness

#### 1. CLAUDE.md: The always-loaded constitution

Every time you open this project in Claude Code, before anything else happens, Claude reads `CLAUDE.md`. This is not optional and cannot be skipped; Claude Code auto-loads it at every session start.

`CLAUDE.md` specifies four things:

**The mandatory boot sequence.** On every session start, the AI must read `wiki/state.md` (current ingestion status), read `wiki/index.md` (cluster counts and statistics), and output a structured status block before it answers anything at all. The file marks this "Do not skip, abbreviate, or defer." This ensures the AI always starts with an accurate picture of the wiki's current state, not a cached or hallucinated one.

**The @-command dispatch table.** A lookup table that maps @-prefixed agent names to specific sub-agent profiles. `@anja` must spawn the `anja-ingest` profile; `@sarah` must spawn the `sarah-curator` profile; `@kylie list` is handled inline without spawning. Every routing decision is written down explicitly; Claude cannot improvise who handles what.

**The retrieval protocol.** Agents must grep `wiki/lookup.md` first; they must never load full cluster registry files at query time; they fall through to `wiki/tier2-sections.md` only if Tier 1 is insufficient; they must log every knowledge gap. Grepping and reading individual pages is the only permitted retrieval path.

**The guardrails.** Source immutability (raw files cannot be edited), index auto-rebuild, citation requirements, and KNOWLEDGE GAP logging are all specified here as rules rather than suggestions.

Think of `CLAUDE.md` as the firmware of the wiki. It is the document that turns a general-purpose AI into this specific system.

---

#### 2. Agent profiles: Persona switching at spawn time

The `.claude/agents/` folder contains seven Markdown files, one per agent. When you type `@anja ingest raw/...`, Claude Code looks up `.claude/agents/anja-ingest.md` and loads it as the persona for a new, isolated sub-agent process.

Each profile contains:
- **Identity and voice:** who this agent is, how they speak, and what their philosophy is
- **Responsibilities:** a precise list of what this agent is and is not accountable for
- **Operational procedures:** step-by-step workflows (Anja's nine-step ingest, Dana's verification checklist, Sarah's proposal rules)
- **Grounding contract:** the specific rules the agent must not violate under any circumstances

The profiles are how a single general-purpose AI becomes seven different specialists. Anja is not "Claude pretending to be an ingestion agent"; Anja is a fully specified persona with her own constraints that override Claude's default behaviour for the duration of her sub-agent process.

The `wiki/agents/` folder contains the extended specification documents for the same agents, with fuller procedure detail that profiles can reference for complex operations.

The two-tier structure (lightweight profile in `.claude/agents/` and full spec in `wiki/agents/`) means sub-agents load quickly and only reach for deeper detail when they need it.

---

#### 3. settings.json: The control panel

`.claude/settings.json` is the wiring diagram that connects everything:

```json
{
  "permissions": {
    "allow": ["Bash(rm other_sources/)"]
  },
  "autoMode": {
    "allow": ["$defaults", "Deleting from other_sources/ is sanctioned..."]
  },
  "hooks": {
    "UserPromptSubmit": [{ "command": "dispatch-subagent.sh" }],
    "PreToolUse":       [{ "matcher": "Write|Edit|MultiEdit", "command": "guard-raw.sh" }],
    "PostToolUse":      [{ "matcher": "Write|Edit|MultiEdit", "command": "mark-index-dirty.sh" }],
    "Stop":             [{ "command": "rebuild-and-verify.sh" }],
    "SubagentStop":     [{ "command": "rebuild-and-verify.sh" }]
  }
}
```

**Permissions** grant specific automated operations without requiring a confirmation prompt each time. Kylie is allowed to delete files from `other_sources/` after conversion; this is whitelisted explicitly so the system does not interrupt the pipeline with "are you sure?" on every file deletion.

**autoMode** controls which justifications Claude Code accepts when operating autonomously. This keeps oversight tight on risky actions while allowing routine pipeline steps (conversion, archival, index rebuild) to flow without constant interruption.

**Hooks** register shell scripts against specific Claude Code lifecycle events. This is what makes the guardrails automatic rather than relying on agent self-discipline. An agent cannot bypass a hook; it fires at the system level before the agent's output is accepted.

---

#### 4. The boot sequence: Consistent initialisation every session

Every session begins with the same mandatory sequence, enforced by `CLAUDE.md`:

```
Step 1: Read wiki/state.md
        Extract: Status value, current source, last completion date

Step 2: Read wiki/index.md
        Extract: Every cluster name + entity count
        Extract: Total pages, total entities, all pending item counts

Step 3: Output the status block
        One table row per cluster
        Pending proposals / cross-links / missing pages counts
        @-command menu
        Warning if an ingest is in progress
```

The reason this is mandatory is consistency. If the AI started answering queries without first reading the current state, it might give you counts, statuses, or cluster sizes from a previous session, or from its training data. The boot sequence forces it to observe the actual current state before it says a single word.

---

#### 5. The two-tier retrieval contract

The harness enforces a strict retrieval discipline that stops the AI from scanning the wrong things or burning context on large files it does not need:

```
Query arrives
      │
      ▼
grep wiki/lookup.md           ← Always first. Grep only; never full-read.
      │
      ├─ Hit → read 1-3 pages ← Only the specific pages the index points to
      │
      └─ Miss → wiki/tier2-sections.md (raw source slices as fallback)
                      │
                      └─ Still miss → log KNOWLEDGE GAP to gap-log.md
```

The rule "never load `wiki/clusters/*.md` at query time" is written explicitly in `CLAUDE.md`. The cluster files are summaries and registries, not retrieval surfaces. Grepping the flat lookup index and reading individual pages is the only permitted path.

This matters because context is finite. If an agent loaded the full `btp-platform` cluster file (covering hundreds of pages) every time someone asked a BTP question, it would exhaust most of its available context before getting to the actual answer. The two-tier contract prevents this by design: grep first, read narrowly, and fall through only when necessary.

---

### How the harness components interact

Here is what actually happens under the hood when you run a command:

```
You open the project in Claude Code
           │
           ▼
  CLAUDE.md auto-loads (always, before anything else)
  → Boot sequence runs (reads state.md + index.md)
  → Alex persona is active on the main thread
           │
You type:  @anja ingest raw/sap-ilm-help-01.md to cluster ilm
           │
           ▼
  dispatch-subagent.sh fires  (UserPromptSubmit hook)
  → Validates @anja routing; confirms sub-agent spawn
           │
           ▼
  .claude/agents/anja-ingest.md loads
  → Anja persona is active in an isolated sub-agent process
  → wiki/agents/anja-ingest.md available for deep procedure reference
           │
  Anja writes pages to wiki/pages/ilm/
           │
           ▼
  guard-raw.sh fires  (PreToolUse hook, before each Write/Edit)
  → Is this file in raw/ or raw_processed/?
  → BLOCK if so (source immutability); ALLOW if it is a new wiki page
           │
  mark-index-dirty.sh fires  (PostToolUse hook, after each Write/Edit)
  → Sets wiki/.index-dirty flag
           │
  Anja finishes her sub-agent turn
           │
           ▼
  rebuild-and-verify.sh fires  (SubagentStop hook)
  → Detects .index-dirty flag
  → Runs build_index.py  →  validate_wiki.py
  → PASS:  flag removed; Anja's turn ends cleanly
  → FAIL:  error report fed back to model; Anja must rework before "done"
```

Every step is automatic. The harness means Anja cannot declare "ingestion complete" with broken pages; the hook catches it and forces a rework before the turn closes.

---

### Why this is different from just asking an AI

Most uses of AI are stateless: you ask a question, get an answer, and the next session knows nothing about the last. There is no memory, no shared state, and no quality gate on the output.

This wiki is stateful. The harness maintains persistence across sessions:

| What persists | Where it lives |
|--------------|---------------|
| Ingestion history and current status | `wiki/state.md` |
| Page and entity counts per cluster | `wiki/index.md` |
| Preferences and project decisions | `wiki/memory/` |
| Full operation audit trail | `wiki/log.md` |
| Pending curation proposals | `wiki/pending/update-proposals.md` |
| Topics the wiki cannot yet answer | `wiki/pending/gap-log.md` |

When you open the wiki tomorrow, the agents know exactly what was ingested last week, what proposals are pending, where any paused ingestion left off, and what queries have hit knowledge gaps. The harness is what makes this a persistent, growing system rather than a series of disconnected AI conversations.

---

## 11. The Scripts Engine

The wiki is maintained by a set of Python scripts. These are the automated backbone:

| Script | What it does |
|--------|-------------|
| `scripts/build_index.py` | Scans all pages in `wiki/pages/`, extracts frontmatter and body entities, regenerates `wiki/lookup.md` and updates page/entity counts in `wiki/index.md`. Run after every ingest. |
| `scripts/validate_wiki.py` | Checks every page for schema compliance: mandatory frontmatter fields, summary match, cluster match, count reconciliation. Returns PASS/FAIL with precise error lines. |
| `scripts/build_tier2_index.py` | Indexes all source files in `raw_processed/` by section for Tier-2 fallback retrieval. Run after archiving a source. |
| `scripts/archive_source.sh` | Moves a file from `raw/` to `raw_processed/` (one-way, permanent). Used by Anja at the end of each ingest. |
| `scripts/convert_pdf.py` | Extracts text from a PDF using `pymupdf4llm`, producing clean Markdown. Used by Kylie. |
| `scripts/convert_pptx.py` | Extracts structured content from a PPTX file using `python-pptx`. Used by Kylie. |
| `scripts/add_frontmatter.py` | Idempotent: adds missing frontmatter to any pages that lack it. Safe to run multiple times. |
| `scripts/clean_markdown.py` | Normalises Markdown: heading hierarchy, whitespace, and boilerplate removal. Used during conversion. |
| `scripts/split_markdown.py` | Splits a large Markdown file into sized parts at section boundaries. Used by Kylie for large MD sources. |
| `scripts/patch_frontmatter.py` | Bulk-updates a specific frontmatter field across multiple pages. Used by Sarah for cluster-wide enrichment. |
| `scripts/rotate_archives.py` | Rotates append-growing files (proposals, log, state) into quarterly archives; `--state-gc` prunes completed Stage Plan blocks from `state.md` so each session boots lean. Called automatically by the Stop hook. |
| `scripts/measure_health.py` | Captures a health snapshot (page/entity/edge counts, cluster sizes, pending volumes) into `wiki/pending/health-history.md`. |
| `scripts/check_thresholds.py` | Surfaces soft-threshold warnings (append-file size, cluster page count) at every Stop hook. |
| `scripts/test_wiki_scripts.py` | Smoke tests for the load-bearing `build_index.py` and `validate_wiki.py`. Run: `python3 scripts/test_wiki_scripts.py`. |

---

## 12. Integrations

Three optional integrations sit around the wiki. None is required for the core system (ingestion, query, curation) to work; all live in `integrations/` and ship as sanitised templates you fill in locally.

### Eclipse plug-in: Claude Code for ABAP

A Joule-style Claude Code chat panel docked inside Eclipse/ADT, built as Paul's live write path for ABAP and RAP. It wires a real Claude Agent SDK session to SAP's embedded ADT MCP Server (ATC, unit tests, activation, transport diff) and adds an editor bridge so Claude can read and edit the ABAP source in your open ADT editors directly: no copy-paste, edits appear live in the buffer, are undoable with Cmd+Z, and save/activate through ADT's own pipeline.

**Requirements:** Eclipse 2026-06 with ABAP Development Tools 3.60+ and the ADT MCP Server enabled; Node.js 20+; an authenticated Claude Code CLI session (`~/.claude`); JDK 21 and Maven, only if building from source.

**Security model:** fail-closed on a Dev-only project allowlist, so source read/write is refused unless the open editor resolves to an allowlisted Dev ABAP project; exactly three bridge tools (`read_source`, `write_source`, `get_editor_context`); the ADT MCP bearer token stays in workspace preferences and reaches the sidecar via environment variables only, never on the command line, in logs, or in the UI; the chat UI binds to `127.0.0.1` with a per-launch token; and there is no direct ADT REST access, so all persistence and activation route through ADT's own save pipeline.

**Setup, in short:** build the update-site zip with `mvn clean verify` (or use a prebuilt one), install it via Eclipse's Install New Software wizard, then set your Dev system allowlist under Preferences → Claude Code for ABAP. Full build, install, configuration, and troubleshooting steps: [`integrations/claude-code-eclipse/README.md`](integrations/claude-code-eclipse/README.md). Governance and design rationale: [`docs/ADR-002-eclipse-editor-bridge.md`](integrations/claude-code-eclipse/docs/ADR-002-eclipse-editor-bridge.md).

### abaplint: shift-left quality gate for ABAP

A static-analysis gate that runs abaplint on every pull request of an abapGit-serialised ABAP repository, catching Clean ABAP and syntax issues on GitHub before the code is ever pulled into an SAP system. It needs no SAP system, no runtime, and no subscription; it reads the serialised `src/**` source directly and annotates its findings inline on the pull request. This is the shift-left companion to Paul's delivery track: where the Eclipse plug-in is Paul's in-system write path, this is the pre-merge check for the abapGit route. It is additive to the ABAP Test Cockpit (ATC), not a replacement, because abaplint catches Clean ABAP patterns that ATC covers only partly, earlier and for free.

**Requirements:** a GitHub repository holding abapGit-serialised ABAP under `src/**`; GitHub Actions enabled (the default `GITHUB_TOKEN` is the only secret needed); no SAP connectivity. For the free path on private repositories, use the GitHub Action shipped here (it runs `@abaplint/cli` in your own workflow) rather than the hosted `abaplint.app` app, which is free for public repos but a paid subscription for private ones.

**Setup, in short:** copy `abaplint.json` to your repo root and set `syntax.version` to your backend's SAP_BASIS release (the README carries the SAP_BASIS to S/4HANA mapping); copy `abaplint.yml` into your repository's `.github/workflows/`; open a pull request to see the inline findings; then require the "abaplint (src/**)" check in branch protection to turn it from advice into an enforced gate. Full config, version mapping, licensing and cost notes, and adaptation guidance: [`integrations/abaplint/README.md`](integrations/abaplint/README.md).

### n8n: WhatsApp to Alex

A reference n8n workflow that lets you query the wiki from WhatsApp: send a message, get a grounded, cited answer back from Alex. n8n cannot run the wiki engine directly, so it reaches the machine where the wiki and Claude Code live over SSH and runs Claude Code headless (`claude -p "@alex ask ..."`), which boots the full constitution and guardrails exactly as an interactive session would.

```
WhatsApp message
  -> POST webhook
  -> Fetch Sender        (parse the text and the sender)
  -> "Working, please wait..."   (WhatsApp send, so there is no silence)
  -> Call Alex           (SSH: unlock keychain, then claude -p "@alex ask ...")
  -> Prep Response       (extract the answer between <<<A>>> and <<<Z>>>)
  -> Reply               (WhatsApp send)
```

**Requirements:** a self-hosted n8n instance; a host running the wiki and Claude Code (signed in), with Remote Login (SSH) enabled and kept powered on; a Meta WhatsApp Cloud API app with a WhatsApp Business Account; a public HTTPS endpoint for the webhook.

**Setup, in short:** import `ask-alex.workflow.json`, replace the placeholders (SSH credential and paths, WhatsApp phone number ID and credential), point your Meta webhook at the n8n webhook URL, subscribe the app to your WABA, and use a permanent System-User token rather than a 24-hour test token.

Do not use the official WhatsApp Trigger node: it answers Meta's verification with a generic acknowledgement rather than echoing `hub.challenge`, so verification never passes. This template uses two plain webhook nodes instead. Full setup steps and every hard-won gotcha: [`integrations/n8n/README.md`](integrations/n8n/README.md).

---

## 13. Folder Structure

```
LLM Wiki/
│
├── CLAUDE.md                    ← Operating rules (auto-loaded every session)
├── LLM wiki.md                  ← Constitution and full protocol spec
│
├── .claude/
│   ├── settings.json            ← Hooks configuration
│   └── agents/                  ← Registered agent profiles (8 agents)
│
├── scripts/
│   ├── build_index.py           ← Regenerates wiki/lookup.md
│   ├── validate_wiki.py         ← Schema and consistency checker
│   ├── build_tier2_index.py     ← Indexes raw_processed/ sources
│   ├── archive_source.sh        ← raw/ → raw_processed/ mover
│   ├── convert_pdf.py           ← PDF → Markdown
│   ├── convert_pptx.py          ← PPTX → Markdown
│   ├── add_frontmatter.py       ← Adds missing frontmatter
│   ├── clean_markdown.py        ← Normalises Markdown
│   ├── split_markdown.py        ← Splits large files into parts
│   ├── patch_frontmatter.py     ← Bulk frontmatter updates
│   ├── rotate_archives.py       ← Quarterly archive rotation + state.md GC
│   ├── measure_health.py        ← Health snapshot capture
│   ├── check_thresholds.py      ← Soft-threshold warnings at Stop
│   ├── test_wiki_scripts.py     ← Smoke tests for index + validator
│   └── hooks/
│       ├── guard-raw.sh         ← Blocks edits to source files
│       ├── rebuild-and-verify.sh← Validates wiki on every stop
│       ├── mark-index-dirty.sh  ← Flags when pages have changed
│       └── dispatch-subagent.sh ← Enforces @-command routing
│
├── other_sources/               ← Drop PDFs, PPTXs, large MDs here
│   └── README.md
│
├── raw/                         ← Split, clean Markdown ready for Anja
│   └── README.md
│
├── raw_processed/               ← Archived sources (immutable after move)
│   └── README.md
│
├── Review/                      ← Design docs to review against the wiki
│   └── README.md
│
├── integrations/                ← Optional bridges and gates around the core loop
│   ├── abaplint/                ← Sanitised abaplint CI templates: shift-left Clean ABAP gate on the pull request
│   ├── claude-code-eclipse/     ← Eclipse plug-in: Claude Code ↔ ADT-open editor, for SAP GUI/Eclipse ABAP workflows
│   └── n8n/                     ← Sanitised n8n workflow template: WhatsApp → @alex ask
│
└── wiki/
    ├── index.md                 ← Master registry (clusters, stats, agents)
    ├── state.md                 ← Current ingestion status (read at session start)
    ├── lookup.md                ← Generated retrieval index (grep only)
    ├── tier2-sections.md        ← Generated Tier-2 fallback index
    ├── log.md                   ← Append-only operation log
    ├── sources.md               ← Source registry
    ├── schema.md                ← Page schema and standards
    ├── runtime-card.md          ← Compact query protocol for agents
    │
    ├── agents/                  ← Full agent specification documents
    │   ├── alex-master.md
    │   ├── aaron-strategy.md
    │   ├── adrian-technical.md
    │   ├── anja-ingest.md
    │   ├── sarah-curator.md
    │   ├── dana-validator.md
    │   ├── kylie-convert.md
    │   ├── paul-dev.md
    │   ├── paul-dev-card.md         ← Paul's craft-rules core (Clean ABAP/OOP-SOLID/TDD/patterns)
    │   └── paul-card-packs/         ← Lazily-loaded rule-body packs for paul-dev-card.md
    │
    ├── clusters/                ← Cluster registries (one per domain)
    │   ├── trm-pscd-core.md
    │   ├── abap-cloud.md
    │   ├── btp-platform.md
    │   ├── btp-ai.md
    │   ├── integration-cloud-integration.md
    │   ├── integration-api-management.md
    │   ├── integration-suite-core.md
    │   ├── ilm.md
    │   ├── s4hana-lifecycle.md
    │   ├── cloud-alm.md
    │   ├── cap-dev.md
    │   └── real-estate.md
    │
    ├── pages/                   ← All Tier-1 wiki pages (you add these via Anja)
    │   ├── trm-pscd-core/
    │   ├── abap-cloud/
    │   ├── btp-platform/
    │   ├── btp-ai/
    │   ├── integration-cloud-integration/
    │   ├── integration-api-management/
    │   ├── integration-suite-core/
    │   ├── ilm/
    │   ├── s4hana-lifecycle/
    │   ├── cloud-alm/
    │   ├── cap-dev/
    │   └── real-estate/
    │
    ├── pending/                 ← Curation queues (all append-only)
    │   ├── update-proposals.md  ← Sarah's change proposals (SP-001, SP-002, ...)
    │   ├── cross-links.md       ← Unresolved [?INTEGRATION] markers
    │   ├── missing-pages.md     ← Referenced but not-yet-created pages
    │   ├── gap-log.md           ← Retrieval failures (drives future ingestion)
    │   └── action-items.md      ← Carry-over tasks ready to execute
    │
    ├── pending_research/        ← Research briefs for knowledge gaps
    │   └── _resolved/           ← Retired briefs (gap now covered)
    │
    └── memory/                  ← Persistent session memory (auto-managed)
```

---

## 14. Command Reference

### Ingestion commands

| Command | Who handles it | What it does |
|---------|---------------|-------------|
| `@kylie list` | Alex (inline) | Shows contents of `other_sources/` |
| `@kylie convert [file]` | Kylie | Converts PDF/PPTX/large MD → `raw/` splits |
| `@anja ingest raw/[file] to cluster [name]` | Anja | Full ingest pipeline: read → extract → write pages → index → archive → log |
| `@anja resume` | Anja | Continues a paused ingestion (checks `wiki/state.md` for current position) |
| `@anja status` | Alex (inline) | Shows current state: status, current source, last completion |

### Query commands

| Command | Who handles it | What it does |
|---------|---------------|-------------|
| `@alex ask [question]` | Alex → Aaron + Adrian | General knowledge query; grounded, cited answer |
| `@alex wiki-review` | Alex | Audits the framework for spec/state drift and consistency (stale cluster/state claims, drifted annotations, orphaned spec); reports findings and routes fixes. Read-only audit |

### Curation commands

| Command | Who handles it | What it does |
|---------|---------------|-------------|
| `@sarah queue` | Alex (inline) | Displays pending proposals from `update-proposals.md` |
| `@sarah approve-all` | Sarah | Executes all pending proposals; clears the queue |
| `@sarah audit [cluster]` | Sarah | Quality audit of a cluster; generates new proposals |
| `@sarah research-gaps` | Sarah | Creates research briefs for knowledge gaps in `pending_research/` |
| `@sarah close-research-gaps` | Sarah | Checks whether recent ingestions resolved open research briefs |

### Validation commands

| Command | Who handles it | What it does |
|---------|---------------|-------------|
| `@dana verify` | Dana | Full post-ingest verification pass (also runs automatically after every ingest) |

### Development commands

| Command | Who handles it | What it does |
|---------|---------------|-------------|
| `@paul scan [object]` | Paul | Phase-1 TDD-conformance review of existing ABAP code |
| `@paul scan [object] full` | Paul | All 3 review phases sequentially, reporting findings after each |

Build tasks are not a fixed command: describe the ABAP/RAP/CAP object you want built and dispatch Paul via the Agent tool. He builds test-first on Write Path A (ADT MCP Server, the default) or, for an abapGit-managed estate with no MCP reach, the bounded opt-in Write Path B (abapGit-serialised source checked by abaplint CI); see Section 4.

### Direct specialist commands

| Command | Who handles it | What it does |
|---------|---------------|-------------|
| `@aaron [topic]` | Aaron | Direct strategic query (bypasses Alex synthesis) |
| `@adrian [topic]` | Adrian | Direct technical validation query (bypasses Alex synthesis) |

---

## 15. Getting Started

### Prerequisites

1. **Claude Code** installed; get it at `claude.ai/code` or install via `npm install -g @anthropic-ai/claude-code`
2. **A Claude login for Claude Code.** A Claude Pro or Max subscription is enough: run `claude` once and sign in with `/login`. An Anthropic API key is optional (only if you prefer API-key billing); it is **not** required to run the wiki.
3. **Python 3.9+** for the scripts
4. For PDF conversion: `pip install pymupdf4llm`
5. For PPTX conversion: `pip install python-pptx`

### First session

Open the `LLM Wiki Setup` folder in Claude Code. The `CLAUDE.md` file auto-loads on every session, so the agent team is immediately available.

The boot sequence runs automatically and shows you the current wiki state:
- Status (idle / in-progress / paused)
- Page and entity counts per cluster
- Pending proposals, cross-links, and missing pages

Since this is a fresh install, you will see all zeroes. That is correct.

### Your first ingest

1. Drop a source document into `other_sources/` (if PDF or PPTX) or directly into `raw/` (if already Markdown)
2. If it is a PDF or PPTX, convert it first:
   ```
   @kylie convert [filename]
   ```
3. Ingest the resulting split files:
   ```
   @anja ingest raw/[slug]-01.md to cluster [cluster-name]
   ```
4. Anja will tell you how many pages were created and Dana will verify automatically

### Your first query

Once at least one source has been ingested:
```
@alex ask [your question about SAP]
```

Alex will grep the index, read the relevant pages, dispatch to Aaron and Adrian, and return a cited answer within a few minutes.

### Building up the wiki

The wiki grows with every source you add. The typical workflow is:

1. Identify a source (documentation, training material, technical books, community blogs, policy documents)
2. Convert with Kylie if needed; drop into `raw/`
3. Ingest with Anja into the appropriate cluster
4. Let Dana verify; let Sarah's proposals accumulate
5. Periodically run `@sarah approve-all` to apply curation improvements
6. Run `@sarah close-research-gaps` after batches to retire resolved briefs

Over time, the retrieval gap log (`wiki/pending/gap-log.md`) shows you which topics keep coming up unanswered; these are your highest-priority next ingestions.

---

## A Note on Trust

The most important property of this wiki is its relationship with truth. Every agent is explicitly prohibited from using their training knowledge as a source. Every answer must come from the pages. Every claim must be cited.

This means the wiki gives you less initially: it will say "I don't know" instead of guessing. But it means that when it does answer, you can trust the answer completely, trace it back to its source, and verify it yourself.

A wiki with 50 grounded pages is more valuable than one with 5,000 unverified claims.

---

## Acknowledgements

This project is an implementation of the **"LLM Wiki" pattern** described by **Andrej Karpathy** in [this gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f). The core idea comes from there: rather than a stateless RAG system that re-reads your raw documents on every query, you have the LLM **incrementally build and maintain a persistent, compounding wiki** that sits between you and your sources, organised in three layers (immutable raw sources, an LLM-maintained Markdown wiki, and a schema file such as `CLAUDE.md`), with ingest, query, and lint operations over an `index.md` catalogue and an append-only `log.md`.

This starter kit is one concrete instantiation of that pattern, specialised for SAP consulting and pushed hard towards grounding: a team of eight specialist agents that check each other, section-level citations on every claim, and hook-enforced guardrails with validation on every change. The pattern is Karpathy's; this particular disciplined, multi-agent realisation is what this repository adds.

*A small homage:* the agents are named, with affection, after a team I was once lucky to work with. The names are the tribute; the personalities and mottos are invented for this project, and any resemblance to how they really work is, of course, entirely deliberate.

---

*This starter kit includes the complete agent team, all scripts, all cluster definitions, and all operational files, all reset to zero. The knowledge comes from you.*


---

## Model Tiering in a Multi-Agent Grounded Knowledge Base: A Three-Way Benchmark

A like-for-like comparison of three model configurations answering one identical query through the same multi-agent orchestration framework. The framework routes a user question to an orchestrator (Alex), which fans the work out to specialist sub-agents (a technical validator and a governance reviewer) running in parallel, then synthesises one grounded, cited answer. Only the model tier assigned to the sub-agents changes between runs.

### Executive summary

- **Cost:** the tiered configuration cost roughly half of either full-strength configuration. Moving the full-strength run from the mid tier to the top tier did **not** save money: the top tier used ~38% fewer tokens but its higher per-token price cancelled the saving almost exactly, landing within ~3%.
- **Quality:** both full-strength configurations produced clean, publishable answers with zero factual errors. The tiered configuration, as delivered, produced an answer with two outright errors, one ungrounded claim, and three material omissions.
- **Interpreting the tiered result:** the cost saving is real, but it is concentrated on narrow, single-dimension query classes where a lighter agent can safely carry the load. A mixed technical-and-governance query like this one should run at full strength on both lenses; the tiered errors here reflect a lighter model being asked to carry a governance judgement beyond its competence, not a saving that comes for free.

### Test setup

| Property | Value |
|---|---|
| Query | A single real query drawn from the knowledge base, combining a technical-feasibility question with a governance dimension |
| Query class | Mixed technical-and-governance (the class most sensitive to model tiering, because it needs both precise retrieval and sound judgement) |
| Sub-agents dispatched | Technical validator + governance reviewer, run in parallel |
| Runs | (1) Tiered: mid-tier technical validator + light-tier governance reviewer; (2) Full mid-tier: both agents mid tier; (3) Full top-tier: both agents top tier |
| Variable changed | Sub-agent model tier only; branch, query, and dispatch pattern held constant where possible |
| Verification method | Every distinctive claim in each answer independently fact-checked against the knowledge base pages, verdict CORRECT / WRONG / UNGROUNDED / PARTIAL with quoted evidence |

Model tiers are referred to as **top**, **mid**, and **light** throughout, mapped to their published prices in the pricing reference table below.

### 1. Processing time per agent

Agents run in parallel, so the wall-clock time is approximately the slowest agent plus orchestrator synthesis, not the sum of both agents.

| Configuration | Technical validator (s) | Governance reviewer (s) | Slowest agent (s) | Sum of agent time (s) | Wall-clock |
|---|---|---|---|---|---|
| Tiered (mid + light) | 118.7 | 54.9 | 118.7 | 173.6 | ~2m 25s |
| Full mid-tier | 201.2 | 198.8 | 201.2 | 400.0 | ~3m 44s |
| Full top-tier | 141.1 | 159.4 | 159.4 | 300.5 | ~4m 04s* |

*The top-tier run's wall-clock window is not clean: it included a framework boot sequence and a re-dispatch between the start and end timestamps. The per-agent durations are the reliable figures; on those, the top tier was faster per agent than the mid tier (159.4s slowest vs 201.2s).

### 2. Actual token usage

Figures are total tokens per sub-agent as reported by each agent's own usage block. The orchestrator's own synthesis and the framework boot are not instrumented in two of the three runs and sit on top of every figure below, roughly constant across runs.

| Configuration | Technical validator (tier / tokens) | Governance reviewer (tier / tokens) | Total tokens | Tool calls (total) |
|---|---|---|---|---|
| Tiered | mid / 87,030 | light / 38,733 | 125,763 | 25 |
| Full mid-tier | mid / 96,303 | mid / 103,698 | 200,001 | 41 |
| Full top-tier | top / 58,683 | top / 64,562 | 123,245 | 17 |

### 3. Sonnet-token equivalents (tier-normalised cost units)

Because each tier is priced at a fixed multiple of the mid tier on **both** input and output (top = 5/3× mid; light = 1/3× mid), the per-token cost ratio between tiers is independent of the input/output split and of any cache discount. Normalising every run to mid-tier-equivalent tokens therefore gives a split-independent, cache-independent cost comparison.

| Configuration | Calculation | Mid-tier-equivalent tokens | Relative to mid-tier baseline |
|---|---|---|---|
| Tiered | 87,030 + (38,733 × 1/3) | 99,941 | 50.0% |
| Full mid-tier | 96,303 + 103,698 | 200,001 | 100% (baseline) |
| Full top-tier | 123,245 × 5/3 | 205,408 | 102.7% |

**Read-out:** the tiered run costs exactly half of either full run; the top-tier run costs ~3% more than the mid-tier run despite using fewer raw tokens. These two facts hold under any assumption about the token mix or caching.

### 4. Cost in USD (as if billed via API)

#### Pricing reference (published per-MTok rates)

| Tier | Input ($/MTok) | Output ($/MTok) | Ratio to mid tier |
|---|---|---|---|
| Top | 5.00 | 25.00 | 5/3× on both |
| Mid | 3.00 | 15.00 | baseline |
| Light | 1.00 | 5.00 | 1/3× on both |

#### Estimated cost

Read-heavy agents (each made 8 to 21 tool calls fetching pages), so input dominates. The estimate below assumes a 90% input / 10% output mix at sticker pricing with no cache discount, giving blended rates of top $7.00, mid $4.20, light $1.40 per MTok. A tighter 95/5 mix gives the lower end of each range.

| Configuration | Technical validator ($) | Governance reviewer ($) | Total ($) | Range (95/5 to 90/10) | Relative |
|---|---|---|---|---|---|
| Tiered | 0.37 | 0.05 | **0.42** | 0.36 to 0.42 | 0.50× |
| Full mid-tier | 0.40 | 0.44 | **0.84** | 0.72 to 0.84 | 1.00× |
| Full top-tier | 0.41 | 0.45 | **0.86** | 0.74 to 0.86 | 1.03× |

**Caveats on the absolute figures:** (1) prompt caching typically discounts the compounding input at ~0.1×, so real billed cost is likely one-third to one-half of these numbers; but caching scales all three runs down proportionally, so the ratios are unaffected. (2) These are sub-agent costs only; the orchestrator's synthesis adds a roughly constant amount to each run. The decision-relevant facts are the **2× gap** between the tiered and full runs and the **near-parity** between the top and mid full runs, both of which are robust.

### 5. Quality

Every distinctive claim in each answer was independently verified against the knowledge base pages.

| Dimension | Tiered | Full mid-tier | Full top-tier |
|---|---|---|---|
| Outright wrong claims | 2 | 0 | 0 |
| Ungrounded claims (asserting a negative from a single lookup) | 1 | 0 | 0 |
| Material omissions of documented facts | 3 | 0 | 0 |
| Verified-correct distinctive claims | mixed / partial | 5 of 5 | 6 of 8 (2 soft spots, synthesis not error) |
| Cited-source discipline | broke on 2 or more claims | intact | intact |
| Safe to send to a stakeholder as written | **No** | Yes | Yes |
| Distinctive strength | fastest and cheapest only | tightest verification record; carefully hedged inferences | added grounded governance context; every gap correctly labelled as out of scope |

The two soft spots in the top-tier answer were synthesis (a plausible inference from enumerated facts, and one internally-inconsistent source flattened), not fabrication; the answer left both uncited or explicitly flagged, so neither is a factual error.

### 6. Derived and efficiency stats

| Metric | Tiered | Full mid-tier | Full top-tier |
|---|---|---|---|
| Wall-clock | ~2m 25s | ~3m 44s | ~4m 04s* |
| Total tool calls | 25 | 41 | 17 |
| Tokens per tool call | ~5,031 | ~4,878 | ~7,250 |
| Defect count (wrong + ungrounded + omitted) | 6 | 0 | 0** |
| Cost per client-ready answer | not applicable (answer not client-ready) | ~$0.84 | ~$0.86 |
| Mid-tier-equivalent cost per verified-correct answer | infinite (no clean answer produced) | 200,001 units | 205,408 units |

*Wall-clock window confounded by boot and re-dispatch; per-agent time is the clean measure.
**Two synthesis soft spots, neither a factual error.

**Reading the efficiency numbers:** the top tier reached a clean answer in the fewest tool calls (17) and fewest tokens of any clean run, indicating tighter retrieval rather than brute-force reading; it simply pays more per token. The tiered run's low cost is misleading in isolation because it did not buy a usable deliverable on this query.

### Scope and reproducibility

This is a single query at N=1 per configuration and a single query class; it is a directional benchmark, not a statistically powered study. Two of the three runs carried prompt confounds: the full mid-tier run's dispatch prompts were not recorded, and the top-tier run's dispatch prompts were composed after the mid-tier run's findings were already known, so a portion of the top tier's extra depth is prompt-inherited rather than purely model-driven. The wall-clock figure for the top-tier run is confounded by a boot sequence inside the timing window; per-agent durations are the reliable timing measure. To harden these findings, re-run each configuration at least three times per query class with dispatch prompts logged and orchestrator-level token instrumentation enabled.

### Conclusion

For open-ended queries that combine a technical and a governance dimension, model tiering offers **no quality or cost advantage**: the safe configuration assigns full strength to both the technical and the governance lens. The tiering win is real but confined to the classes the router can classify with high confidence: narrow lookups and clean single-dimension questions, where a lighter tier can safely carry the load. On answer quality alone the two full-strength configurations tie: the mid tier for the tightest verification record, the top tier for added grounded depth, at effectively equal cost. The one clear lesson that generalises: in a tiered multi-agent system, the highest-leverage investment is not the tier assignment but the enforcement and verification layer that guarantees the orchestrator honours its own routing and escalates when a lighter agent reaches beyond its competence.
