package is.mehta.claudecode.abap.adt;

import org.eclipse.core.runtime.preferences.IEclipsePreferences;
import org.eclipse.core.runtime.preferences.InstanceScope;

/**
 * Reads the official ADT MCP Server settings from the workspace preference
 * node maintained by com.sap.adt.mcp.core.ui. No compile dependency on any
 * SAP bundle: this is the generic Eclipse preferences API against a known
 * node name and keys (observed in ADT 3.60). If SAP renames the node or
 * keys in a future ADT, token() returns "" and the UI surfaces remediation.
 */
public final class AdtMcpTokenLocator {

    private static final String NODE = "com.sap.adt.mcp.core.ui";
    private static final String KEY_ENABLE = "PREFERENCE_ADT_MCP_SERVER_ENABLE";
    private static final String KEY_TOKEN = "PREFERENCE_ADT_MCP_SERVER_TOKEN";

    private AdtMcpTokenLocator() {
    }

    private static IEclipsePreferences node() {
        return InstanceScope.INSTANCE.getNode(NODE);
    }

    public static boolean isEnabled() {
        return Boolean.parseBoolean(node().get(KEY_ENABLE, "false"));
    }

    public static String token() {
        return node().get(KEY_TOKEN, "");
    }

    /** Notifies on any change to the ADT MCP settings (enable toggled, token regenerated). */
    public static void onChange(Runnable callback) {
        node().addPreferenceChangeListener(event -> callback.run());
    }
}
