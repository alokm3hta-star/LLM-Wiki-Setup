/*
 * Claude Code for ABAP — Node sidecar.
 *
 * Spawned by the Eclipse plug-in (SidecarProcessManager). Responsibilities:
 *   - run a Claude Agent SDK session (streaming input, one query at a time)
 *   - serve the chat UI statics + a WebSocket on 127.0.0.1:<ephemeral>
 *   - expose the 3 ADT bridge tools as an in-process MCP server that RPCs
 *     to Java over stdio (NDJSON)
 *
 * process.stdout is PROTOCOL ONLY (NDJSON frames to Java). All logging goes
 * to stderr.
 */

// ---------------------------------------------------------------------------
// Section 0: stdout hygiene — MUST run before anything else can log.
// ---------------------------------------------------------------------------
/* eslint-disable no-console */
console.log = console.error.bind(console);
console.info = console.error.bind(console);
console.warn = console.error.bind(console);
console.debug = console.error.bind(console);

import * as http from "node:http";
import * as fs from "node:fs";
import * as path from "node:path";
import * as readline from "node:readline";
import { randomUUID } from "node:crypto";
import { WebSocketServer, WebSocket } from "ws";
import { z } from "zod";
import type {
  CanUseTool,
  EffortLevel,
  McpSdkServerConfigWithInstance,
  McpServerConfig,
  Options,
  PermissionMode,
  PermissionResult,
  Query,
  SDKMessage,
  SDKUserMessage,
} from "@anthropic-ai/claude-agent-sdk";

// The Agent SDK is ESM-only ("type":"module"). This bundle is CJS, so load it
// via a real dynamic import() that esbuild cannot rewrite into require().
// (require(esm) also works on Node >=20.19/22.12, but this is safe everywhere.)
type SdkModule = typeof import("@anthropic-ai/claude-agent-sdk");
const dynamicImport = new Function("s", "return import(s)") as (
  s: string
) => Promise<unknown>;
let sdk: SdkModule;

// ---------------------------------------------------------------------------
// Section 1: environment + logging helpers
// ---------------------------------------------------------------------------

// Seeded from the spawn environment, but LIVE: Java pushes an `adt_config`
// stdin frame on the sidecar becoming ready and on every ADT MCP settings
// change, so a token that was absent or stale at spawn is corrected without a
// process restart (see applyAdtConfig / Section 9). Not const for that reason.
let ADT_MCP_URL = process.env.ADT_MCP_URL || "http://localhost:2234/mcp";
let ADT_MCP_TOKEN = (process.env.ADT_MCP_TOKEN || "").trim();
const UI_TOKEN = (process.env.UI_TOKEN || "").trim();
const DEV_ALLOWLIST = process.env.DEV_ALLOWLIST || "";
const CLAUDE_CWD = process.env.CLAUDE_CWD || process.cwd();
const UI_DIR = process.env.UI_DIR || "";

// Uploaded files are materialised to disk in the session workspace so the
// agent consumes them with its native Read tool (images/PDF/text), exactly as
// a real Claude Code session would with a referenced path. Kept in step with
// the UI's ALLOWED_FILE_EXT and MAX_FILE_BYTES.
const UPLOADS_ROOT = path.join(CLAUDE_CWD, ".claude-uploads");
const MAX_ATTACH_BYTES = 25 * 1024 * 1024; // per file
const MAX_ATTACH_TOTAL_BYTES = 100 * 1024 * 1024; // per message, safety cap
const ALLOWED_ATTACH_EXT = new Set([
  ".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp",
  ".pdf",
  ".md", ".markdown", ".txt", ".text", ".csv", ".tsv", ".json", ".log", ".xml", ".yaml", ".yml",
  // Office formats — Read cannot open these; the sidecar extracts text on ingest
  // (Excel via xlsx/SheetJS → CSV, Word via mammoth → text), mirroring Desktop.
  ".xlsx", ".xlsm", ".xls", ".docx",
]);
// Subset of the above that needs text extraction before the agent can read it.
const OFFICE_EXT = new Set([".xlsx", ".xlsm", ".xls", ".docx"]);

const VALID_WS_MODES = [
  "default",
  "auto",
  "acceptEdits",
  "plan",
  "bypassPermissions",
] as const;
type WsPermissionMode = (typeof VALID_WS_MODES)[number];
function asWsPermissionMode(v: unknown): WsPermissionMode | null {
  return VALID_WS_MODES.includes(v as WsPermissionMode)
    ? (v as WsPermissionMode)
    : null;
}

function log(...args: unknown[]): void {
  const ts = new Date().toISOString();
  process.stderr.write(
    `[sidecar ${ts}] ${args
      .map((a) =>
        typeof a === "string" ? a : a instanceof Error ? a.stack || a.message : safeStringify(a)
      )
      .join(" ")}\n`
  );
}

function safeStringify(v: unknown): string {
  try {
    return JSON.stringify(v);
  } catch {
    return String(v);
  }
}

function errMsg(e: unknown): string {
  return e instanceof Error ? e.message : String(e);
}

if (!UI_TOKEN) {
  log("FATAL: UI_TOKEN env var is missing/empty — cannot secure the UI WebSocket.");
  process.exit(1);
}
if (!UI_DIR) {
  log("FATAL: UI_DIR env var is missing/empty — cannot serve the chat UI.");
  process.exit(1);
}

// ---------------------------------------------------------------------------
// Section 2: stdio southbound writer (protocol frames to Java)
// ---------------------------------------------------------------------------

function writeStdout(frame: Record<string, unknown>): void {
  try {
    process.stdout.write(JSON.stringify(frame) + "\n");
  } catch (e) {
    log("failed to write stdout frame:", e);
  }
}

// ---------------------------------------------------------------------------
// Section 3: bridge RPC (sidecar -> Java -> ADT editor) with pending map
// ---------------------------------------------------------------------------

const BRIDGE_TIMEOUT_MS = 15_000;

interface PendingBridge {
  resolve: (result: Record<string, unknown>) => void;
  timer: NodeJS.Timeout;
}

const pendingBridge = new Map<string, PendingBridge>();
let bridgeSeq = 0;

function bridgeRequest(
  tool: "read_source" | "write_source" | "get_editor_context",
  params: Record<string, unknown>
): Promise<Record<string, unknown>> {
  const id = `b${++bridgeSeq}-${randomUUID()}`;
  return new Promise((resolve) => {
    const timer = setTimeout(() => {
      pendingBridge.delete(id);
      resolve({
        ok: false,
        error: `Bridge request '${tool}' timed out after ${BRIDGE_TIMEOUT_MS / 1000}s (Eclipse plug-in did not respond).`,
      });
    }, BRIDGE_TIMEOUT_MS);
    pendingBridge.set(id, { resolve, timer });
    writeStdout({ type: "bridge_request", id, tool, params });
  });
}

