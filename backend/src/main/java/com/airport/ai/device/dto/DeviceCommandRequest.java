package com.airport.ai.device.dto;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import java.time.OffsetDateTime;
import java.util.Map;

public class DeviceCommandRequest {
    @NotBlank
    private String commandId;
    @NotBlank
    private String commandType;
    @Min(0) @Max(1)
    private Integer attemptNo = 0;
    private String taskId;
    private Integer stepSeq;
    private String capabilityType;
    private Map<String, Object> inputParams;
    private OffsetDateTime issuedAt;
    private OffsetDateTime deadline;

    public String getCommandId() { return commandId; }
    public void setCommandId(String commandId) { this.commandId = commandId; }
    public String getCommandType() { return commandType; }
    public void setCommandType(String commandType) { this.commandType = commandType; }
    public Integer getAttemptNo() { return attemptNo == null ? 0 : attemptNo; }
    public void setAttemptNo(Integer attemptNo) { this.attemptNo = attemptNo; }
    public String getTaskId() { return taskId; }
    public void setTaskId(String taskId) { this.taskId = taskId; }
    public Integer getStepSeq() { return stepSeq; }
    public void setStepSeq(Integer stepSeq) { this.stepSeq = stepSeq; }
    public String getCapabilityType() { return capabilityType; }
    public void setCapabilityType(String capabilityType) { this.capabilityType = capabilityType; }
    public Map<String, Object> getInputParams() { return inputParams; }
    public void setInputParams(Map<String, Object> inputParams) { this.inputParams = inputParams; }
    public OffsetDateTime getIssuedAt() { return issuedAt; }
    public void setIssuedAt(OffsetDateTime issuedAt) { this.issuedAt = issuedAt; }
    public OffsetDateTime getDeadline() { return deadline; }
    public void setDeadline(OffsetDateTime deadline) { this.deadline = deadline; }
}
