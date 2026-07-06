/* Claude Code for ABAP — chat UI client.
 * Vanilla TypeScript, bundled by esbuild into ../web/app.js.
 * Talks the pinned WS protocol to the sidecar at ws://<host>/ws?token=<UI_TOKEN>.
 * Self-contained: no CDN, no external fonts, no cross-origin fetches.
 */

import { marked } from "marked";
import DOMPurify from "dompurify";
import hljs from "highlight.js/lib/core";
import jsonLang from "highlight.js/lib/languages/json";
import type { LanguageFn } from "highlight.js";

/* highlight.js core ships no ABAP grammar (it is a third-party module), so a
 * compact grammar is defined inline — keeps the bundle self-contained. */
const abapLanguage: LanguageFn = (h) => {
  const KEYWORDS =
    "report program data types constants tables parameters select-options " +
    "class endclass methods method endmethod class-methods class-data " +
    "interface endinterface interfaces function endfunction form endform " +
    "perform module endmodule if else elseif endif case when others endcase " +
    "loop endloop do enddo while endwhile try catch cleanup endtry " +
    "select endselect from where into and or not is between like in " +
    "for all entries inner left outer join on as order by group having " +
    "single up to rows appending corresponding fields of table begin end " +
    "read modify delete insert update append clear refresh free move " +
    "move-corresponding concatenate split condense translate replace shift " +
    "assign unassign check exit continue return leave submit commit rollback " +
    "work call new create object ref value type standard sorted hashed with " +
    "unique non-unique key default optional preferred parameter returning " +
    "importing exporting changing raising exceptions exception raise event " +
    "events message authority-check start-of-selection end-of-selection " +
    "initialization at selection-screen field-symbols field-symbol casting " +
    "public private protected section final abstract definition " +
    "implementation inheriting redefinition constructor aliases include " +
    "structure occurs header line ranges write uline skip format sort " +
    "ascending descending reduce filter cond switch conv exact lines strlen " +
    "using testing duration risk level then until step next me super wait " +
    "assigned bound instance supplied requested initial";
  return {
    name: "ABAP",
    case_insensitive: true,
    keywords: {
      $pattern: "[a-zA-Z][\\w-]*",
      keyword: KEYWORDS,
      built_in:
        "sy-subrc sy-tabix sy-index sy-dbcnt sy-datum sy-uzeit sy-uname " +
        "sy-mandt sy-langu sy-msgid sy-msgno sy-msgty sy-msgv1 sy-msgv2 " +
        "sy-msgv3 sy-msgv4 sy-repid sy-tcode sy-ucomm string xstring " +
        "abap_bool decfloat16 decfloat34 int8 utclong timestamp timestampl",
      literal: "abap_true abap_false abap_undefined space",
    },
    contains: [
      h.COMMENT(/^\*/, /$/),
      h.COMMENT(/"/, /$/),
      {
        className: "string",
        variants: [
          { begin: /'/, end: /'/, contains: [{ begin: /''/ }] },
          { begin: /`/, end: /`/ },
        ],
      },
      {
        className: "string",
        begin: /\|/,
        end: /\|/,
        contains: [
          { begin: /\\\|/ },
          { className: "subst", begin: /\{/, end: /\}/ },
        ],
      },
      { className: "number", begin: /\b\d+(\.\d+)?\b/ },
      { className: "symbol", begin: /<[a-zA-Z_]\w*>/ },
      { className: "meta", begin: /##\w+/ },
    ],
  };
};

hljs.registerLanguage("abap", abapLanguage);
hljs.registerLanguage("json", jsonLang);

marked.setOptions({ gfm: true, breaks: true });

// Links must not navigate the docked panel away from the chat.
DOMPurify.addHook("afterSanitizeAttributes", (node) => {
  if (node.tagName === "A") {
    node.setAttribute("target", "_blank");
    node.setAttribute("rel", "noopener noreferrer");
  }
});

/* ---------------- protocol types (pinned contract) ---------------- */

interface EditorSelection {
  start_line: number;
  end_line: number;
  text: string;
}

interface EditorContext {
  object_name: string;
  project: string | null;
  selection?: EditorSelection;
}

interface ReadyFrame {
  type: "ready";
  sessionId: string | null;
  model: string | null;
  cwd: string;
  permissionMode: string;
  devAllowlist: string;
  adtMcp: { connected: boolean | null };
  modelOverride?: string | null;
  effort?: string | null;
}

interface ModelOption {
  value: string;
  displayName: string;
  supportsEffort?: boolean;
}

type ServerFrame =
  | ReadyFrame
  | { type: "models"; models: ModelOption[] }
  | { type: "assistant_text_delta"; text: string }
  | { type: "thinking_delta"; text: string }
  | { type: "assistant_message_final"; text: string }
  | { type: "tool_started"; id: string; name: string; input: Record<string, unknown> }
  | { type: "tool_result"; id: string; ok: boolean; preview: string }
  | { type: "permission_request"; id: string; toolName: string; input: Record<string, unknown> }
  | { type: "turn_complete"; costUsd: number | null; durationMs: number | null; sessionId: string | null }
  | { type: "status"; adtMcp: { connected: boolean }; model: string | null }
  | { type: "error"; message: string }
  | { type: "editor_context"; context: EditorContext };

/* ---------------- bootstrap: query params + theme ---------------- */

const params = new URLSearchParams(location.search);
const token = params.get("token") ?? "";
const themeParam = params.get("theme");

document.documentElement.dataset.theme =
  themeParam === "dark" || themeParam === "light"
    ? themeParam
    : window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light";

/* ---------------- DOM refs ---------------- */

function el<T extends HTMLElement>(id: string): T {
  const e = document.getElementById(id);
  if (!e) throw new Error("missing element #" + id);
  return e as T;
}

const titleEl = el<HTMLSpanElement>("title");
const modelChip = el<HTMLSpanElement>("model-chip");
const adtDot = el<HTMLSpanElement>("adt-dot");
const permSelect = el<HTMLSelectElement>("permission-mode");
const modelSelect = el<HTMLSelectElement>("model-select");
const effortSelect = el<HTMLSelectElement>("effort-select");
const btnNew = el<HTMLButtonElement>("btn-new");
const btnStop = el<HTMLButtonElement>("btn-stop");
const banner = el<HTMLDivElement>("banner");
const transcript = el<HTMLElement>("transcript");
const attachArea = el<HTMLDivElement>("attach-area");
const attachChip = el<HTMLSpanElement>("attach-chip");
const attachDismiss = el<HTMLButtonElement>("attach-dismiss");
const input = el<HTMLTextAreaElement>("input");
const btnSend = el<HTMLButtonElement>("btn-send");

/* ---------------- state ---------------- */

let ws: WebSocket | null = null;
let wsOpen = false;
let sessionReady = false;
let busy = false;
let backoff = 500;
const BACKOFF_MAX = 10000;

interface AssistantBubble {
  root: HTMLElement;
  md: HTMLElement;
  thinkingPre: HTMLElement | null;
}
let current: AssistantBubble | null = null;
let currentMd = "";
let renderTimer: number | null = null;
let lastRenderAt = 0;
const RENDER_THROTTLE_MS = 100;

interface ToolEntry {
  chip: HTMLButtonElement;
  status: HTMLSpanElement;
  spinner: HTMLSpanElement;
  detail: HTMLPreElement;
  inputJson: string;
}
const tools = new Map<string, ToolEntry>();

let pendingContext: EditorContext | null = null;

/* ---------------- helpers ---------------- */

function sendFrame(obj: unknown): void {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(obj));
  }
}

