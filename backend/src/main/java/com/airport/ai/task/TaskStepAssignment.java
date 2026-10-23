package com.airport.ai.task;

import java.time.LocalDateTime;

/**
 * 对应数据库设计说明书V2.0 4.5.3节 task_step_assignments表，承载5.5.1~5.5.3步骤设备匹配、
 * 指令下发与执行反馈的落地状态。计划版本冻结后即为每个步骤插入一行（step_status=PENDING_ASSIGNMENT），
 * 5.5链路后续按plan_version_id驱动推进，不再依赖plan_steps原始JSON做状态判断。
 */
public class TaskStepAssignment {

    private Long id;
    private Long taskId;
    private Long planVersionId;
    private Integer stepSeq;
    private Long deviceAgentId;
    /** 全局唯一，重试沿用同一编号（对应5.5.2业务规则2） */
    private String commandId;
    /** PENDING_ASSIGNMENT / EXECUTING / COMPLETED / FAILED / FROZEN */
    private String stepStatus = "PENDING_ASSIGNMENT";
    /** 上限1（对应5.5.2业务规则2、5.5.3业务规则6："失败只自动重试一次"） */
    private Integer retryCount = 0;
    /** SUCCESS / FAILED / TIMEOUT */
    private String executionResult;
    private String reasonCode;
    private String outputParams;
    private LocalDateTime dispatchedAt;
    private LocalDateTime feedbackAt;
    /** 对应5.5.1候选轮询：已询问过并被拒绝的候选代理编码清单（JSON数组），下一次挑选候选时须排除 */
    private String rejectedAgentIds = "[]";
    private LocalDateTime createdAt = LocalDateTime.now();
    private LocalDateTime updatedAt = LocalDateTime.now();

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public Long getTaskId() { return taskId; }
    public void setTaskId(Long taskId) { this.taskId = taskId; }
    public Long getPlanVersionId() { return planVersionId; }
    public void setPlanVersionId(Long planVersionId) { this.planVersionId = planVersionId; }
    public Integer getStepSeq() { return stepSeq; }
    public void setStepSeq(Integer stepSeq) { this.stepSeq = stepSeq; }
    public Long getDeviceAgentId() { return deviceAgentId; }
    public void setDeviceAgentId(Long deviceAgentId) { this.deviceAgentId = deviceAgentId; }
    public String getCommandId() { return commandId; }
    public void setCommandId(String commandId) { this.commandId = commandId; }
    public String getStepStatus() { return stepStatus; }
    public void setStepStatus(String stepStatus) { this.stepStatus = stepStatus; }
    public Integer getRetryCount() { return retryCount; }
    public void setRetryCount(Integer retryCount) { this.retryCount = retryCount; }
    public String getExecutionResult() { return executionResult; }
    public void setExecutionResult(String executionResult) { this.executionResult = executionResult; }
    public String getReasonCode() { return reasonCode; }
    public void setReasonCode(String reasonCode) { this.reasonCode = reasonCode; }
    public String getOutputParams() { return outputParams; }
    public void setOutputParams(String outputParams) { this.outputParams = outputParams; }
    public LocalDateTime getDispatchedAt() { return dispatchedAt; }
    public void setDispatchedAt(LocalDateTime dispatchedAt) { this.dispatchedAt = dispatchedAt; }
    public LocalDateTime getFeedbackAt() { return feedbackAt; }
    public void setFeedbackAt(LocalDateTime feedbackAt) { this.feedbackAt = feedbackAt; }
    public String getRejectedAgentIds() { return rejectedAgentIds; }
    public void setRejectedAgentIds(String rejectedAgentIds) { this.rejectedAgentIds = rejectedAgentIds; }
    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }
    public LocalDateTime getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(LocalDateTime updatedAt) { this.updatedAt = updatedAt; }
}
