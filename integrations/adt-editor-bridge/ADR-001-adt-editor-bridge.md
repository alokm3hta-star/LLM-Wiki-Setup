# ADR-001: ADT Editor-Bridge extension for Paul's source-write step

- **Status**: Accepted (Dev-only), 2026-07-03
- **Deciders**: user (owner); Alex (orchestrator); Aaron (governance); Adrian (technical)
- **Supersedes**: nothing. Complements the official SAP ADT MCP Server; does not replace it.

## Context

SAP's official ADT MCP Server (for VS Code) exposes no source-write or source-read tool. Per SAP's own
"Scenario: Agentic Loop" docs, `create_object` makes only a skeleton and the implementation is written by
"the built-in edit tool from MCP host (Not from ADT MCP Server)". Claude Code ("Paul") is a terminal MCP
host whose Edit/Write tools write OS files only; it cannot edit VS Code virtual `abap:` documents (confirmed
via claude-code-guide vs Anthropic docs). So Paul can drive every official MCP tool but cannot perform the
one source-edit step. Off-policy bridges (`abap-adt-api`, `erpl-adt`, direct `/sap/bc/adt/` REST) are banned
by SAP API Policy v4/2026.

## Decision

Build a thin VS Code extension that hosts a localhost MCP server exposing exactly two tools, `write_source`
and `read_source`. Their handlers call **VS Code public APIs only** (`vscode.workspace.fs.writeFile/readFile`)
against the `abap:` URI. VS Code routes those to SAP's **official ADT `FileSystemProvider`**, which performs
the backend persistence via SAP's bundled native client. Paul connects as an MCP client and gains the
missing verb; his harness, grounding, TDD, and orchestration are unchanged.

We chose this over: (a) an `abap-adt-api`/ADT-REST bridge — off-policy; (b) adopting Cline/Roo — loses
Paul's harness; (c) accepting the manual relay indefinitely — slower and not autonomous.

## Support boundary (Aaron Condition 4)

| Component | Owner | Support / escalation |
|---|---|---|
| VS Code editor + extension API (`workspace.fs`, `WorkspaceEdit`) | Microsoft | VS Code channels |
| Official ADT extension, `abap:` FileSystemProvider, native `Adt-ls.app` client, ADT REST to backend | SAP | SAP support (ADT for VS Code); the REST is entirely SAP's code |
| This `adt-editor-bridge` extension (glue: MCP host, 2 tools, Dev guard, error mapping) | us (the team) | our own repo/issues; not an SAP-supported component |
| ABAP backend `YOUR_DEV_SYS` (Dev) | SAP / basis | normal system support |

**Incident routing**: failures inside `writeFile`/`readFile` or logon/transport behaviour trace to SAP's ADT
extension → SAP channel. Failures in tool registration, the Dev guard, the HTTP host, or error mapping →
our extension → our repo. We never patch or call SAP internals to "fix" a backend issue.

## Conditions of use (from Aaron; all mandatory)

1. **No direct ADT REST, ever** — the whole write flows through the FileSystemProvider. Verified: `sap/bc/adt`
   appears 0× in the SAP extension JS; REST lives in SAP's native binary, not our path. Our code contains no
   HTTP client to the backend.
2. **Dev-only, enforced in the extension** — destination = `uri.path.split("/")[2]`, checked against
   `devSystemAllowlist`; dotted/empty destinations and empty allowlist are refused.
3. **Scope = `write_source` + `read_source` only** — any further tool requires a fresh governance review.
4. **This ADR** documents the support boundary — done.
5. **Upgrade-impact check** — after any SAP ADT extension update, re-run the `$TMP` write→read round-trip
   before trusting it (the `abap:` scheme is an undocumented cross-extension contract).
6. **No token in our transport** — the official ADT MCP bearer token is never accessed or relayed here; the
   two MCP servers stay separate; this server binds `127.0.0.1` only and holds no credential.

## Consequences

- **Positive**: Paul's loop becomes MCP-closed for a terminal host, on official channels; the manual relay
  disappears for Dev work; no off-policy dependency; Paul is undiluted.
- **Negative / accepted**: a custom extension to maintain; dependence on SAP's undocumented `abap:` contract
  (mitigated by Conditions 5 + the smoke test); two procedural preconditions Paul must satisfy first —
  transport assignment (non-`$TMP`) and destination logon.
- **Boundaries**: Dev systems only; never Production. Any productive use voids this ADR and needs re-review.

## Open items before first active use

- Live `$TMP` write→read round-trip proving persistence (see README).
- Populate `devSystemAllowlist` with the Dev destination ID(s).
