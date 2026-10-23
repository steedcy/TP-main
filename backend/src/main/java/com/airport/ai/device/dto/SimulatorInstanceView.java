package com.airport.ai.device.dto;

import com.airport.ai.device.Device;
import com.airport.ai.device.DeviceAgent;

import java.math.BigDecimal;
import java.time.LocalDateTime;

public record SimulatorInstanceView(String deviceCode, String deviceName, String simulatedDeviceType,
                                    String connectionTestStatus, String agentCode, String agentStatus,
                                    String onlineStatus, String workStatus, Long currentTaskId,
                                    Integer currentStepSeq, LocalDateTime lastReportedAt,
                                    BigDecimal positionX, BigDecimal positionY, String areaCode,
                                    String scenarioResult) {
    public static SimulatorInstanceView from(Device device, DeviceAgent agent, String scenarioResult) {
        return new SimulatorInstanceView(device.getDeviceCode(), device.getDeviceName(), device.getSimulatedDeviceType(),
                device.getConnectionTestStatus(), agent == null ? null : agent.getAgentCode(),
                agent == null ? null : agent.getAgentStatus(), agent == null ? "OFFLINE" : agent.getOnlineStatus(),
                agent == null ? "IDLE" : agent.getWorkStatus(), agent == null ? null : agent.getCurrentTaskId(),
                agent == null ? null : agent.getCurrentStepSeq(), agent == null ? null : agent.getLastReportedAt(),
                device.getPositionX(), device.getPositionY(), device.getAreaCode(), scenarioResult);
    }
}