function resolveBridgeResponse(id: unknown, result: unknown): void {
  if (typeof id !== "string") return;
  const pending = pendingBridge.get(id);
  if (!pending) {
    log(`bridge_response for unknown/expired id '${id}' — ignored`);
    return;
  }
  pendingBridge.delete(id);
  clearTimeout(pending.timer);
  const r =
    result !== null && typeof result === "object"
      ? (result as Record<string, unknown>)
      : { ok: false, error: "Malformed bridge_response: result is not an object" };
  pending.resolve(r);
}

// ---------------------------------------------------------------------------
// Section 4: UI WebSocket state + frame sender
// ---------------------------------------------------------------------------

let uiSocket: WebSocket | null = null;

function sendToUi(frame: Record<string, unknown>): void {
  if (uiSocket && uiSocket.readyState === WebSocket.OPEN) {
    try {
      uiSocket.send(JSON.stringify(frame));
    } catch (e) {
      log("failed to send WS frame:", e);
    }
  }
}

// ---------------------------------------------------------------------------
// Section 5: session state
// ---------------------------------------------------------------------------

let activeQuery: Query | null = null;
let activeQueue: MessageQueue | null = null;
let lastSessionId: string | null = null;
let currentSessionId: string | null = null;
let currentModel: string | null = null;
let permissionMode: PermissionMode = (() => {
  const m = asWsPermissionMode(process.env.PERMISSION_MODE);
  return m ?? "default";
})();
let resumeOnNext = false;
// null = unknown (not yet probed); false = known-disconnected/absent.
let adtConnected: boolean | null = ADT_MCP_TOKEN ? null : false;
// null = CLI defaults. Model switches live via Query.setModel; effort has no
// runtime setter, so a change tears the query down and resumes the same
// conversation with the new level on the next message.
let modelOverride: string | null = null;
let effortOverride: EffortLevel | null = null;
let cachedModels: Array<{ value: string; displayName: string; supportsEffort: boolean }> | null =
  null;

/** Push-based async queue used as the streaming-input prompt generator. */
class MessageQueue implements AsyncIterable<SDKUserMessage> {
  private items: SDKUserMessage[] = [];
  private waiter: ((r: IteratorResult<SDKUserMessage, void>) => void) | null = null;
  private ended = false;

  push(m: SDKUserMessage): void {
    if (this.ended) return;
    if (this.waiter) {
      const w = this.waiter;
      this.waiter = null;
      w({ value: m, done: false });
    } else {
      this.items.push(m);
    }
  }

  end(): void {
    if (this.ended) return;
    this.ended = true;
    if (this.waiter) {
      const w = this.waiter;
      this.waiter = null;
      w({ value: undefined, done: true });
    }
  }

  [Symbol.asyncIterator](): AsyncIterator<SDKUserMessage, void> {
    return {
      next: (): Promise<IteratorResult<SDKUserMessage, void>> => {
        if (this.items.length > 0) {
          return Promise.resolve({ value: this.items.shift()!, done: false });
        }
        if (this.ended) {
          return Promise.resolve({ value: undefined, done: true });
        }
        return new Promise((res) => {
          this.waiter = res;
        });
      },
      return: (): Promise<IteratorResult<SDKUserMessage, void>> => {
        this.end();
        return Promise.resolve({ value: undefined, done: true });
      },
    };
  }
}

// ---------------------------------------------------------------------------
// Section 6: permission round-trip (canUseTool <-> UI permission cards)
// ---------------------------------------------------------------------------

const alwaysAllow = new Set<string>();
let permSeq = 0;

interface PermissionReply {
  behavior: "allow" | "deny";
  always: boolean;
}

const pendingPermissions = new Map<string, (r: PermissionReply) => void>();

const canUseTool: CanUseTool = (toolName, input, { signal }) => {
  // AskUserQuestion is resolved entirely through this permission callback: the
  // CLI's built-in tool reads the chosen option(s) back out of its OWN input
  // (`input.answers`, keyed by question text), which is delivered via the
  // `updatedInput` we return here. Auto-allowing with the input UNCHANGED (the
  // old behaviour) left `answers` absent, so the tool reported "The user did
  // not answer the questions." The `permission_ask_user_question`
  // request_user_dialog is the CLI's own REPL path and is never emitted to an
  // SDK host, so onUserDialog below never fires — we render the picker here.
  if (toolName === "AskUserQuestion") {
    if (!uiSocket || uiSocket.readyState !== WebSocket.OPEN) {
      // No panel to ask; allow unchanged so the tool degrades to "no answer"
      // rather than blocking the turn.
      return Promise.resolve<PermissionResult>({ behavior: "allow", updatedInput: input });
    }
    return askQuestionsViaUi(input, signal).then((raw) => {
      if (raw === null) {
        return { behavior: "deny", message: "User declined to answer the questions." };
      }
      // Mirror the CLI's own shape: single-select -> the bare label string,
      // multi-select -> the array of labels. Keyed by question text.
      const answers: Record<string, string | string[]> = {};
      for (const [q, labels] of Object.entries(raw)) {
        answers[q] = labels.length === 1 ? labels[0] : labels;
      }
      return {
        behavior: "allow",
        updatedInput: { ...(input as Record<string, unknown>), answers },
      };
    });
  }
  if (alwaysAllow.has(toolName)) {
    return Promise.resolve<PermissionResult>({ behavior: "allow", updatedInput: input });
  }
  if (!uiSocket || uiSocket.readyState !== WebSocket.OPEN) {
    return Promise.resolve<PermissionResult>({
      behavior: "deny",
      message: "Chat panel is not connected; cannot ask for permission.",
    });
  }
  const id = `perm-${++permSeq}`;
  return new Promise<PermissionResult>((resolve) => {
    pendingPermissions.set(id, (reply) => {
      pendingPermissions.delete(id);
      if (reply.behavior === "allow") {
        if (reply.always) alwaysAllow.add(toolName);
        resolve({ behavior: "allow", updatedInput: input });
      } else {
        resolve({ behavior: "deny", message: "User denied in chat panel" });
      }
    });
    signal.addEventListener(
      "abort",
      () => {
        if (pendingPermissions.delete(id)) {
          resolve({ behavior: "deny", message: "Interrupted before the user answered." });
        }
      },
      { once: true }
    );
    sendToUi({ type: "permission_request", id, toolName, input });
  });
};

