import * as vscode from "vscode";
import * as http from "http";
import { startBridge, BridgeConfig } from "./mcpServer";

let server: http.Server | undefined;
let out: vscode.OutputChannel;

function readConfig(): BridgeConfig {
  const c = vscode.workspace.getConfiguration("adtEditorBridge");
  return {
    port: c.get<number>("port", 3939),
    devSystemAllowlist: c.get<string[]>("devSystemAllowlist", []),
  };
}

function restart(): void {
  server?.close();
  const cfg = readConfig();
  server = startBridge(cfg, out);
  out.appendLine(
    `ADT Editor Bridge MCP server listening on http://127.0.0.1:${cfg.port}/mcp ` +
      `(Dev allowlist: ${JSON.stringify(cfg.devSystemAllowlist)}).`
  );
  if (cfg.devSystemAllowlist.length === 0) {
    out.appendLine(
      "WARNING: adtEditorBridge.devSystemAllowlist is empty — every write/read will be refused. " +
        "Set it in Settings to the Dev destination ID(s)."
    );
  }
}

export function activate(context: vscode.ExtensionContext): void {
  out = vscode.window.createOutputChannel("ADT Editor Bridge");
  context.subscriptions.push(out);
  restart();
  context.subscriptions.push({ dispose: () => server?.close() });
  context.subscriptions.push(
    vscode.workspace.onDidChangeConfiguration((e) => {
      if (e.affectsConfiguration("adtEditorBridge")) {
        out.appendLine("Configuration changed; restarting MCP server.");
        restart();
      }
    })
  );
}

export function deactivate(): void {
  server?.close();
}
