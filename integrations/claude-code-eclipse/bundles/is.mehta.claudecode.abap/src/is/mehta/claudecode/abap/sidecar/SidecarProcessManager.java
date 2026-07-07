package is.mehta.claudecode.abap.sidecar;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.File;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.io.Writer;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.RejectedExecutionException;
import java.util.concurrent.TimeUnit;

import org.eclipse.core.runtime.FileLocator;
import org.eclipse.core.runtime.IStatus;
import org.eclipse.core.runtime.Status;
import org.eclipse.jface.preference.IPreferenceStore;
import org.osgi.framework.Bundle;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

import is.mehta.claudecode.abap.Activator;
import is.mehta.claudecode.abap.adt.AdtMcpTokenLocator;
import is.mehta.claudecode.abap.bridge.BridgeToolDispatcher;
import is.mehta.claudecode.abap.prefs.Prefs;

/**
 * Owns the Node sidecar process. Java-to-sidecar transport is stdio NDJSON:
 * the sidecar's stdout carries protocol frames only (ready / bridge_request),
 * stderr carries diagnostics, and stdin receives bridge_response /
 * editor_context / shutdown frames. The sidecar self-exits on stdin EOF, so
 * closing stdin is a second, independent exit trigger next to the shutdown
 * frame.
 */
public final class SidecarProcessManager {

    private static final long INITIAL_BACKOFF_MS = 1_000;
    private static final long MAX_BACKOFF_MS = 30_000;
    private static final long STABLE_RUN_MS = 60_000;
    private static final int MAX_BUFFERED_CONTEXTS = 4;

    private final IPreferenceStore store;
    private final BridgeToolDispatcher dispatcher;
    private final List<Runnable> readyListeners = new CopyOnWriteArrayList<>();
    private final Deque<JsonObject> pendingEditorContext = new ArrayDeque<>();
    private final Object writeLock = new Object();

    private volatile Process process;
    private volatile Writer stdinWriter;
    private volatile boolean ready;
    private volatile int uiPort = -1;
    private volatile String uiToken;
    private volatile String lastError;
    private volatile boolean shuttingDown;
    private boolean everStarted;
    private long startedAt;
    private long backoffMs = INITIAL_BACKOFF_MS;
    private ExecutorService bridgeExecutor;

