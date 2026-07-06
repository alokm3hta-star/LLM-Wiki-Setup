## Specification Registry: Wiki Index

### Operational Objective

Contains the master registry of all knowledge clusters, active agents, and cross-cluster dependencies. This configuration file must be loaded at the initialization of every execution session to establish operational context.

**Last Updated**: fresh install — counts are auto-reconciled by `scripts/build_index.py` after your first ingestion.

## Cluster Registry

The eleven domain clusters below ship pre-defined but empty. Entity counts and Primary Sources populate as you ingest. Add, rename, or remove clusters to match your own corpus.

| **Cluster**      | **Description**                                              | **Entities** | **File**                         | **Primary Sources**            |
| ---------------- | ------------------------------------------------------------ | ------------ | -------------------------------- | ------------------------------ |
| trm-pscd-core    | SAP Tax and Revenue Management; Public Sector Collection and Disbursement | 0 | `clusters/trm-pscd-core.md` | — |
| abap-cloud       | Core ABAP, RAP, CDS, XCO library, Clean Core methodology, ADT tooling, ABAP environment operations | 0 | `clusters/abap-cloud.md` | — |
| cap-dev          | SAP Cloud Application Programming Model (CAP) — Node.js/Java services, OData, multitenancy | 0 | `clusters/cap-dev.md` | — |
| integration-cloud-integration | SAP Integration Suite — Cloud Integration: iFlows, adapters, mappings, EIP, Edge Integration Cell, data integration (SDI/SDQ, SLT), Data Space | 0 | `clusters/integration-cloud-integration.md` | — |
| integration-api-management | SAP Integration Suite — API Management: proxies, policies, products, Developer Hub, Graph | 0 | `clusters/integration-api-management.md` | — |
| integration-suite-core | SAP Integration Suite cross-cutting: provisioning, ISA-M, overview, B2B (Integration Advisor + TPM), Event Mesh, AIF error handling, IAM, Migration Assessment | 0 | `clusters/integration-suite-core.md` | — |
| ilm              | SAP Information Lifecycle Management — archiving, GDPR, data destruction, retention warehouse | 0 | `clusters/ilm.md` | — |
| cloud-alm        | SAP Cloud ALM — project management, test management, change management, operations monitoring | 0 | `clusters/cloud-alm.md` | — |
| s4hana-lifecycle | S/4HANA implementation methodology, ACTIVATE framework, Situation Handling, migration tooling | 0 | `clusters/s4hana-lifecycle.md` | — |
| btp-platform     | SAP BTP platform services: Kyma, CF, security, identity, Work Zone, BAS, datasphere, IAG, ETD | 0 | `clusters/btp-platform.md` | — |
| btp-ai           | SAP BTP AI and intelligent services — Gen AI Hub, ISLM, Behavioural Insights, Joule, MCP, Claude Code; also houses SAP services and support portfolio content when the primary context is Business AI Platform | 0 | `clusters/btp-ai.md` | — |
| real-estate      | SAP Flexible Real Estate Management (RE-FX) — portfolio and contract management, rental accounting, condition-based rent adjustment, service charge settlement, space management, implementation methodology | 0 | `clusters/real-estate.md` | — |

## Agent Registry

| **Agent** | **Role**             | **Specification File**            | **Status** |
| --------- | -------------------- | --------------------------------- | ---------- |
| Alex      | Master Orchestrator  | `wiki/agents/alex-master.md`      | active     |
| Aaron     | Strategic Advisor    | `wiki/agents/aaron-strategy.md`   | active     |
| Adrian    | Technical Validation | `wiki/agents/adrian-technical.md` | active     |
| Anja      | Source Ingestion     | `wiki/agents/anja-ingest.md`      | active     |
| Sarah     | Knowledge Curator    | `wiki/agents/sarah-curator.md`    | active     |
| Dana      | Post-Ingestion Verification | `wiki/agents/dana-validator.md` | active     |
| Kylie     | Source Conversion           | `wiki/agents/kylie-convert.md`  | active     |

