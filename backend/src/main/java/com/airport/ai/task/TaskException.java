package com.airport.ai.task;

import java.time.LocalDateTime;

/**
 * 对应5.5.3异常识别与恢复、5.5.5"未处置异常在运行总览计数/已处置异常归档至历史列表"。
 * task_events是仅追加的事件日志，无法承载"待处置->处置中->已处置/已忽略"的可变状态，
 * 本表独立承载异常的处置状态流转，具体过程细节仍通过task_events记录。
 */
public class TaskException {

    private Long id;
    private Long taskId;
    private Integer stepSeq;
    /** AGENT_OFFLINE / CAPABILITY_GAP / EXECUTION_TIMEOUT / STEP_FAILED / REPLAN_FAILED */
    private String exceptionType;
    private LocalDateTime occurredAt = LocalDateTime.now();
    private String recoveryAction;
    /** SUCCESS / FAILED，恢复动作尚未执行时为null */
    private String recoveryResult;
    private String impactConclusion;
    private String reasonCode;
    /** PENDING / PROCESSING / RESOLVED / IGNORED */
    private String exceptionStatus = "PENDING";
    private LocalDateTime resolvedAt;
    private String resolvedBy;

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public Long getTaskId() { return taskId; }
    public void setTaskId(Long taskId) { this.taskId = taskId; }
    public Integer getStepSeq() { return stepSeq; }
    public void setStepSeq(Integer stepSeq) { this.stepSeq = stepSeq; }
    public String getExceptionType() { return exceptionType; }
    public void setExceptionType(String exceptionType) { this.exceptionType = exceptionType; }
    public LocalDateTime getOccurredAt() { return occurredAt; }
    public void setOccurredAt(LocalDateTime occurredAt) { this.occurredAt = occurredAt; }
    public String getRecoveryAction() { return recoveryAction; }
    public void setRecoveryAction(String recoveryAction) { this.recoveryAction = recoveryAction; }
    public String getRecoveryResult() { return recoveryResult; }
    public void setRecoveryResult(String recoveryResult) { this.recoveryResult = recoveryResult; }
    public String getImpactConclusion() { return impactConclusion; }
    public void setImpactConclusion(String impactConclusion) { this.impactConclusion = impactConclusion; }
    public String getReasonCode() { return reasonCode; }
    public void setReasonCode(String reasonCode) { this.reasonCode = reasonCode; }
    public String getExceptionStatus() { return exceptionStatus; }
    public void setExceptionStatus(String exceptionStatus) { this.exceptionStatus = exceptionStatus; }
    public LocalDateTime getResolvedAt() { return resolvedAt; }
    public void setResolvedAt(LocalDateTime resolvedAt) { this.resolvedAt = resolvedAt; }
    public String getResolvedBy() { return resolvedBy; }
    public void setResolvedBy(String resolvedBy) { this.resolvedBy = resolvedBy; }
}