function resolvePermissionResponse(msg: Record<string, unknown>): void {
  const id = typeof msg.id === "string" ? msg.id : null;
  if (!id) return;
  const fn = pendingPermissions.get(id);
  if (!fn) {
    log(`permission_response for unknown id '${id}' — ignored`);
    return;
  }
  fn({
    behavior: msg.behavior === "allow" ? "allow" : "deny",
    always: msg.always === true,
  });
}

// ---------------------------------------------------------------------------
// Section 6b: AskUserQuestion round-trip (canUseTool <-> UI question cards)
// ---------------------------------------------------------------------------

// AskUserQuestion is delivered to an SDK host purely through canUseTool (see
// Section 6): the CLI never emits the `permission_ask_user_question`
// request_user_dialog to an out-of-process consumer, so the onUserDialog path
// below is retained only as a harmless fallback should a future CLI wire it up.
// The live path is askQuestionsViaUi(), called from canUseTool.

let questionSeq = 0;
// Resolves with the chosen option label(s) per question ({ [question]: string[] }),
// or null if the user cancelled / the panel disconnected.
const pendingQuestions = new Map<string, (answers: Record<string, string[]> | null) => void>();

// Render the multiple-choice picker in the chat panel and await the user's
// selection. `input` is the AskUserQuestion tool input ({ questions: [...] });
// the UI's extractQuestions() reads `payload.questions` directly.
function askQuestionsViaUi(
  input: unknown,
  signal: AbortSignal
): Promise<Record<string, string[]> | null> {
  const id = `ask-${++questionSeq}`;
  return new Promise((resolve) => {
    pendingQuestions.set(id, (answers) => {
      pendingQuestions.delete(id);
      resolve(answers);
    });
    signal.addEventListener(
      "abort",
      () => {
        if (pendingQuestions.delete(id)) resolve(null);
      },
      { once: true }
    );
    sendToUi({ type: "question_request", id, payload: input });
  });
}

function resolveQuestionResponse(msg: Record<string, unknown>): void {
  const id = typeof msg.id === "string" ? msg.id : null;
  if (!id) return;
  const fn = pendingQuestions.get(id);
  if (!fn) {
    log(`question_response for unknown id '${id}' — ignored`);
    return;
  }
  if (msg.cancelled === true) {
    fn(null);
    return;
  }
  // The UI sends { answers: { [questionText]: string[] } } — the chosen option
  // label(s) per question. Normalise to string[] and hand back raw; the caller
  // (canUseTool) folds single-select answers to a bare string for the tool.
  const rawAnswers = (msg.answers ?? {}) as Record<string, unknown>;
  const answers: Record<string, string[]> = {};
  for (const [q, labels] of Object.entries(rawAnswers)) {
    answers[q] = Array.isArray(labels) ? labels.map((x) => String(x)) : [String(labels)];
  }
  fn(answers);
}

// ---------------------------------------------------------------------------
// Section 7: adt-bridge in-process MCP server (3 tools -> stdio RPC)
// ---------------------------------------------------------------------------

interface McpToolResult {
  content: Array<{ type: "text"; text: string }>;
  isError?: boolean;
  [key: string]: unknown;
}

function mcpText(text: string, isError = false): McpToolResult {
  const r: McpToolResult = { content: [{ type: "text", text }] };
  if (isError) r.isError = true;
  return r;
}

async function runBridgeTool(
  tool: "read_source" | "write_source" | "get_editor_context",
  params: Record<string, unknown>
): Promise<McpToolResult> {
  const result = await bridgeRequest(tool, params);
  if (result.ok === false) {
    return mcpText(
      typeof result.error === "string" && result.error
        ? result.error
        : "Bridge call failed (no error detail from Eclipse).",
      true
    );
  }
  return mcpText(JSON.stringify(result));
}

function buildBridgeServer(): McpSdkServerConfigWithInstance {
  return sdk.createSdkMcpServer({
    name: "adt-bridge",
    version: "1.0.0",
    instructions:
      "In-process bridge to the live Eclipse ADT editors. Objects must be OPEN in an ADT " +
      "editor to be readable/writable. Writes go through the editor buffer (visible and " +
      "undoable) and are restricted to allowlisted development systems.",
    tools: [
      sdk.tool(
        "read_source",
        "Read the full ABAP source of an object currently OPEN in an ADT editor",
        { object_name: z.string().describe("ABAP object name, e.g. ZCL_MY_CLASS") },
        async (args) => runBridgeTool("read_source", { object_name: args.object_name })
      ),
      sdk.tool(
        "write_source",
        "Replace the full source of an open ADT editor buffer (visible + undoable); " +
          "save:true runs ADT save (may prompt the user for transport)",
        {
          object_name: z.string().describe("ABAP object name, e.g. ZCL_MY_CLASS"),
          content: z.string().describe("The complete new source text for the object"),
          save: z
            .boolean()
            .optional()
            .describe("When true, run the ADT save pipeline after replacing the buffer"),
        },
        async (args) =>
          runBridgeTool("write_source", {
            object_name: args.object_name,
            content: args.content,
            ...(args.save === undefined ? {} : { save: args.save }),
          })
      ),
      sdk.tool(
        "get_editor_context",
        "List open ADT editors, the active editor and selection, and Dev-allowlist status",
        {},
        async () => runBridgeTool("get_editor_context", {})
      ),
    ],
  });
}

// ---------------------------------------------------------------------------
// Section 8: query lifecycle + message pump
// ---------------------------------------------------------------------------

const ABAP_WORKFLOW_GUIDANCE =
  "You are working inside Eclipse ABAP Development Tools (ADT). " +
  "For reading and writing ABAP source, always use the adt-bridge MCP tools " +
  "(read_source / write_source / get_editor_context) — they operate on the live editor " +
  "buffer, and objects must be OPEN in an ADT editor first; if a bridge call reports the " +
  "object is not open, ask the user to open it. Use the sap-adt-mcp MCP tools for everything " +
  "else on the ABAP system: activation, running unit tests, ATC checks, and transport " +
  "operations. Never guess ABAP signatures, types, or interfaces — read the relevant " +
  "source with read_source (or the sap-adt tools) before writing any code.";

// Built from the LIVE ADT URL/token so it can be re-applied to a running query
// via Query.setMcpServers when the token changes (see applyAdtConfig). Always
// includes the in-process bridge; setMcpServers replaces the whole dynamic set,
// so the bridge must be present on every rebuild or it would be disconnected.
function buildMcpServers(): Record<string, McpServerConfig> {
  const mcpServers: Record<string, McpServerConfig> = {
    "adt-bridge": buildBridgeServer(),
  };
  if (ADT_MCP_TOKEN) {
    // Named to match the tool grants in existing agent definitions
    // (e.g. the LLM Wiki's paul-dev allows mcp__sap-adt-mcp__*).
    mcpServers["sap-adt-mcp"] = {
      type: "http",
      url: ADT_MCP_URL,
      headers: { Authorization: `Bearer ${ADT_MCP_TOKEN}` },
    };
  }
  return mcpServers;
}

