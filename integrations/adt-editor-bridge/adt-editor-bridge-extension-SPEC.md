# ADT Editor-Bridge Extension — Build Spec

**Status**: design, pre-build. Drafted 2026-07-03 by Alex (LLM Wiki orchestrator).
**Governance**: on-policy with conditions, Dev-only — verdict by Aaron (aaron-strategy), 2026-07-03.
**Technical**: design sound; go with conditions — verdict by Adrian (adrian-technical), 2026-07-03. Q1
(writable `abap:` provider, no REST in our path) CONFIRMED; Q2 (stability) PARTIAL (functionally stable at
`sapse.adt-vscode-1.0.1` / ADT JARs 3.58.2, no deprecation, but undocumented cross-extension contract); Q3
(no source read/write in the 18-tool set, none roadmapped) CONFIRMED. Blockers are NOT architectural — see
§4a Preconditions (transport + logon).
**Purpose**: give Paul (Claude Code) the one verb SAP's official ADT MCP Server deliberately omits —
writing bespoke ABAP source into an editor-opened object — WITHOUT diluting Paul and WITHOUT an off-policy
ADT-REST/`abap-adt-api` bridge.

---

## 1. Problem this closes

SAP's official ADT MCP Server (for VS Code) has no source-write or source-read tool by design. Per
help.sap.com "Scenario: Agentic Loop", `abap_creation-create_object` makes only a **skeleton**; the actual
implementation is written by "the built-in edit tool from MCP host (Not from ADT MCP Server)" into the
editor-opened object, then `abap_activate_objects` + `abap_run_unit_tests` run.

Claude Code (Paul) is a terminal-first MCP host whose Edit/Write tools write **OS filesystem files only**;
it cannot edit VS Code virtual `abap:` documents (confirmed via claude-code-guide vs Anthropic docs). So
Paul can call every official MCP tool but cannot perform the source-edit step. The gap is one verb, not the
whole agent.

## 2. Design

A thin **VS Code extension that hosts a localhost MCP server** exposing exactly two tools, `write_source`
and `read_source`. The tool handlers run in the extension host (so they hold the `vscode` API) and perform
I/O the native in-editor way, through VS Code's **public** extension API:

```
Paul (Claude Code, MCP client)
   │  mcp call: write_source(uri, content)
   ▼
adt-editor-bridge extension (our code)  ── uses only vscode.* public API ──►  vscode.workspace.fs.writeFile(Uri.parse('abap:/…'), bytes)
                                                                                   │
                                                                                   ▼
                                                         SAP official ADT extension FileSystemProvider (writeFile)
                                                                                   │  SAP's own native client (this.client.sendRequest)
                                                                                   ▼
                                                                          ABAP backend  (SAP does the /sap/bc/adt/ REST, not us)
```

Paul's loop becomes fully closed for a terminal host, all on official channels:
`create_object` (skeleton, official) → **`write_source`** (ours → SAP provider) → `abap_activate_objects`
(official) → `abap_run_unit_tests` (official). Paul's harness, wiki grounding, TDD, and orchestration are
unchanged; he only gains a tool.

### Why this is on-policy (Aaron 2026-07-03)
Our code calls **VS Code public APIs only** (Microsoft's, not SAP's). The SAP-facing REST is performed by
SAP's own shipped ADT provider/native client. This is materially the same mechanism GitHub Copilot and
Joule use, which SAP documents and sanctions as the "MCP host's built-in edit tool". It is categorically
different from the banned `abap-adt-api`/`erpl-adt` bridges, which call `/sap/bc/adt/` REST directly.

## 3. Primary-source evidence (extension inspection 2026-07-03)

Official extension: `sapse.adt-vscode-1.0.1-darwin-arm64`, `main: dist/_bundle/extension.js`.
- Registers a FileSystemProvider: `registerFileSystemProvider(de, this, {isCaseSensitive:true})` — **no
  `isReadonly`, no `isWritableFileSystem:false`** → the `abap:` provider is **writable**.