## Cluster Relationships

- `trm-pscd-core` is the primary consulting domain; integration points with other clusters should be flagged but not auto-linked.
- `abap-cloud` contains ABAP development content that spans both BTP ABAP Environment and S/4HANA Cloud; cross-links to `trm-pscd-core` arise for PSCD OData/extensibility scenarios.
- `integration-cloud-integration`, `integration-api-management`, and `integration-suite-core` are the three SAP Integration Suite sub-clusters (split from the former `integration` cluster); they interrelate and each cross-links to `btp-platform` (API Management/connectivity) and `trm-pscd-core` (PSCD integration patterns). `integration-suite-core` folds in B2B (Integration Advisor + TPM), Event Mesh, and Assessment until each clears ~8–10 pages, then graduates to its own cluster.
- `ilm` cross-links to `trm-pscd-core` for PSCD archiving objects and to `s4hana-lifecycle` for migration/data lifecycle scenarios.
- `cloud-alm` cross-links to `s4hana-lifecycle` for ACTIVATE methodology and to `btp-platform` for Cloud ALM service provisioning.
- `cap-dev` cross-links to `btp-platform` for BTP service bindings and to `abap-cloud` for RAP/CAP hybrid scenarios.
- `btp-ai` cross-links to `abap-cloud` (ABAP AI SDK, ADT Joule), `btp-platform` (AI Core provisioning), and `trm-pscd-core` (Behavioural Insights/ISLM collections scenarios).

## Pending Work

| **Category**     | **File**                           | **Count** |
| ---------------- | ---------------------------------- | --------- |
| Cross-links      | `wiki/pending/cross-links.md`      | 0 pending |
| Missing pages    | `wiki/pending/missing-pages.md`    | 0         |
| Update proposals | `wiki/pending/update-proposals.md` | 0 pending |
| Retrieval gaps   | `wiki/pending/gap-log.md`          | append-only |


## Statistics

| **Metric**            | **Value** |
| --------------------- | --------- |
| Total entities        | 0         |
| Total pages           | 0         |
| Active clusters       | 12        |
| Pending cross-links   | 0         |
| Pending missing pages | 0         |
| Pending proposals     | 0         |
| Active agents         | 7         |

## Quick Reference

### Session Start Execution Sequence

1. Load this master index file (`wiki/index.md`).
2. For queries, load `wiki/runtime-card.md` (compact) and resolve pages by **grepping `wiki/lookup.md`** — do not load cluster registries (Guardrail #2). Fall through to `wiki/tier2-sections.md` only when Tier 1 is insufficient.
3. Delegate queries via Alex to establish agent orchestration routing.

### Agent Console Commands

- `@alex [query]`: Route query to the master orchestrator for allocation.
- `@aaron [topic]`: Dispatch strategic and advisory questions directly.
- `@adrian [topic]`: Extract explicit technical execution and configuration details.
- `@anja [action]`: Trigger source ingestion operations.
- `@sarah [action]`: Trigger targeted wiki curation and maintenance operations.

### Ingestion Routines

- `@anja ingest raw/[file] to cluster [name]`: Full ingestion pipeline.
- `@anja pending`: List files awaiting ingestion.
- `@anja status`: Show current processing metrics.

### Curation Routines

- `@sarah propose [topic]`: Force generation of a new wiki update proposal.
- `@sarah audit [cluster]`: Initiate an automated quality and compliance loop.
- `@sarah gaps`: Summarise the retrieval gap log (`wiki/pending/gap-log.md`) to prioritise curation.
- `@sarah queue`: Surface the active queue of pending update proposals.

## Working Folders

| **Folder** | **Purpose**                                          |
| ---------- | ---------------------------------------------------- |
| `Review/`  | Live solution documents for review against the wiki. |
| `scratch/` | Development utilities and automation scripts.        |
