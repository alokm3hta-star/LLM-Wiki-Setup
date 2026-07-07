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
  | { type: "question_request"; id: string; payload: unknown }
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
const composer = el<HTMLElement>("composer");
const fileAttachArea = el<HTMLDivElement>("file-attach-area");
const btnAttach = el<HTMLButtonElement>("btn-attach");
const fileInput = el<HTMLInputElement>("file-input");
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

interface PendingFile {
  id: string;
  name: string;
  mime: string;
  size: number;
  dataBase64: string;
}
let pendingFiles: PendingFile[] = [];

// Kept in step with the sidecar's ALLOWED_ATTACH_EXT and the <input accept>.
const ALLOWED_FILE_EXT = new Set([
  ".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp",
  ".pdf",
  ".md", ".markdown", ".txt", ".text", ".csv", ".tsv", ".json", ".log", ".xml", ".yaml", ".yml",
  ".xlsx", ".xlsm", ".xls", ".docx",
]);
const MAX_FILE_BYTES = 25 * 1024 * 1024; // per file; also enforced sidecar-side
let fileSeq = 0;

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
  btnAttach.disabled = !canType;
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

function addUserBubble(
  text: string,
  ctx: EditorContext | null,
  fileNames: string[] = []
): void {
  const root = document.createElement("div");
  root.className = "msg user";
  root.textContent = text;
  if (ctx) {
    const tag = document.createElement("span");
    tag.className = "ctx-tag";
    tag.textContent = "context: " + contextLabel(ctx);
    root.appendChild(tag);
  }
  for (const name of fileNames) {
    const tag = document.createElement("span");
    tag.className = "ctx-tag";
    tag.textContent = "file: " + name;
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

/* ---------------- AskUserQuestion picker ---------------- */

interface QuestionOption {
  label: string;
  description?: string;
}
interface QuestionSpec {
  question: string;
  header?: string;
  options: QuestionOption[];
  multiSelect: boolean;
}

/** The dialog payload is transported opaquely by the SDK; pull the questions
 *  out defensively so an unexpected wrapper does not break the picker. */
function extractQuestions(payload: unknown): QuestionSpec[] {
  const p = payload as Record<string, unknown> | null;
  const arr: unknown =
    p && Array.isArray(p["questions"])
      ? p["questions"]
      : Array.isArray(payload)
        ? payload
        : null;
  if (!Array.isArray(arr)) return [];
  const out: QuestionSpec[] = [];
  for (const q of arr) {
    if (!q || typeof q !== "object") continue;
    const qo = q as Record<string, unknown>;
    const options: QuestionOption[] = [];
    const rawOpts = Array.isArray(qo["options"]) ? (qo["options"] as unknown[]) : [];
    for (const o of rawOpts) {
      if (typeof o === "string") {
        options.push({ label: o });
      } else if (o && typeof o === "object") {
        const oo = o as Record<string, unknown>;
        const label =
          typeof oo["label"] === "string"
            ? (oo["label"] as string)
            : typeof oo["text"] === "string"
              ? (oo["text"] as string)
              : null;
        if (label) {
          options.push({
            label,
            description:
              typeof oo["description"] === "string" ? (oo["description"] as string) : undefined,
          });
        }
      }
    }
    out.push({
      question:
        typeof qo["question"] === "string"
          ? (qo["question"] as string)
          : typeof qo["prompt"] === "string"
            ? (qo["prompt"] as string)
            : "",
      header: typeof qo["header"] === "string" ? (qo["header"] as string) : undefined,
      options,
      multiSelect: qo["multiSelect"] === true || qo["multi_select"] === true,
    });
  }
  return out;
}

function onQuestionRequest(id: string, payload: unknown): void {
  const questions = extractQuestions(payload);

  const card = document.createElement("div");
  card.className = "q-card";

  const title = document.createElement("div");
  title.className = "q-title";
  title.textContent = questions.length > 1 ? "Claude has a few questions" : "Claude is asking";
  card.appendChild(title);

  const selections = new Map<string, Set<string>>();
  const otherText = new Map<string, string>();

  const submitBtn = document.createElement("button");
  submitBtn.type = "button";
  submitBtn.className = "allow";
  submitBtn.textContent = "Submit";

  const refreshSubmit = (): void => {
    submitBtn.disabled = !questions.every((q) => {
      const sel = selections.get(q.question);
      const other = (otherText.get(q.question) ?? "").trim();
      return (sel != null && sel.size > 0) || other.length > 0;
    });
  };

  if (questions.length === 0) {
    // Could not parse the payload — show it raw so the user can Cancel rather
    // than the session hanging on an unanswered dialog.
    const pre = document.createElement("pre");
    pre.className = "perm-json mono";
    pre.textContent = safeJson(payload);
    card.appendChild(pre);
  }

  for (const q of questions) {
    selections.set(q.question, new Set<string>());

    const block = document.createElement("div");
    block.className = "q-block";

    if (q.header) {
      const h = document.createElement("div");
      h.className = "q-header";
      h.textContent = q.header;
      block.appendChild(h);
    }
    const qt = document.createElement("div");
    qt.className = "q-question";
    qt.textContent = q.question;
    block.appendChild(qt);

    const opts = document.createElement("div");
    opts.className = "q-options";

    for (const o of q.options) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "q-option";

      const lab = document.createElement("div");
      lab.className = "q-option-label";
      lab.textContent = o.label;
      btn.appendChild(lab);
      if (o.description) {
        const d = document.createElement("div");
        d.className = "q-option-desc";
        d.textContent = o.description;
        btn.appendChild(d);
      }

      btn.addEventListener("click", () => {
        const set = selections.get(q.question) as Set<string>;
        if (q.multiSelect) {
          if (set.has(o.label)) {
            set.delete(o.label);
            btn.classList.remove("selected");
          } else {
            set.add(o.label);
            btn.classList.add("selected");
          }
        } else {
          set.clear();
          for (const c of Array.from(opts.querySelectorAll(".q-option"))) {
            c.classList.remove("selected");
          }
          set.add(o.label);
          btn.classList.add("selected");
        }
        refreshSubmit();
      });
      opts.appendChild(btn);
    }
    block.appendChild(opts);

    // AskUserQuestion always permits a free-text answer ("Other").
    const otherInput = document.createElement("input");
    otherInput.type = "text";
    otherInput.className = "q-other";
    otherInput.placeholder = "Other… (type a custom answer)";
    otherInput.addEventListener("input", () => {
      otherText.set(q.question, otherInput.value);
      if (!q.multiSelect && otherInput.value.trim().length > 0) {
        const set = selections.get(q.question) as Set<string>;
        set.clear();
        for (const c of Array.from(opts.querySelectorAll(".q-option"))) {
          c.classList.remove("selected");
        }
      }
      refreshSubmit();
    });
    block.appendChild(otherInput);

    card.appendChild(block);
  }

  const actions = document.createElement("div");
  actions.className = "q-actions";

  const cancelBtn = document.createElement("button");
  cancelBtn.type = "button";
  cancelBtn.className = "deny";
  cancelBtn.textContent = "Cancel";

  const finish = (cancelled: boolean): void => {
    submitBtn.disabled = cancelBtn.disabled = true;
    if (cancelled) {
      sendFrame({ type: "question_response", id, cancelled: true });
    } else {
      const answers: Record<string, string[]> = {};
      for (const q of questions) {
        const list = Array.from(selections.get(q.question) as Set<string>);
        const other = (otherText.get(q.question) ?? "").trim();
        if (other) list.push(other);
        answers[q.question] = list;
      }
      sendFrame({ type: "question_response", id, answers });
    }
    withStick(() => {
      const outcome = document.createElement("div");
      outcome.className = "perm-outcome " + (cancelled ? "denied" : "ok");
      outcome.textContent = cancelled ? "Question dismissed" : "Answer sent";
      card.classList.add("resolved");
      card.replaceChildren(outcome);
    });
  };

  submitBtn.addEventListener("click", () => finish(false));
  cancelBtn.addEventListener("click", () => finish(true));

  if (questions.length > 0) {
    submitBtn.disabled = true;
    actions.appendChild(submitBtn);
  }
  actions.appendChild(cancelBtn);
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

/* ---------------- file attachments ---------------- */

function extOf(name: string): string {
  const dot = name.lastIndexOf(".");
  return dot >= 0 ? name.slice(dot).toLowerCase() : "";
}

function humanSize(bytes: number): string {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return Math.round(bytes / 1024) + " KB";
  return (bytes / (1024 * 1024)).toFixed(1) + " MB";
}

function readAsBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const r = new FileReader();
    r.onload = () => {
      const res = String(r.result); // "data:<mime>;base64,<payload>"
      const comma = res.indexOf(",");
      resolve(comma >= 0 ? res.slice(comma + 1) : res);
    };
    r.onerror = () => reject(r.error);
    r.readAsDataURL(file);
  });
}

