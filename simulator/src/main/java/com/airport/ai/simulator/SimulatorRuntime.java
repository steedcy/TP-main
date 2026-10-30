package com.airport.ai.simulator;

import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestTemplate;
import jakarta.annotation.PostConstruct;

import java.time.OffsetDateTime;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicReference;

@Service
public class SimulatorRuntime {
    private static final Set<String> FORBIDDEN = Set.of("speed", "velocity", "acceleration", "pose", "waypoints",
            "obstacleAvoidance", "emergencyStop", "speedLimit", "safeStopOnDisconnect",
            "attitude", "orientation", "pathPoints", "lostConnectionParking");
    private static final Set<String> FORBIDDEN_NORMALIZED = FORBIDDEN.stream()
            .map(k -> k.toLowerCase().replaceAll("[\\s_\\-]", "")).collect(java.util.stream.Collectors.toSet());
    private final SimulatorProperties properties;
    private final Map<String, CapabilityDriver> drivers;
    private final CapabilityDriver driver;
    private final RestTemplate http = new RestTemplate();
    private final AtomicBoolean heartbeatEnabled = new AtomicBoolean(true);
    private final java.util.Set<String> cancelled = ConcurrentHashMap.newKeySet();
    private final AtomicBoolean online = new AtomicBoolean(true);
    private final AtomicBoolean busy = new AtomicBoolean(false);
    private final AtomicReference<SimulatorProtocol.Location> currentLocation;
    private final Map<String, String> commandStates = new ConcurrentHashMap<>();
    private final Map<String, SimulatorProtocol.Report> commandReports = new ConcurrentHashMap<>();
    private final AtomicReference<String> activeCommand = new AtomicReference<>();
    private volatile String agentCode;
    private volatile String reportUrl;

    public SimulatorRuntime(SimulatorProperties properties, java.util.List<CapabilityDriver> availableDrivers) {
        this.properties = properties;
        this.drivers = availableDrivers.stream().collect(java.util.stream.Collectors.toUnmodifiableMap(
                CapabilityDriver::deviceType, candidate -> candidate));
        this.driver = drivers.get(properties.getSimulatedDeviceType());
        if (!"SIMULATOR".equals(properties.getDeviceType())
                || this.driver == null) {
            throw new IllegalStateException("设备类型必须为SIMULATOR，且模拟类型必须有已注册驱动");
        }
        this.currentLocation = new AtomicReference<>(new SimulatorProtocol.Location(properties.getX(), properties.getY(), properties.getZone()));
        if (properties.getHeartbeatIntervalSeconds() < 5 || properties.getHeartbeatIntervalSeconds() > 60
                || properties.getHeartbeatTimeoutSeconds() < 10 || properties.getHeartbeatTimeoutSeconds() > 120
                || properties.getExecutionDelayMilliseconds() < 0 || properties.getExecutionDelayMilliseconds() > 60000) {
            throw new IllegalStateException("心跳或执行延迟配置超出通信契约范围");
        }
        if (!Set.of("SUCCESS", "FAILED", "TIMEOUT", "NO_FEEDBACK", "NO_OBJECT", "LOST_TARGET").contains(properties.getScenarioResult())) {
            throw new IllegalStateException("scenario-result不受支持");
        }
        if (("NO_OBJECT".equals(properties.getScenarioResult()) && !"BAGGAGE_SCANNER".equals(driver.deviceType()))
                || ("LOST_TARGET".equals(properties.getScenarioResult()) && !"MOBILE_ROBOT".equals(driver.deviceType()))) {
            throw new IllegalStateException("scenario-result与模拟设备类型不匹配");
        }
    }

    /** Named fictional fixtures for the two baggage decision branches. */
    public synchronized Map<String, Object> setBaggageSample(String sample) {
        if (!"BAGGAGE_SCANNER".equals(properties.getSimulatedDeviceType()))
            throw new IllegalArgumentException("仅行李测量仿真体可切换样本");
        if ("OVERSIZE".equals(sample)) {
            properties.setBaggageLengthCm(80); properties.setBaggageWidthCm(55);
            properties.setBaggageHeightCm(35); properties.setBaggageWeightKg(35);
        } else if ("NORMAL".equals(sample)) {
            properties.setBaggageLengthCm(55); properties.setBaggageWidthCm(40);
            properties.setBaggageHeightCm(20); properties.setBaggageWeightKg(10);
        } else throw new IllegalArgumentException("sample须为OVERSIZE或NORMAL");
        return Map.of("sample", sample, "length", properties.getBaggageLengthCm(),
                "width", properties.getBaggageWidthCm(), "height", properties.getBaggageHeightCm(),
                "weight", properties.getBaggageWeightKg());
    }

