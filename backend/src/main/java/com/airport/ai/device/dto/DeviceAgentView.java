package com.airport.ai.device.dto;

import com.airport.ai.device.Device;
import com.airport.ai.device.DeviceAgent;
import java.time.LocalDateTime;

/**
 * 对应5.2.2界面元素与附录B 6.3.3节响应结构
 */
public class DeviceAgentView {

    private String agentId;
    private String deviceCode;
    private String deviceName;
    private String agentStatus;
    private String onlineStatus;
    private String workStatus;
    private Long currentTaskId;
    private Integer currentStepSeq;
    private LocalDateTime lastReportedAt;

    public static DeviceAgentView from(DeviceAgent agent, Device device) {
        DeviceAgentView v = new DeviceAgentView();
        v.agentId = agent.getAgentCode();
        v.deviceCode = device.getDeviceCode();
        v.deviceName = device.getDeviceName();
        v.agentStatus = agent.getAgentStatus();
        v.onlineStatus = agent.getOnlineStatus();
        v.workStatus = agent.getWorkStatus();
        v.currentTaskId = agent.getCurrentTaskId();
        v.currentStepSeq = agent.getCurrentStepSeq();
        v.lastReportedAt = agent.getLastReportedAt();
        return v;
    }

    public String getAgentId() { return agentId; }
    public String getDeviceCode() { return deviceCode; }
    public String getDeviceName() { return deviceName; }
    public String getAgentStatus() { return agentStatus; }
    public String getOnlineStatus() { return onlineStatus; }
    public String getWorkStatus() { return workStatus; }
    public Long getCurrentTaskId() { return currentTaskId; }
    public Integer getCurrentStepSeq() { return currentStepSeq; }
    public LocalDateTime getLastReportedAt() { return lastReportedAt; }
}