function buildOptions(): Options {
  const mcpServers = buildMcpServers();
  const options: Options = {
    systemPrompt: {
      type: "preset",
      preset: "claude_code",
      append: ABAP_WORKFLOW_GUIDANCE,
    },
    includePartialMessages: true,
    cwd: CLAUDE_CWD,
    // Behave like a real Claude Code session in CLAUDE_CWD: load CLAUDE.md,
    // .claude/settings hooks, .claude/agents subagents, and skills from the
    // user/project/local setting tiers.
    settingSources: ["user", "project", "local"],
    // Force AskUserQuestion onto the "ask" permission path in every mode. An
    // explicit ask-rule outranks the auto-mode classifier (decision_reason_type
    // rule > classifier), so the tool's answers always round-trip through
    // canUseTool instead of being auto-allowed with no selection. This flag tier
    // sits above user/project/local and permission rules union across tiers, so
    // it adds to — never replaces — the user's own rules. (bypassPermissions
    // still skips all checks; the picker is unavailable there by design.)
    settings: { permissions: { ask: ["AskUserQuestion"] } },
    permissionMode,
    // Required by the SDK before permissionMode "bypassPermissions" is honoured;
    // the actual mode is still user-selected in the UI dropdown.
    allowDangerouslySkipPermissions: true,
    mcpServers,
    allowedTools: [
      "mcp__adt-bridge__read_source",
      "mcp__adt-bridge__get_editor_context",
    ],
    // canUseTool also renders AskUserQuestion's multiple-choice picker (via
    // askQuestionsViaUi) and returns the selection through updatedInput.answers.
    canUseTool,
    stderr: (data: string) => process.stderr.write(data),
  };
  if (resumeOnNext && lastSessionId) {
    options.resume = lastSessionId;
  }
  if (modelOverride) {
    options.model = modelOverride;
  }
  if (effortOverride) {
    options.effort = effortOverride;
  }
  return options;
}

function ensureQuery(): void {
  if (activeQuery) return;
  const queue = new MessageQueue();
  activeQueue = queue;
  let q: Query;
  try {
    q = sdk.query({ prompt: queue, options: buildOptions() });
  } catch (e) {
    activeQueue = null;
    log("failed to start query:", e);
    sendToUi({ type: "error", message: `Failed to start Claude session: ${errMsg(e)}` });
    return;
  }
  activeQuery = q;
  resumeOnNext = false;
  currentSessionId = null;
  void runPump(q);
  startStatusPolling(q);
  // Control requests answer before the first user message (verified against
  // 0.3.201), so the model list and ADT status are available as soon as the
  // query exists. MCP connects async at spawn: re-probe early so the status
  // dot resolves in seconds rather than at the first 20s interval tick.
  void publishModels(q);
  void pollMcpStatus(q);
  for (const delay of [3000, 8000]) {
    const t = setTimeout(() => {
      if (activeQuery === q) void pollMcpStatus(q);
    }, delay);
    if (typeof t.unref === "function") t.unref();
  }
}

async function runPump(q: Query): Promise<void> {
  try {
    for await (const msg of q) {
      try {
        handleSdkMessage(q, msg);
      } catch (e) {
        log("error handling SDK message:", e);
      }
    }
  } catch (e) {
    // Deliberate teardown nulls activeQuery first — only report unexpected deaths.
    if (activeQuery === q) {
      log("query pump error:", e);
      sendToUi({ type: "error", message: `Claude session error: ${errMsg(e)}` });
    }
  } finally {
    if (activeQuery === q) {
      activeQuery = null;
      activeQueue = null;
    }
    stopStatusPolling(q);
    log("query pump finished");
  }
}

function handleSdkMessage(q: Query, msg: SDKMessage): void {
  switch (msg.type) {
    case "system": {
      if (msg.subtype === "init") {
        lastSessionId = msg.session_id;
        currentSessionId = msg.session_id;
        currentModel = msg.model;
        if (msg.permissionMode) permissionMode = msg.permissionMode;
        sendReadyFrame();
        void pollMcpStatus(q);
        void publishModels(q);
      }
      break;
    }
    case "stream_event": {
      if (msg.parent_tool_use_id !== null) break;
      const ev = msg.event as { type?: string; delta?: Record<string, unknown> };
      if (ev && ev.type === "content_block_delta" && ev.delta) {
        const d = ev.delta;
        if (d.type === "text_delta" && typeof d.text === "string") {
          sendToUi({ type: "assistant_text_delta", text: d.text });
        } else if (d.type === "thinking_delta" && typeof d.thinking === "string") {
          sendToUi({ type: "thinking_delta", text: d.thinking });
        }
      }
      break;
    }
    case "assistant": {
      if (msg.parent_tool_use_id !== null) break;
      const content = (msg.message as { content?: unknown }).content;
      if (!Array.isArray(content)) break;
      let text = "";
      for (const block of content as Array<Record<string, unknown>>) {
        if (!block || typeof block !== "object") continue;
        if (block.type === "text" && typeof block.text === "string") {
          text += block.text;
        } else if (block.type === "tool_use") {
          sendToUi({
            type: "tool_started",
            id: typeof block.id === "string" ? block.id : "",
            name: typeof block.name === "string" ? block.name : "",
            input:
              block.input !== null && typeof block.input === "object" ? block.input : {},
          });
        }
      }
      if (text) sendToUi({ type: "assistant_message_final", text });
      break;
    }
    case "user": {
      if (msg.parent_tool_use_id !== null) break;
      const content = (msg.message as { content?: unknown }).content;
      if (!Array.isArray(content)) break;
      for (const block of content as Array<Record<string, unknown>>) {
        if (!block || typeof block !== "object" || block.type !== "tool_result") continue;
        sendToUi({
          type: "tool_result",
          id: typeof block.tool_use_id === "string" ? block.tool_use_id : "",
          ok: block.is_error !== true,
          preview: extractPreview(block.content),
        });
      }
      break;
    }
    case "result": {
      lastSessionId = msg.session_id ?? lastSessionId;
      sendToUi({
        type: "turn_complete",
        costUsd: typeof msg.total_cost_usd === "number" ? msg.total_cost_usd : null,
        durationMs: typeof msg.duration_ms === "number" ? msg.duration_ms : null,
        sessionId: msg.session_id ?? null,
      });
      break;
    }
    default:
      break;
  }
}