    @PostConstruct
    void restoreConfiguredBinding() {
        if (properties.getAgentCode() != null && !properties.getAgentCode().isBlank()
                && properties.getPlatformReportUrl() != null && !properties.getPlatformReportUrl().isBlank()) {
            this.agentCode = properties.getAgentCode();
            this.reportUrl = properties.getPlatformReportUrl();
        }
    }

    public SimulatorProtocol.HealthResponse health(String nonce) {
        return new SimulatorProtocol.HealthResponse("1.0", nonce, properties.getDeviceCode(),
                properties.getDeviceType(), properties.getSimulatedDeviceType(), online.get() ? "ONLINE" : "OFFLINE",
                busy.get() ? "BUSY" : "IDLE", location(), driver.capabilities().stream().sorted().toList(),
                OffsetDateTime.now().toString());
    }

    public synchronized void bind(String pathAgentCode, SimulatorProtocol.BindingRequest request) {
        if (!properties.getDeviceCode().equals(request.deviceCode()) || !pathAgentCode.equals(request.agentCode())) {
            throw new IllegalArgumentException("绑定设备身份不匹配");
        }
        if (agentCode != null && !agentCode.equals(pathAgentCode)) {
            throw new IllegalArgumentException("该仿真实例已绑定其他代理");
        }
        if (request.reportUrl() == null || !request.reportUrl().startsWith("http")) {
            throw new IllegalArgumentException("reportUrl无效");
        }
        if (request.heartbeatIntervalSeconds() == null || request.heartbeatIntervalSeconds() < 5
                || request.heartbeatIntervalSeconds() > 60) throw new IllegalArgumentException("心跳周期必须为5~60秒");
        this.agentCode = pathAgentCode;
        this.reportUrl = request.reportUrl();
        online.set(true);
    }

    public void accept(SimulatorProtocol.Command command) {
        if (command.commandId() == null || command.commandId().isBlank()) throw new IllegalArgumentException("commandId不能为空");
        rejectSafetyFields(command.inputParams() == null ? Map.of() : command.inputParams());
        String commandType = command.commandType();
        if (!online.get() && !"TASK_CANCEL".equals(commandType)) {
            throw new IllegalStateException("仿真体已停止，不能接收业务命令");
        }
        if ("TASK_ACCEPT".equals(commandType)) {
            String key = command.commandId() + ":accept";
            if (commandStates.putIfAbsent(key, "PROCESSING") != null) {
                replay(key);
                return;
            }
            if (!busy.compareAndSet(false, true)) {
                commandStates.put(key, "REJECTED");
                reportTaskResponse(command.commandId(), false, "DEVICE_BUSY");
                return;
            }
            activeCommand.set(command.commandId());
            commandStates.put(key, "ACCEPTED");
            reportTaskResponse(command.commandId(), true, null);
            return;
        }
        if ("EXECUTE_CAPABILITY".equals(commandType)) {
            String key = command.commandId() + ":" + (command.attemptNo() == null ? 0 : command.attemptNo());
            if (commandStates.putIfAbsent(key, "RUNNING") != null) {
                replay(key);
                return;
            }
            activeCommand.set(command.commandId());
            busy.set(true);
            java.util.concurrent.CompletableFuture.runAsync(() -> execute(command, key));
            return;
        }
        if ("TASK_CANCEL".equals(commandType)) {
            commandStates.put(command.commandId() + ":cancel", "CANCELLED");
            cancelled.add(command.commandId());
            release(command.commandId());
            reportStatus();
            return;
        }
        throw new IllegalArgumentException("不支持commandType " + commandType);
    }

