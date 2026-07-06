package is.mehta.claudecode.abap.bridge;

import java.util.ArrayList;
import java.util.List;

import org.eclipse.core.resources.IProject;
import org.eclipse.core.resources.IResource;
import org.eclipse.jface.text.IDocument;
import org.eclipse.ui.IEditorInput;
import org.eclipse.ui.IEditorPart;
import org.eclipse.ui.IEditorReference;
import org.eclipse.ui.IWorkbenchPage;
import org.eclipse.ui.IWorkbenchWindow;
import org.eclipse.ui.PlatformUI;
import org.eclipse.ui.texteditor.ITextEditor;

/**
 * UI-thread editor operations. All methods MUST be called from the SWT UI
 * thread (the dispatcher wraps calls in Display.syncExec).
 *
 * The write path is deliberately the Eclipse Platform text-editor API
 * (ITextEditor -> IDocumentProvider -> IDocument): edits appear live in the
 * open editor, participate in undo, and persistence/activation go through
 * ADT's own save pipeline. No ADT-internal API and no direct ADT REST.
 */
public final class EditorSourceGateway {

    /** Diagnostic-rich handle for one open editor. */
    public record EditorHandle(IEditorPart part, ITextEditor textEditor, IDocument document,
            String title, String tooltip, String project) {

        public String describe() {
            return title + " [project=" + project + ", editorClass=" + part.getClass().getSimpleName()
                    + ", textEditor=" + (textEditor != null) + ", document=" + (document != null) + "]";
        }
    }

    /** Enumerates every open editor across all workbench windows/pages. */
    public List<EditorHandle> openEditors() {
        List<EditorHandle> out = new ArrayList<>();
        for (IWorkbenchWindow window : PlatformUI.getWorkbench().getWorkbenchWindows()) {
            for (IWorkbenchPage page : window.getPages()) {
                for (IEditorReference ref : page.getEditorReferences()) {
                    IEditorPart part = ref.getEditor(true);
                    if (part != null) {
                        out.add(toHandle(part));
                    }
                }
            }
        }
        return out;
    }

    public EditorHandle activeEditor() {
        IWorkbenchWindow window = PlatformUI.getWorkbench().getActiveWorkbenchWindow();
        if (window == null || window.getActivePage() == null) {
            return null;
        }
        IEditorPart part = window.getActivePage().getActiveEditor();
        return part == null ? null : toHandle(part);
    }

    public EditorHandle toHandle(IEditorPart part) {
        ITextEditor textEditor = adaptTextEditor(part);
        IDocument document = null;
        if (textEditor != null && textEditor.getDocumentProvider() != null) {
            document = textEditor.getDocumentProvider().getDocument(textEditor.getEditorInput());
        }
        if (document == null) {
            document = part.getAdapter(IDocument.class);
        }
        return new EditorHandle(part, textEditor, document, cleanTitle(part.getTitle()),
                part.getTitleToolTip(), projectOf(part));
    }

    /** Editors whose (dirty-marker-stripped) title matches the object name. */
    public List<EditorHandle> findByObjectName(String objectName) {
        String wanted = objectName.trim();
        List<EditorHandle> exact = new ArrayList<>();
        List<EditorHandle> prefixed = new ArrayList<>();
        for (EditorHandle h : openEditors()) {
            if (h.title().equalsIgnoreCase(wanted)) {
                exact.add(h);
            } else if (startsWithWord(h.title(), wanted)) {
                prefixed.add(h);
            }
        }
        return exact.isEmpty() ? prefixed : exact;
    }

    private static boolean startsWithWord(String title, String word) {
        if (title.length() <= word.length() || !title.regionMatches(true, 0, word, 0, word.length())) {
            return false;
        }
        char next = title.charAt(word.length());
        return !Character.isLetterOrDigit(next) && next != '_';
    }

    private static ITextEditor adaptTextEditor(IEditorPart part) {
        if (part instanceof ITextEditor editor) {
            return editor;
        }
        return part.getAdapter(ITextEditor.class);
    }

    private static String projectOf(IEditorPart part) {
        IEditorInput input = part.getEditorInput();
        if (input == null) {
            return null;
        }
        IResource resource = input.getAdapter(IResource.class);
        if (resource != null && resource.getProject() != null) {
            return resource.getProject().getName();
        }
        IProject project = input.getAdapter(IProject.class);
        return project == null ? null : project.getName();
    }

    /** Strips the dirty marker Eclipse prefixes onto part names. */
    private static String cleanTitle(String title) {
        if (title == null) {
            return "";
        }
        return title.startsWith("*") ? title.substring(1).trim() : title.trim();
    }
}