const PREVIEW_LIMIT = 500;

function extractPreview(content: unknown): string {
  let text: string;
  if (typeof content === "string") {
    text = content;
  } else if (Array.isArray(content)) {
    text = content
      .map((item) =>
        item && typeof item === "object" && (item as Record<string, unknown>).type === "text"
          ? String((item as Record<string, unknown>).text ?? "")
          : ""
      )
      .join("");
    if (!text) text = safeStringify(content);
  } else if (content === undefined || content === null) {
    text = "";
  } else {
    text = safeStringify(content);
  }
  return text.length > PREVIEW_LIMIT ? text.slice(0, PREVIEW_LIMIT) + "…" : text;
}

function teardownQuery(): void {
  const q = activeQuery;
  const queue = activeQueue;
  activeQuery = null;
  activeQueue = null;
  currentSessionId = null;
  if (queue) {
    try {
      queue.end();
    } catch {
      /* ignore */
    }
  }
  if (q) {
    stopStatusPolling(q);
    try {
      q.interrupt().catch(() => {
        /* ignore — session may not be running */
      });
    } catch {
      /* ignore */
    }
    try {
      if (typeof q.close === "function") q.close();
    } catch (e) {
      log("query close failed:", e);
    }
  }
  // Deny anything still waiting on a permission card from the old session.
  for (const [, fn] of pendingPermissions) {
    try {
      fn({ behavior: "deny", always: false });
    } catch {
      /* ignore */
    }
  }
  pendingPermissions.clear();
}

// ---------------------------------------------------------------------------
// Section 9: ADT MCP status polling
// ---------------------------------------------------------------------------

const STATUS_POLL_MS = 20_000;
let statusTimer: NodeJS.Timeout | null = null;
let statusTimerOwner: Query | null = null;

function startStatusPolling(q: Query): void {
  stopStatusPollingAny();
  statusTimerOwner = q;
  statusTimer = setInterval(() => {
    if (activeQuery !== q) {
      stopStatusPolling(q);
      return;
    }
    void pollMcpStatus(q);
  }, STATUS_POLL_MS);
  if (typeof statusTimer.unref === "function") statusTimer.unref();
}

function stopStatusPolling(q: Query): void {
  if (statusTimerOwner === q) stopStatusPollingAny();
}

function stopStatusPollingAny(): void {
  if (statusTimer) clearInterval(statusTimer);
  statusTimer = null;
  statusTimerOwner = null;
}

async function pollMcpStatus(q: Query): Promise<void> {
  if (typeof q.mcpServerStatus !== "function") return;
  try {
    const statuses = await q.mcpServerStatus();
    if (!Array.isArray(statuses)) return;
    const sap = statuses.find((s) => s && s.name === "sap-adt-mcp");
    const connected = !!sap && sap.status === "connected";
    adtConnected = connected;
    sendToUi({
      type: "status",
      adtMcp: { connected },
      model: currentModel,
    });
    // Any non-connected terminal-ish state is worth a reconnect: the ADT HTTP
    // server may have come up after us, or auth may have settled. 'pending' is
    // the transient connecting state, so leave it alone to avoid churn.
    if (
      sap &&
      (sap.status === "failed" || sap.status === "disabled" || sap.status === "needs-auth") &&
      typeof q.reconnectMcpServer === "function" &&
      activeQuery === q
    ) {
      log(`sap-adt-mcp server status '${sap.status}' — attempting reconnect`);
      q.reconnectMcpServer("sap-adt-mcp").catch((e: unknown) =>
        log("sap-adt-mcp reconnect failed:", e)
      );
    }
  } catch (e) {
    log("mcpServerStatus() failed:", e);
  }
}

/**
 * Live-apply an ADT MCP config pushed from Java (url/token). Corrects a token
 * that was empty or stale at spawn without restarting the process: updates the
 * mutable url/token and, if the effective config changed while a query is live,
 * re-registers sap-adt-mcp via Query.setMcpServers (which reconnects the server
 * with the fresh Bearer token and keeps the in-process bridge). A short re-poll
 * settles the status dot within seconds rather than at the next 20s tick.
 */
async function applyAdtConfig(url: string, token: string): Promise<void> {
  const nextUrl = url.trim() || ADT_MCP_URL;
  const nextToken = token.trim();
  if (nextUrl === ADT_MCP_URL && nextToken === ADT_MCP_TOKEN) {
    return; // no change — avoid needless reconnect churn
  }
  ADT_MCP_URL = nextUrl;
  ADT_MCP_TOKEN = nextToken;
  log(`adt_config applied: url=${ADT_MCP_URL} token=${ADT_MCP_TOKEN ? "present" : "(none)"}`);
  const q = activeQuery;
  if (!q || typeof q.setMcpServers !== "function") {
    // No live query yet (or SDK too old): the new values are used the next
    // time a query is built. Not connected until a query exists and polls.
    adtConnected = ADT_MCP_TOKEN ? null : false;
    sendToUi({ type: "status", adtMcp: { connected: false }, model: currentModel });
    return;
  }
  try {
    const result = await q.setMcpServers(buildMcpServers());
    if (result && result.errors && result.errors["sap-adt-mcp"]) {
      log("setMcpServers reported sap-adt-mcp error:", result.errors["sap-adt-mcp"]);
    }
  } catch (e) {
    log("setMcpServers failed:", e);
  }
  if (activeQuery === q) void pollMcpStatus(q);
}

// ---------------------------------------------------------------------------
// Section 10: WS southbound (UI -> sidecar) handling
// ---------------------------------------------------------------------------

function sendReadyFrame(): void {
  sendToUi({
    type: "ready",
    sessionId: currentSessionId ?? (resumeOnNext ? lastSessionId : null),
    model: currentModel,
    cwd: CLAUDE_CWD,
    permissionMode,
    devAllowlist: DEV_ALLOWLIST,
    adtMcp: { connected: adtConnected },
    modelOverride,
    effort: effortOverride,
  });
}

async function publishModels(q: Query): Promise<void> {
  if (cachedModels || typeof q.supportedModels !== "function") return;
  try {
    const list = await q.supportedModels();
    if (!Array.isArray(list) || list.length === 0) return;
    cachedModels = list.map((m) => ({
      value: String(m.value),
      displayName: String(m.displayName ?? m.value),
      supportsEffort: m.supportsEffort === true,
    }));
    sendModelsFrame();
  } catch (e) {
    log("supportedModels() failed:", e);
  }
}

function sendModelsFrame(): void {
  if (cachedModels) {
    sendToUi({ type: "models", models: cachedModels });
  }
}