function shortToolName(name: string): string {
  return name.replace(/^mcp__.+?__/, "");
}

function atBottom(): boolean {
  return transcript.scrollHeight - transcript.scrollTop - transcript.clientHeight < 40;
}

/** Run a transcript mutation, keeping the view pinned to the bottom only if the
 *  user was already there. */
function withStick(fn: () => void): void {
  const stick = atBottom();
  fn();
  if (stick) transcript.scrollTop = transcript.scrollHeight;
}

function appendEntry(node: HTMLElement): void {
  withStick(() => transcript.appendChild(node));
}

function renderMarkdownInto(target: HTMLElement, md: string): void {
  const html = marked.parse(md, { async: false }) as string;
  target.innerHTML = DOMPurify.sanitize(html, { USE_PROFILES: { html: true } });
  highlightCodeIn(target);
}

function highlightCodeIn(container: HTMLElement): void {
  container.querySelectorAll<HTMLElement>("pre code").forEach((block) => {
    const m = /language-([\w+-]+)/.exec(block.className);
    const lang = m ? m[1].toLowerCase() : "";
    block.classList.add("hljs");
    if (lang && hljs.getLanguage(lang)) {
      try {
        const code = block.textContent ?? "";
        // hljs escapes its output itself; safe to assign.
        block.innerHTML = hljs.highlight(code, {
          language: lang,
          ignoreIllegals: true,
        }).value;
      } catch {
        /* leave the escaped plain text from marked untouched */
      }
    }
  });
}

