package com.airport.ai.device.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import java.util.Map;

public class DeviceAgentMessageRequest {
    @NotBlank
    @jakarta.validation.constraints.Size(max = 64)
    private String commandId;
    @NotBlank
    @Pattern(regexp = "CAPABILITY_QUERY|STATUS_QUERY|TASK_ACCEPT|TASK_REJECT|EXECUTION_FEEDBACK|TASK_CANCEL",
            message = "messageType须为六类统一消息之一")
    private String messageType;
    @NotBlank
    private String agentId;
    private Map<String, Object> payload;
    public String getCommandId() { return commandId; }
    public void setCommandId(String commandId) { this.commandId = commandId; }
    public String getMessageType() { return messageType; }
    public void setMessageType(String messageType) { this.messageType = messageType; }
    public String getAgentId() { return agentId; }
    public void setAgentId(String agentId) { this.agentId = agentId; }
    public Map<String, Object> getPayload() { return payload; }
    public void setPayload(Map<String, Object> payload) { this.payload = payload; }
}
