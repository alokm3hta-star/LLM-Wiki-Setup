# Claude Code for ABAP

A Joule-style **Claude Code chat panel inside Eclipse / ADT**. The docked view hosts a real Claude
Code session (Claude Agent SDK) wired to SAP's embedded **ADT MCP Server** (ATC, unit tests,
activation, transport diff — 20 tools), plus an **editor bridge** that lets Claude read and edit
the ABAP source in your open ADT editors directly: no copy-paste, edits appear live in the buffer,
are undoable with Cmd+Z, and save/activate through ADT's own pipeline.

## Architecture at a glance

```
 Eclipse / ADT (Java plug-in)                     Node sidecar (bundled)
+----------------------------+   stdio NDJSON   +--------------------------------+
| ClaudeChatView             |<---------------->| Claude Agent SDK session       |
|   SWT Browser =============|=== HTTP + WS ===>|  - serves chat UI (127.0.0.1,  |
| SidecarProcessManager      |                  |    per-launch token)           |
| BridgeToolDispatcher       |                  | MCP servers:                   |
|   EditorSourceGateway      |                  |  - "sap-adt-mcp"  HTTP ->      |
|   DevDestinationGuard      |                  |      localhost:2234/mcp        |
+-------------+--------------+                  |  - "adt-bridge" in-process:    |
              | live IDocument edits            |      read_source, write_source,|
              v                                 |      get_editor_context        |
   ADT editor buffer -> ADT save/activation     +--------------------------------+
   pipeline -> ABAP backend
```

Bridge tool calls travel sidecar → stdio → Java → the live editor document; no code in this
repository talks HTTP to the ABAP backend. See [docs/ADR-002](docs/ADR-002-eclipse-editor-bridge.md).

## Requirements

- **Eclipse 2026-06** with **ABAP Development Tools 3.60+**, and the **ADT MCP Server enabled**
  (Preferences → ABAP Development → MCP Server; default port 2234).
- **Node.js >= 20** on `PATH` (or set the path in the plug-in preferences).
- **Claude Code CLI authentication already set up** in `~/.claude` (the sidecar reuses it; run
  `claude` once in a terminal and log in if you have not).
- **JDK 21 + Maven** — only needed to build; not needed to install or run the packaged zip.

## Build

```sh
export JAVA_HOME=/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home
mvn clean verify
```

The installable update-site zip lands at `releng/is.mehta.claudecode.abap.site/target/*.zip`.
The build runs `npm install && npm run build` for the sidecar and UI; pass `-DskipNpm=true` to skip
that when the built `sidecar/` and `web/` outputs are already current.

## Install

1. Eclipse → **Help → Install New Software… → Add… → Archive…**, select the site zip.
2. Tick the *Claude Code for ABAP* feature, finish the wizard (accept the unsigned-content prompt).
3. Restart Eclipse.

## Configure

**Preferences → Claude Code for ABAP**:

- **Dev system allowlist** — **mandatory** for source read/write. Comma-separated ABAP project
  names (e.g. `S4H_100_myuser_en`). The bridge is **fail-closed**: with an empty allowlist, or an
  editor that does not resolve to an allowlisted project, `read_source`/`write_source` refuse.
- **Node path** — set if `node` is not on Eclipse's `PATH`.
- **Permission mode** — `default` (ask before writes), `acceptEdits`, or `plan`.
- **ADT MCP port** — only change if you moved the ADT MCP Server off 2234.

The ADT MCP bearer token is picked up automatically from your workspace preferences; there is
nothing to paste.

## First run

1. **Window → Show View → Other… → Claude Code → Claude Code**, or
2. select some code in an ABAP editor → right-click → **Send to Claude** (or **Cmd+Option+C**).
   The selection arrives as an attach-chip on the chat input.

Check the header: the ADT dot should be green (MCP server reachable). Then try, for example:
*"implement the missing method bodies"* — Claude reads via `read_source`, proposes a
`write_source` with a diff preview, and on Allow the edit appears live in your editor.

## Fast dev loop (contributors)

Set the **devOverridePath** preference to this git tree's bundle directory
(`…/claude-code-eclipse/bundles/is.mehta.claudecode.abap`). The plug-in then loads `sidecar/` and
`web/` from the git tree instead of the installed bundle: after a sidecar or UI change, run
`npm run build` in `sidecar-src/` / `ui-src/` and use **Restart Sidecar** from the view toolbar —
no Eclipse restart, no reinstall. Java changes still need a rebuild + reinstall (or a runtime
workbench).

## Security

Governed by [ADR-002](docs/ADR-002-eclipse-editor-bridge.md). In short:

- **Dev-only, fail-closed**: source read/write is refused unless the editor resolves to the Dev
  allowlist, enforced in the Java plug-in.
- **Three tools only**: `read_source`, `write_source`, `get_editor_context`; nothing else crosses
  the bridge, and `get_editor_context` withholds selection text for non-allowlisted projects.
- **Token via env only**: the ADT MCP token is read from workspace preferences and passed to the
  sidecar in its environment; never on the command line, in logs, or in the UI.
- **Localhost-only UI**: the chat UI and WebSocket bind `127.0.0.1` and require a per-launch UUID
  token; no external interface is ever opened.
- **No direct ADT REST**: all persistence and activation go through ADT's own save pipeline; SAP's
  transport/logon dialogs come to you, not to the model.

## Troubleshooting

| Symptom | Fix |
|---|---|
| View stuck on the splash/loading page | The sidecar failed to start. Open **Window → Show View → Error Log** and look for entries from `is.mehta.claudecode.abap` carrying the sidecar's stderr (bad node path, port clash, missing `~/.claude` auth). |
| ADT status dot red | The ADT MCP Server is disabled or the token is stale. Enable it under **Preferences → ABAP Development → MCP Server** and regenerate the token; the plug-in picks up the change and restarts the sidecar. |
| Tool error: "No open editor matches '…' — the object must be OPEN in an ADT editor first" | The bridge only operates on open editors by design. Open the object in ADT and retry. |
| Tool error: "the Dev system allowlist is empty" / "does not resolve to any allowlisted Dev system" | Fail-closed guard. Add your Dev ABAP project name under **Preferences → Claude Code for ABAP**. |
| Tool error mentioning "the known G6 adapter risk" | An ADT editor stopped adapting to the Platform text-editor APIs (typically after an ADT update). File an issue with the full diagnostic string; see ADR-002 condition 5. |
| "Save was requested but the editor is still dirty" note in a tool result | You cancelled (or still have open) an ADT transport-assignment or logon dialog; service it and ask Claude to save again. |