function renderFileChips(): void {
  fileAttachArea.replaceChildren();
  for (const f of pendingFiles) {
    const chip = document.createElement("span");
    chip.className = "file-chip";

    const nameEl = document.createElement("span");
    nameEl.className = "file-name";
    nameEl.textContent = f.name;
    nameEl.title = f.name;

    const sizeEl = document.createElement("span");
    sizeEl.className = "file-size";
    sizeEl.textContent = humanSize(f.size);

    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "file-remove";
    remove.textContent = "×";
    remove.title = "Remove " + f.name;
    remove.addEventListener("click", () => {
      pendingFiles = pendingFiles.filter((x) => x.id !== f.id);
      renderFileChips();
    });

    chip.append(nameEl, sizeEl, remove);
    fileAttachArea.appendChild(chip);
  }
  fileAttachArea.hidden = pendingFiles.length === 0;
}

function clearPendingFiles(): void {
  pendingFiles = [];
  renderFileChips();
}

async function addFiles(files: FileList | File[]): Promise<void> {
  const rejected: string[] = [];
  for (const file of Array.from(files)) {
    const ext = extOf(file.name);
    if (ext && !ALLOWED_FILE_EXT.has(ext)) {
      rejected.push(file.name + " (type not supported)");
      continue;
    }
    if (file.size > MAX_FILE_BYTES) {
      rejected.push(file.name + " (over " + humanSize(MAX_FILE_BYTES) + ")");
      continue;
    }
    try {
      const dataBase64 = await readAsBase64(file);
      pendingFiles.push({
        id: "f" + ++fileSeq,
        name: file.name,
        mime: file.type || "",
        size: file.size,
        dataBase64,
      });
    } catch {
      rejected.push(file.name + " (could not read)");
    }
  }
  renderFileChips();
  if (rejected.length) {
    addErrorBubble("Some files were not attached: " + rejected.join("; "));
  }
}