- `writeFile` is a real implementation:
  `async writeFile(e,t,n){ let r={uri:e.toString(), content:Buffer.from(t).toString("utf8"), options:n};
  try{ await this.client.sendRequest(...) …}` → it delegates to SAP's native client, which does the backend
  write. Not a "not supported" throw.
- `sap/bc/adt` appears **0 times** in the JS bundle (REST lives in the bundled native binary, i.e. SAP's
  code, not ours). This is the structural basis for Aaron's Condition 1.

Remaining empirical step (must run before first real use): a live `write_source` → `read_source` round-trip
against a `$TMP` object, proving the programmatic write persists to the backend end to end.

## 4. Tool contract

### `write_source`
- **params**: `{ "uri": string, "content": string }` — `uri` is the `abap:/repotree-v1/<DEST>/…/<obj>.clas.abap`
  returned by `abap_creation-create_object`; `content` is the full ABAP source for that include.
- **behaviour**: `await vscode.workspace.fs.writeFile(vscode.Uri.parse(uri), Buffer.from(content,'utf8'))`.
  (Fallback if activation needs editor-dirty semantics: open the `TextDocument`, apply a `WorkspaceEdit`,
  `save()`.)
- **returns**: `{ ok: true }` or `{ ok: false, error }`. Does NOT activate — Paul calls
  `abap_activate_objects` next via the official server.
- **guard**: Dev-only (see Condition 2).

### `read_source`
- **params**: `{ "uri": string }`.
- **behaviour**: `new TextDecoder().decode(await vscode.workspace.fs.readFile(vscode.Uri.parse(uri)))`.
- **returns**: `{ ok: true, content }` or `{ ok: false, error }`.

**No other tools.** Everything else (create, generate, transport, activate, unit tests, ATC) stays on the
official ADT MCP Server. Adding any further tool requires a fresh governance review (Aaron Condition 3).

**URIs are never hand-constructed** (Adrian Risk C). `write_source`/`read_source` accept only a URI as
returned by `abap_creation-create_object` (or read from `vscode.window.activeTextEditor.document.uri`).
The native provider derives the destination from `uri.path.split("/")[2]` and rejects a destination
containing a dot, so a malformed/constructed URI will fail; do not build `abap:` paths by hand.

## 4a. Preconditions (Adrian 2026-07-03 — MUST be in the workflow)

Both are enforced by SAP's provider, surface as `FileSystemError`, and a headless MCP server cannot service
the interactive dialogs SAP would otherwise show. Paul must satisfy them via the OFFICIAL MCP tools before
calling `write_source`:

1. **Transport assignment (Risk B).** `writeFile` on a non-`$TMP` object requires the object be assigned to
   a workbench transport; with none, the native client returns an error that SAP's extension answers with a
   UI transport-picker dialog — which our headless server cannot service — failing as
   `NoPermissions("Save failed: No transport assigned.")`. So Paul must call `abap_transport-create` /
   `abap_transport-get` and ensure assignment BEFORE `write_source` (or the Dev system is configured for
   automatic assignment). **`$TMP` objects are local/non-transportable and need no transport** — which is
   why the first write-persistence spike should target `$TMP` to sidestep this entirely.
