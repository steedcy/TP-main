package com.airport.ai.device;

import jakarta.annotation.PreDestroy;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.net.ServerSocket;
import java.net.Socket;
import java.net.ConnectException;
import java.net.URI;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.TimeUnit;

/** Owns only processes it launches. Never kills a process discovered by port number. */
@Service
public class ManagedSimulatorService implements AutoCloseable {
    private static final org.slf4j.Logger LOG = org.slf4j.LoggerFactory.getLogger(ManagedSimulatorService.class);
    private final DeviceMapper devices;
    private final boolean enabled;
    private final Path jar;
    private final Path logs;
    private record ManagedProcess(Process process, int port) { }
    private final Map<String, ManagedProcess> processes = new HashMap<>();
    private final Map<String, String> reservations = new HashMap<>();

    public ManagedSimulatorService(DeviceMapper devices,
            @Value("${app.device.simulator-management-enabled:true}") boolean enabled,
            @Value("${app.device.simulator-jar:}") String configuredJar) {
        this.devices = devices;
        this.enabled = enabled;
        Path cwd = Path.of("").toAbsolutePath();
        Path root = Files.isDirectory(cwd.resolve("backend")) ? cwd
                : "backend".equals(String.valueOf(cwd.getFileName())) ? cwd.getParent() : cwd;
        this.jar = configuredJar == null || configuredJar.isBlank()
                ? root.resolve("simulator/target/device-simulator-runtime.jar")
                : Path.of(configuredJar).toAbsolutePath().normalize();
        this.logs = root.resolve(".local-test/managed-simulators");
    }

    public synchronized String allocateEndpoint(String deviceCode) {
        Set<Integer> used = new HashSet<>();
        for (String endpoint : devices.findActiveSimulatorEndpoints()) {
            try { used.add(localPort(endpoint)); } catch (IllegalArgumentException ignored) { }
        }
        for (String endpoint : reservations.values()) used.add(localPort(endpoint));
        for (int port = 18100; port <= 18199; port++) {
            if (!used.contains(port) && available(port)) {
                String endpoint = "http://127.0.0.1:" + port;
                reservations.put(deviceCode, endpoint);
                return endpoint;
            }
        }
        throw new IllegalStateException("没有可用仿真端口（18100～18199）");
    }

    static int localPort(String endpoint) {
        try {
            URI uri = URI.create(endpoint);
            if (!"http".equalsIgnoreCase(uri.getScheme())
                    || !("127.0.0.1".equals(uri.getHost()) || "localhost".equalsIgnoreCase(uri.getHost()))
                    || uri.getPort() < 1024 || uri.getPort() > 65535
                    || uri.getUserInfo() != null || uri.getQuery() != null || uri.getFragment() != null
                    || !(uri.getPath().isEmpty() || "/".equals(uri.getPath()))) {
                throw new IllegalArgumentException();
            }
            return uri.getPort();
        } catch (RuntimeException ex) {
            throw new IllegalArgumentException("自动进程管理仅支持本机HTTP根地址及1024～65535端口；远程仿真体请人工部署后连接测试");
        }
    }

    public synchronized void releaseReservation(String code) { reservations.remove(code); }