    public SidecarProcessManager(IPreferenceStore store) {
        this.store = store;
        this.dispatcher = new BridgeToolDispatcher(store);
        // Registered exactly once: the Activator holds a single manager instance.
        // Push the new url/token to the live sidecar instead of restarting it:
        // the sidecar re-registers sap-adt-mcp in place (Query.setMcpServers),
        // so a token that was absent or stale at spawn is corrected without the
        // user having to toggle the ADT MCP Server off and on. If the sidecar is
        // not running the push is a no-op; onReady re-sends the current config.
        AdtMcpTokenLocator.onChange(this::sendAdtConfig);
        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            Process p = process;
            if (p != null) {
                p.destroyForcibly();
            }
        }, "claude-sidecar-killer"));
    }

    // ---- lifecycle -------------------------------------------------------

    public synchronized void ensureStarted() {
        shuttingDown = false;
        Process p = process;
        if (p != null && p.isAlive()) {
            return;
        }
        stopProcessLocked();
        ensureExecutorLocked();
        startLocked();
    }

    public synchronized void restart(String reason) {
        if (!everStarted) {
            return;
        }
        log(IStatus.INFO, "Restarting sidecar: " + reason, null);
        stopProcessLocked();
        backoffMs = INITIAL_BACKOFF_MS;
        if (!shuttingDown) {
            ensureExecutorLocked();
            startLocked();
        }
    }

    public synchronized void shutdown(String reason) {
        shuttingDown = true;
        log(IStatus.INFO, "Stopping sidecar: " + reason, null);
        stopProcessLocked();
        if (bridgeExecutor != null) {
            bridgeExecutor.shutdownNow();
        }
    }

    public boolean isReady() {
        return ready;
    }

    public int getUiPort() {
        return uiPort;
    }

    public String getUiToken() {
        return uiToken;
    }

    public String lastError() {
        return lastError;
    }

    public boolean isRunning() {
        Process p = process;
        return p != null && p.isAlive();
    }

    /**
     * Listeners persist across restarts and fire on every ready event; a
     * listener registered while already ready also fires immediately. May be
     * invoked from the stdout reader thread - callers marshal to SWT.
     */
    public void addReadyListener(Runnable listener) {
        readyListeners.add(listener);
        if (ready) {
            safeRun(listener);
        }
    }

    public void removeReadyListener(Runnable listener) {
        readyListeners.remove(listener);
    }

    public void sendEditorContext(JsonObject context) {
        JsonObject frame = new JsonObject();
        frame.addProperty("type", "editor_context");
        frame.add("context", context);
        synchronized (this) {
            if (!ready) {
                pendingEditorContext.addLast(frame);
                while (pendingEditorContext.size() > MAX_BUFFERED_CONTEXTS) {
                    pendingEditorContext.removeFirst();
                }
                return;
            }
        }
        writeFrame(frame);
    }

    // ---- process start/stop ---------------------------------------------

    private void startLocked() {
        lastError = null;
        File installDir = resolveInstallDir();
        if (installDir == null) {
            return;
        }
        File script = new File(installDir, "sidecar/sidecar.js");
        if (!script.isFile()) {
            lastError = "Sidecar script not found: " + script.getAbsolutePath();
            log(IStatus.ERROR, lastError, null);
            return;
        }
        String node = findNode();
        if (node == null) {
            lastError = "Node.js not found (searched the Node.js preference, /opt/homebrew/bin, "
                    + "/usr/local/bin and PATH). Set the executable in Preferences > Claude Code for ABAP.";
            log(IStatus.ERROR, lastError, null);
            return;
        }
        uiToken = UUID.randomUUID().toString();
        ProcessBuilder pb = new ProcessBuilder(node, script.getAbsolutePath());
        pb.directory(installDir);
        var env = pb.environment();
        env.put("ADT_MCP_URL", "http://localhost:" + store.getInt(Prefs.ADT_MCP_PORT) + "/mcp");
        env.put("ADT_MCP_TOKEN", AdtMcpTokenLocator.token());
        env.put("UI_TOKEN", uiToken);
        env.put("DEV_ALLOWLIST", store.getString(Prefs.DEV_ALLOWLIST));
        env.put("CLAUDE_CWD", store.getString(Prefs.CLAUDE_CWD));
        env.put("UI_DIR", new File(installDir, "web").getAbsolutePath());
        env.put("PERMISSION_MODE", store.getString(Prefs.PERMISSION_MODE));
        // Eclipse launches with a minimal GUI environment; the SDK-spawned
        // claude CLI must still resolve on PATH.
        env.put("PATH", "/opt/homebrew/bin:/usr/local/bin:" + env.getOrDefault("PATH", ""));
        try {
            Process p = pb.start();
            process = p;
            stdinWriter = new BufferedWriter(new OutputStreamWriter(p.getOutputStream(), StandardCharsets.UTF_8));
            startedAt = System.currentTimeMillis();
            everStarted = true;
            p.onExit().thenAccept(this::handleExit);
            Thread stdout = new Thread(() -> readStdout(p), "claude-sidecar-stdout");
            stdout.setDaemon(true);
            stdout.start();
            Thread stderr = new Thread(() -> readStderr(p), "claude-sidecar-stderr");
            stderr.setDaemon(true);
            stderr.start();
            log(IStatus.INFO, "Sidecar started (pid " + p.pid() + ", node " + node
                    + ", dir " + installDir.getAbsolutePath() + ")", null);
        } catch (IOException e) {
            lastError = "Failed to start sidecar: " + e.getMessage();
            log(IStatus.ERROR, lastError, e);
        }
    }

    /**
     * Graceful stop: shutdown frame, stdin close (EOF), 2s grace, then kill.
     * Nulls the process field first so handleExit can tell this deliberate
     * stop from a crash.
     */
    private void stopProcessLocked() {
        Process p = process;
        Writer w = stdinWriter;
        process = null;
        stdinWriter = null;
        ready = false;
        uiPort = -1;
        if (p == null) {
            return;
        }
        synchronized (writeLock) {
            try {
                if (w != null) {
                    w.write("{\"type\":\"shutdown\"}\n");
                    w.flush();
                    w.close();
                }
            } catch (IOException e) {
                // pipe already broken - the process is likely dead
            }
        }
        try {
            if (!p.waitFor(2, TimeUnit.SECONDS)) {
                p.destroyForcibly();
            }
        } catch (InterruptedException e) {
            p.destroyForcibly();
            Thread.currentThread().interrupt();
        }
    }

    private void handleExit(Process p) {
        long delay;
        synchronized (this) {
            if (shuttingDown || p != process) {
                return; // deliberate stop or superseded process
            }
            process = null;
            stdinWriter = null;
            ready = false;
            uiPort = -1;
            if (!store.getBoolean(Prefs.KEEP_ALIVE)) {
                lastError = "Sidecar exited (code " + p.exitValue() + ") and keep-alive is off. "
                        + "Use 'Restart Sidecar' in the view toolbar.";
                log(IStatus.WARNING, lastError, null);
                return;
            }
            if (System.currentTimeMillis() - startedAt >= STABLE_RUN_MS) {
                backoffMs = INITIAL_BACKOFF_MS;
            }
            delay = backoffMs;
            backoffMs = Math.min(backoffMs * 2, MAX_BACKOFF_MS);
        }
        log(IStatus.WARNING, "Sidecar exited unexpectedly (code " + p.exitValue()
                + "); restarting in " + delay + " ms", null);
        Thread t = new Thread(() -> {
            try {
                Thread.sleep(delay);
            } catch (InterruptedException e) {
                return;
            }
            synchronized (this) {
                if (!shuttingDown && process == null) {
                    ensureExecutorLocked();
                    startLocked();
                }
            }
        }, "claude-sidecar-restart");
        t.setDaemon(true);
        t.start();
    }

    private void ensureExecutorLocked() {
        if (bridgeExecutor == null || bridgeExecutor.isShutdown()) {
            bridgeExecutor = Executors.newSingleThreadExecutor(r -> {
                Thread t = new Thread(r, "claude-bridge-dispatch");
                t.setDaemon(true);
                return t;
            });
        }
    }

    // ---- discovery -------------------------------------------------------

    private File resolveInstallDir() {
        String override = store.getString(Prefs.DEV_OVERRIDE_PATH).trim();
        if (!override.isEmpty()) {
            File dir = new File(override);
            if (dir.isDirectory()) {
                return dir;
            }
            lastError = "Dev override path is not a directory: " + override;
            log(IStatus.ERROR, lastError, null);
            return null;
        }
        Bundle bundle = Activator.getDefault().getBundle();
        Optional<File> location = FileLocator.getBundleFileLocation(bundle);
        if (location.isPresent()) {
            return location.get();
        }
        try {
            URL root = bundle.getEntry("/");
            if (root != null) {
                // toFileURL leaves special characters unescaped, so the raw
                // path component is the real filesystem path.
                return new File(FileLocator.toFileURL(root).getPath());
            }
        } catch (IOException e) {
            log(IStatus.ERROR, "FileLocator.toFileURL failed for the bundle root", e);
        }
        lastError = "Cannot resolve the installed bundle to a directory (expected Eclipse-BundleShape: dir).";
        log(IStatus.ERROR, lastError, null);
        return null;
    }

    private String findNode() {
        String pref = store.getString(Prefs.NODE_PATH).trim();
        if (!pref.isEmpty()) {
            return pref;
        }
        for (String candidate : List.of("/opt/homebrew/bin/node", "/usr/local/bin/node")) {
            if (new File(candidate).canExecute()) {
                return candidate;
            }
        }
        String path = System.getenv("PATH");
        if (path != null) {
            for (String dir : path.split(File.pathSeparator)) {
                if (dir.isBlank()) {
                    continue;
                }
                File f = new File(dir.trim(), "node");
                if (f.isFile() && f.canExecute()) {
                    return f.getAbsolutePath();
                }
            }
        }
        return null;
    }

    // ---- stdio protocol ---------------------------------------------------

    private void readStdout(Process proc) {
        try (BufferedReader reader = new BufferedReader(
                new InputStreamReader(proc.getInputStream(), StandardCharsets.UTF_8))) {
            String line;
            while ((line = reader.readLine()) != null) {
                if (line.isBlank()) {
                    continue;
                }
                JsonObject msg;
                try {
                    msg = JsonParser.parseString(line).getAsJsonObject();
                } catch (RuntimeException e) {
                    log(IStatus.WARNING, "Malformed sidecar frame: " + line, e);
                    continue;
                }
                try {
                    dispatchFrame(proc, msg);
                } catch (RuntimeException e) {
                    log(IStatus.ERROR, "Error handling sidecar frame: " + line, e);
                }
            }
        } catch (IOException e) {
            // stream closes when the process dies; handleExit takes over
        }
    }

    private void readStderr(Process proc) {
        try (BufferedReader reader = new BufferedReader(
                new InputStreamReader(proc.getErrorStream(), StandardCharsets.UTF_8))) {
            String line;
            while ((line = reader.readLine()) != null) {
                if (!line.isBlank()) {
                    log(IStatus.INFO, "[sidecar] " + line, null);
                }
            }
        } catch (IOException e) {
            // stream closed with the process
        }
    }

    private void dispatchFrame(Process proc, JsonObject msg) {
        String type = msg.has("type") ? msg.get("type").getAsString() : "";
        switch (type) {
            case "ready" -> onReady(proc, msg.get("uiPort").getAsInt());
            case "bridge_request" -> onBridgeRequest(msg);
            default -> log(IStatus.INFO, "Ignoring sidecar frame type '" + type + "'", null);
        }
    }

    private void onReady(Process proc, int port) {
        List<JsonObject> buffered;
        synchronized (this) {
            if (proc != process) {
                return;
            }
            uiPort = port;
            ready = true;
            buffered = new ArrayList<>(pendingEditorContext);
            pendingEditorContext.clear();
        }
        log(IStatus.INFO, "Sidecar ready on 127.0.0.1:" + port, null);
        // Read the ADT token fresh at ready-time and push it: the spawn-time env
        // snapshot can be empty or stale if SAP's ADT MCP bundle initialised (or
        // rotated its token) after we launched. This closes that startup race.
        sendAdtConfig();
        for (JsonObject frame : buffered) {
            writeFrame(frame);
        }
        for (Runnable listener : readyListeners) {
            safeRun(listener);
        }
    }

    /**
     * Pushes the current ADT MCP url + token to the sidecar as an {@code
     * adt_config} frame. No-op when the sidecar has no open stdin (not started);
     * onReady re-sends once it is up. Safe to call from the preference-change
     * thread — writeFrame serialises on the write lock.
     */
    private void sendAdtConfig() {
        JsonObject frame = new JsonObject();
        frame.addProperty("type", "adt_config");
        frame.addProperty("url", "http://localhost:" + store.getInt(Prefs.ADT_MCP_PORT) + "/mcp");
        frame.addProperty("token", AdtMcpTokenLocator.token());
        writeFrame(frame);
    }

    private void onBridgeRequest(JsonObject msg) {
        String id = msg.get("id").getAsString();
        String tool = msg.get("tool").getAsString();
        JsonObject params = msg.has("params") && msg.get("params").isJsonObject()
                ? msg.getAsJsonObject("params")
                : new JsonObject();
        ExecutorService exec;
        synchronized (this) {
            exec = bridgeExecutor;
        }
        if (exec == null || exec.isShutdown()) {
            return;
        }
        try {
            exec.execute(() -> {
                JsonObject result;
                try {
                    result = dispatcher.handle(tool, params);
                } catch (RuntimeException e) {
                    result = new JsonObject();
                    result.addProperty("ok", false);
                    result.addProperty("error", e.getClass().getSimpleName() + ": " + e.getMessage());
                }
                JsonObject reply = new JsonObject();
                reply.addProperty("type", "bridge_response");
                reply.addProperty("id", id);
                reply.add("result", result);
                writeFrame(reply);
            });
        } catch (RejectedExecutionException e) {
            // shutting down; the sidecar is going away with us
        }
    }

    private void writeFrame(JsonObject frame) {
        Writer w = stdinWriter;
        if (w == null) {
            return;
        }
        String line = frame.toString(); // gson emits compact single-line JSON
        synchronized (writeLock) {
            try {
                w.write(line);
                w.write('\n');
                w.flush();
            } catch (IOException e) {
                log(IStatus.WARNING, "Failed to write to sidecar stdin: " + e.getMessage(), null);
            }
        }
    }

    private static void safeRun(Runnable listener) {
        try {
            listener.run();
        } catch (RuntimeException e) {
            log(IStatus.ERROR, "Ready listener failed", e);
        }
    }

    private static void log(int severity, String message, Throwable t) {
        Activator activator = Activator.getDefault();
        if (activator != null) {
            activator.getLog().log(new Status(severity, Activator.PLUGIN_ID, message, t));
        }
    }
}
