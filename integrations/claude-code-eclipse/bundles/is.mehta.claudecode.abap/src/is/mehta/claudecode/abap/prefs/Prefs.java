package is.mehta.claudecode.abap.prefs;

/** Preference keys for the plug-in's own preference store. */
public final class Prefs {

    public static final String NODE_PATH = "nodePath";
    public static final String DEV_ALLOWLIST = "devSystemAllowlist";
    public static final String CLAUDE_CWD = "claudeCwd";
    public static final String DEV_OVERRIDE_PATH = "devOverridePath";
    public static final String ADT_MCP_PORT = "adtMcpPort";
    public static final String KEEP_ALIVE = "keepSidecarAlive";
    public static final String PERMISSION_MODE = "permissionMode";

    private Prefs() {
    }
}
