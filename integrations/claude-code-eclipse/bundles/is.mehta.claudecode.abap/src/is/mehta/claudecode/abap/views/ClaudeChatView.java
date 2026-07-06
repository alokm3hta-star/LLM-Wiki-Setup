package is.mehta.claudecode.abap.views;

import org.eclipse.jface.action.Action;
import org.eclipse.jface.action.IToolBarManager;
import org.eclipse.swt.SWT;
import org.eclipse.swt.browser.Browser;
import org.eclipse.swt.browser.LocationAdapter;
import org.eclipse.swt.browser.LocationEvent;
import org.eclipse.swt.browser.WindowEvent;
import org.eclipse.swt.program.Program;
import org.eclipse.swt.widgets.Composite;
import org.eclipse.swt.widgets.Display;
import org.eclipse.swt.widgets.Shell;
import org.eclipse.ui.dialogs.PreferencesUtil;
import org.eclipse.ui.part.ViewPart;

import is.mehta.claudecode.abap.Activator;
import is.mehta.claudecode.abap.adt.AdtMcpTokenLocator;
import is.mehta.claudecode.abap.prefs.Prefs;
import is.mehta.claudecode.abap.sidecar.SidecarProcessManager;

/**
 * Joule-style docked chat panel: an SWT Browser (WebKit on macOS) that loads
 * the sidecar-served chat UI once the sidecar reports ready. Until then it
 * shows an inline splash with remediation hints.
 */
public class ClaudeChatView extends ViewPart {

    public static final String ID = "is.mehta.claudecode.abap.chatView";

    private static final String PREF_PAGE_ID = "is.mehta.claudecode.abap.preferences";

    private Browser browser;
    private SidecarProcessManager manager;
    private final Runnable readyListener = () -> Display.getDefault().asyncExec(this::navigateToUi);

    @Override
    public void createPartControl(Composite parent) {
        browser = new Browser(parent, SWT.NONE);
        // The panel stays pinned to the sidecar UI; everything else (links in
        // Claude's markdown render with target=_blank) opens externally.
        browser.addLocationListener(new LocationAdapter() {
            @Override
            public void changing(LocationEvent event) {
                if (event.top && isExternal(event.location)) {
                    event.doit = false;
                    Program.launch(event.location);
                }
            }
        });
        browser.addOpenWindowListener(this::openExternally);
        manager = Activator.getDefault().getSidecarManager();
        manager.ensureStarted();
        showSplash();
        manager.addReadyListener(readyListener);
        createToolbar();
    }

    private static boolean isExternal(String location) {
        return location != null
                && (location.startsWith("http://") || location.startsWith("https://"))
                && !location.startsWith("http://127.0.0.1:");
    }

    /**
     * target=_blank has no window to open in a view-embedded Browser; capture
     * the navigation in a throwaway hidden browser and hand the URL to the
     * system browser instead.
     */
    private void openExternally(WindowEvent event) {
        Shell shell = new Shell(browser.getDisplay());
        Browser hidden = new Browser(shell, SWT.NONE);
        event.browser = hidden;
        hidden.addLocationListener(new LocationAdapter() {
            @Override
            public void changing(LocationEvent e) {
                e.doit = false;
                if (isExternal(e.location)) {
                    Program.launch(e.location);
                }
                shell.getDisplay().asyncExec(shell::dispose);
            }
        });
    }

    private void navigateToUi() {
        if (browser == null || browser.isDisposed() || !manager.isReady()) {
            return;
        }
        browser.setUrl("http://127.0.0.1:" + manager.getUiPort() + "/ui/?token=" + manager.getUiToken()
                + "&theme=" + (Display.isSystemDarkTheme() ? "dark" : "light"));
    }

    private void showSplash() {
        if (browser == null || browser.isDisposed()) {
            return;
        }
        boolean dark = Display.isSystemDarkTheme();
        String bg = dark ? "#1f1f1f" : "#ffffff";
        String fg = dark ? "#cccccc" : "#333333";
        String dim = dark ? "#8c8c8c" : "#777777";
        StringBuilder html = new StringBuilder(640);
        html.append("<html><body style=\"margin:0;display:flex;align-items:center;justify-content:center;")
                .append("height:100vh;background:").append(bg).append(";color:").append(fg)
                .append(";font-family:-apple-system,'Helvetica Neue',sans-serif\">")
                .append("<div style=\"text-align:center;max-width:28em;padding:1em\">")
                .append("<p style=\"font-size:1.1em\">Starting Claude Code&hellip;</p>");
        if (!AdtMcpTokenLocator.isEnabled() || AdtMcpTokenLocator.token().isEmpty()) {
            // The sidecar tolerates a missing token; the ADT tools just stay dark.
            html.append("<p style=\"font-size:0.85em;color:").append(dim).append("\">")
                    .append("Enable the ADT MCP Server under Preferences &gt; ABAP Development &gt; ")
                    .append("MCP Server, then restart the sidecar.</p>");
        }
        if (manager.lastError() != null) {
            html.append("<p style=\"font-size:0.85em;color:#d9534f\">")
                    .append(escapeHtml(manager.lastError())).append("</p>");
        }
        html.append("</div></body></html>");
        browser.setText(html.toString());
    }

    private void createToolbar() {
        IToolBarManager toolbar = getViewSite().getActionBars().getToolBarManager();
        Action restart = new Action("Restart Sidecar") {
            @Override
            public void run() {
                showSplash();
                manager.restart("user request");
            }
        };
        restart.setToolTipText("Stop and relaunch the Claude Code sidecar process");
        Action preferences = new Action("Preferences…") {
            @Override
            public void run() {
                PreferencesUtil.createPreferenceDialogOn(getSite().getShell(), PREF_PAGE_ID, null, null).open();
            }
        };
        preferences.setToolTipText("Open the Claude Code for ABAP preferences");
        toolbar.add(restart);
        toolbar.add(preferences);
        getViewSite().getActionBars().updateActionBars();
    }

    @Override
    public void setFocus() {
        if (browser != null && !browser.isDisposed()) {
            browser.setFocus();
        }
    }

    @Override
    public void dispose() {
        if (manager != null) {
            manager.removeReadyListener(readyListener);
            Activator activator = Activator.getDefault();
            if (activator != null && !activator.getPreferenceStore().getBoolean(Prefs.KEEP_ALIVE)) {
                manager.shutdown("view closed");
            }
        }
        super.dispose();
    }

    private static String escapeHtml(String s) {
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;");
    }
}
