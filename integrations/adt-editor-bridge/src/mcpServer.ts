import * as http from "http";
import * as vscode from "vscode";
import { z } from "zod";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";

export interface BridgeConfig {
  port: number;
  devSystemAllowlist: string[];
}

/**
 * Raised by the Dev-only guard. Distinct from ADT FileSystemError so the tool
 * handler can report a guard refusal separately from a backend failure.
 */
class GuardError extends Error {}

/**
 * Dev-only guard (Aaron Condition 2 / Adrian mechanism).
 *
 * The official ADT extension derives the destination from `uri.path.split("/")[2]`
 * and rejects a destination containing a dot. We replicate that and additionally
 * require the destination be on the configured Dev allowlist. Returns the resolved
 * destination ID, or throws GuardError.
 */
function assertDevDestination(uri: vscode.Uri, allowlist: string[]): string {
  if (uri.scheme !== "abap") {
    throw new GuardError(
      `Refused: URI scheme is '${uri.scheme}', expected 'abap'. Pass the URI returned by abap_creation-create_object.`
    );
  }
  const dest = uri.path.split("/")[2] ?? "";
  if (!dest || dest.includes(".")) {
    throw new GuardError(
      `Refused: could not resolve a plain destination ID from the URI (segment[2]='${dest}'). Do not hand-construct abap: URIs.`
    );
  }
  if (allowlist.length === 0) {
    throw new GuardError(
      "Refused: adtEditorBridge.devSystemAllowlist is empty. This bridge writes to Dev systems only; add the Dev destination ID to settings."
    );
  }
  if (!allowlist.includes(dest)) {
    throw new GuardError(
      `Refused: destination '${dest}' is not on the Dev allowlist ${JSON.stringify(allowlist)}. This bridge writes to Dev systems only.`
    );
  }
  return dest;
}

/**
 * Map the precondition failures Adrian identified (§4a) into actionable messages
 * for the MCP client (Paul), since a headless server cannot service SAP's dialogs.
 */
function mapFsError(e: unknown): string {
  if (e instanceof vscode.FileSystemError) {
    const code = String(e.code);
    if (code === "Unavailable") {
      return (
        "Destination not logged on (FileSystemError.Unavailable). Open any file from the target system " +
        "in VS Code first to trigger the ADT logon flow, then retry."
      );
    }
    if (code === "NoPermissions") {
      return (
        "Write refused by ADT (FileSystemError.NoPermissions) — usually no transport assigned. " +
        "Assign the object to a workbench transport via abap_transport-create / abap_transport-get " +
        "(or target a $TMP object, which needs none), then retry. Original: " +
        e.message
      );
    }
    if (code === "FileNotFound") {
      return (
        "Object not found (FileSystemError.FileNotFound). Create the skeleton first via " +
        "abap_creation-create_object and pass the URI it returns. Original: " +
        e.message
      );
    }
    return `ADT filesystem error (${code}): ${e.message}`;
  }
  return (e as Error)?.message ?? String(e);
}

/** Build a fresh McpServer instance (stateless: one per request). */
function buildServer(cfg: BridgeConfig): McpServer {
  const server = new McpServer({ name: "adt-editor-bridge", version: "0.1.0" });

  server.registerTool(
    "write_source",
    {
      title: "Write ABAP source",
      description:
        "Writes ABAP source into an editor-opened ADT object through VS Code's official ADT " +
        "FileSystemProvider (the same path Copilot/Joule use; no direct ADT REST). Dev systems only. " +
        "The URI MUST be the one returned by abap_creation-create_object (never hand-built). " +
        "Preconditions: the object must already be transport-assigned ($TMP is exempt), and the " +
        "destination must be logged on. Does not activate — call abap_activate_objects next.",
      inputSchema: {
        uri: z
          .string()
          .describe("abap: URI exactly as returned by abap_creation-create_object"),
        content: z.string().describe("Full ABAP source text for the object's main include"),
      },
    },
    async ({ uri, content }) => {
      try {
        const u = vscode.Uri.parse(uri, true);
        const dest = assertDevDestination(u, cfg.devSystemAllowlist);
        await vscode.workspace.fs.writeFile(u, Buffer.from(content, "utf8"));
        return {
          content: [
            { type: "text", text: `OK: wrote ${content.length} chars to ${dest} (${uri}).` },
          ],
        };
      } catch (e) {
        const msg = e instanceof GuardError ? e.message : mapFsError(e);
        return { content: [{ type: "text", text: `ERROR: ${msg}` }], isError: true };
      }
    }
  );

  server.registerTool(
    "read_source",
    {
      title: "Read ABAP source",
      description:
        "Reads the source of an editor-opened ADT object through VS Code's official ADT " +
        "FileSystemProvider. Dev systems only. The URI MUST come from abap_creation-create_object or " +
        "an open editor tab. Precondition: the destination must be logged on.",
      inputSchema: {
        uri: z.string().describe("abap: URI of the object to read"),
      },
    },
    async ({ uri }) => {
      try {
        const u = vscode.Uri.parse(uri, true);
        assertDevDestination(u, cfg.devSystemAllowlist);
        const bytes = await vscode.workspace.fs.readFile(u);
        return { content: [{ type: "text", text: new TextDecoder().decode(bytes) }] };
      } catch (e) {
        const msg = e instanceof GuardError ? e.message : mapFsError(e);
        return { content: [{ type: "text", text: `ERROR: ${msg}` }], isError: true };
      }
    }
  );

  return server;
}

/**
 * Start the localhost MCP server. Stateless Streamable HTTP: a fresh McpServer +
 * transport per POST /mcp. Bound to 127.0.0.1 only. Returns the http.Server so the
 * caller can close it on deactivate / config change.
 */
export function startBridge(cfg: BridgeConfig, out: vscode.OutputChannel): http.Server {
  const httpServer = http.createServer((req, res) => {
    if (req.url !== "/mcp" || req.method !== "POST") {
      res.writeHead(404, { "content-type": "text/plain" }).end("Not found. POST /mcp only.");
      return;
    }
    let body = "";
    req.on("data", (chunk) => (body += chunk));
    req.on("end", async () => {
      let parsed: unknown = undefined;
      if (body) {
        try {
          parsed = JSON.parse(body);
        } catch {
          res.writeHead(400, { "content-type": "text/plain" }).end("Invalid JSON body.");
          return;
        }
      }
      const server = buildServer(cfg);
      const transport = new StreamableHTTPServerTransport({ sessionIdGenerator: undefined });
      res.on("close", () => {
        transport.close();
        server.close();
      });
      try {
        await server.connect(transport);
        await transport.handleRequest(req, res, parsed);
      } catch (err) {
        out.appendLine(`MCP request error: ${(err as Error).message}`);
        if (!res.headersSent) {
          res.writeHead(500, { "content-type": "text/plain" }).end("Internal error.");
        }
      }
    });
  });

  httpServer.on("error", (err) => out.appendLine(`HTTP server error: ${err.message}`));
  httpServer.listen(cfg.port, "127.0.0.1");
  return httpServer;
}
