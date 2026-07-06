# ADR-002: Eclipse editor bridge for Claude Code for ABAP

- **Status**: Accepted (Dev-only), 2026-07-04
- **Deciders**: user (owner); Alex (orchestrator); Aaron (governance); Adrian (technical)
- **Supersedes**: extends ADR-001 (`adt-editor-bridge`, VS Code) to the Eclipse plug-in. ADR-001's
  conditions are carried forward here, freshly scoped; for Eclipse-based work this ADR is the
  governing document. Complements the official SAP ADT MCP Server; does not replace it.

## Context

ADT 3.60 ships an embedded ADT MCP Server (Jetty, `http://localhost:2234/mcp`, bearer auth, 20 tools
including the ATC suite) — but, as with the VS Code variant covered by ADR-001, it exposes no
source-read or source-write tool. SAP's own agentic-loop documentation states the implementation is
written by "the built-in edit tool from MCP host (Not from ADT MCP Server)". Claude Code's built-in
Edit/Write tools operate on OS files only; they cannot reach an ADT editor buffer.

The "Claude Code for ABAP" Eclipse plug-in therefore supplies the missing verb itself: a Node
sidecar hosts the Claude Agent SDK session and registers an in-process MCP server (`adt-bridge`)
whose tool handlers are relayed over stdio NDJSON to the Java plug-in, which performs the edit
against the **live ADT editor buffer** via Eclipse Platform APIs. Edits appear in the open editor,
participate in undo, and persist through ADT's own save/activation pipeline. Off-policy routes
(`abap-adt-api`, direct `/sap/bc/adt/` REST) remain banned by SAP API Policy v4/2026 and are not
used anywhere in this codebase.

## Decision

Implement the source bridge inside the Eclipse plug-in using **Eclipse Foundation platform APIs
only**. The write path is `IEditorPart` → `getAdapter(ITextEditor.class)` →
`IDocumentProvider.getDocument()` → a single atomic `IDocument.replace(0, length, content)`
(one undo step); optional persistence is `IEditorPart.doSave(...)`, which runs ADT's own save
pipeline and raises SAP's transport-assignment/logon dialogs to the user. No `com.sap.adt.*` bundle
is a compile dependency; no code in this repository issues HTTP to the ABAP backend.

The bridge tool surface is implemented in `bridge/BridgeToolDispatcher` (all operations inside
`Display.syncExec` with in-runnable re-validation), editor resolution and the adapter chain in
`bridge/EditorSourceGateway`, and the Dev-only gate in `bridge/DevDestinationGuard`.

We chose this over: (a) any ADT-REST or `abap-adt-api` bridge — off-policy; (b) waiting for SAP to
ship an official source-write MCP tool — timeline unknown, and this design collapses gracefully if
one arrives (see revisit triggers); (c) keeping the VS Code bridge as the only write path — the
deliverable is an Eclipse-native, Joule-style panel and the write must land in the same editor the
user is looking at.

## Support boundary (carried from ADR-001 Condition 4)

| Component | Owner | Support / escalation |
|---|---|---|
| Eclipse Platform APIs (`ITextEditor`, `IDocument`, `IDocumentProvider`, workbench/part model, SWT Browser) | Eclipse Foundation | Eclipse channels |
| ADT editors, save/activation/transport pipeline, embedded ADT MCP Server (`localhost:2234/mcp`, its 20 tools, its bearer token) | SAP | SAP support (ABAP Development Tools); the backend REST is entirely SAP's code |
| This plug-in: editor bridge (dispatcher, gateway, guard), Node sidecar (Agent SDK session, local HTTP/WS), chat UI, stdio protocol | us (the team) | our own repo/issues; not an SAP-supported component |
| ABAP backend `S4H_100` (Dev) | SAP / basis | normal system support |

**Incident routing**: failures during save/activation, transport dialogs, or logon behaviour trace
to ADT → SAP channel. Failures in tool dispatch, editor/adapter resolution, the Dev guard, the
sidecar, or the UI → this plug-in → our repo. We never patch or invoke SAP internals to "fix" a
backend or ADT issue.

## Conditions of use (all mandatory; carried from ADR-001 and re-scoped)

1. **No direct ADT REST, ever.** Our code contains no HTTP client to the ABAP backend. All source
   writes go through Eclipse Platform editor APIs (`ITextEditor` → `IDocument`) and all
   persistence/activation through ADT's own save pipeline (`IEditorPart.doSave`). Backend traffic
   from the official `sap-adt-mcp` MCP server is SAP's code, not ours.
2. **Dev-only, enforced Java-side, fail-closed.** `DevDestinationGuard` checks every `read_source`
   and `write_source` call against the `devSystemAllowlist` preference before touching the
   document. An **empty allowlist refuses**; an editor whose destination cannot be resolved to an
   allowlist entry (by exact ABAP project name, then tooltip containment) **refuses**. The refusal
   message tells the user exactly which preference to set. The guard runs in the Java plug-in, not
   the sidecar or the model — a compromised or confused sidecar cannot bypass it.
