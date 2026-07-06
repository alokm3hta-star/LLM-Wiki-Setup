package is.mehta.claudecode.abap.bridge;

import java.util.List;
import java.util.concurrent.atomic.AtomicReference;

import org.eclipse.core.runtime.NullProgressMonitor;
import org.eclipse.jface.preference.IPreferenceStore;
import org.eclipse.jface.text.ITextSelection;
import org.eclipse.jface.viewers.ISelection;
import org.eclipse.swt.widgets.Display;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;

/**
 * Implements the bridge tool surface (ADR-002 condition 3 — exactly these
 * three tools): read_source, write_source, get_editor_context. Every
 * operation runs inside Display.syncExec with state re-validated in the
 * runnable; error messages are actionable for the calling model.
 */
public final class BridgeToolDispatcher {

    private final EditorSourceGateway gateway = new EditorSourceGateway();
    private final DevDestinationGuard guard;

    public BridgeToolDispatcher(IPreferenceStore store) {
        this.guard = new DevDestinationGuard(store);
    }

    public JsonObject handle(String tool, JsonObject params) {
        return switch (tool) {
            case "read_source" -> onUiThread(() -> readSource(params));
            case "write_source" -> onUiThread(() -> writeSource(params));
            case "get_editor_context" -> onUiThread(this::editorContext);
            default -> error("Unknown bridge tool '" + tool
                    + "'. Available: read_source, write_source, get_editor_context.");
        };
    }

    private JsonObject onUiThread(java.util.function.Supplier<JsonObject> op) {
        AtomicReference<JsonObject> result = new AtomicReference<>();
        Display.getDefault().syncExec(() -> {
            try {
                result.set(op.get());
            } catch (Exception e) {
                result.set(error(e.getClass().getSimpleName() + ": " + e.getMessage()));
            }
        });
        return result.get();
    }

    private JsonObject readSource(JsonObject params) {
        String objectName = requireString(params, "object_name");
        EditorHandleResolution res = resolveSingle(objectName);
        if (res.error != null) {
            return res.error;
        }
        EditorSourceGateway.EditorHandle handle = res.handle;
        String destination = guard.resolve(handle);
        if (destination == null) {
            return error(guard.refusalMessage(handle));
        }
        if (handle.document() == null) {
            return adapterMiss(handle, "read");
        }
        JsonObject ok = ok();
        ok.addProperty("object_name", handle.title());
        ok.addProperty("destination", destination);
        ok.addProperty("dirty", handle.part().isDirty());
        ok.addProperty("content", handle.document().get());
        return ok;
    }

    private JsonObject writeSource(JsonObject params) {
        String objectName = requireString(params, "object_name");
        String content = requireString(params, "content");
        boolean save = params.has("save") && params.get("save").getAsBoolean();

        EditorHandleResolution res = resolveSingle(objectName);
        if (res.error != null) {
            return res.error;
        }
        EditorSourceGateway.EditorHandle handle = res.handle;
        String destination = guard.resolve(handle);
        if (destination == null) {
            return error(guard.refusalMessage(handle));
        }
        if (handle.document() == null) {
            return adapterMiss(handle, "write");
        }
        try {
            handle.document().replace(0, handle.document().getLength(), content);
        } catch (org.eclipse.jface.text.BadLocationException e) {
            return error("Document replace failed: " + e.getMessage());
        }
        boolean saved = false;
        if (save) {
            // Runs ADT's own save pipeline; may raise SAP dialogs (transport
            // assignment, logon) which the user services interactively.
            handle.part().doSave(new NullProgressMonitor());
            saved = !handle.part().isDirty();
        }
        JsonObject ok = ok();
        ok.addProperty("object_name", handle.title());
        ok.addProperty("destination", destination);
        ok.addProperty("chars_written", content.length());
        ok.addProperty("saved", saved);
        if (save && !saved) {
            ok.addProperty("note", "Save was requested but the editor is still dirty - "
                    + "the user may have cancelled a transport/logon dialog.");
        }
        return ok;
    }

