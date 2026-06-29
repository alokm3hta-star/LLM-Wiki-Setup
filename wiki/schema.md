## Specification Registry: Wiki Page Schema

### Operational Objective

Defines the required structural models, syntactic validation rules, and extension blocks governing all knowledge assets across the wiki workspace directories. This file serves as the definitive architecture definition for page parsing and generation.

**Last Updated**: 2026-06-04 (added SAP Integration Suite artefact schema: Integration Suite Page Extension, Technical Artefacts subsections, formatter rows, render styles)

## File Naming Conventions

The ingestion engine and agent routines enforce uniform structural names based on asset classifications:

| **Type**                 | **Pattern Syntax**  | **System Example**         |
| ------------------------ | ------------------- | -------------------------- |
| **Wiki pages**           | `kebab-case.md`     | `clearing-control-fica.md` |
| **Cluster registries**   | `[cluster-name].md` | `fica-operations.md`       |
| **Agent specifications** | `[name]-[role].md`  | `anja-ingest.md`           |

**S8 — Page title standard**: The page `# Title` must be the canonical concept name in Title Case. Do not prefix with a series or document name using a colon separator (e.g., ✓ "Claude Code Key Bindings", ✗ "Claude Code Tips: Key Bindings"). The kebab-case filename must derive directly from the title.

## YAML Frontmatter (Mandatory)

Every page in `wiki/pages/**` MUST begin with a YAML frontmatter block, before the `# Title`. It is the source from which the retrieval index (`wiki/lookup.md`) is generated, and it powers Obsidian search/tags/graph:

```
---
cluster: [cluster-name]
aliases: ["Full Page Title", "alternate concept name"]
keywords: [lowercase, searchable, terms]
tags: [cluster-name]
summary: "One-line summary (machine copy of the body **Summary**)."
entities: ["TCODE", "TABLE", "BADI_NAME"]   # key technical artefacts
---
```

Generate/refresh with `scripts/add_frontmatter.py` (idempotent — skips pages that already have it). The body `**Summary**`, `**Cluster**`, etc. remain below for human reading. After any page add/edit, re-run `scripts/build_index.py` so the index reflects the change.

**S4 — Summary specificity standard**: A summary must name the specific mechanisms, artefacts, or capabilities covered — not just the topic category. ✗ Bad: "A reference guide to key bindings in Claude Code." ✓ Good: "Claude Code exposes terminal shortcuts for auto-accepting edits (Shift+Tab), stopping mid-task (Escape), dropping to bash (!), and persisting preferences (#) — none visible in the UI by default." The body `**Summary**` and frontmatter `summary:` must be identical.

**S5 — Alias richness minimum**: At least 3 aliases per page. Include: (1) the full page title exactly as written, (2) at least one alternate formulation (abbreviation, acronym, or practitioner shorthand), (3) at least one use-case or question form (e.g., "how to resume a Claude Code session", "auto-accept edits mode"). Aliases are the primary retrieval surface — more is better.

**S6 — Keyword quality minimum**: Minimum 8 keywords. Include: technical names exactly as they appear in source (tool names, command names, config keys), action verbs (configure, enable, deploy, monitor, trigger), and use-case scenario terms (onboarding, parallel execution, debugging). Avoid generic category labels without qualifiers ("integration", "setup"). Keywords power retrieval — specificity directly improves query hit rate.

**S2 — `entities` never blank**: `entities` must never be an empty array `[]`. SAP content: populate with primary T-codes, tables, BAdIs, role collections, iFlow/adapter names, etc. Non-SAP content (BTP services, AI tools, external platforms): populate with the primary tool or service name (e.g., `["claude-code"]`, `["SAP Build Apps"]`, `["Joule"]`). Pure-concept pages with no named technical entity: use the concept's canonical identifier (e.g., `["clean-core-principle"]`). An empty `entities` array is a schema violation and a Dana hard-gate error.

**`entities` on Integration Suite pages**: populate with the **concrete identifiers present on the page** — role collections, technical names, service paths (e.g. `["Integration_Provisioner", "APIManagement.SelfService.Administrator"]`) — not artefact *type* words like `IFLOW`/`ADAPTER`. Note: `build_index.py` builds the entity index from **body backtick tokens** (via `is_code()`), not from this array — the array powers Obsidian/human reading, while the retrieval levers are body-backtick rendering (see Technical Render Styles) plus `keywords`/`aliases`. Only **single-token** technical names index as entities; multi-word display names (e.g. `Content Modifier`) do not, so record the artefact's technical name in backticks where one exists.

