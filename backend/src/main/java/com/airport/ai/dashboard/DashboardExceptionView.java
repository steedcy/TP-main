package com.airport.ai.dashboard;

import java.time.LocalDateTime;

public class DashboardExceptionView {
    private Long id;
    private Long taskId;
    private String taskCode;
    private String exceptionType;
    private LocalDateTime occurredAt;
    private String exceptionStatus;
    private String reasonCode;
    private String impactConclusion;

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public Long getTaskId() { return taskId; }
    public void setTaskId(Long taskId) { this.taskId = taskId; }
    public String getTaskCode() { return taskCode; }
    public void setTaskCode(String taskCode) { this.taskCode = taskCode; }
    public String getExceptionType() { return exceptionType; }
    public void setExceptionType(String exceptionType) { this.exceptionType = exceptionType; }
    public LocalDateTime getOccurredAt() { return occurredAt; }
    public void setOccurredAt(LocalDateTime occurredAt) { this.occurredAt = occurredAt; }
    public String getExceptionStatus() { return exceptionStatus; }
    public void setExceptionStatus(String exceptionStatus) { this.exceptionStatus = exceptionStatus; }
    public String getReasonCode() { return reasonCode; }
    public void setReasonCode(String reasonCode) { this.reasonCode = reasonCode; }
    public String getImpactConclusion() { return impactConclusion; }
    public void setImpactConclusion(String impactConclusion) { this.impactConclusion = impactConclusion; }
}