3. **Tool scope frozen at exactly three tools**: `read_source`, `write_source`,
   `get_editor_context`. `BridgeToolDispatcher.handle()` rejects anything else by construction.
   Any additional bridge tool requires a fresh governance review and an ADR amendment.
4. **This ADR documents the support boundary** — done (table above).
5. **Upgrade-impact re-spike after every ADT update.** The risk surface is the adapter chain in
   `EditorSourceGateway`: ADT's multi-page source editors are not guaranteed to adapt to Platform
   text-editor interfaces across versions. The implemented fallback chain (Gate G6) is:
   `getAdapter(ITextEditor.class)` (or direct instanceof) → `IDocumentProvider.getDocument()` →
   `getAdapter(IDocument.class)`; on a miss, the tool returns a structured error carrying the full
   diagnostic (`editorClass`, adaptability flags) so the failure is visible to the model and the
   user rather than silent. A last-resort **reflective access to ADT's active page is documented
   here but deliberately not implemented**; implementing it would itself require re-review under
   this condition. After any ADT update, re-run the G6 spike (read → write → undo → `save:true`
   round-trip on a `$TMP` object) before trusting the bridge.
6. **Token hygiene.** The ADT MCP bearer token is read in-process from the workspace preference
   node `com.sap.adt.mcp.core.ui` (`AdtMcpTokenLocator`, generic Eclipse preferences API — no SAP
   compile dependency) and handed to the sidecar **via environment variable only**
   (`ADT_MCP_TOKEN`): never on argv, never written to any log, never rendered in the chat UI. The
   sidecar uses it solely as the Authorization header of the Agent SDK's HTTP MCP client to
   `localhost:2234/mcp`. The bridge stdio path (Java ⇄ sidecar) carries **no credential** — bridge
   requests are authorised by the Java-side guard, not by a token.

## Local UI surface (additional to ADR-001)

Unlike the VS Code bridge, this plug-in exposes a local HTTP + WebSocket surface (the sidecar
serves the chat UI to the SWT Browser). Its model:

- **Loopback only**: the sidecar binds `127.0.0.1`; nothing listens on external interfaces.
- **Per-launch UUID token** (`UI_TOKEN`): generated fresh by the plug-in at each sidecar launch,
  passed by env, required as a query parameter on the UI page and the `/ws` upgrade; the sidecar
  additionally enforces same-origin on WebSocket connections. A stale browser tab from a previous
  launch cannot reconnect.
- **Editor context is a user gesture**: selection text leaves the editor only when the user
  invokes "Send to Claude" (context menu or keybinding) — the attachment is deliberate, visible as
  a chip in the UI, and removable before sending.
- **Allowlist-aware context**: `get_editor_context` reports object names and line ranges for any
  open editor, but **withholds selection text when the project is not on the Dev allowlist**
  (the payload carries an explanatory note instead). Source content never crosses the bridge for
  a non-allowlisted system by any path.

## Consequences

- **Positive**: Joule-parity flow with no copy-paste — select, send, and Claude reads and edits the
  live buffer; edits are visible and undoable in the editor the user already has open; save,
  transport, and activation remain SAP's own pipeline with SAP's own dialogs; the official 20 ADT
  MCP tools (ATC, unit tests, activation, transport diff) ride alongside with zero-config token
  wiring; everything stays on documented platform APIs.
- **Negative / accepted**: a plug-in, sidecar, and UI to maintain; the adapter chain depends on
  ADT editors continuing to adapt to Platform text-editor interfaces (mitigated by Condition 5's
  re-spike and by loud, diagnostic-rich failures); `write_source` replaces the whole document
  (simple and atomic, but large objects mean large payloads); the user must service transport and
  logon dialogs interactively — the model cannot and must not.
- **Boundaries**: Dev systems only; never Production. Any productive use voids this ADR and
  requires re-review.

## Revisit triggers

Re-open this ADR when any of the following occurs:

1. Any ADT update (mandatory Condition 5 re-spike; if the adapter chain breaks, decide between a
   new adaptation path and the documented-but-unimplemented reflective fallback — the latter needs
   explicit approval).
2. SAP ships an official source read/write tool on the ADT MCP Server — plan migration of the
   bridge's write path onto it and shrink our surface accordingly.
3. Any request to widen the tool scope beyond the frozen three (Condition 3).
4. Any change to how the ADT MCP token is stored (`com.sap.adt.mcp.core.ui` node or key renames) —
   `AdtMcpTokenLocator` fails soft (empty token, UI remediation message) but the wiring must be
   re-verified.
5. Any proposal to bind the sidecar to a non-loopback interface, persist the UI token, or attach
   editor context automatically without a user gesture.
6. Any proposal to use the bridge against a non-Dev system.
