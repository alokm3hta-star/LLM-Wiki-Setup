# ADT Editor Bridge (MCP)

A thin VS Code extension that hosts a localhost MCP server exposing exactly two tools, `write_source` and
`read_source`, so a terminal MCP host (Claude Code / "Paul") can write and read ABAP source in an
editor-opened ADT object. It gives Paul the one verb SAP's official ADT MCP Server deliberately omits.

**It is on-policy** because it calls only VS Code public APIs (`vscode.workspace.fs.writeFile/readFile`)
against the `abap:` URI; VS Code routes that to SAP's own official ADT `FileSystemProvider`, which performs
the backend I/O via SAP's native client. This extension never calls `/sap/bc/adt/` REST. See
`adt-editor-bridge-extension-SPEC.md` and `ADR-001-adt-editor-bridge.md`.

> **New here? Start with [`INSTALL.md`](INSTALL.md)** for the full step-by-step setup: installing this
> extension, registering both MCP servers (the official SAP ADT one and this bridge), the VS Code settings,
> and the terminal commands. The `setup-template/` folder is a sanitised per-destination workspace to copy.

Governance: Aaron (on-policy, Dev-only, 6 conditions) + Adrian (technically sound; two preconditions),
2026-07-03.

## Prerequisites

- VS Code with the official **SAP ADT extension** (`sapse.adt-vscode`) installed, active, and **connected**
  to your Dev destination.
- Node.js + npm (to build).
- Claude Code CLI (to register and consume the server).

## Build

```bash
cd "adt-editor-bridge"
npm install
npm run build        # esbuild bundles src/extension.ts -> dist/extension.js (CJS; bundles the ESM MCP SDK)
npm run typecheck    # optional: tsc --noEmit
```

## Run it (dev)

Open this folder in VS Code and press F5 (Extension Development Host), or package with `vsce package` and
install the `.vsix`. On startup it opens the "ADT Editor Bridge" output channel and logs the listen URL.

## Configure (required)

Settings → search "ADT Editor Bridge":

- `adtEditorBridge.devSystemAllowlist`: array of **Dev** destination IDs allowed for write/read, e.g.
  `["YOUR_DEV_DEST"]`. Empty means everything is refused. This is the Dev-only guard.
- `adtEditorBridge.port`: localhost port (default `3939`).

## Register with Claude Code

```bash
claude mcp add --scope user --transport http adt-editor-bridge http://127.0.0.1:3939/mcp
```

Then in a Claude Code session the tools are `mcp__adt-editor-bridge__write_source` /
`mcp__adt-editor-bridge__read_source` (load via ToolSearch, like the ADT MCP tools).

## The write-persistence spike (do this first)

Prove the programmatic write persists before trusting it in a workflow. Target `$TMP` so no transport is
needed (Adrian Risk B):

1. In Claude Code, via the **official** ADT MCP server, create a `$TMP` class skeleton
   (`abap_creation-create_object`, empty `transportRequestNumber`). Keep the returned `abap:` URI.
2. Call `write_source` (this extension) with that URI and a real class body.
3. Call `read_source` with the same URI; confirm the body you wrote comes back.
4. Via the official server, `abap_activate_objects` then `abap_run_unit_tests`.
5. Confirm in VS Code (open the object) that the source persisted to the backend.

Then repeat against a transported package object to exercise the transport precondition.

## Guardrails honoured

- Only `write_source` + `read_source`. No other tools (Aaron Condition 3).
- Dev-only guard on `uri.path.split("/")[2]` against the allowlist; refuses dotted/empty destinations.
- No `/sap/bc/adt/` calls; no `abap-adt-api` / `erpl-adt`; do not enable `murbani.vscode-abap-remote-fs`
  in this profile (Adrian Risk F).
- Bound to `127.0.0.1` only. Holds no ADT bearer token (that stays with the official ADT MCP server).

## Known limits

- Stateless Streamable HTTP (POST /mcp). No SSE/GET streaming; fine for request/response tool calls.
- Depends on SAP's undocumented `abap:` scheme/URI contract; re-run the spike after any SAP ADT update
  (Aaron Condition 5).