## Standard Master Page Template

Every standard documentation asset must compile the mandatory **YAML Frontmatter** block (above) followed by headers and sections in the following chronological sequence:

Markdown

```
---
cluster: [cluster-name]
aliases: ["Full Page Title"]
keywords: [searchable, terms]
tags: [cluster-name]
summary: "Machine copy of the Summary below."
entities: ["TCODE", "TABLE"]
---

# [Page Title]

**Summary**: [Two to three sentences synthesising the core concept. This should be understandable without reading the full page.]

**Cluster**: [[cluster-name]]

**Sources**: 
- chunk-filename-1.md
- chunk-filename-2.md

**Last updated**: YYYY-MM-DD

---

## Overview

[Expanded explanation of the concept. This section provides context and foundational understanding.]

## Technical Artefacts

[Include this section when any technical artefacts exist. Omit subsections that have no content.]

### Transactions

| T-Code | Description |
|--------|-------------|
| `[TCODE]` | [description] |

### Fiori Apps

| App ID | Name | Description |
|--------|------|-------------|
| `[Fnnnn]` | [App Name] | [description] |

### Configuration

**IMG Path**: 
```

[Full IMG path starting with SPRO]

```
### Authorisation

| Auth Object | Description | Key Fields |
|-------------|-------------|------------|
| `[AUTH_OBJ]` | [description] | [field1], [field2] |

### Data Model

**Tables**:

| Table | Description |
|-------|-------------|
| `[TABLE]` | [description] |

**CDS Views**:

| View | Description |
|------|-------------|
| `[VIEW]` | [description] |

### Enhancements

| Type | Name | Description |
|------|------|-------------|
| BAdI | `[BADI_NAME]` | [description] |
| User Exit | `[EXIT_NAME]` | [description] |

### Integration

**APIs**:

| Service | Type | Description |
|---------|------|-------------|
| `[API_PATH]` | OData/RFC/SOAP | [description] |

**IDocs**:

| IDoc Type | Description |
|-----------|-------------|
| `[IDOC]` | [description] |

### Archiving

| Archiving Object | Description | Retention |
|------------------|-------------|-----------|
| `[ARCH_OBJ]` | [description] | [period if known] |

### Programs & Functions

| Type | Name | Description |
|------|------|-------------|
| Report | `[REPORT]` | [description] |
| FM | `[FUNCTION]` | [description] |

### Messages

| Class | Number | Text |
|-------|--------|------|
| `[CLASS]` | `[NNN]` | [message text] |

### Support

**OSS Notes**:

| Note | Description | Relevance |
|------|-------------|-----------|
| [number] | [description] | [why relevant] |

## Details

[S3 — Mandatory: one `### [Name]` subsection per distinct concept/feature/artefact with non-obvious behaviour. A reference table alone does not satisfy this standard. Exemption: omit a subsection only when the table row is self-evident. See "Content Depth Standard" section below.]

[S7 — Every prose claim must end with `(source: filename.md)`. A subsection with no citation is incomplete.]

### [Subsection Title]

[What it does — one sentence.]

**When to use** (if non-obvious):
- [Scenario]

**Caveats** (if any):
- [Limitation]

(source: [source-filename].md)

### [Subsection Title]

[Content with inline citation: (source: source-filename.md)]

## Related Pages

[S9 — Aim for at least 2 entries. If only 1 genuine intra-cluster link exists, add a `[?INTEGRATION:]` marker for the most likely cross-cluster concept. If truly standalone, add `<!-- standalone — no related pages identified -->` rather than leaving empty.]
- [[related-concept-1]]
- [[related-concept-2]]
- [[related-concept-3]]
- [?INTEGRATION: [cross-cluster-concept]]
```

## Content Depth Standard

### `## Details` subsections are MANDATORY