    private void execute(SimulatorProtocol.Command command, String key) {
        try {
            Thread.sleep(properties.getExecutionDelayMilliseconds());
            if (cancelled.contains(command.commandId())) return;
            String configured = properties.getScenarioResult();
            if ("NO_FEEDBACK".equals(configured)) { commandStates.put(key, "NO_FEEDBACK"); return; }
            if (isScenarioApplicable(configured, command.capabilityType())) {
                reportFeedback(command, "FAILED", "SIMULATED_" + configured, scenarioOutput(command.capabilityType(), configured));
                commandStates.put(key, "FAILED");
                return;
            }
            if ("TIMEOUT".equals(configured)) {
                reportFeedback(command, "TIMEOUT", "SIMULATED_TIMEOUT", timeoutOutput(command.capabilityType()));
                commandStates.put(key, "TIMED_OUT");
                return;
            }
            if ("FAILED".equals(configured)) {
                reportFeedback(command, "FAILED", "SIMULATED_DEVICE_ERROR", errorOutput(command.capabilityType()));
                commandStates.put(key, "FAILED");
                return;
            }
            Map<String, Object> params = command.inputParams() == null ? Map.of() : command.inputParams();
            Map<String, Object> output = executeCapability(command.capabilityType(), params);
            progressAlong(command.commandId(), driver.routeLocations(command.capabilityType(), params, location(), output));
            if (cancelled.contains(command.commandId())) return;
            reportFeedback(command, "SUCCESS", null, output);
            commandStates.put(key, "SUCCEEDED");
        } catch (InterruptedException ex) {
            Thread.currentThread().interrupt();
            reportFeedback(command, "FAILED", "SIMULATOR_INTERRUPTED", Map.of());
            commandStates.put(key, "FAILED");
        } catch (RuntimeException ex) {
            reportFeedback(command, "FAILED", "INVALID_CAPABILITY_INPUT", Map.of("message", ex.getMessage()));
            commandStates.put(key, "FAILED");
        } finally {
            if (!"NO_FEEDBACK".equals(commandStates.get(key))) release(command.commandId());
            reportStatus();
        }
    }
    private void release(String commandId) {
        String active=activeCommand.get();
        if (java.util.Objects.equals(active,commandId) && activeCommand.compareAndSet(active, null)) busy.set(false);
    }

    @Scheduled(fixedDelayString = "${simulator.heartbeat-interval-seconds:15}000")
    public void heartbeat() {
        if (online.get() && heartbeatEnabled.get() && agentCode != null) reportStatus();
    }

    public void setOnline(boolean value) {
        boolean changed = online.getAndSet(value) != value;
        if (changed && agentCode != null) reportStatus();
    }
    public void setHeartbeatEnabled(boolean value) { heartbeatEnabled.set(value); if (value) reportStatus(); }
    public void setExecutionDelay(int value) {
        if (value<0 || value>60000) throw new IllegalArgumentException("执行延迟范围0~60000毫秒");
        properties.setExecutionDelayMilliseconds(value);
    }
    public boolean isOnline() { return online.get(); }
    public void setScenarioResult(String scenarioResult) {
        if (scenarioResult == null || !Set.of("SUCCESS", "FAILED", "TIMEOUT", "NO_FEEDBACK", "NO_OBJECT", "LOST_TARGET").contains(scenarioResult)) {
            throw new IllegalArgumentException("scenario-result不受支持");
        }
        if ("NO_OBJECT".equals(scenarioResult) && !"BAGGAGE_SCANNER".equals(driver.deviceType())) {
            throw new IllegalArgumentException("NO_OBJECT仅适用于BAGGAGE_SCANNER");
        }
        if ("LOST_TARGET".equals(scenarioResult) && !"MOBILE_ROBOT".equals(driver.deviceType())) {
            throw new IllegalArgumentException("LOST_TARGET仅适用于MOBILE_ROBOT");
        }
        properties.setScenarioResult(scenarioResult);
        reportStatus();
    }
    public String agentCode() { return agentCode; }

