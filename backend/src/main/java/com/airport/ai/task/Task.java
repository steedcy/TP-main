package com.airport.ai.task;

import java.time.LocalDateTime;

/**
 * 对应数据库设计说明书V2.0 4.5.1节 tasks表。纯POJO，持久化映射见 mapper/TaskMapper.xml。
 * sceneParams/goalParsingResult为JSON列，Java侧统一用String承载。
 */
public class Task {

    private Long id;
    private String taskCode;
    private String taskGoal;
    private String taskFamily;
    private String sceneParams;
    private String goalParsingResult;
    private TaskStatus status = TaskStatus.PLANNING;
    private Long currentPlanVersionId;
    private Boolean replanUsed = false;
    private String replanningReason;
    private String manualTerminateReason;
    private String failureReason;
    /** 对应5.4.1业务规则4：目标理解返回的待补充问题清单，JSON数组，信息补充完成前不得进入计划生成 */
    private String missingInfoQuestions;
    /** 对应5.4.6业务规则6：降级任务须记录降级原因（高风险原因码/规划失败/模型不可用等触发原因） */
    private String downgradeReason;
    /** 对应5.3.2业务规则3/5：试运行实例与正式任务共用表结构，但需标记且不计入运行总览统计 */
    private Boolean isDryRun = false;
    private LocalDateTime createdAt = LocalDateTime.now();
    private LocalDateTime updatedAt = LocalDateTime.now();
    private String createdBy;

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public String getTaskCode() { return taskCode; }
    public void setTaskCode(String taskCode) { this.taskCode = taskCode; }
    public String getTaskGoal() { return taskGoal; }
    public void setTaskGoal(String taskGoal) { this.taskGoal = taskGoal; }
    public String getTaskFamily() { return taskFamily; }
    public void setTaskFamily(String taskFamily) { this.taskFamily = taskFamily; }
    public String getSceneParams() { return sceneParams; }
    public void setSceneParams(String sceneParams) { this.sceneParams = sceneParams; }
    public String getGoalParsingResult() { return goalParsingResult; }
    public void setGoalParsingResult(String goalParsingResult) { this.goalParsingResult = goalParsingResult; }
    public TaskStatus getStatus() { return status; }
    public void setStatus(TaskStatus status) { this.status = status; }
    public Long getCurrentPlanVersionId() { return currentPlanVersionId; }
    public void setCurrentPlanVersionId(Long currentPlanVersionId) { this.currentPlanVersionId = currentPlanVersionId; }
    public Boolean getReplanUsed() { return replanUsed; }
    public void setReplanUsed(Boolean replanUsed) { this.replanUsed = replanUsed; }
    public String getReplanningReason() { return replanningReason; }
    public void setReplanningReason(String replanningReason) { this.replanningReason = replanningReason; }
    public String getManualTerminateReason() { return manualTerminateReason; }
    public void setManualTerminateReason(String manualTerminateReason) { this.manualTerminateReason = manualTerminateReason; }
    public String getFailureReason() { return failureReason; }
    public void setFailureReason(String failureReason) { this.failureReason = failureReason; }
    public String getMissingInfoQuestions() { return missingInfoQuestions; }
    public void setMissingInfoQuestions(String missingInfoQuestions) { this.missingInfoQuestions = missingInfoQuestions; }
    public String getDowngradeReason() { return downgradeReason; }
    public void setDowngradeReason(String downgradeReason) { this.downgradeReason = downgradeReason; }
    public Boolean getIsDryRun() { return isDryRun; }
    public void setIsDryRun(Boolean isDryRun) { this.isDryRun = isDryRun; }
    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }
    public LocalDateTime getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(LocalDateTime updatedAt) { this.updatedAt = updatedAt; }
    public String getCreatedBy() { return createdBy; }
    public void setCreatedBy(String createdBy) { this.createdBy = createdBy; }
}