Every distinct concept, feature, shortcut, or artefact on a page **must** have its own `### [Name]` subsection in `## Details`. The **only** exemption: omit a subsection when the table row is entirely self-evident (the description already says everything useful). A reference table alone does not satisfy this standard.

**Mandatory subsection structure** (include only elements that have content):

```markdown
### [Name]

[One sentence: what it does / what it is.]

**When to use** (if non-obvious):
- [Scenario 1]
- [Scenario 2]

**Caveats / prerequisites** (if any):
- [Limitation or condition]

(source: [filename].md)
```

### `## Overview` vs `## Details` — scope boundary

| Section | Purpose | Approximate cap |
|---|---|---|
| `## Overview` | Context, purpose, when to use the concept overall | ~200 words |
| `## Details` | Operational specifics — one subsection per feature/artefact | No limit |

Do not put operational specifics in `## Overview`. Do not duplicate Overview context in `## Details`.

### Minimum subsection count

- Single-concept pages: at least 2 named subsections in `## Details`.
- Multi-artefact/feature pages: one subsection per artefact with non-obvious behaviour.

Dana checks for subsection presence: TABLE-ONLY `## Details` routes to Sarah as an advisory; absent `## Details` section is a hard-gate error.

## Technical Artefacts — Non-SAP Pages

For pages covering non-SAP content (BTP services, AI tools, external platforms) where no T-codes, Fiori apps, tables, BAdIs, or Integration Suite artefacts exist, **replace** the `## Technical Artefacts` block with the following single line rather than omitting or filling it with empty tables:

```
No SAP technical artefacts — this page covers [tool/concept] without T-codes, tables, or integration objects.
```

Do not silently omit the section; do not fill it with empty subsection tables.

## Cluster-Specific Metadata Extensions

### 1. SAP TRM/PSCD Page Extension

**MANDATORY for all `trm-pscd-core` pages** — all 5 fields required; no page in this cluster may omit this block. Inject immediately following the `Sources` array field:

- **T-Codes**: [List of relevant transaction codes; or "N/A" if none]
- **IMG Path**: [Configuration path in SAP IMG starting with SPRO; or "N/A" if not applicable]
- **Process Area**: [One of: Tax Calculation; Revenue Recognition; Collections; Disbursement; Posting; Contract Management; Correspondence; Integration]
- **S/4HANA Status**: [One of: Available; Modified from ECC; Deprecated; New in S/4HANA; Unknown]
- **Jurisdictions**: [Specific administrative jurisdictions if applicable; or "All" for universal applicability]

### 2. SAP BTP Page Extension

**MANDATORY for all `btp-platform` and `btp-ai` pages** — all 4 fields required; no page in these clusters may omit this block. Inject immediately following the `Sources` array field:

- **Service**: [BTP service name as it appears in the official SAP BTP cockpit]
- **Service Category**: [One of: Application Development; Integration; Data and Analytics; AI; Security; User Experience]
- **Documentation Version**: [Specific version number or formal documentation release date if identifiable]
- **Integration Points**: [Related upstream/downstream BTP services or external engines; or "Standalone" if none]

### 3. S/4HANA Lifecycle Page Extension

**MANDATORY for all `s4hana-lifecycle` pages** — all 3 fields required; no page in this cluster may omit this block. Inject immediately following the `Sources` array field:

- **Lifecycle Phase**: [One of: Assessment; Preparation; Migration; Optimisation; Operations]
- **Applicable Transitions**: [One of: Greenfield; Brownfield; Selective Data Transition; All]
- **Tools Referenced**: [SAP migration/management tools explicitly mentioned; or "N/A"]

### 4. Roadmap Content Extension

**MANDATORY for any page incorporating predictive roadmap documentation** — all 4 fields required plus the warning notice; omit only when the page contains no roadmap content. Append immediately beneath the cluster extension fields:

- **Extraction Date**: YYYY-MM-DD
- **Feature Status**: [One of: Delivered; Planned; Exploratory]
- **Target Release**: [Release identifier or GA timeline if known; or "Unspecified"]
- **Roadmap Source**: [Specific roadmap documentation catalog or URL repository section]

> ⚠️ **Roadmap Notice**: This content reflects forward-looking roadmap specifications as of the extraction date; SAP product roadmaps are subject to frequent change; verify parameters against current official release notes before committing to implementation patterns.

