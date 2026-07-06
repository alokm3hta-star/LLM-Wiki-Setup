# Installing and wiring the ADT Editor Bridge

This is the full, ordered setup: from nothing to a working create -> write -> read -> activate loop that a
terminal Claude Code session can drive against a Development ABAP system.

You end up with **two local MCP servers, both running inside VS Code**:

1. **SAP's official ADT MCP server** (ships in the SAP ADT extension): creates object skeletons, assigns
   transports, activates, runs ABAP Unit tests. It deliberately has no source-write tool.
2. **This editor-bridge extension**: supplies the one missing verb, `write_source` / `read_source`, by
   calling VS Code's own ADT `FileSystemProvider`. On-policy, Dev-only, no direct ADT REST.

A terminal `claude` session with both registered gets the complete loop. See `README.md` and
`ADR-001-adt-editor-bridge.md` for the design and governance; this file is just the how-to.

> **Development systems only.** Everything below assumes a Dev destination. Never point any of this at a
> Production system. The editor-bridge enforces this with an allow-list, but confirm it yourself too.

## Prerequisites

- Visual Studio Code (version 1.105 or later).
- **SAP ABAP Development Tools** extension for VS Code (`sapse.adt-vscode`), connected and logged on to a
  Development ABAP destination.
- Node.js and npm (to build the extension).
- Claude Code CLI (to register and use the servers).
- A terminal (the desktop app cannot reach a local MCP server; see "Gotchas").

---

## Part A: the official SAP ADT MCP server

1. **Install the SAP ADT extension** and connect it to your Development destination. Open any ABAP object
   once so the logon completes; the connection must be live.

2. **Enable its MCP server.** Open Settings (`Cmd/Ctrl+,`), search for `Adt Mcp Server`, and turn on
   **`Adt > Mcp Server: Enable`**. It now listens on `http://localhost:2236/mcp`.

3. **Copy its token.** In the same settings, copy the value of **`Adt > Mcp Server: Token`**. This is the
   bearer token the next step needs. Treat it like a password; never commit it.

4. **Register it with Claude Code.** Two ways, pick one:

   **Option 1, per-workspace file (matches `setup-template/`):** copy the `setup-template/` folder to a
   location **outside** this repo, rename `.mcp.json.example` to `.mcp.json`, and paste your token in place
   of `<YOUR_ADT_MCP_TOKEN>`. A `claude` session started in that folder picks the server up automatically.
   `.mcp.json` is gitignored so a real token never gets committed.

   **Option 2, user scope (available in every session):**
   ```bash
   claude mcp add --scope user --transport http \
     --header "Authorization: Bearer <YOUR_ADT_MCP_TOKEN>" \
     sap-adt-mcp http://localhost:2236/mcp
   ```
   The connection details live in your personal Claude config (`~/.claude.json`), never in a project file.

---

## Part B: the editor-bridge extension (this folder)

5. **Build it.** From this folder:
   ```bash
   npm install
   npm run build        # esbuild bundles src/ -> dist/extension.js
   npm run typecheck    # optional
   ```

6. **Package it into an installable `.vsix`:**
   ```bash
   npx @vscode/vsce package     # produces adt-editor-bridge-0.1.0.vsix
   ```

7. **Install the `.vsix` into VS Code**, either:
   ```bash
   code --install-extension adt-editor-bridge-0.1.0.vsix
   ```
   or in VS Code: Extensions view -> the `...` menu -> **Install from VSIX** -> pick the file.
   (For quick iteration you can instead open this folder in VS Code and press **F5** to launch an Extension
   Development Host, skipping the package/install step.)

8. **Configure its two settings.** This is the safety guard, so do not skip it. Open Settings, search
   **`ADT Editor Bridge`**, and set the Dev destination allow-list and (optionally) the port. Equivalently,
   add to your **User** `settings.json`:
   ```json
   "adtEditorBridge.devSystemAllowlist": ["YOUR_DEV_DEST"],
   "adtEditorBridge.port": 3939
   ```
   `devSystemAllowlist` must contain your Dev destination ID (see "Finding your destination ID" below). If
   the list is empty the bridge refuses every write and read by design.

9. **Register it with Claude Code (user scope):**
   ```bash
   claude mcp add --scope user --transport http \
     adt-editor-bridge http://127.0.0.1:3939/mcp
   ```
   No token here: this server holds no credentials and binds to `127.0.0.1` only.

---

## Part C: verify it works

10. **Check the servers are live.** Keep VS Code open with the ADT destination logged on. The editor-bridge
    logs its listen address in its "ADT Editor Bridge" output channel. A quick health check:
    ```bash
    curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:3939/mcp   # expect 404 "POST /mcp only" = server up
    ```
    Confirm registration with `claude mcp list`.

11. **Start a terminal Claude Code session** (`claude`) and confirm both `sap-adt-mcp` and
    `adt-editor-bridge` are connected. (If your harness defers MCP tools, load them by name first.)

12. **Run the round-trip smoke test** (details in `README.md`, "The write-persistence spike"). Target a
    `$TMP` object so no transport is needed:
    - create a `$TMP` class skeleton via the official server (`abap_creation-create_object`, empty transport);
    - `write_source` a real class body through the editor-bridge, using the `abap:` URI the create returned;
    - `read_source` the same URI and confirm the body comes back verbatim (persistence proven);
    - `abap_activate_objects` and confirm it compiles clean.
    If all four pass, the loop is wired. Repeat once against a transported package object to exercise the
    transport precondition (create the object on a workbench transport first).

---

## Finding your destination ID

The value for `devSystemAllowlist` is the **ADT destination name** you connected with. Internally the bridge
derives it as segment 2 of the object's `abap:` URI (`uri.path.split("/")[2]`), which is exactly that
destination ID. It is shown in the SAP ADT connection you set up; use it verbatim, with no dots.

## Gotchas (all learned the hard way)

- **Terminal, not the desktop app, for local servers.** The Claude Desktop app cannot reach a local HTTP
  MCP server directly. Its Connectors UI accepts only remote HTTPS URLs (it rejects `http://localhost`), and
  its `claude_desktop_config.json` is stdio-only: a direct `"type": "http"` / `"url"` entry is not supported
  and can silently wipe the `mcpServers` block. The only desktop workaround is to bridge each server to
  stdio with `npx mcp-remote <url>` (which adds a process per server and copies any bearer token into a
  second local file). The clean path is a terminal `claude` session: it reads `~/.claude.json` and speaks
  Streamable HTTP to `127.0.0.1` natively, no bridge. Ordinary (non-MCP) work is fine in the desktop app.
- **VS Code must stay open.** Both MCP servers live inside VS Code. Close it and the tools disappear;
  reopen it and they return.
- **Sub-agents may not inherit MCP tools.** In some harnesses a spawned sub-agent gets an empty tool
  registry; the main session holds the connection. If so, have the main session do the ABAP work directly.
- **Older ADT builds expose fewer tools.** If ATC or the transport-diff tools are missing, update the SAP
  ADT extension; they are documented and come with newer builds.
- **Re-test after SAP updates.** The `abap:` URI behaviour the bridge relies on is an internal SAP detail.
  After any SAP ADT extension update, re-run the `$TMP` smoke test before trusting it (ADR Condition 5).
- **Token persistence.** The official server's token is a stored VS Code setting; it survives server and
  VS Code restarts and does not auto-regenerate, so you only need to re-register if you deliberately
  regenerate it.
- **No delete tool.** Neither server can delete objects. Clean up throwaway spike objects manually in ADT.
