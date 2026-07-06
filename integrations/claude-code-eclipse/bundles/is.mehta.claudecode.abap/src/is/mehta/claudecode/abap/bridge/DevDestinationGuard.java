package is.mehta.claudecode.abap.bridge;

import java.util.Arrays;
import java.util.List;

import org.eclipse.jface.preference.IPreferenceStore;

import is.mehta.claudecode.abap.prefs.Prefs;

/**
 * Dev-only guard (ADR-002 condition 2). Source read/write is permitted only
 * when the target editor resolves to an entry on the Dev system allowlist.
 * Fail-closed: an empty allowlist, or an editor whose destination cannot be
 * resolved to an allowlist entry, is refused.
 */
public final class DevDestinationGuard {

    private final IPreferenceStore store;

    public DevDestinationGuard(IPreferenceStore store) {
        this.store = store;
    }

    public List<String> allowlist() {
        String raw = store.getString(Prefs.DEV_ALLOWLIST);
        return Arrays.stream(raw.split("[,\n]"))
                .map(String::trim)
                .filter(s -> !s.isEmpty())
                .toList();
    }

    /**
     * Returns the matched allowlist entry, or null if the editor does not
     * resolve to any allowed destination. Match order: exact ABAP project
     * name, then tooltip containment (ADT tooltips carry the project name).
     */
    public String resolve(EditorSourceGateway.EditorHandle handle) {
        List<String> allowed = allowlist();
        if (allowed.isEmpty()) {
            return null;
        }
        for (String entry : allowed) {
            if (entry.equalsIgnoreCase(handle.project())) {
                return entry;
            }
        }
        String tooltip = handle.tooltip() == null ? "" : handle.tooltip().toLowerCase();
        for (String entry : allowed) {
            if (!tooltip.isEmpty() && tooltip.contains(entry.toLowerCase())) {
                return entry;
            }
        }
        return null;
    }

    public String refusalMessage(EditorSourceGateway.EditorHandle handle) {
        if (allowlist().isEmpty()) {
            return "Refused: the Dev system allowlist is empty. Add your Dev ABAP project name "
                    + "(e.g. S4H_100_myuser_en) in Preferences > Claude Code for ABAP.";
        }
        return "Refused: editor '" + handle.title() + "' (project '" + handle.project()
                + "') does not resolve to any allowlisted Dev system. Allowlist: " + allowlist();
    }
}
