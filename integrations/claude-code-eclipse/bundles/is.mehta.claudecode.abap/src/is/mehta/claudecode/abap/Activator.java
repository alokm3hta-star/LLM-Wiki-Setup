package is.mehta.claudecode.abap;

import org.eclipse.ui.plugin.AbstractUIPlugin;
import org.osgi.framework.BundleContext;

import is.mehta.claudecode.abap.sidecar.SidecarProcessManager;

public class Activator extends AbstractUIPlugin {

    public static final String PLUGIN_ID = "is.mehta.claudecode.abap";

    private static Activator instance;
    private SidecarProcessManager sidecarManager;

    @Override
    public void start(BundleContext context) throws Exception {
        super.start(context);
        instance = this;
    }

    @Override
    public void stop(BundleContext context) throws Exception {
        if (sidecarManager != null) {
            sidecarManager.shutdown("plug-in stop");
            sidecarManager = null;
        }
        instance = null;
        super.stop(context);
    }

    public static Activator getDefault() {
        return instance;
    }

    public synchronized SidecarProcessManager getSidecarManager() {
        if (sidecarManager == null) {
            sidecarManager = new SidecarProcessManager(getPreferenceStore());
        }
        return sidecarManager;
    }
}
