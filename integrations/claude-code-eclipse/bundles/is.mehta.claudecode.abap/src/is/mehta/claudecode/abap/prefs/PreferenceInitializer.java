package is.mehta.claudecode.abap.prefs;

import org.eclipse.core.runtime.preferences.AbstractPreferenceInitializer;
import org.eclipse.jface.preference.IPreferenceStore;

import is.mehta.claudecode.abap.Activator;

public class PreferenceInitializer extends AbstractPreferenceInitializer {

    @Override
    public void initializeDefaultPreferences() {
        IPreferenceStore store = Activator.getDefault().getPreferenceStore();
        store.setDefault(Prefs.NODE_PATH, "");
        store.setDefault(Prefs.DEV_ALLOWLIST, "");
        store.setDefault(Prefs.CLAUDE_CWD, System.getProperty("user.home", "/tmp"));
        store.setDefault(Prefs.DEV_OVERRIDE_PATH, "");
        store.setDefault(Prefs.ADT_MCP_PORT, 2234);
        store.setDefault(Prefs.KEEP_ALIVE, true);
        store.setDefault(Prefs.PERMISSION_MODE, "default");
    }
}
