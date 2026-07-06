package is.mehta.claudecode.abap.handlers;

import org.eclipse.core.commands.AbstractHandler;
import org.eclipse.core.commands.ExecutionEvent;
import org.eclipse.core.commands.ExecutionException;
import org.eclipse.jface.text.ITextSelection;
import org.eclipse.jface.viewers.ISelection;
import org.eclipse.ui.IEditorPart;
import org.eclipse.ui.IWorkbenchPage;
import org.eclipse.ui.IWorkbenchWindow;
import org.eclipse.ui.PartInitException;
import org.eclipse.ui.handlers.HandlerUtil;

import com.google.gson.JsonObject;

import is.mehta.claudecode.abap.Activator;
import is.mehta.claudecode.abap.bridge.EditorSourceGateway;
import is.mehta.claudecode.abap.sidecar.SidecarProcessManager;
import is.mehta.claudecode.abap.views.ClaudeChatView;

/**
 * "Send to Claude": captures the active editor's object name, project and
 * text selection, then shows the chat view and forwards the context as an
 * editor_context frame (the UI renders it as an attach-chip). Handlers run
 * on the UI thread, so editor access here is safe.
 */
public class SendToClaudeHandler extends AbstractHandler {

    @Override
    public Object execute(ExecutionEvent event) throws ExecutionException {
        IWorkbenchWindow window = HandlerUtil.getActiveWorkbenchWindowChecked(event);
        IEditorPart editor = HandlerUtil.getActiveEditor(event);
        if (editor == null) {
            showView(window);
            return null;
        }
        // Capture the context before showView shifts focus off the editor.
        EditorSourceGateway.EditorHandle handle = new EditorSourceGateway().toHandle(editor);
        JsonObject context = new JsonObject();
        context.addProperty("object_name", handle.title());
        if (handle.project() != null) {
            context.addProperty("project", handle.project());
        }
        ISelection sel = handle.textEditor() != null && handle.textEditor().getSelectionProvider() != null
                ? handle.textEditor().getSelectionProvider().getSelection()
                : null;
        if (sel instanceof ITextSelection ts && ts.getLength() > 0) {
            JsonObject s = new JsonObject();
            s.addProperty("start_line", ts.getStartLine() + 1);
            s.addProperty("end_line", ts.getEndLine() + 1);
            s.addProperty("text", ts.getText());
            context.add("selection", s);
        }
        showView(window);
        SidecarProcessManager manager = Activator.getDefault().getSidecarManager();
        manager.ensureStarted();
        manager.sendEditorContext(context);
        return null;
    }

    private void showView(IWorkbenchWindow window) throws ExecutionException {
        IWorkbenchPage page = window.getActivePage();
        if (page == null) {
            return;
        }
        try {
            page.showView(ClaudeChatView.ID);
        } catch (PartInitException e) {
            throw new ExecutionException("Cannot open the Claude Code view", e);
        }
    }
}
