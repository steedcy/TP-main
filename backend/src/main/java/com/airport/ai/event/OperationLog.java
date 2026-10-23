package com.airport.ai.event;

import java.time.LocalDateTime;

/**
 * 对应数据库设计说明书V2.0 4.6.2节 operation_logs表
 */
public class OperationLog {

    private Long id;
    private Long userId;
    private String username;
    private String role;
    private String operationType;
    private String operationTarget;
    private String operationResult;
    private String sourceIp;
    private String detail;
    private LocalDateTime createdAt = LocalDateTime.now();

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public Long getUserId() { return userId; }
    public void setUserId(Long userId) { this.userId = userId; }
    public String getUsername() { return username; }
    public void setUsername(String username) { this.username = username; }
    public String getRole() { return role; }
    public void setRole(String role) { this.role = role; }
    public String getOperationType() { return operationType; }
    public void setOperationType(String operationType) { this.operationType = operationType; }
    public String getOperationTarget() { return operationTarget; }
    public void setOperationTarget(String operationTarget) { this.operationTarget = operationTarget; }
    public String getOperationResult() { return operationResult; }
    public void setOperationResult(String operationResult) { this.operationResult = operationResult; }
    public String getSourceIp() { return sourceIp; }
    public void setSourceIp(String sourceIp) { this.sourceIp = sourceIp; }
    public String getDetail() { return detail; }
    public void setDetail(String detail) { this.detail = detail; }
    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }
}