interface EditorSelection {
  start_line?: number;
  end_line?: number;
  text?: string;
}

function formatContextBlock(context: Record<string, unknown>): string {
  const objectName =
    typeof context.object_name === "string" ? context.object_name : "(unknown object)";
  const project = typeof context.project === "string" ? context.project : null;
  const lines: string[] = ["[Editor context from ADT]", `Object: ${objectName}`];
  if (project) lines.push(`Project: ${project}`);
  const sel =
    context.selection !== null && typeof context.selection === "object"
      ? (context.selection as EditorSelection)
      : null;
  if (sel && typeof sel.text === "string" && sel.text.length > 0) {
    const range =
      typeof sel.start_line === "number" && typeof sel.end_line === "number"
        ? ` (lines ${sel.start_line}-${sel.end_line})`
        : "";
    lines.push(`Selected code${range}:`);
    lines.push("```abap");
    lines.push(sel.text);
    lines.push("```");
  }
  return lines.join("\n");
}

interface SavedAttachment {
  path: string; // the path the agent should Read (extracted text for Office files)
  originalPath: string; // the raw uploaded file as written to disk
  name: string; // display name (original filename)
  size: number;
  mime: string;
  note?: string; // set when path is an extracted-text sibling, e.g. "Excel → CSV"
}

// basename only, non-safe chars collapsed, leading dots stripped: prevents path
// traversal (../, absolute paths) and keeps the on-disk name predictable.
function sanitiseFilename(name: string): string {
  const base = path.basename(String(name || "file"));
  const cleaned = base.replace(/[^A-Za-z0-9._-]+/g, "_").replace(/^\.+/, "");
  return cleaned || "file";
}

// Extract text from Excel/Word into a sibling file the Read tool can consume.
// Both libraries are externalised and vendored into sidecar/node_modules;
// imported lazily so a session that never uploads Office files pays nothing.
async function convertOfficeToText(
  buf: Buffer,
  srcPath: string,
  ext: string
): Promise<{ path: string; note: string } | null> {
  try {
    if (ext === ".xlsx" || ext === ".xlsm" || ext === ".xls") {
      // Read from the buffer (XLSX.readFile's fs binding is unreliable under
      // the bundled/externalised interop; XLSX.read on a Buffer is portable).
      const XLSX = await import("xlsx");
      const wb = XLSX.read(buf, { type: "buffer" });
      const parts: string[] = [];
      for (const sheetName of wb.SheetNames) {
        const sheet = wb.Sheets[sheetName];
        const csv = XLSX.utils.sheet_to_csv(sheet);
        parts.push(`# Sheet: ${sheetName}\n\n${csv}`);
      }
      const out = srcPath + ".extracted.md";
      fs.writeFileSync(out, parts.join("\n\n") || "(empty workbook)");
      return { path: out, note: "Excel → CSV text" };
    }
    if (ext === ".docx") {
      const mammoth = await import("mammoth");
      const result = await mammoth.extractRawText({ buffer: buf });
      const out = srcPath + ".extracted.md";
      fs.writeFileSync(out, result.value || "(empty document)");
      return { path: out, note: "Word → text" };
    }
  } catch (e) {
    log("office conversion failed:", srcPath, e);
    return null;
  }
  return null;
}

async function materialiseAttachments(raw: unknown): Promise<{
  saved: SavedAttachment[];
  errors: string[];
}> {
  const saved: SavedAttachment[] = [];
  const errors: string[] = [];
  if (!Array.isArray(raw) || raw.length === 0) return { saved, errors };

  const stamp = new Date().toISOString().replace(/[:.]/g, "-");
  const dir = path.join(UPLOADS_ROOT, stamp);
  let total = 0;

  for (const item of raw) {
    if (!item || typeof item !== "object") continue;
    const a = item as Record<string, unknown>;
    const name = typeof a.name === "string" ? a.name : "file";
    const b64 = typeof a.dataBase64 === "string" ? a.dataBase64 : "";
    if (!b64) {
      errors.push(`${name}: empty`);
      continue;
    }
    const safe = sanitiseFilename(name);
    const ext = path.extname(safe).toLowerCase();
    if (!ALLOWED_ATTACH_EXT.has(ext)) {
      errors.push(`${name}: type ${ext || "(none)"} not supported`);
      continue;
    }
    let buf: Buffer;
    try {
      buf = Buffer.from(b64, "base64");
    } catch {
      errors.push(`${name}: could not decode`);
      continue;
    }
    if (buf.length > MAX_ATTACH_BYTES) {
      errors.push(`${name}: over ${Math.round(MAX_ATTACH_BYTES / (1024 * 1024))} MB`);
      continue;
    }
    total += buf.length;
    if (total > MAX_ATTACH_TOTAL_BYTES) {
      errors.push(`${name}: message upload size exceeded`);
      break;
    }
    try {
      fs.mkdirSync(dir, { recursive: true });
      let dest = path.join(dir, safe);
      const stem = path.basename(safe, ext);
      let n = 1;
      while (fs.existsSync(dest)) {
        dest = path.join(dir, `${stem}-${n}${ext}`);
        n++;
      }
      fs.writeFileSync(dest, buf);

      let readPath = dest;
      let note: string | undefined;
      if (OFFICE_EXT.has(ext)) {
        const converted = await convertOfficeToText(buf, dest, ext);
        if (converted) {
          readPath = converted.path;
          note = converted.note;
        } else {
          errors.push(`${path.basename(dest)}: stored but text extraction failed`);
        }
      }

      saved.push({
        path: readPath,
        originalPath: dest,
        name: path.basename(dest),
        size: buf.length,
        mime: typeof a.mime === "string" ? a.mime : "",
        note,
      });
    } catch (e) {
      errors.push(`${name}: write failed`);
      log("attachment write failed:", e);
    }
  }
  return { saved, errors };
}

function cleanupUploads(): void {
  try {
    fs.rmSync(UPLOADS_ROOT, { recursive: true, force: true });
  } catch (e) {
    log("uploads cleanup failed:", e);
  }
}

function formatAttachmentsBlock(saved: SavedAttachment[]): string {
  const lines = [
    "[Attached files — saved to the session workspace; read them with the Read tool]",
  ];
  for (const f of saved) {
    const kb = Math.max(1, Math.round(f.size / 1024));
    if (f.note) {
      lines.push(`- ${f.path} (${f.note} extracted from ${f.name}, original ${kb} KB)`);
    } else {
      lines.push(`- ${f.path} (${f.mime || "unknown type"}, ${kb} KB)`);
    }
  }
  return lines.join("\n");
}