    private JsonObject editorContext() {
        JsonObject ok = ok();
        EditorSourceGateway.EditorHandle active = gateway.activeEditor();
        if (active != null) {
            JsonObject a = new JsonObject();
            a.addProperty("object_name", active.title());
            a.addProperty("project", active.project());
            a.addProperty("dirty", active.part().isDirty());
            String destination = guard.resolve(active);
            a.addProperty("on_dev_allowlist", destination != null);
            ISelection sel = active.textEditor() != null && active.textEditor().getSelectionProvider() != null
                    ? active.textEditor().getSelectionProvider().getSelection()
                    : null;
            if (sel instanceof ITextSelection ts && ts.getLength() > 0) {
                JsonObject s = new JsonObject();
                s.addProperty("start_line", ts.getStartLine() + 1);
                s.addProperty("end_line", ts.getEndLine() + 1);
                if (destination != null) {
                    s.addProperty("text", ts.getText());
                } else {
                    s.addProperty("note", "selection text withheld: project not on Dev allowlist");
                }
                a.add("selection", s);
            }
            ok.add("active_editor", a);
        }
        JsonArray open = new JsonArray();
        for (EditorSourceGateway.EditorHandle h : gateway.openEditors()) {
            JsonObject o = new JsonObject();
            o.addProperty("object_name", h.title());
            o.addProperty("project", h.project());
            o.addProperty("text_editor_adaptable", h.textEditor() != null);
            o.addProperty("document_available", h.document() != null);
            open.add(o);
        }
        ok.add("open_editors", open);
        ok.addProperty("dev_allowlist", String.join(",", guard.allowlist()));
        return ok;
    }

    // ---- helpers -------------------------------------------------------

    private record EditorHandleResolution(EditorSourceGateway.EditorHandle handle, JsonObject error) {
    }

    private EditorHandleResolution resolveSingle(String objectName) {
        List<EditorSourceGateway.EditorHandle> matches = gateway.findByObjectName(objectName);
        if (matches.isEmpty()) {
            StringBuilder sb = new StringBuilder("No open editor matches '").append(objectName)
                    .append("'. The object must be OPEN in an ADT editor first (ask the user to open it). Open editors: ");
            List<EditorSourceGateway.EditorHandle> all = gateway.openEditors();
            if (all.isEmpty()) {
                sb.append("none");
            } else {
                sb.append(String.join("; ", all.stream().map(EditorSourceGateway.EditorHandle::describe).toList()));
            }
            return new EditorHandleResolution(null, error(sb.toString()));
        }
        if (matches.size() > 1) {
            return new EditorHandleResolution(null, error("Ambiguous: " + matches.size()
                    + " open editors match '" + objectName + "': "
                    + String.join("; ", matches.stream().map(EditorSourceGateway.EditorHandle::describe).toList())));
        }
        return new EditorHandleResolution(matches.get(0), null);
    }

    private JsonObject adapterMiss(EditorSourceGateway.EditorHandle handle, String op) {
        return error("Cannot " + op + " '" + handle.title() + "': the editor does not expose a text document. "
                + "Diagnostics: " + handle.describe()
                + ". This is the known G6 adapter risk - report this diagnostic string.");
    }

    private static String requireString(JsonObject params, String key) {
        if (params == null || !params.has(key) || params.get(key).getAsString().isEmpty()) {
            throw new IllegalArgumentException("missing required parameter '" + key + "'");
        }
        return params.get(key).getAsString();
    }

    private static JsonObject ok() {
        JsonObject o = new JsonObject();
        o.addProperty("ok", true);
        return o;
    }

    private static JsonObject error(String message) {
        JsonObject o = new JsonObject();
        o.addProperty("ok", false);
        o.addProperty("error", message);
        return o;
    }
}
