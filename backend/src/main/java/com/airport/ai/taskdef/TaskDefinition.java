package com.airport.ai.taskdef;

import java.time.LocalDateTime;

/**
 * 对应5.6.1旅客服务任务定义管理、数据库设计说明书V2.0扩展4.x节 task_definitions表。
 * 纯POJO，持久化映射见 mapper/TaskDefinitionMapper.xml。sceneParams/availableCapabilityTypes
 * 为JSON列，Java侧统一用String承载，序列化/反序列化在Service层处理（与BaselineTemplate同一模式）。
 */
public class TaskDefinition {

    private Long id;
    private String definitionCode;
    private String taskName;
    private String goalTemplate;
    private String sceneParams;
    private String availableCapabilityTypes;
    private String constraintDescription;
    private String completionCondition;
    private Boolean isPreset = false;
    /** ENABLED / DISABLED */
    private String definitionStatus = "ENABLED";
    private LocalDateTime createdAt = LocalDateTime.now();
    private LocalDateTime updatedAt = LocalDateTime.now();
    private String updatedBy;

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public String getDefinitionCode() { return definitionCode; }
    public void setDefinitionCode(String definitionCode) { this.definitionCode = definitionCode; }
    public String getTaskName() { return taskName; }
    public void setTaskName(String taskName) { this.taskName = taskName; }
    public String getGoalTemplate() { return goalTemplate; }
    public void setGoalTemplate(String goalTemplate) { this.goalTemplate = goalTemplate; }
    public String getSceneParams() { return sceneParams; }
    public void setSceneParams(String sceneParams) { this.sceneParams = sceneParams; }
    public String getAvailableCapabilityTypes() { return availableCapabilityTypes; }
    public void setAvailableCapabilityTypes(String availableCapabilityTypes) { this.availableCapabilityTypes = availableCapabilityTypes; }
    public String getConstraintDescription() { return constraintDescription; }
    public void setConstraintDescription(String constraintDescription) { this.constraintDescription = constraintDescription; }
    public String getCompletionCondition() { return completionCondition; }
    public void setCompletionCondition(String completionCondition) { this.completionCondition = completionCondition; }
    public Boolean getIsPreset() { return isPreset; }
    public void setIsPreset(Boolean isPreset) { this.isPreset = isPreset; }
    public String getDefinitionStatus() { return definitionStatus; }
    public void setDefinitionStatus(String definitionStatus) { this.definitionStatus = definitionStatus; }
    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }
    public LocalDateTime getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(LocalDateTime updatedAt) { this.updatedAt = updatedAt; }
    public String getUpdatedBy() { return updatedBy; }
    public void setUpdatedBy(String updatedBy) { this.updatedBy = updatedBy; }
}
