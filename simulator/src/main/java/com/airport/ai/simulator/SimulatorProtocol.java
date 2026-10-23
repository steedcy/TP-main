package com.airport.ai.simulator;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

public final class SimulatorProtocol {
    private SimulatorProtocol() {}

    public record Location(BigDecimal x, BigDecimal y, String zone) {}
    public record HealthResponse(String protocolVersion, String nonce, String deviceCode,
                                 String deviceTypeCode, String simulatedDeviceType,
                                 String onlineStatus, String workStatus, Location location,
                                 List<String> capabilities, String reportedAt) {}
    public record BindingRequest(String deviceCode, String agentCode, String reportUrl,
                                 Integer heartbeatIntervalSeconds, Integer heartbeatTimeoutSeconds) {}
    public record Command(String commandId, String commandType, Integer attemptNo, String taskId,
                          Integer stepSeq, String capabilityType, Map<String, Object> inputParams,
                          String issuedAt, String deadline) {}
    public record Report(String reportType, String reportedAt, Map<String, Object> status,
                         Map<String, Object> response, Map<String, Object> feedback) {}
}
