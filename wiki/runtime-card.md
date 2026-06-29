# Wiki Runtime Card — Query Mode hot-load

**Load this for every query — not the full `LLM wiki.md`.** The rest of the master config (ingestion protocol, schema, behavioural-ingestion rules, memory docs) is loaded only by Anja/Sarah in Ingestion/Maintenance mode.

## Retrieval — index-first, in order

1. **GREP `wiki/lookup.md`** for the query's keywords AND any technical identifiers (T-codes, tables, reports — e.g. `ML_CONFIG`, `DFKKOP`). Use its `## Entities` section to resolve an exact code → page. **Never load a cluster registry (`wiki/clusters/*.md`) at query time** — the index replaces it (Guardrail #2).
2. **READ only the 1–3 pages** the index points to (Tier 1, `wiki/pages/`). Prefer `★`-marked canonical pages.
3. **Cross-cluster:** follow the `## Edges` section of `wiki/lookup.md`. The index spans all clusters, so multi-cluster queries need no extra loads.
4. **Fallthrough only if Tier 1 is insufficient:** GREP `wiki/tier2-sections.md` → read the exact `file:line-range` slice of a `raw_processed/` source (never the whole file).
5. **Absent from all tiers →** state `KNOWLEDGE GAP: [topic]`. Never infer.

## Two tiers

| Tier | Source | ~cost | Cite |
|------|--------|-------|------|
| 1 | `wiki/pages/` | ~800 | `(wiki: page.md, Tier 1)` |
| 2 | `raw_processed/` (slice via `tier2-sections.md`) | ~4,200 whole / low if sliced | `(source: file.md, L#, Tier 2)` |

## Query classes — Alex always fans out to both (always-both rule)

Every `@alex` query — lookup, validation, or design — fans out to **both** Aaron (strategy) and Adrian (technical) before synthesis; never answer inline from retrieval alone, even for a single fact. The class sets pre-fetch breadth and which lens leads, not whether both run:

- **lookup** (single fact) → pre-fetch the 1–3 resolving pages; both agents confirm against them (Adrian leads the technical fact, Aaron checks any governance angle).
- **validation** → **completeness sweep**: grep the cluster/concept prefix in `lookup.md` to pull **all** candidate pages, confirm the claim across all of them, and separate **CONFIRMED / NUANCE / KNOWLEDGE GAP**. Both agents apply their lens. **Never assert a negative from a single hit.**
- **design** → full Aaron + Adrian fan-out over all clusters the design touches.

## Flow

Alex decompose → **dispatch Aaron ∥ Adrian in parallel** (both Agent calls in one turn; serialise only when one genuinely depends on the other's output) → Alex reconciles cross-questions from the two returns, runs one bounded challenge round only if a contradiction survives (a full design review or a shared-boundary disagreement) → Alex synthesise → user; append any Tier-2 hit or KNOWLEDGE GAP to `wiki/pending/gap-log.md`, and one row per query to `wiki/pending/retrieval-log.md` (Sarah reviews via `@sarah gaps`).

## Grounding — non-negotiable

- Every claim maps to a cited source passage; no speculation, no invented links.
- Cross-cluster links on pages stay flagged `[?INTEGRATION:]`; **traversal uses the index `## Edges`, not auto-rendered page links** (Guardrail #5).

## Clean Core — governs Aaron

- *"Decouple the Experience; Protect the Engine"*: FI-CA postings, BRFplus rules, tax calc, FPF forms stay in the S/4HANA PCE core; BTP = experience / orchestration / analytics only. Integrate via released OData / SOAP / RFC.