    public synchronized void restart(Device device, String token) {
        if (!enabled) throw new IllegalStateException("仿真进程管理已关闭，请启用DEVICE_SIMULATOR_MANAGEMENT_ENABLED");
        int port = localPort(device.getAccessEndpoint());
        if (!Files.isRegularFile(jar)) throw new IllegalStateException("仿真运行包不存在，请先构建simulator或配置DEVICE_SIMULATOR_JAR");
        ManagedProcess previous = processes.get(device.getDeviceCode());
        boolean replacingOwnedPort = previous != null && previous.process().isAlive() && previous.port() == port;
        stop(device.getDeviceCode());
        // Windows can still report the just-stopped listener briefly. For our own port,
        // let the replacement JVM perform the actual bind after startup. Foreign ports
        // must pass a listener check; no process discovered there is ever terminated.
        if (!replacingOwnedPort && hasListener(port)) throw new IllegalStateException("仿真端口已被其他进程占用，未停止该进程；请更换接入地址或人工处理");
        try {
            Files.createDirectories(logs);
            String javaName = System.getProperty("os.name").toLowerCase().contains("win") ? "java.exe" : "java";
            ProcessBuilder builder = new ProcessBuilder(Path.of(System.getProperty("java.home"), "bin", javaName).toString(),
                    "-Xms32m", "-Xmx128m", "-XX:MaxMetaspaceSize=128m", "-XX:+UseSerialGC", "-jar", jar.toString());
            Map<String, String> environment = builder.environment();
            Map<String, String> inherited = new HashMap<>(environment);
            environment.clear();
            inherited.forEach((key, value) -> {
                if (Set.of("SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP", "LANG", "HOME").contains(key.toUpperCase()))
                    environment.put(key, value);
            });
            environment.put("SERVER_ADDRESS", "127.0.0.1");
            environment.put("SIMULATOR_PORT", String.valueOf(port));
            environment.put("SIMULATOR_DEVICE_CODE", device.getDeviceCode());
            environment.put("SIMULATOR_DEVICE_TYPE", "SIMULATOR");
            environment.put("SIMULATED_DEVICE_TYPE", device.getSimulatedDeviceType());
            environment.put("SIMULATOR_DEVICE_TOKEN", token);
            environment.put("SIMULATOR_X", device.getPositionX().toPlainString());
            environment.put("SIMULATOR_Y", device.getPositionY().toPlainString());
            environment.put("SIMULATOR_ZONE", device.getAreaCode());
            environment.put("SIMULATOR_HEARTBEAT_INTERVAL_SECONDS", String.valueOf(device.getStatusReportInterval()));
            builder.redirectErrorStream(true).redirectOutput(ProcessBuilder.Redirect.appendTo(
                    logs.resolve(device.getDeviceCode() + ".log").toFile()));
            Process process = builder.start();
            processes.put(device.getDeviceCode(), new ManagedProcess(process, port));
            LOG.info("Started managed simulator {} pid={} port={}", device.getDeviceCode(), process.pid(), port);
        } catch (IOException ex) {
            throw new IllegalStateException("无法启动仿真进程，请检查Java、运行包与日志目录权限");
        }
    }

    public synchronized boolean isAlive(String deviceCode) {
        ManagedProcess owned = processes.get(deviceCode);
        return owned != null && owned.process().isAlive();
    }

    public synchronized void stop(String deviceCode) {
        ManagedProcess owned = processes.remove(deviceCode);
        reservations.remove(deviceCode);
        if (owned == null || !owned.process().isAlive()) return;
        Process process = owned.process();
        LOG.info("Stopping managed simulator {} pid={}", deviceCode, process.pid());
        process.destroy();
        try {
            if (!process.waitFor(5, TimeUnit.SECONDS)) {
                process.destroyForcibly();
                if (!process.waitFor(5, TimeUnit.SECONDS)) throw new IllegalStateException("原仿真进程未能停止，请稍后重试");
            }
            LOG.info("Stopped managed simulator {} pid={} alive={}", deviceCode, process.pid(), process.isAlive());
        } catch (InterruptedException ex) {
            process.destroyForcibly();
            Thread.currentThread().interrupt();
            throw new IllegalStateException("仿真进程停止被中断");
        }
    }

    private static boolean available(int port) {
        try (ServerSocket socket = new ServerSocket()) {
            socket.setReuseAddress(false);
            socket.bind(new InetSocketAddress("127.0.0.1", port));
            return true;
        } catch (IOException ex) { return false; }
    }

    private static boolean hasListener(int port) {
        try (Socket socket = new Socket()) {
            socket.connect(new InetSocketAddress("127.0.0.1", port), 500);
            return true;
        } catch (ConnectException ex) {
            return false;
        } catch (IOException ex) {
            return true;
        }
    }

    @PreDestroy
    public synchronized void close() {
        for (String code : Set.copyOf(processes.keySet())) stop(code);
    }
}
