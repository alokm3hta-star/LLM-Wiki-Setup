package is.mehta.claudecode.abap.prefs;

import org.eclipse.jface.preference.BooleanFieldEditor;
import org.eclipse.jface.preference.ComboFieldEditor;
import org.eclipse.jface.preference.DirectoryFieldEditor;
import org.eclipse.jface.preference.FieldEditorPreferencePage;
import org.eclipse.jface.preference.FileFieldEditor;
import org.eclipse.jface.preference.IntegerFieldEditor;
import org.eclipse.jface.preference.StringFieldEditor;
import org.eclipse.ui.IWorkbench;
import org.eclipse.ui.IWorkbenchPreferencePage;

import is.mehta.claudecode.abap.Activator;

public class ClaudeCodePreferencePage extends FieldEditorPreferencePage implements IWorkbenchPreferencePage {

    public ClaudeCodePreferencePage() {
        super(GRID);
        setPreferenceStore(Activator.getDefault().getPreferenceStore());
        setDescription("Claude Code for ABAP. The Dev allowlist is mandatory for source read/write: "
                + "the bridge refuses every editor whose ABAP project is not listed (comma-separated project names, "
                + "e.g. S4H_100_myuser_en). Changes take effect after 'Restart sidecar' in the view toolbar.");
    }

    @Override
    public void createFieldEditors() {
        addField(new StringFieldEditor(Prefs.DEV_ALLOWLIST, "Dev system allowlist (comma-separated):",
                getFieldEditorParent()));
        addField(new FileFieldEditor(Prefs.NODE_PATH, "Node.js executable (blank = auto-detect):",
                getFieldEditorParent()));
        addField(new DirectoryFieldEditor(Prefs.CLAUDE_CWD, "Claude session working directory:",
                getFieldEditorParent()));
        addField(new IntegerFieldEditor(Prefs.ADT_MCP_PORT, "ADT MCP server port:", getFieldEditorParent()));
        addField(new ComboFieldEditor(Prefs.PERMISSION_MODE, "Default permission mode:",
                new String[][] { { "default (ask)", "default" }, { "acceptEdits", "acceptEdits" },
                        { "plan", "plan" } },
                getFieldEditorParent()));
        addField(new BooleanFieldEditor(Prefs.KEEP_ALIVE, "Keep sidecar alive when the view is closed",
                getFieldEditorParent()));
        addField(new DirectoryFieldEditor(Prefs.DEV_OVERRIDE_PATH,
                "Dev override path (git tree with web/ + sidecar/; blank = installed bundle):",
                getFieldEditorParent()));
    }

    @Override
    public void init(IWorkbench workbench) {
    }
}
