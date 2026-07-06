package is.mehta.claudecode.abap.handlers;

import org.eclipse.core.commands.AbstractHandler;
import org.eclipse.core.commands.ExecutionEvent;
import org.eclipse.core.commands.ExecutionException;
import org.eclipse.ui.IWorkbenchPage;
import org.eclipse.ui.IWorkbenchWindow;
import org.eclipse.ui.PartInitException;
import org.eclipse.ui.handlers.HandlerUtil;

import is.mehta.claudecode.abap.views.ClaudeChatView;

public class OpenChatViewHandler extends AbstractHandler {

    @Override
    public Object execute(ExecutionEvent event) throws ExecutionException {
        IWorkbenchWindow window = HandlerUtil.getActiveWorkbenchWindowChecked(event);
        IWorkbenchPage page = window.getActivePage();
        if (page == null) {
            return null;
        }
        try {
            page.showView(ClaudeChatView.ID);
        } catch (PartInitException e) {
            throw new ExecutionException("Cannot open the Claude Code view", e);
        }
        return null;
    }
}
