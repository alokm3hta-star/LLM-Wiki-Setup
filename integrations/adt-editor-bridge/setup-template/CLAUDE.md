# ABAP MCP Workspace — TEMPLATE

Copy this folder to a location **outside** your knowledge-base repo (one folder per ABAP destination) and
fill in the placeholders. It holds no code and no credentials of its own; it only records which SAP
destination this workspace targets and confirms it is a Development system.

> **Never commit a real token or a real system ID to a public repo.** Rename `.mcp.json.example` to
> `.mcp.json` locally and paste your own local ADT MCP token into it; `.mcp.json` is gitignored on purpose.

## Connection

- MCP server: `com.sap.adt/mcp` (SAP ADT MCP Server, running locally from VS Code's ABAP Development Tools extension)
- Config: `.mcp.json` in this folder (HTTP, `http://localhost:2236/mcp`, bearer token from VS Code `Adt > Mcp Server: Token`)
- ABAP destination behind this connection: **`<YOUR_DEV_DEST>`**
- Environment: **Dev** — confirm this yourself before any write. Never treat this as Production.

## Purpose

This workspace exists so ABAP/RAP development work never writes code into your knowledge-base repo. The dev
agent reads the wiki read-only for grounding but writes only here (and to the SAP system via MCP).

The live source-write path is the `adt-editor-bridge` extension in the parent folder: the official SAP ADT
MCP server creates and activates objects, and the editor-bridge supplies the one verb SAP's server omits
(`write_source`/`read_source`) through VS Code's own ADT FileSystemProvider. See the parent `README.md` and
`ADR-001-adt-editor-bridge.md` for the full design, governance conditions, and the Dev-only guard.

## Adding a further destination

Copy this folder again as a sibling (`<SYSTEM_NAME>`), point the ADT MCP server at that system, add the new
destination ID to the editor-bridge `devSystemAllowlist`, and record Dev/Prod status here as above.