function updateControls(): void {
  const canType = wsOpen && sessionReady && !busy;
  input.disabled = !canType;
  btnSend.disabled = !canType;
  btnStop.disabled = !(wsOpen && busy);
  btnNew.disabled = !wsOpen;
  permSelect.disabled = !wsOpen;
  modelSelect.disabled = !wsOpen;
  effortSelect.disabled = !wsOpen;
}

function setBusy(v: boolean): void {
  busy = v;
  updateControls();
}

function setAdtDot(connected: boolean | null): void {
  adtDot.classList.remove("on", "off", "unknown");
  if (connected === true) {
    adtDot.classList.add("on");
    adtDot.title = "ADT MCP server: connected";
  } else if (connected === false) {
    adtDot.classList.add("off");
    adtDot.title =
      "ADT MCP server: disconnected — enable the ADT MCP Server in " +
      "ABAP Development preferences, then start a new session";
  } else {
    adtDot.classList.add("unknown");
    adtDot.title = "ADT MCP server: status unknown";
  }
}

function setModel(model: string | null): void {
  if (model) {
    modelChip.textContent = model;
    modelChip.hidden = false;
  } else {
    modelChip.hidden = true;
  }
}

function showBanner(text: string): void {
  banner.textContent = text;
  banner.hidden = false;
}

function hideBanner(): void {
  banner.hidden = true;
}

function finishStreamingBubble(): void {
  if (renderTimer !== null) {
    clearTimeout(renderTimer);
    renderTimer = null;
  }
  current = null;
  currentMd = "";
}

/* ---------------- transcript builders ---------------- */

function ensureAssistantBubble(): AssistantBubble {
  if (!current) {
    const root = document.createElement("div");
    root.className = "msg assistant";
    const md = document.createElement("div");
    md.className = "md";
    root.appendChild(md);
    appendEntry(root);
    current = { root, md, thinkingPre: null };
  }
  return current;
}

function scheduleStreamRender(): void {
  if (renderTimer !== null) return;
  const wait = Math.max(0, RENDER_THROTTLE_MS - (performance.now() - lastRenderAt));
  renderTimer = window.setTimeout(() => {
    renderTimer = null;
    lastRenderAt = performance.now();
    if (current) {
      const target = current.md;
      withStick(() => renderMarkdownInto(target, currentMd));
    }
  }, wait);
}

function addUserBubble(text: string, ctx: EditorContext | null): void {
  const root = document.createElement("div");
  root.className = "msg user";
  root.textContent = text;
  if (ctx) {
    const tag = document.createElement("span");
    tag.className = "ctx-tag";
    tag.textContent = "context: " + contextLabel(ctx);
    root.appendChild(tag);
  }
  appendEntry(root);
}

