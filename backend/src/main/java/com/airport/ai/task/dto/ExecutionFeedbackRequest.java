package com.airport.ai.task.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;

import java.util.Map;

/**
 * 对应附录B 5.2节平台统一设备接口执行反馈体：commandId、executionResult、reasonCode、outputParams。
 */
public class ExecutionFeedbackRequest {

    @NotBlank(message = "commandId不可为空")
    private String commandId;

    @Min(0) @Max(1)
    private Integer attemptNo = 0;

    // 取值不在SUCCESS/FAILED/TIMEOUT内时不在此拒绝，由DeviceAgentReportService归一为FAILED并记录原因码（SRS_F007.R06）
    @NotBlank(message = "executionResult不可为空")
    private String executionResult;

    private String reasonCode;
    private Map<String, Object> outputParams;

    public String getCommandId() { return commandId; }
    public void setCommandId(String commandId) { this.commandId = commandId; }
    public Integer getAttemptNo() { return attemptNo == null ? 0 : attemptNo; }
    public void setAttemptNo(Integer attemptNo) { this.attemptNo = attemptNo; }
    public String getExecutionResult() { return executionResult; }
    public void setExecutionResult(String executionResult) { this.executionResult = executionResult; }
    public String getReasonCode() { return reasonCode; }
    public void setReasonCode(String reasonCode) { this.reasonCode = reasonCode; }
    public Map<String, Object> getOutputParams() { return outputParams; }
    public void setOutputParams(Map<String, Object> outputParams) { this.outputParams = outputParams; }
}
