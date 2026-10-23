package com.airport.ai.devicetype;

import java.time.LocalDateTime;

/**
 * 对应数据库设计说明书/5.2.4A数据模型 capability_template表：标准能力模板。
 * 模板编码在所属设备类型下唯一（对应界面元素约束），模板版本保存后自动分配（业务规则12）。
 */
public class CapabilityTemplate {

    private Long id;

    private String deviceTypeCode;

    private String templateCode;

    private String templateName;

    private String capabilityType;

    private String inputParams;

    private String outputParams;

    private String templateVersion = "V1.0";

    /** ACTIVE / INACTIVE */
    private String templateStatus = "ACTIVE";

    private String templateDescription;

    private Integer usageCount = 0;

    private LocalDateTime createdAt = LocalDateTime.now();

    private LocalDateTime updatedAt = LocalDateTime.now();

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public String getDeviceTypeCode() { return deviceTypeCode; }
    public void setDeviceTypeCode(String deviceTypeCode) { this.deviceTypeCode = deviceTypeCode; }
    public String getTemplateCode() { return templateCode; }
    public void setTemplateCode(String templateCode) { this.templateCode = templateCode; }
    public String getTemplateName() { return templateName; }
    public void setTemplateName(String templateName) { this.templateName = templateName; }
    public String getCapabilityType() { return capabilityType; }
    public void setCapabilityType(String capabilityType) { this.capabilityType = capabilityType; }
    public String getInputParams() { return inputParams; }
    public void setInputParams(String inputParams) { this.inputParams = inputParams; }
    public String getOutputParams() { return outputParams; }
    public void setOutputParams(String outputParams) { this.outputParams = outputParams; }
    public String getTemplateVersion() { return templateVersion; }
    public void setTemplateVersion(String templateVersion) { this.templateVersion = templateVersion; }
    public String getTemplateStatus() { return templateStatus; }
    public void setTemplateStatus(String templateStatus) { this.templateStatus = templateStatus; }
    public String getTemplateDescription() { return templateDescription; }
    public void setTemplateDescription(String templateDescription) { this.templateDescription = templateDescription; }
    public Integer getUsageCount() { return usageCount; }
    public void setUsageCount(Integer usageCount) { this.usageCount = usageCount; }
    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }
    public LocalDateTime getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(LocalDateTime updatedAt) { this.updatedAt = updatedAt; }
}