function addErrorBubble(message: string): void {
  const root = document.createElement("div");
  root.className = "msg system-error";
  root.textContent = message;
  appendEntry(root);
}

function contextLabel(ctx: EditorContext): string {
  let label = ctx.object_name;
  if (ctx.selection) {
    label += " lines " + ctx.selection.start_line + "-" + ctx.selection.end_line;
  }
  return label;
}

/* ---------------- tool chips ---------------- */

function onToolStarted(id: string, name: string, toolInput: Record<string, unknown>): void {
  const entry = document.createElement("div");
  entry.className = "tool-entry";

  const chip = document.createElement("button");
  chip.type = "button";
  chip.className = "tool-chip";
  chip.title = name;

  const spinner = document.createElement("span");
  spinner.className = "spinner";

  const status = document.createElement("span");
  status.className = "tool-status";

  const label = document.createElement("span");
  label.className = "tool-name";
  label.textContent = shortToolName(name);

  chip.append(spinner, status, label);

  const detail = document.createElement("pre");
  detail.className = "tool-detail mono";
  detail.hidden = true;
  const inputJson = safeJson(toolInput);
  detail.textContent = "Input:\n" + inputJson;

  chip.addEventListener("click", () => {
    detail.hidden = !detail.hidden;
  });

  entry.append(chip, detail);
  appendEntry(entry);
  tools.set(id, { chip, status, spinner, detail, inputJson });
}

function onToolResult(id: string, ok: boolean, preview: string): void {
  const t = tools.get(id);
  if (!t) return;
  withStick(() => {
    t.spinner.remove();
    t.chip.classList.add(ok ? "ok" : "err");
    t.status.textContent = ok ? "✓" : "✗";
    t.detail.textContent = "Input:\n" + t.inputJson + "\n\nResult:\n" + preview;
  });
}

function safeJson(value: unknown): string {
  try {
    return JSON.stringify(value, null, 2) ?? String(value);
  } catch {
    return String(value);
  }
}

/* ---------------- permission cards ---------------- */

function onPermissionRequest(id: string, toolName: string, toolInput: Record<string, unknown>): void {
  const short = shortToolName(toolName);

  const card = document.createElement("div");
  card.className = "perm-card";

  const title = document.createElement("div");
  title.className = "perm-title";
  title.textContent = "Permission required: " + short;
  card.appendChild(title);

  if (short === "write_source") {
    // Show the object name prominently and the code the user is approving.
    const obj = document.createElement("div");
    obj.className = "perm-object";
    obj.textContent = String(toolInput["object_name"] ?? "(unknown object)");
    card.appendChild(obj);

    const code = document.createElement("pre");
    code.className = "code-preview";
    code.textContent = String(toolInput["content"] ?? "");
    card.appendChild(code);

    const rest: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(toolInput)) {
      if (k !== "content" && k !== "object_name") rest[k] = v;
    }
    if (Object.keys(rest).length > 0) {
      const restPre = document.createElement("pre");
      restPre.className = "perm-json mono";
      restPre.textContent = safeJson(rest);
      card.appendChild(restPre);
    }
  } else {
    const pre = document.createElement("pre");
    pre.className = "perm-json mono";
    pre.textContent = safeJson(toolInput);
    card.appendChild(pre);
  }

  const actions = document.createElement("div");
  actions.className = "perm-actions";

  const btnOnce = document.createElement("button");
  btnOnce.type = "button";
  btnOnce.className = "allow";
  btnOnce.textContent = "Allow once";

  const btnAlways = document.createElement("button");
  btnAlways.type = "button";
  btnAlways.textContent = "Always allow";

  const btnDeny = document.createElement("button");
  btnDeny.type = "button";
  btnDeny.className = "deny";
  btnDeny.textContent = "Deny";

  const respond = (behavior: "allow" | "deny", always: boolean): void => {
    sendFrame({ type: "permission_response", id, behavior, always });
    btnOnce.disabled = btnAlways.disabled = btnDeny.disabled = true;
    const outcome = document.createElement("div");
    outcome.className = "perm-outcome " + (behavior === "allow" ? "ok" : "denied");
    outcome.textContent =
      behavior === "deny"
        ? "Denied " + short
        : (always ? "Always allowed " : "Allowed ") + short + (always ? "" : " (once)");
    withStick(() => {
      card.classList.add("resolved");
      card.replaceChildren(outcome);
    });
  };

  btnOnce.addEventListener("click", () => respond("allow", false));
  btnAlways.addEventListener("click", () => respond("allow", true));
  btnDeny.addEventListener("click", () => respond("deny", false));

  actions.append(btnOnce, btnAlways, btnDeny);
  card.appendChild(actions);
  appendEntry(card);
}

