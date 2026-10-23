package com.airport.ai.device;

import java.time.LocalDateTime;

/**
 * 对应5.2.4设备能力画像管理（实例层），数据库设计说明书 device_capabilities表。
 * 能力编码在同一设备内唯一（对应5.2.4界面元素约束）。纯POJO，持久化映射见 mapper/DeviceCapabilityMapper.xml。
 * inputParams/outputParams对应数据库json列，Java侧用String承载序列化后的JSON文本，Service层负责Jackson序列化/反序列化。
 */
public class DeviceCapability {

    private Long id;
    private Long deviceId;
    /** 创建时若基于5.2.4A标准能力模板预填，记录来源模板id，可为空（自定义能力） */
    private Long templateId;
    private String capabilityCode;
    private String capabilityName;
    private String capabilityType;
    private String inputParams;
    private String outputParams;
    private String applicableConditions;
    /** UNTESTED / TESTED_PASSED / TESTED_FAILED / ENABLED / DISABLED */
    private String capabilityStatus = "UNTESTED";
    private String testResult;
    private LocalDateTime lastTestAt;
    private String capabilityDescription;
    private LocalDateTime createdAt = LocalDateTime.now();
    private LocalDateTime updatedAt = LocalDateTime.now();

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public Long getDeviceId() { return deviceId; }
    public void setDeviceId(Long deviceId) { this.deviceId = deviceId; }
    public Long getTemplateId() { return templateId; }
    public void setTemplateId(Long templateId) { this.templateId = templateId; }
    public String getCapabilityCode() { return capabilityCode; }
    public void setCapabilityCode(String capabilityCode) { this.capabilityCode = capabilityCode; }
    public String getCapabilityName() { return capabilityName; }
    public void setCapabilityName(String capabilityName) { this.capabilityName = capabilityName; }
    public String getCapabilityType() { return capabilityType; }
    public void setCapabilityType(String capabilityType) { this.capabilityType = capabilityType; }
    public String getInputParams() { return inputParams; }
    public void setInputParams(String inputParams) { this.inputParams = inputParams; }
    public String getOutputParams() { return outputParams; }
    public void setOutputParams(String outputParams) { this.outputParams = outputParams; }
    public String getApplicableConditions() { return applicableConditions; }
    public void setApplicableConditions(String applicableConditions) { this.applicableConditions = applicableConditions; }
    public String getCapabilityStatus() { return capabilityStatus; }
    public void setCapabilityStatus(String capabilityStatus) { this.capabilityStatus = capabilityStatus; }
    public String getTestResult() { return testResult; }
    public void setTestResult(String testResult) { this.testResult = testResult; }
    public LocalDateTime getLastTestAt() { return lastTestAt; }
    public void setLastTestAt(LocalDateTime lastTestAt) { this.lastTestAt = lastTestAt; }
    public String getCapabilityDescription() { return capabilityDescription; }
    public void setCapabilityDescription(String capabilityDescription) { this.capabilityDescription = capabilityDescription; }
    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }
    public LocalDateTime getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(LocalDateTime updatedAt) { this.updatedAt = updatedAt; }
}