### 5. SAP Integration Suite Page Extension

**MANDATORY for all `integration-cloud-integration`, `integration-api-management`, and `integration-suite-core` pages** — all 4 fields required (including the derived `Capability`); no page in these clusters may omit this block. Inject immediately following the `Sources` array field:

- **Capability**: [derived classification — see vocabulary below]
- **Runtime**: [One of: Cloud Foundry; Edge Integration Cell; Neo (deprecated); N/A]
- **Deployment Scope**: [One of: Tenant-level; Artifact-level; N/A]
- **Security Level**: [One of: Transport-level (TLS/mTLS); Message-level (PGP/signature); Both; N/A]

**Capability** is mandatory on every page in these three clusters — it carries most of the in-cluster routing. It is a **derived classification** (like `Process Area`/`Service Category` above), assigned from the page's cluster + dominant artefacts rather than quoted verbatim, so it is always available even when the source does not state it:

- `integration-api-management` → **API Management**
- `integration-cloud-integration` → **Cloud Integration** (or **Open Connectors** for the Open Connectors catalogue)
- `integration-suite-core` → by the dominant artefact present: Queues/Topics/Webhooks/Message Clients → **Event Mesh**; MIG/MAG/Type Systems → **Integration Advisor**; Trading Partners/Agreements → **Trading Partner Management**; provisioning/role assignment → **Provisioning & Setup**; keystores/certificates/destinations/Cloud Connector → **Connectivity & Security**; monitoring/AIF error handling → **Operations & Monitoring**; ISA-M → **Methodology & Advisory**; suite overview/reference architecture → **Suite Overview**; assessment tooling → **Integration Assessment**/**Migration Assessment**; genuinely cross-cutting with no single capability → **N/A — Foundational**.

The controlled vocabulary is single-sourced in the machine-readable block below; `scripts/validate_wiki.py` parses this exact block (with an internal fallback if it is absent), so keep it in sync with the derivation rules above:

```capability-vocab
Cloud Integration
Open Connectors
API Management
Event Mesh
Integration Advisor
Trading Partner Management
Provisioning & Setup
Connectivity & Security
Operations & Monitoring
Methodology & Advisory
Suite Overview
Integration Assessment
Migration Assessment
N/A — Foundational
```

> `integration-event-mesh` and `integration-b2b` are **not** separate clusters: Event Mesh and B2B (Integration Advisor + Trading Partner Management) are Capability values inside `integration-suite-core`, graduating to their own `integration-*` cluster only once each clears ~8–10 pages (see memory `project-integration-cluster-split`).

## Technical Artefacts — Integration Suite Subsections

For pages in the three `integration-*` clusters, the `## Technical Artefacts` block uses the capability-grouped subsections below **in place of** the ABAP subsections (Transactions, Fiori Apps, CDS Views, Enhancements, etc.), which are omitted per "Omit Empty Elements". Maintain subsection order: Cloud Integration → API Management → Event Mesh → B2B → Cross-Cutting. The heading `### Role Collections` (already used on existing pages) is an accepted alias for the Cross-Cutting **Authorisation** table.

### Cloud Integration

#### Integration Flows

| iFlow | Technical Name | Description |
|-------|----------------|-------------|
| `[Name]` | `[technical_name]` | [description] |

#### Integration Packages

| Package | Technical Name | Description |
|---------|----------------|-------------|
| `[Name]` | `[technical_name]` | [description] |

#### Adapters

| Adapter | Direction | Protocol | Description |
|---------|-----------|----------|-------------|
| `[Type]` | Sender/Receiver | [HTTPS/SFTP/OData/JMS/...] | [description] |

#### Flow Steps

| Step | Category | Description |
|------|----------|-------------|
| `[Step Name]` | Message Transformer / Routing / Call / ... | [description] |

#### Enterprise Integration Patterns

| Pattern | Description |
|---------|-------------|
| `[Pattern]` | [description] |

#### Mappings

| Mapping | Type | Description |
|---------|------|-------------|
| `[Name]` | Message Mapping / Value Mapping | [description] |

#### Data Stores

| Data Store | Scope | Description |
|------------|-------|-------------|
| `[Name]` | Local / Global | [description] |

#### Variables & Parameters

| Name | Type | Description |
|------|------|-------------|
| `[Name]` | Global Variable / Local Variable / Externalized Parameter | [description] |

#### Scripts

| Script | Language | Description |
|--------|----------|-------------|
| `[filename]` | Groovy / JavaScript | [description] |

### API Management

#### API Proxies

| Proxy | Technical Name | Service Type | Description |
|-------|----------------|--------------|-------------|
| `[Name]` | `[technical_name]` | REST / OData / SOAP | [description] |

#### API Providers

| Provider | Description |
|----------|-------------|
| `[Name]` | [description] |

#### Policies

| Policy | Flow | Description |
|--------|------|-------------|
| `[Policy Name]` | PreFlow / PostFlow / Conditional / PostClientFlow | [description] |

#### Products & Applications

| Object | Type | Description |
|--------|------|-------------|
| `[Name]` | Product / Application | [description] |

#### Subscriptions

| Subscription | Product | Description |
|--------------|---------|-------------|
| `[Name]` | `[Product]` | [description] |

### Event Mesh

#### Queues

| Queue | Description |
|-------|-------------|
| `[namespace/name]` | [description] |

#### Topics

| Topic | Description |
|-------|-------------|
| `[hierarchical/topic/path]` | [description] |

#### Webhook Subscriptions

| Subscription | Target | Description |
|--------------|--------|-------------|
| `[Name]` | [endpoint] | [description] |

#### Message Clients

| Client | Description |
|--------|-------------|
| `[Name]` | [description] |

### B2B (Integration Advisor / Trading Partner Management)

#### Message Implementation Guidelines (MIG)

| MIG | Version | Type System | Description |
|-----|---------|-------------|-------------|
| `[Name]` | [version] | EDIFACT / ASC X12 / ... | [description] |

#### Mapping Guidelines (MAG)

| MAG | Source → Target | Description |
|-----|-----------------|-------------|
| `[Name]` | `[source]` → `[target]` | [description] |

#### Type Systems

| Type System | Description |
|-------------|-------------|
| `[Name]` | [description] |

#### Trading Partners

| Partner | Role | Description |
|---------|------|-------------|
| `[Name]` | [role] | [description] |

#### Agreement Templates

| Template | Description |
|----------|-------------|
| `[Name]` | [description] |

### Cross-Cutting (any cluster; predominantly `integration-suite-core`)

#### Security Material

| Artefact | Type | Description |
|----------|------|-------------|
| `[alias / name]` | Keystore Entry / Key Alias / Key Pair / X.509 Certificate / Root Certificate / Client Certificate / PGP Public Key / PGP Secret Key / SSH Key / Known Hosts | [description] |

#### Credentials

| Name | Type | Description |
|------|------|-------------|
| `[Name]` | OAuth2 Client Credentials / User Credentials / Secure Parameter / API Key | [description] |

> Record the **name/alias only** — never the secret, key value, or token.

#### Authorisation

| Role Collection / Access Policy | Type | Description |
|---------------------------------|------|-------------|
| `[Name]` | Role Collection / Access Policy | [description] |

#### Connectivity

| Artefact | Type | Description |
|----------|------|-------------|
| `[Name]` | Destination / Cloud Connector (Location ID) / Virtual Host / On-Premise System | [description] |

#### Content Transport

| Transport Option | Description |
|------------------|-------------|
| CTS+ / Cloud TMS / MTAR Download / Manual Export-Import | [description] |

## Technical Artefacts Section Validation Rules

### Structural Integration Thresholds

The `## Technical Artefacts` block must generate if any structural system footprint (T-codes, Fiori apps, tables, CDS views, BAdIs, function modules, API services, archiving structures, messages, or notes) is present within the parsed source data.

### Subsections Management Matrix

- **Omit Empty Elements**: Empty tables are barred; remove the subsection container entirely if no specific configurations or parameters of that category exist.
- **Chronological Section Alignment**: Subsections must maintain the exact order mapped in the master layout model (Transactions, Fiori Apps, Configuration, Authorisation, Data Model, Enhancements, Integration, Archiving, Programs and Functions, Messages, Support).

### Integration Suite Artefact Rules

These apply to pages in the `integration-cloud-integration`, `integration-api-management`, and `integration-suite-core` clusters (see "Technical Artefacts — Integration Suite Subsections").

- **Generation Threshold**: The `## Technical Artefacts` block must generate if any Integration Suite artefact (iFlow, package, adapter, flow step, EIP, mapping, data store, variable/parameter, script, API proxy/provider/policy/product/application/subscription, queue, topic, webhook, message client, MIG, MAG, type system, trading partner, agreement template, security material, credential, role collection, access policy, destination, transport option) is present in the parsed source.
- **Omit Empty Elements**: As with the ABAP subsections — remove any subsection whose table would be empty.
- **Integration Section Order**: Within an integration page keep the subsection order Cloud Integration → API Management → Event Mesh → B2B → Cross-Cutting (this replaces the ABAP subsection order for these pages).
- **Quality of Service**: Where an iFlow's QoS is stated, record it as a flow attribute (`Exactly Once` / `At Least Once` / `Best Effort`), not as a standalone artefact.

### Granular Formatter Validation Constraints

| **Technical Target** | **Mandatory Formatting Pattern**                            | **Syntactic Valid Example** | **Syntactic Invalid Example**    |
| -------------------- | ----------------------------------------------------------- | --------------------------- | -------------------------------- |
| **T-Code**           | 2-20 characters; uppercase alphanumeric; accepts `/`        | `FP06`, `/SAPSLL/MENU`      | `fp06` (lowercase error)         |
| **Fiori App**        | String matches pattern `Fnnnn` or `Fnnnnn` exactly          | `F0711`, `F12345`           | `0711` (missing prefix)          |
| **Auth Object**      | Uppercase characters with underscore boundaries             | `F_KNA1_BUK`                | `f_kna1_buk` (lowercase error)   |
| **Table**            | Uppercase characters; starts with a letter or `/` symbol    | `DFKKKO`, `/SAPSLL/TBL`     | `dfkkko` (lowercase error)       |
| **CDS View**         | Enforces root prefix `I_`, `C_`, `A_`, `P_`, or `Z`         | `I_BillingDocument`         | `BillingDocument` (no prefix)    |
| **OSS Note**         | Purely numerical string bounded between 7 and 10 digits     | `3045678`                   | `SAP Note 3045678` (string junk) |
| **IMG Path**         | Verifies root customising string initiates with `SPRO`      | `SPRO > FA > ...`           | `IMG > FA` (missing root)        |
| **BAdI**             | Uppercase characters only with tracking underscores         | `BADI_FICA_CLEARING`        | `BAdI Clearing` (casing/space)   |
| **Function Module**  | Uppercase characters only with tracking underscores         | `FKK_CLEARING`              | `fkk_clearing` (lowercase error) |
| **Report**           | Uppercase characters starting with letter `R`, `Z`, or `Y`  | `RFKKOP00`, `ZFICA_REP`     | `rfkkop00` (lowercase error)     |
| **IDoc**             | Uppercase text block; structural sequence numbers allowed   | `INVOIC02`                  | `Invoic02` (casing error)        |
| **API Path**         | Absolute path structure initiating with a forward slash `/` | `/sap/opu/odata/...`        | `sap/opu/odata` (missing slash)  |
| Integration Flow | Title Case display or technical name; reference in backticks | `Replicate_Cost_Centers` | replicate cost centers (unquoted prose) |
| Adapter | Protocol token uppercase + direction word | `SFTP Receiver`, `OData Sender` | sftp adapter (lowercase, no direction) |
| Flow Step | Title Case palette name | `Content Modifier`, `Splitter` | content modifier (lowercase) |
| Enterprise Integration Pattern | Title Case from EIP catalogue | `Aggregator`, `Recipient List` | aggregator step (lowercase + suffix) |
| Mapping | Title Case artefact name | `Invoice_to_IDoc` | invoice mapping (descriptive, not name) |
| Data Store | Title Case name + scope (Local/Global) | `OrderCache (Global)` | order cache (lowercase, no scope) |
| Externalized Parameter | Double-brace enclosure | `{{Receiver_Host}}` | Receiver_Host (missing braces) |
| API Proxy | Title Case / technical name | `BusinessPartner_API` | businesspartner api (lowercase, spaced) |
| Policy | Title Case from fixed policy list | `Spike Arrest`, `Verify API Key` | spikearrest (no spacing/casing) |
| Product / Application | Title Case name | `Partner_Gold_Plan`, `MobileBankingApp` | gold plan (lowercase) |
| Queue | Namespaced lowercase path | `myqueue/orders` | MyQueue Orders (casing/space) |
| Topic | Hierarchical slash-separated path | `sap/order/created/v1` | sap.order.created (dot-separated) |
| MIG | Standard message name + version | `ORDERS D.96A` | orders d96a (lowercase, no version dot) |
| Type System | Standard name, uppercase where canonical | `EDIFACT`, `ASC X12` | edifact (lowercase) |
| Keystore / Key Alias | Alias string in backticks | `sap_cloudintegrationcertificate` | (the certificate file contents) |
| Role Collection | One or more capitalised tokens separated by `.` or `_`, **or** PascalCase; in backticks | `AuthGroup.API.Admin`, `Integration_Provisioner`, `MonitoringDataRead` | authgroup.api.admin (lowercase) |
| Access Policy | Title Case name | `Restricted_Artifacts` | restricted (lowercase) |
| Destination | Title Case name | `S4_OnPremise` | s4 onpremise (lowercase, spaced) |
| API Key / Credential | Name only, never the value | `app_consumer_key` | (the actual key/secret value) |

### Technical Render Styles

- **Inline Technical Codes**: Display wrapped in backticks (e.g., `FP06`, `F_KNA1_BUK`, `DFKKKO`).
- **IMG Pathways**: Render inside an isolated markdown code block.
- **SAP Notes**: Render as clear unformatted numerical digits; include anchor links if external registry connection is established.
- **Secrets**: Names/aliases of keystores, key pairs, credentials, OAuth clients, and API keys are rendered in backticks; the **secret material itself (key values, tokens, passwords, certificate bodies) is never reproduced**, even if present in a source.
- **Topics & Queues**: Render the full hierarchical path in backticks exactly as defined (preserve slashes and namespace), e.g. `sap/order/created/v1`, `myqueue/orders`.
- **Externalized Parameters**: Render with their double-brace syntax in backticks: `{{Parameter_Name}}`.

## Content Inconsistencies and Conflict Documentation

If data retrieved across disparate ingestion units reveals direct functional contradictions, agents must compile a conflict matrix directly preceding the `## Related Pages` block:

Markdown

```
## Conflicting Information

This page contains information from sources that present different statements on certain points.

| Topic | Statement A | Source A | Statement B | Source B |
| :--- | :--- | :--- | :--- | :--- |
| [Subject] | [Claim from first source] | chunk-a.md | [Different claim from second source] | chunk-b.md |

**Resolution Status**: [One of: Awaiting user review; Resolved: version difference; Resolved: context-dependent; Resolved: source A supersedes]

[If resolved, explain the technical or contextual resolution here.]
```

## Data Provenance and Citation Formats

### Standard Source Citation

**S7 — Mandatory**: Every prose claim in `## Details` subsections must end with `(source: filename.md)`. This is not optional. A subsection with no citation is incomplete. For single-source pages, one citation per subsection is sufficient; for multi-source pages, cite per claim where sources differ.

Prose claims must link to their explicit source via trailing inline notes:

Markdown

```
Contract accounts store business partner financial relationships (source: fica-book-003).
```

### Multi-Source Association

Markdown

```
Payment lots group items for processing (source: fica-book-007, fica-docs-012).
```

### Curation Lifecycle Shunting

When Sarah processes raw source sections to promote the text elements into the curated Tier 1 domain index, the citation appends structural lineage indicators:

Markdown

```
(source: fica-book-003 [T2→T1])
```

## Inter-Wiki Reference Syntax

- **Intra-Cluster Pointers**: Connect local files using standard wiki-link notation strings: `[[Concept Name]]`.
- **Cross-Cluster Boundaries**: Flag unverified interface relationships using integration tokens to prevent automated mapping breakages: `[?INTEGRATION: This concept may relate to [[Target Concept]] in cluster-name cluster]`.
- **External Registries**: Document external web links via explicit unverified tags: `[External: Description](URL) [UNVERIFIED]`.

