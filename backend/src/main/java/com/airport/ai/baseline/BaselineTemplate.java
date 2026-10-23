package com.airport.ai.baseline;

import java.time.LocalDateTime;

/**
 * 对应数据库设计说明书V2.0 4.4.1节 baseline_templates表。纯POJO，持久化映射见 mapper/BaselineTemplateMapper.xml。
 * inputParams/steps为JSON列，Java侧统一用String承载，序列化/反序列化在Service层处理。
 */
public class BaselineTemplate {

    private Long id;
    private String templateName;
    private String taskFamily;
    private Boolean isPreset = false;
    private String inputParams;
    private String steps;
    private String templateVersion = "V1.0";
    /** DRAFT / DRY_RUN_PASSED / ENABLED / DISABLED */
    private String templateStatus = "DRAFT";
    private LocalDateTime createdAt = LocalDateTime.now();
    private LocalDateTime updatedAt = LocalDateTime.now();
    private String updatedBy;

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public String getTemplateName() { return templateName; }
    public void setTemplateName(String templateName) { this.templateName = templateName; }
    public String getTaskFamily() { return taskFamily; }
    public void setTaskFamily(String taskFamily) { this.taskFamily = taskFamily; }
    public Boolean getIsPreset() { return isPreset; }
    public void setIsPreset(Boolean isPreset) { this.isPreset = isPreset; }
    public String getInputParams() { return inputParams; }
    public void setInputParams(String inputParams) { this.inputParams = inputParams; }
    public String getSteps() { return steps; }
    public void setSteps(String steps) { this.steps = steps; }
    public String getTemplateVersion() { return templateVersion; }
    public void setTemplateVersion(String templateVersion) { this.templateVersion = templateVersion; }
    public String getTemplateStatus() { return templateStatus; }
    public void setTemplateStatus(String templateStatus) { this.templateStatus = templateStatus; }
    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }
    public LocalDateTime getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(LocalDateTime updatedAt) { this.updatedAt = updatedAt; }
    public String getUpdatedBy() { return updatedBy; }
    public void setUpdatedBy(String updatedBy) { this.updatedBy = updatedBy; }
}