2. **Logon state (Risk A).** `read_source` (and `write_source` if the destination is not yet connected)
   needs the destination logged on; otherwise it throws `FileSystemError.Unavailable`. The extension must
   **catch that and return a meaningful MCP error** telling the caller to open a file from the target
   system in VS Code first (triggering SAP's own logon flow). Do not attempt to drive logon via a SAP
   internal API — only VS Code public APIs are permitted.

## 5. Hard requirements — Aaron's six conditions (all mandatory)

1. **No direct ADT REST, ever.** No code path calls a `/sap/bc/adt/` endpoint by any route (incl.
   fallbacks/error handlers/reads). The whole write flows through the VS Code FileSystemProvider. Verifiable
   by inspection of the extension's complete network surface, not by assertion.
2. **Dev-only, enforced in the extension.** Resolve the destination behind the `abap:` URI and refuse any
   write if it is not a known Dev system. The extension carries the guard itself (it is the write path);
   Paul's session-level check is necessary but not sufficient. **Mechanism (Adrian)**: the destination ID
   is `uri.path.split("/")[2]` (e.g. `YOUR_DEV_DEST`); validate it against an allowlist of known Dev
   system IDs and reject otherwise. Also **disable the off-policy `murbani.vscode-abap-remote-fs` extension
   in the Dev profile** (Adrian Risk F) so no competing FileSystemProvider/`abap-adt-api` path is active.
3. **Scoped to `write_source` + `read_source` only.** No additional tools without re-review.
4. **Documented support boundary (ADR).** One page: SAP supports the ADT extension/provider/backend; the
   team supports this glue extension; incident escalation paths for each.
5. **Upgrade-impact check at every ADT extension update.** Validate the `abap:` scheme + FileSystemProvider
   write contract are unchanged before upgrading SAP's ADT extension. Automate a `$TMP` write→read
   round-trip smoke test to run post-upgrade.
6. **No token/credential in our transport.** The official ADT MCP Server bearer token must not be
   accessible to or relayed through this extension. The two MCP servers stay separate and independently
   secured.

## 6. Risks (Aaron) + mitigations

- **FileSystemProvider contract stability** (Med/High): the `abap:` scheme is an undocumented
  extension-to-extension interface; a SAP ADT update could change it. → Condition 5 + post-upgrade smoke
  test.
- **Agentic-orchestration policy interpretation** (Low-Med/High): policy §2.2.2 restricts agentic API
  orchestration to SAP-endorsed pathways; this is a defensible gap-fill of the documented loop, but an
  interpretation. → Record the rationale in the ADR; watch for SAP policy updates.
- **Precedent** (Low/Med): approval is scoped to the FileSystemProvider path, write/read of the opened
  source object, Dev only, VS Code public APIs only. Any successor extension is reviewed independently.
- **Clean Core / data handling** (Low/Low): dev toolchain only, no productive impact; Dev-system source is
  not production/personal data.

## 7. Build notes

- **Scaffold**: standard VS Code extension (TypeScript), `activationEvents` on startup; host a localhost MCP
  server (HTTP, like the ADT MCP Server at `localhost:2236`) whose handlers run in the extension host so
  they hold the `vscode` API.
- **Register with Claude Code**: `claude mcp add --scope user` (same pattern as `sap-adt-mcp`), a distinct
  server name e.g. `adt-editor-bridge`. Paul connects as MCP client and loads the two tools via `ToolSearch`
  (they will be deferred tools in the harness, same as the ADT MCP tools).
- **Prereqs**: VS Code open with SAP ADT extension active and connected to the Dev destination (same
  operational dependency as the ADT MCP Server itself).
- **Out of scope**: any RFC, any direct REST, any use of `murbani.vscode-abap-remote-fs` /`abap-adt-api`
  (off-policy; do not import).

## 8. Pre-build gates

1. **[DONE 2026-07-03]** Formal Adrian technical validation — all three questions resolved favourably; two
   non-architectural preconditions surfaced and folded into §4a. See header for verdicts.
2. **[NEXT — empirical]** Live `$TMP` write→read round-trip proving persistence. Target `$TMP` first
   (no transport needed, sidesteps Risk B). Needs the extension to exist (or a manual VS Code check that a
   programmatic `workspace.fs.writeFile` on an opened `$TMP` object source persists to the backend). Then a
   second round-trip against a transported package object to exercise the Risk-B transport precondition.
3. **[BEFORE FIRST USE]** Write the support-boundary ADR (Aaron Condition 4).
4. Scaffold the extension (TypeScript + localhost MCP host + the two handlers + Dev-only guard + the §4a
   precondition error-handling), register via `claude mcp add --scope user` as `adt-editor-bridge`.
