package is.mehta.claudecode.abap.views;

import org.eclipse.jface.action.Action;
import org.eclipse.jface.action.IToolBarManager;
import org.eclipse.swt.SWT;
import org.eclipse.swt.browser.Browser;
import org.eclipse.swt.browser.LocationAdapter;
import org.eclipse.swt.browser.LocationEvent;
import org.eclipse.swt.browser.WindowEvent;
import org.eclipse.swt.dnd.Clipboard;
import org.eclipse.swt.dnd.TextTransfer;
import org.eclipse.swt.dnd.Transfer;
import org.eclipse.swt.program.Program;
import org.eclipse.swt.widgets.Composite;
import org.eclipse.swt.widgets.Display;
import org.eclipse.swt.widgets.Shell;
import org.eclipse.ui.IActionBars;
import org.eclipse.ui.actions.ActionFactory;
import org.eclipse.ui.dialogs.PreferencesUtil;
import org.eclipse.ui.part.ViewPart;

import is.mehta.claudecode.abap.Activator;
import is.mehta.claudecode.abap.adt.AdtMcpServerStarter;
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
        installEditActionHandlers();
    }

    /**
     * The workbench key-binding service catches Select All / Copy / Cut / Paste
     * (⌘A/C/X/V on macOS, Ctrl+ on Windows/Linux) at a Display-level filter and
     * routes them to the retargetable edit commands before the embedded WebKit
     * view sees the keystroke. With no handler registered they are simply
     * swallowed, which is why nothing happens inside the chat panel. Registering
     * global action handlers on this view's action bars makes those accelerators
     * resolve to us; we bridge each into the browser DOM. The accelerator-to-
     * command binding is already platform-aware, so this covers ⌘ and Ctrl at
     * once.
     */
    private void installEditActionHandlers() {
        IActionBars bars = getViewSite().getActionBars();
        bars.setGlobalActionHandler(ActionFactory.SELECT_ALL.getId(), new Action() {
            @Override
            public void run() {
                runJs(SELECT_ALL_JS);
            }
        });
        bars.setGlobalActionHandler(ActionFactory.COPY.getId(), new Action() {
            @Override
            public void run() {
                copySelection(false);
            }
        });
        bars.setGlobalActionHandler(ActionFactory.CUT.getId(), new Action() {
            @Override
            public void run() {
                copySelection(true);
            }
        });
        bars.setGlobalActionHandler(ActionFactory.PASTE.getId(), new Action() {
            @Override
            public void run() {
                pasteFromClipboard();
            }
        });
        bars.updateActionBars();
    }

    private static final String SELECT_ALL_JS =
            "var el=document.activeElement;"
            + "if(el&&(el.tagName==='INPUT'||el.tagName==='TEXTAREA')&&typeof el.select==='function'){el.select();}"
            + "else{document.execCommand('selectAll',false,null);}";

    private static final String SELECTION_TEXT_JS =
            "var el=document.activeElement;"
            + "if(el&&(el.tagName==='INPUT'||el.tagName==='TEXTAREA')&&typeof el.selectionStart==='number'){"
            + "return el.value.substring(el.selectionStart,el.selectionEnd);}"
            + "var sel=window.getSelection();return sel?sel.toString():'';";

    private static final String DELETE_SELECTION_JS =
            "var el=document.activeElement;"
            + "if(el&&(el.tagName==='INPUT'||el.tagName==='TEXTAREA')&&typeof el.selectionStart==='number'){"
            + "var s=el.selectionStart,e=el.selectionEnd;"
            + "if(e>s){el.value=el.value.slice(0,s)+el.value.slice(e);"
            + "el.selectionStart=el.selectionEnd=s;"
            + "el.dispatchEvent(new Event('input',{bubbles:true}));}}"
            + "else{document.execCommand('delete',false,null);}";

    /** Copy the current DOM/input selection into the SWT clipboard; optionally delete it (cut). */
    private void copySelection(boolean cut) {
        if (browser == null || browser.isDisposed()) {
            return;
        }
        Object result = browser.evaluate(SELECTION_TEXT_JS);
        String text = result instanceof String ? (String) result : "";
        if (!text.isEmpty()) {
            Clipboard clipboard = new Clipboard(browser.getDisplay());
            try {
                clipboard.setContents(new Object[] { text }, new Transfer[] { TextTransfer.getInstance() });
            } finally {
                clipboard.dispose();
            }
        }
        if (cut) {
            browser.execute(DELETE_SELECTION_JS);
        }
    }

    /** Read text from the SWT clipboard and insert it at the caret in the focused editable element. */
    private void pasteFromClipboard() {
        if (browser == null || browser.isDisposed()) {
            return;
        }
        String text;
        Clipboard clipboard = new Clipboard(browser.getDisplay());
        try {
            Object contents = clipboard.getContents(TextTransfer.getInstance());
            text = contents instanceof String ? (String) contents : null;
        } finally {
            clipboard.dispose();
        }
        if (text == null || text.isEmpty()) {
            return;
        }
        browser.execute("(function(t){var el=document.activeElement;"
                + "if(el&&(el.tagName==='INPUT'||el.tagName==='TEXTAREA')&&typeof el.selectionStart==='number'){"
                + "var s=el.selectionStart,e=el.selectionEnd;"
                + "el.value=el.value.slice(0,s)+t+el.value.slice(e);"
                + "var p=s+t.length;el.selectionStart=el.selectionEnd=p;"
                + "el.dispatchEvent(new Event('input',{bubbles:true}));}"
                + "else{document.execCommand('insertText',false,t);}})(" + toJsString(text) + ");");
    }

    private void runJs(String script) {
        if (browser != null && !browser.isDisposed()) {
            browser.execute(script);
        }
    }

    /** Encode an arbitrary string as a safe JavaScript string literal (including quotes). */
    private static String toJsString(String s) {
        StringBuilder out = new StringBuilder(s.length() + 2);
        out.append('"');
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            switch (c) {
                case '"':
                    out.append("\\\"");
                    break;
                case '\\':
                    out.append("\\\\");
                    break;
                case '\n':
                    out.append("\\n");
                    break;
                case '\r':
                    out.append("\\r");
                    break;
                case '\t':
                    out.append("\\t");
                    break;
                case '<':
                    // Avoid an accidental </script> breaking out of any host context.
                    out.append("\\u003c");
                    break;
                default:
                    // Escape controls plus U+2028/U+2029, illegal raw in JS strings.
                    if (c < 0x20 || c == 0x2028 || c == 0x2029) {
                        out.append(String.format("\\u%04x", (int) c));
                    } else {
                        out.append(c);
                    }
            }
        }
        out.append('"');
        return out.toString();
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
                linkAdtMcpServer();
                manager.restart("user request");
            }
        };
        restart.setToolTipText("Start the ADT MCP Server if it is down, then relaunch the Claude Code sidecar");
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

    /**
     * Brings SAP's ADT MCP Server up when it is not listening, so a click on
     * "Restart Sidecar" (the recover-when-red action) also fixes the common
     * cause of the red dot: SAP does not bind the server at boot on a customer
     * install, only on a manual preference toggle. {@link AdtMcpServerStarter}
     * reproduces that toggle via SAP's own start call; if that ever fails
     * (SAP internal API moved) we open SAP's MCP preference page so the user
     * can enable it by hand. No-op when it is already running or disabled.
     */
    private void linkAdtMcpServer() {
        int port = Activator.getDefault().getPreferenceStore().getInt(Prefs.ADT_MCP_PORT);
        AdtMcpServerStarter.Result result = AdtMcpServerStarter.ensureRunning(port, AdtMcpTokenLocator.token());
        if (result == AdtMcpServerStarter.Result.START_FAILED) {
            PreferencesUtil.createPreferenceDialogOn(
                    getSite().getShell(), AdtMcpServerStarter.SAP_PREF_PAGE_ID, null, null).open();
        }
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