    @SuppressWarnings("unchecked")
    public Map<String, Object> testCapability(Map<String, Object> body) {
        long started = System.nanoTime();
        String id = String.valueOf(body.get("commandId"));
        try {
            if (!online.get() || busy.get()) throw new IllegalStateException("仿真体离线或占用中");
            String type = String.valueOf(body.get("capabilityType"));
            Map<String, Object> params = body.get("inputParams") instanceof Map<?, ?> map
                    ? (Map<String, Object>)map : Map.of();
            rejectSafetyFields(params);
            if (!"SUCCESS".equals(properties.getScenarioResult())) throw new IllegalStateException("SIMULATED_" + properties.getScenarioResult());
            Map<String, Object> output = executeCapability(type, params);
            return Map.of("commandId", id, "result", "SUCCESS", "outputParams", output,
                    "durationMs", (System.nanoTime() - started) / 1_000_000);
        } catch (RuntimeException ex) {
            return Map.of("commandId", id, "result", "FAILED", "reasonCode", ex.getMessage(),
                    "durationMs", (System.nanoTime() - started) / 1_000_000);
        }
    }
    /**
     * CAP_SIM_STATUS是仿真体自身的能力（5.2.4A：仿真体含仿真状态生成），与所模拟设备类型无关，
     * 由运行时直接返回当前仿真状态快照，不交给设备类型驱动（DEF-S3-079）。
     */
    private Map<String, Object> executeCapability(String capabilityType, Map<String, Object> params) {
        if ("CAP_SIM_STATUS".equals(capabilityType)) {
            Map<String, Object> snapshot = new LinkedHashMap<>();
            snapshot.put("simulatedDeviceType", driver.deviceType());
            snapshot.put("onlineStatus", online.get() ? "ONLINE" : "OFFLINE");
            snapshot.put("workStatus", busy.get() ? "BUSY" : "IDLE");
            snapshot.put("scenarioResult", properties.getScenarioResult());
            snapshot.put("location", Map.of("x", location().x(), "y", location().y(), "zone", location().zone()));
            snapshot.put("generatedAt", OffsetDateTime.now().toString());
            return snapshot;
        }
        return driver.execute(capabilityType, params);
    }

    public String token() { return properties.getToken(); }
    public Set<String> capabilities() { return driver.capabilities(); }

    private void reportStatus() {
        sendReport(new SimulatorProtocol.Report("STATUS", OffsetDateTime.now().toString(),
                Map.of("onlineStatus", online.get() ? "ONLINE" : "OFFLINE", "workStatus", busy.get() ? "BUSY" : "IDLE",
                        "location", Map.of("x", location().x(), "y", location().y(), "zone", location().zone()),
                        "businessStatus", Map.of("simulatedDeviceType", driver.deviceType(), "scenarioResult", properties.getScenarioResult())), null, null));
    }

    private void reportTaskResponse(String commandId, boolean accepted, String reason) {
        Map<String, Object> response = new LinkedHashMap<>();
        response.put("commandId", commandId);
        response.put("accepted", accepted);
        response.put("rejectReason", reason);
        String key = commandId + ":accept";
        SimulatorProtocol.Report report = new SimulatorProtocol.Report("TASK_RESPONSE", OffsetDateTime.now().toString(), null, response, null);
        commandReports.put(key, report);
        sendReport(report);
    }

    private void reportFeedback(SimulatorProtocol.Command command, String result, String reason, Map<String, Object> output) {
        release(command.commandId());
        Map<String, Object> feedback = new LinkedHashMap<>();
        feedback.put("commandId", command.commandId());
        feedback.put("attemptNo", command.attemptNo() == null ? 0 : command.attemptNo());
        feedback.put("executionResult", result);
        feedback.put("reasonCode", reason);
        feedback.put("outputParams", output);
        String key = command.commandId() + ":" + (command.attemptNo() == null ? 0 : command.attemptNo());
        SimulatorProtocol.Report report = new SimulatorProtocol.Report("EXECUTION_FEEDBACK", OffsetDateTime.now().toString(), null, null, feedback);
        commandReports.put(key, report);
        sendReport(report);
    }

    private void replay(String key) {
        SimulatorProtocol.Report previous = commandReports.get(key);
        if (previous != null) sendReport(previous);
    }

    private void sendReport(SimulatorProtocol.Report report) {
        String url = reportUrl;
        if (url == null || url.isBlank()) return;
        HttpHeaders headers = new HttpHeaders();
        headers.setBearerAuth(properties.getToken());
        headers.setContentType(MediaType.APPLICATION_JSON);
        try { http.postForEntity(url, new org.springframework.http.HttpEntity<>(report, headers), Void.class); }
        catch (RestClientException ignored) { /* next heartbeat retries state; command feedback is visible via platform timeout */ }
    }

    private SimulatorProtocol.Location location() {
        return currentLocation.get();
    }

    private void progressAlong(String commandId, java.util.List<SimulatorProtocol.Location> route) {
        if (route == null || route.isEmpty()) return;
        long delayPerPoint = Math.max(1, properties.getExecutionDelayMilliseconds() / route.size());
        for (SimulatorProtocol.Location waypoint : route) {
            if (cancelled.contains(commandId)) return;
            try { Thread.sleep(delayPerPoint); }
            catch (InterruptedException ex) { Thread.currentThread().interrupt(); return; }
            currentLocation.set(waypoint);
            reportStatus();
        }
    }