/* ---------------- attach chip ---------------- */

function setPendingContext(ctx: EditorContext): void {
  pendingContext = ctx;
  attachChip.textContent = contextLabel(ctx);
  attachChip.title =
    ctx.object_name + (ctx.project ? " (" + ctx.project + ")" : "") +
    (ctx.selection ? " — lines " + ctx.selection.start_line + "-" + ctx.selection.end_line : "");
  attachArea.hidden = false;
}

function clearPendingContext(): void {
  pendingContext = null;
  attachArea.hidden = true;
  attachChip.textContent = "";
}

attachDismiss.addEventListener("click", clearPendingContext);

/* ---------------- frame handling ---------------- */

function handleFrame(frame: ServerFrame): void {
  switch (frame.type) {
    case "ready": {
      sessionReady = true;
      setBusy(false);
      setModel(frame.model);
      setAdtDot(frame.adtMcp ? frame.adtMcp.connected : null);
      if (["default", "acceptEdits", "plan"].includes(frame.permissionMode)) {
        permSelect.value = frame.permissionMode;
      }
      if (frame.modelOverride !== undefined) {
        modelSelect.value = frame.modelOverride ?? "";
        if (modelSelect.selectedIndex < 0) modelSelect.selectedIndex = 0;
      }
      if (frame.effort !== undefined) {
        effortSelect.value = frame.effort ?? "";
      }
      titleEl.title =
        "cwd: " + frame.cwd +
        (frame.devAllowlist ? "\nDev allowlist: " + frame.devAllowlist : "\nDev allowlist: (empty)");
      updateControls();
      break;
    }
    case "assistant_text_delta": {
      ensureAssistantBubble();
      currentMd += frame.text;
      scheduleStreamRender();
      break;
    }
    case "thinking_delta": {
      const bubble = ensureAssistantBubble();
      if (!bubble.thinkingPre) {
        const details = document.createElement("details");
        details.className = "thinking";
        const summary = document.createElement("summary");
        summary.textContent = "Thinking…";
        const pre = document.createElement("pre");
        details.append(summary, pre);
        withStick(() => bubble.root.insertBefore(details, bubble.md));
        bubble.thinkingPre = pre;
      }
      const pre = bubble.thinkingPre;
      withStick(() => {
        pre.textContent = (pre.textContent ?? "") + frame.text;
      });
      break;
    }
    case "assistant_message_final": {
      if (!current && !frame.text) break;
      const bubble = ensureAssistantBubble();
      if (renderTimer !== null) {
        clearTimeout(renderTimer);
        renderTimer = null;
      }
      withStick(() => renderMarkdownInto(bubble.md, frame.text));
      finishStreamingBubble();
      break;
    }
    case "tool_started": {
      onToolStarted(frame.id, frame.name, frame.input ?? {});
      break;
    }
    case "tool_result": {
      onToolResult(frame.id, frame.ok, frame.preview ?? "");
      break;
    }
    case "permission_request": {
      onPermissionRequest(frame.id, frame.toolName, frame.input ?? {});
      break;
    }
    case "turn_complete": {
      finishStreamingBubble();
      setBusy(false);
      break;
    }
    case "status": {
      setAdtDot(frame.adtMcp ? frame.adtMcp.connected : null);
      setModel(frame.model);
      break;
    }
    case "models": {
      const previous = modelSelect.value;
      modelSelect.replaceChildren();
      const def = document.createElement("option");
      def.value = "";
      def.textContent = "model: default";
      modelSelect.appendChild(def);
      for (const m of frame.models) {
        if (m.value === "default") continue; // covered by the built-in first option
        const o = document.createElement("option");
        o.value = m.value;
        o.textContent = m.displayName;
        modelSelect.appendChild(o);
      }
      modelSelect.value = previous;
      if (modelSelect.selectedIndex < 0) modelSelect.selectedIndex = 0;
      break;
    }
    case "error": {
      addErrorBubble(frame.message);
      // A fatal session error may never deliver turn_complete; do not leave the
      // composer locked forever.
      setBusy(false);
      break;
    }
    case "editor_context": {
      setPendingContext(frame.context);
      break;
    }
    default:
      break;
  }
}

