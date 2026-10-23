package com.airport.ai.device;

import java.time.LocalDateTime;

/**
 * 对应数据库设计说明书V2.0 4.3.2节 device_agents表。纯POJO，持久化映射见 mapper/DeviceAgentMapper.xml。
 */
public class DeviceAgent {

    private Long id;
    private String agentCode;
    private Long deviceId;
    /** ENABLED / DISABLED / ARCHIVED */
    private String agentStatus = "ENABLED";
    /** ONLINE / OFFLINE */
    private String onlineStatus = "OFFLINE";
    /** IDLE / BUSY */
    private String workStatus = "IDLE";
    /** Latest device-specific business snapshot serialized as JSON. */
    private String businessStatus;
    private Long currentTaskId;
    private Integer currentStepSeq;
    private LocalDateTime lastReportedAt;
    private LocalDateTime createdAt = LocalDateTime.now();
    private LocalDateTime updatedAt = LocalDateTime.now();

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public String getAgentCode() { return agentCode; }
    public void setAgentCode(String agentCode) { this.agentCode = agentCode; }
    public Long getDeviceId() { return deviceId; }
    public void setDeviceId(Long deviceId) { this.deviceId = deviceId; }
    public String getAgentStatus() { return agentStatus; }
    public void setAgentStatus(String agentStatus) { this.agentStatus = agentStatus; }
    public String getOnlineStatus() { return onlineStatus; }
    public void setOnlineStatus(String onlineStatus) { this.onlineStatus = onlineStatus; }
    public String getWorkStatus() { return workStatus; }
    public void setWorkStatus(String workStatus) { this.workStatus = workStatus; }
    public String getBusinessStatus() { return businessStatus; }
    public void setBusinessStatus(String businessStatus) { this.businessStatus = businessStatus; }
    public Long getCurrentTaskId() { return currentTaskId; }
    public void setCurrentTaskId(Long currentTaskId) { this.currentTaskId = currentTaskId; }
    public Integer getCurrentStepSeq() { return currentStepSeq; }
    public void setCurrentStepSeq(Integer currentStepSeq) { this.currentStepSeq = currentStepSeq; }
    public LocalDateTime getLastReportedAt() { return lastReportedAt; }
    public void setLastReportedAt(LocalDateTime lastReportedAt) { this.lastReportedAt = lastReportedAt; }
    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }
    public LocalDateTime getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(LocalDateTime updatedAt) { this.updatedAt = updatedAt; }
}