    private Map<String, Object> scenarioOutput(String capabilityType, String scenario) {
        if ("CAP_BAGGAGE_MEASURE".equals(capabilityType) && "NO_OBJECT".equals(scenario)) {
            return Map.of("length", 0, "width", 0, "height", 0, "weight", 0, "isOversize", false, "measureStatus", "NO_OBJECT");
        }
        if ("CAP_ESCORT".equals(capabilityType) && "LOST_TARGET".equals(scenario)) {
            return Map.of("arrivalStatus", "LOST_TARGET", "actualDistance", 0, "actualDuration", 0);
        }
        return errorOutput(capabilityType);
    }

    private boolean isScenarioApplicable(String scenario, String capabilityType) {
        return ("NO_OBJECT".equals(scenario) && "CAP_BAGGAGE_MEASURE".equals(capabilityType))
                || ("LOST_TARGET".equals(scenario) && "CAP_ESCORT".equals(capabilityType));
    }

    private Map<String, Object> errorOutput(String capabilityType) {
        return switch (capabilityType == null ? "" : capabilityType) {
            case "CAP_INFO_DISPLAY" -> Map.of("displayStatus", "DEVICE_ERROR", "actualDuration", 0, "errorMessage", "仿真设备错误");
            case "CAP_FLIGHT_UPDATE" -> Map.of("publishStatus", "FAILED", "publishTime", OffsetDateTime.now().toString());
            case "CAP_NAVIGATION" -> Map.of("routeGenerated", false, "estimatedDistance", 0, "estimatedDuration", 0, "waypointCount", 0);
            case "CAP_BAGGAGE_MEASURE" -> Map.of("length", 0, "width", 0, "height", 0, "weight", 0,
                    "isOversize", false, "measureStatus", "TIMEOUT");
            case "CAP_OVERSIZE_ALERT" -> Map.of("alertId", "", "reportStatus", "FAILED", "reportTime", OffsetDateTime.now().toString());
            case "CAP_ESCORT" -> Map.of("arrivalStatus", "TIMEOUT", "actualDistance", 0, "actualDuration", 0);
            case "CAP_NOTIFICATION" -> Map.of("notificationStatus", "FAILED", "actualRepeatCount", 0);
            default -> Map.of();
        };
    }

    private Map<String, Object> timeoutOutput(String capabilityType) {
        return switch (capabilityType == null ? "" : capabilityType) {
            case "CAP_INFO_DISPLAY" -> Map.of("displayStatus", "TIMEOUT", "actualDuration", 0, "errorMessage", "展示超时");
            case "CAP_FLIGHT_UPDATE" -> Map.of("publishStatus", "FAILED", "publishTime", OffsetDateTime.now().toString());
            case "CAP_NAVIGATION" -> Map.of("routeGenerated", false, "estimatedDistance", 0, "estimatedDuration", 0, "waypointCount", 0);
            case "CAP_BAGGAGE_MEASURE" -> Map.of("length", 0, "width", 0, "height", 0, "weight", 0,
                    "isOversize", false, "measureStatus", "TIMEOUT");
            case "CAP_OVERSIZE_ALERT" -> Map.of("alertId", "", "reportStatus", "FAILED", "reportTime", OffsetDateTime.now().toString());
            case "CAP_ESCORT" -> Map.of("arrivalStatus", "TIMEOUT", "actualDistance", 0, "actualDuration", 0);
            case "CAP_NOTIFICATION" -> Map.of("notificationStatus", "FAILED", "actualRepeatCount", 0);
            default -> Map.of();
        };
    }

    private void rejectSafetyFields(Object value) {
        if (value instanceof Map<?, ?> map) for (var entry : map.entrySet()) {
            String key = String.valueOf(entry.getKey());
            if (FORBIDDEN.contains(key) || FORBIDDEN_NORMALIZED.contains(key.toLowerCase().replaceAll("[\\s_\\-]", "")))
                throw new IllegalArgumentException("禁止运动安全字段: " + key);
            rejectSafetyFields(entry.getValue());
        }
        if (value instanceof Iterable<?> items) items.forEach(this::rejectSafetyFields);
    }
}
