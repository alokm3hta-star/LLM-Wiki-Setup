package is.mehta.claudecode.abap.adt;

import java.lang.reflect.Method;
import java.net.InetSocketAddress;
import java.net.Socket;

import org.eclipse.core.runtime.Platform;
import org.osgi.framework.Bundle;

/**
 * Starts SAP's ADT MCP Server on demand.
 *
 * <p>SAP only auto-starts the server at boot when the system property
 * {@code adtMcpServerPrefEnabled=true} is set, and on a non-SAP-internal
 * install that property is read through a fixed allow-list that excludes it,
 * so the flag is silently ignored. The only other start site is the ADT MCP
 * Server preference page's OK handler. The upshot: a freshly launched Eclipse
 * leaves the server unbound even though the Enable checkbox is ticked, and the
 * sidecar's sap-adt-mcp connection fails ("Unable to connect") until the user
 * toggles the preference by hand.
 *
 * <p>This reproduces the preference page's action programmatically: it calls
 * SAP's own {@code AdtMCPCorePlugin.startMCPServer(port, token, SFS)} through
 * the SAP bundle's own class loader (no compile dependency on any SAP bundle,
 * matching {@link AdtMcpTokenLocator}). If SAP renames or re-signs that
 * internal method in a future ADT the reflective call fails cleanly and the
 * caller falls back to opening {@link #SAP_PREF_PAGE_ID}.
 */
public final class AdtMcpServerStarter {

    /** SAP's ADT MCP Server preference page id (from com.sap.adt.mcp.core.ui plugin.xml). */
    public static final String SAP_PREF_PAGE_ID =
            "com.sap.adt.mcp.core.ui.internal.preferences.AdtMcpPreferences";

    private static final String SAP_CORE_BUNDLE = "com.sap.adt.mcp.core";
    private static final String CORE_PLUGIN_CLASS = "com.sap.adt.mcp.core.internal.AdtMCPCorePlugin";
    private static final String FS_MODE_CLASS = "com.sap.adt.mcp.core.IAdtMcpEnvironmentInfo$FileSystemMode";
    private static final String FS_MODE_SFS = "SFS";
    private static final int CONNECT_TIMEOUT_MS = 300;

    public enum Result {
        /** The server was already bound to the port; nothing to do. */
        ALREADY_RUNNING,
        /** The server was not listening and we started it. */
        STARTED,
        /** The Enable checkbox is off; we do not force it on. */
        DISABLED,
        /** The server was down and the reflective start failed; fall back to the pref page. */
        START_FAILED
    }

    private AdtMcpServerStarter() {
    }

    /** True when something accepts a TCP connection on localhost:port. */
    public static boolean isListening(int port) {
        try (Socket s = new Socket()) {
            s.connect(new InetSocketAddress("127.0.0.1", port), CONNECT_TIMEOUT_MS);
            return true;
        } catch (Exception e) {
            return false;
        }
    }

    /**
     * Ensures SAP's ADT MCP Server is listening on {@code port}. No-op when it
     * is already up or the user has disabled it; otherwise starts it with the
     * token SAP itself would use. Safe to call from any thread; the reflective
     * start binds a socket and returns quickly, mirroring SAP's own OK handler.
     */
    public static Result ensureRunning(int port, String token) {
        if (isListening(port)) {
            return Result.ALREADY_RUNNING;
        }
        if (!AdtMcpTokenLocator.isEnabled()) {
            return Result.DISABLED;
        }
        try {
            startViaReflection(port, token);
            return Result.STARTED;
        } catch (Throwable t) {
            return Result.START_FAILED;
        }
    }

    private static void startViaReflection(int port, String token) throws Exception {
        Bundle core = Platform.getBundle(SAP_CORE_BUNDLE);
        if (core == null) {
            throw new IllegalStateException(SAP_CORE_BUNDLE + " bundle not present");
        }
        Class<?> pluginCls = core.loadClass(CORE_PLUGIN_CLASS);
        Object plugin = pluginCls.getMethod("getInstance").invoke(null);
        if (plugin == null) {
            throw new IllegalStateException(CORE_PLUGIN_CLASS + ".getInstance() returned null");
        }
        Class<?> fsMode = core.loadClass(FS_MODE_CLASS);
        Object sfs = fsMode.getField(FS_MODE_SFS).get(null);
        Method start = pluginCls.getMethod("startMCPServer", int.class, String.class, fsMode);
        start.invoke(plugin, port, token, sfs);
    }
}