/* ---------------- websocket + reconnect ---------------- */

function connect(): void {
  const url = "ws://" + location.host + "/ws?token=" + encodeURIComponent(token);
  const sock = new WebSocket(url);
  ws = sock;

  sock.onopen = () => {
    if (ws !== sock) return;
    wsOpen = true;
    backoff = 500;
    hideBanner();
    updateControls(); // composer stays disabled until the ready frame
  };

  sock.onmessage = (ev: MessageEvent) => {
    if (ws !== sock) return;
    let frame: ServerFrame;
    try {
      frame = JSON.parse(String(ev.data)) as ServerFrame;
    } catch {
      return;
    }
    handleFrame(frame);
  };

  sock.onclose = () => {
    if (ws !== sock) return;
    ws = null;
    wsOpen = false;
    sessionReady = false;
    setBusy(false);
    updateControls();
    showBanner("Disconnected — reconnecting…");
    window.setTimeout(() => {
      backoff = Math.min(backoff * 2, BACKOFF_MAX);
      connect();
    }, backoff);
  };

  sock.onerror = () => {
    sock.close();
  };
}

/* ---------------- composer ---------------- */

function doSend(): void {
  const text = input.value.trim();
  if (!text || !wsOpen || !sessionReady || busy) return;
  const ctx = pendingContext;
  sendFrame({ type: "user_message", text, context: ctx ?? null });
  addUserBubble(text, ctx);
  clearPendingContext();
  input.value = "";
  autoGrow();
  setBusy(true);
  transcript.scrollTop = transcript.scrollHeight;
}

function autoGrow(): void {
  input.style.height = "auto";
  input.style.height = Math.min(input.scrollHeight, 130) + "px";
}

input.addEventListener("keydown", (e: KeyboardEvent) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    doSend();
  }
});
input.addEventListener("input", autoGrow);

btnSend.addEventListener("click", doSend);

btnStop.addEventListener("click", () => {
  if (busy) sendFrame({ type: "interrupt" });
});

btnNew.addEventListener("click", () => {
  sendFrame({ type: "new_session" });
  transcript.replaceChildren();
  tools.clear();
  finishStreamingBubble();
  clearPendingContext();
  setBusy(false);
});

permSelect.addEventListener("change", () => {
  const mode = permSelect.value;
  if (mode === "default" || mode === "acceptEdits" || mode === "plan") {
    sendFrame({ type: "set_permission_mode", mode });
  }
});

modelSelect.addEventListener("change", () => {
  sendFrame({ type: "set_model", model: modelSelect.value || null });
});

effortSelect.addEventListener("change", () => {
  sendFrame({ type: "set_effort", effort: effortSelect.value || null });
});

/* ---------------- go ---------------- */

updateControls();
showBanner("Connecting…");
connect();