async function handleUserMessage(msg: Record<string, unknown>): Promise<void> {
  const text = typeof msg.text === "string" ? msg.text : "";
  const { saved, errors } = await materialiseAttachments(msg.attachments);
  if (errors.length) {
    sendToUi({
      type: "error",
      message: "Some attachments were rejected: " + errors.join("; "),
    });
  }
  if (!text.trim() && saved.length === 0) return;

  const parts: string[] = [];
  if (msg.context !== null && msg.context !== undefined && typeof msg.context === "object") {
    parts.push(formatContextBlock(msg.context as Record<string, unknown>));
  }
  if (saved.length > 0) {
    parts.push(formatAttachmentsBlock(saved));
  }
  if (text) parts.push(text);
  const prompt = parts.join("\n\n");

  ensureQuery();
  if (!activeQueue) {
    sendToUi({ type: "error", message: "Claude session is not available; try New Session." });
    return;
  }
  const userMessage: SDKUserMessage = {
    type: "user",
    message: { role: "user", content: prompt },
    parent_tool_use_id: null,
  };
  activeQueue.push(userMessage);
}

function handleWsMessage(raw: string): void {
  let msg: Record<string, unknown>;
  try {
    const parsed: unknown = JSON.parse(raw);
    if (parsed === null || typeof parsed !== "object") return;
    msg = parsed as Record<string, unknown>;
  } catch {
    log("ignoring non-JSON WS message");
    return;
  }
  switch (msg.type) {
    case "user_message":
      handleUserMessage(msg).catch((e: unknown) => {
        log("handleUserMessage failed:", e);
        sendToUi({ type: "error", message: "Failed to process the message or its attachments." });
      });
      break;
    case "permission_response":
      resolvePermissionResponse(msg);
      break;
    case "question_response":
      resolveQuestionResponse(msg);
      break;
    case "interrupt":
      if (activeQuery) {
        try {
          activeQuery.interrupt().catch((e: unknown) => log("interrupt failed:", e));
        } catch (e) {
          log("interrupt threw:", e);
        }
      }
      break;
    case "new_session":
      teardownQuery();
      cleanupUploads();
      resumeOnNext = false;
      currentModel = null;
      sendReadyFrame();
      ensureQuery(); // re-warm so the next message has no spawn latency
      break;
    case "resume_session":
      teardownQuery();
      resumeOnNext = lastSessionId !== null;
      if (!resumeOnNext) {
        sendToUi({ type: "error", message: "No previous session to resume." });
      }
      sendReadyFrame();
      ensureQuery();
      break;
    case "set_model": {
      const model =
        typeof msg.model === "string" && msg.model.trim() ? msg.model.trim() : null;
      modelOverride = model;
      const q = activeQuery;
      if (q && typeof q.setModel === "function") {
        q.setModel(model ?? undefined)
          .then(() => {
            currentModel = model ?? currentModel;
            sendToUi({
              type: "status",
              adtMcp: { connected: adtConnected === true },
              model: currentModel,
            });
          })
          .catch((e: unknown) => {
            log("setModel failed:", e);
            sendToUi({ type: "error", message: `Could not switch model: ${errMsg(e)}` });
          });
      }
      break;
    }
    case "set_effort": {
      const raw = typeof msg.effort === "string" ? msg.effort.trim() : "";
      const valid: readonly string[] = ["low", "medium", "high", "xhigh", "max"];
      if (raw && !valid.includes(raw)) {
        sendToUi({ type: "error", message: `Invalid effort level: ${safeStringify(msg.effort)}` });
        break;
      }
      effortOverride = (raw || null) as EffortLevel | null;
      if (activeQuery) {
        // No runtime effort setter in the SDK: restart the query and resume
        // this conversation so the new level applies from the next message.
        teardownQuery();
        resumeOnNext = lastSessionId !== null;
      }
      sendReadyFrame();
      ensureQuery();
      break;
    }
    case "set_permission_mode": {
      const mode = asWsPermissionMode(msg.mode);
      if (!mode) {
        sendToUi({ type: "error", message: `Invalid permission mode: ${safeStringify(msg.mode)}` });
        break;
      }
      permissionMode = mode;
      if (activeQuery && typeof activeQuery.setPermissionMode === "function") {
        activeQuery
          .setPermissionMode(mode)
          .catch((e: unknown) => log("setPermissionMode failed:", e));
      }
      break;
    }
    default:
      log(`unknown WS message type: ${safeStringify(msg.type)}`);
      break;
  }
}

// ---------------------------------------------------------------------------
// Section 11: HTTP static server + WebSocket endpoint
// ---------------------------------------------------------------------------

const CONTENT_TYPES: Record<string, string> = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".ico": "image/x-icon",
  ".json": "application/json; charset=utf-8",
  ".map": "application/json; charset=utf-8",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
};

let boundPort = 0;
const uiRoot = path.resolve(UI_DIR);

function serveStatic(req: http.IncomingMessage, res: http.ServerResponse): void {
  if (req.method !== "GET" && req.method !== "HEAD") {
    res.writeHead(405, { "Content-Type": "text/plain" }).end("Method Not Allowed");
    return;
  }
  let pathname: string;
  try {
    pathname = decodeURIComponent(
      new URL(req.url ?? "/", `http://127.0.0.1:${boundPort}`).pathname
    );
  } catch {
    res.writeHead(400, { "Content-Type": "text/plain" }).end("Bad Request");
    return;
  }
  if (pathname !== "/ui" && pathname !== "/ui/" && !pathname.startsWith("/ui/")) {
    res.writeHead(404, { "Content-Type": "text/plain" }).end("Not Found");
    return;
  }
  let rel = pathname === "/ui" || pathname === "/ui/" ? "index.html" : pathname.slice("/ui/".length);
  if (!rel) rel = "index.html";
  const filePath = path.resolve(uiRoot, rel);
  if (filePath !== uiRoot && !filePath.startsWith(uiRoot + path.sep)) {
    res.writeHead(403, { "Content-Type": "text/plain" }).end("Forbidden");
    return;
  }
  fs.readFile(filePath, (err, data) => {
    if (err) {
      res.writeHead(404, { "Content-Type": "text/plain" }).end("Not Found");
      return;
    }
    const contentType =
      CONTENT_TYPES[path.extname(filePath).toLowerCase()] ?? "application/octet-stream";
    res.writeHead(200, {
      "Content-Type": contentType,
      "Content-Length": data.length,
      "Cache-Control": "no-store",
    });
    res.end(req.method === "HEAD" ? undefined : data);
  });
}

