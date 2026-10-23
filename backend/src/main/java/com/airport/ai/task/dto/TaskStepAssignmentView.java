package com.airport.ai.task.dto;

import com.airport.ai.device.DeviceAgent;
import com.airport.ai.task.TaskStepAssignment;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

/**
 * 对应5.5.1界面元素：步骤序号、候选设备清单、分配设备、设备响应、步骤状态；
 * 5.5.2界面元素：指令编号、下发/反馈时间、执行结果、重试次数
 */
public class TaskStepAssignmentView {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private Long id;
    private Integer stepSeq;
    private String deviceAgentCode;
    private String commandId;
    private String stepStatus;
    private Integer retryCount;
    private String executionResult;
    private String reasonCode;
    private Map<String, Object> outputParams;
    private LocalDateTime dispatchedAt;
    private LocalDateTime feedbackAt;
    private List<String> rejectedAgentIds;

    public static TaskStepAssignmentView from(TaskStepAssignment a, DeviceAgent agent) {
        TaskStepAssignmentView v = new TaskStepAssignmentView();
        v.id = a.getId();
        v.stepSeq = a.getStepSeq();
        v.deviceAgentCode = agent == null ? null : agent.getAgentCode();
        v.commandId = a.getCommandId();
        v.stepStatus = a.getStepStatus();
        v.retryCount = a.getRetryCount();
        v.executionResult = a.getExecutionResult();
        v.reasonCode = a.getReasonCode();
        v.outputParams = parseMap(a.getOutputParams());
        v.dispatchedAt = a.getDispatchedAt();
        v.feedbackAt = a.getFeedbackAt();
        v.rejectedAgentIds = parseList(a.getRejectedAgentIds());
        return v;
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> parseMap(String json) {
        if (json == null || json.isBlank()) return null;
        try { return MAPPER.readValue(json, Map.class); } catch (Exception e) { return null; }
    }

    @SuppressWarnings("unchecked")
    private static List<String> parseList(String json) {
        if (json == null || json.isBlank()) return List.of();
        try { return MAPPER.readValue(json, List.class); } catch (Exception e) { return List.of(); }
    }

    public Long getId() { return id; }
    public Integer getStepSeq() { return stepSeq; }
    public String getDeviceAgentCode() { return deviceAgentCode; }
    public String getCommandId() { return commandId; }
    public String getStepStatus() { return stepStatus; }
    public Integer getRetryCount() { return retryCount; }
    public String getExecutionResult() { return executionResult; }
    public String getReasonCode() { return reasonCode; }
    public Map<String, Object> getOutputParams() { return outputParams; }
    public LocalDateTime getDispatchedAt() { return dispatchedAt; }
    public LocalDateTime getFeedbackAt() { return feedbackAt; }
    public List<String> getRejectedAgentIds() { return rejectedAgentIds; }
}