btnAttach.addEventListener("click", () => fileInput.click());
fileInput.addEventListener("change", () => {
  if (fileInput.files && fileInput.files.length) void addFiles(fileInput.files);
  fileInput.value = ""; // allow re-picking the same file
});

// Drag-and-drop anywhere on the composer.
composer.addEventListener("dragover", (e: DragEvent) => {
  if (e.dataTransfer && Array.from(e.dataTransfer.types).includes("Files")) {
    e.preventDefault();
    e.dataTransfer.dropEffect = "copy";
  }
});
composer.addEventListener("drop", (e: DragEvent) => {
  if (e.dataTransfer && e.dataTransfer.files.length) {
    e.preventDefault();
    void addFiles(e.dataTransfer.files);
  }
});

// Paste an image straight from the clipboard.
input.addEventListener("paste", (e: ClipboardEvent) => {
  const items = e.clipboardData?.files;
  if (items && items.length) {
    e.preventDefault();
    void addFiles(items);
  }
});

/* ---------------- frame handling ---------------- */

function handleFrame(frame: ServerFrame): void {
  switch (frame.type) {
    case "ready": {
      sessionReady = true;
      setBusy(false);
      setModel(frame.model);
      setAdtDot(frame.adtMcp ? frame.adtMcp.connected : null);
      if (
        ["default", "auto", "acceptEdits", "plan", "bypassPermissions"].includes(
          frame.permissionMode,
        )
      ) {
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
    case "question_request": {
      onQuestionRequest(frame.id, frame.payload);
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
  if ((!text && pendingFiles.length === 0) || !wsOpen || !sessionReady || busy) return;
  const ctx = pendingContext;
  const attachments = pendingFiles.map((f) => ({
    name: f.name,
    mime: f.mime,
    size: f.size,
    dataBase64: f.dataBase64,
  }));
  const fileNames = pendingFiles.map((f) => f.name);
  sendFrame({ type: "user_message", text, context: ctx ?? null, attachments });
  addUserBubble(text, ctx, fileNames);
  clearPendingContext();
  clearPendingFiles();
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
  clearPendingFiles();
  setBusy(false);
});

permSelect.addEventListener("change", () => {
  const mode = permSelect.value;
  if (
    mode === "default" ||
    mode === "auto" ||
    mode === "acceptEdits" ||
    mode === "plan" ||
    mode === "bypassPermissions"
  ) {
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