function startHttpServer(): Promise<http.Server> {
  return new Promise((resolve, reject) => {
    const server = http.createServer(serveStatic);
    const wss = new WebSocketServer({ noServer: true });

    server.on("upgrade", (req, socket, head) => {
      try {
        const url = new URL(req.url ?? "", `http://127.0.0.1:${boundPort}`);
        if (url.pathname !== "/ws") {
          socket.destroy();
          return;
        }
        if (url.searchParams.get("token") !== UI_TOKEN) {
          log("WS upgrade rejected: bad token");
          socket.destroy();
          return;
        }
        const origin = req.headers.origin;
        if (origin !== undefined && origin !== `http://127.0.0.1:${boundPort}`) {
          log(`WS upgrade rejected: bad origin '${origin}'`);
          socket.destroy();
          return;
        }
        wss.handleUpgrade(req, socket, head, (ws) => {
          wss.emit("connection", ws, req);
        });
      } catch (e) {
        log("WS upgrade error:", e);
        socket.destroy();
      }
    });

    wss.on("connection", (ws: WebSocket) => {
      if (uiSocket && uiSocket !== ws) {
        try {
          uiSocket.close(4000, "superseded by a new connection");
        } catch {
          /* ignore */
        }
      }
      uiSocket = ws;
      log("UI WebSocket connected");

      ws.on("message", (data: unknown) => {
        try {
          handleWsMessage(String(data));
        } catch (e) {
          log("error handling WS message:", e);
        }
      });
      ws.on("close", () => {
        if (uiSocket === ws) uiSocket = null;
        log("UI WebSocket closed");
      });
      ws.on("error", (e: unknown) => log("UI WebSocket error:", e));

      sendReadyFrame();
      sendModelsFrame();
      if (!ADT_MCP_TOKEN) {
        sendToUi({ type: "status", adtMcp: { connected: false }, model: currentModel });
        sendToUi({
          type: "error",
          message:
            "ADT MCP Server is not available: no token was found. Enable it in Eclipse " +
            "Preferences → ABAP Development → MCP Server, then reopen this panel. " +
            "Source read/write through the editor bridge still works.",
        });
      }
    });

    server.on("error", (e) => reject(e));
    server.listen(0, "127.0.0.1", () => {
      const addr = server.address();
      if (addr === null || typeof addr === "string") {
        reject(new Error("HTTP server bound to a non-TCP address"));
        return;
      }
      boundPort = addr.port;
      resolve(server);
    });
  });
}

// ---------------------------------------------------------------------------
// Section 12: stdio northbound (Java -> sidecar)
// ---------------------------------------------------------------------------

function startStdinReader(): void {
  const rl = readline.createInterface({ input: process.stdin, terminal: false });
  rl.on("line", (line: string) => {
    const trimmed = line.trim();
    if (!trimmed) return;
    let frame: Record<string, unknown>;
    try {
      const parsed: unknown = JSON.parse(trimmed);
      if (parsed === null || typeof parsed !== "object") return;
      frame = parsed as Record<string, unknown>;
    } catch {
      log("ignoring non-JSON stdin line");
      return;
    }
    try {
      switch (frame.type) {
        case "bridge_response":
          resolveBridgeResponse(frame.id, frame.result);
          break;
        case "editor_context":
          // Forward verbatim to the UI (it renders an attach-chip).
          sendToUi(frame);
          break;
        case "adt_config": {
          // Live ADT MCP url/token push from Java (ready + on settings change).
          const url = typeof frame.url === "string" ? frame.url : "";
          const token = typeof frame.token === "string" ? frame.token : "";
          void applyAdtConfig(url, token);
          break;
        }
        case "shutdown":
          log("shutdown frame received — exiting");
          gracefulExit(0);
          break;
        default:
          log(`unknown stdin frame type: ${safeStringify(frame.type)}`);
          break;
      }
    } catch (e) {
      log("error handling stdin frame:", e);
    }
  });
  rl.on("close", () => {
    log("stdin closed (EOF) — exiting");
    gracefulExit(0);
  });
  process.stdin.on("error", (e) => {
    log("stdin error:", e);
    gracefulExit(0);
  });
}

let exiting = false;

function gracefulExit(code: number): void {
  if (exiting) return;
  exiting = true;
  try {
    teardownQuery();
  } catch {
    /* ignore */
  }
  // Give teardown a beat, then hard-exit; Java expects prompt self-termination.
  setTimeout(() => process.exit(code), 150).unref();
  process.exitCode = code;
}

// ---------------------------------------------------------------------------
// Section 13: startup
// ---------------------------------------------------------------------------

process.on("unhandledRejection", (reason) => {
  log("unhandledRejection:", reason instanceof Error ? reason : safeStringify(reason));
});
process.on("uncaughtException", (err) => {
  log("uncaughtException:", err);
});
process.on("SIGTERM", () => gracefulExit(0));
process.on("SIGINT", () => gracefulExit(0));

/**
 * The Agent SDK resolves the Claude CLI from a vendored platform package
 * (node_modules/@anthropic-ai/claude-agent-sdk-<platform>/claude). p2 unzips
 * the plug-in at install time (Eclipse-BundleShape: dir) without preserving
 * unix permissions, so restore the execute bit before the SDK spawns it.
 */
function ensureVendoredCliExecutable(): void {
  const scope = path.join(__dirname, "node_modules", "@anthropic-ai");
  let entries: string[];
  try {
    entries = fs.readdirSync(scope);
  } catch {
    return; // no vendored scope (dev override tree) — fine
  }
  for (const entry of entries) {
    const bin = path.join(scope, entry, "claude");
    try {
      const st = fs.statSync(bin);
      if (st.isFile() && (st.mode & 0o111) === 0) {
        fs.chmodSync(bin, 0o755);
        log(`restored execute bit on ${bin}`);
      }
    } catch {
      /* package without a claude binary — fine */
    }
  }
}

async function main(): Promise<void> {
  ensureVendoredCliExecutable();
  sdk = (await dynamicImport("@anthropic-ai/claude-agent-sdk")) as SdkModule;
  log(`Agent SDK loaded; cwd=${CLAUDE_CWD} adtMcp=${ADT_MCP_TOKEN ? ADT_MCP_URL : "(disabled: no token)"}`);
  startStdinReader();
  await startHttpServer();
  log(`HTTP/WS listening on 127.0.0.1:${boundPort} (ui from ${uiRoot})`);
  writeStdout({ type: "ready", uiPort: boundPort });
  // Warm-start the session: the CLI spawn cost is paid before the first
  // message, and the model list is fetched for the header dropdown.
  ensureQuery();
}

main().catch((e) => {
  log("FATAL during startup:", e);
  process.exit(1);
});
