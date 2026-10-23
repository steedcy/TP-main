package com.airport.ai.devicetype;

import java.time.LocalDateTime;

/**
 * 对应数据库设计说明书/5.2.4A数据模型 device_type_capability表：设备类型能力边界（类型层）。
 * 五类设备类型系统预置，不可新增或删除（对应业务规则1）。
 */
public class DeviceTypeCapability {

    private Long id;

    private String deviceTypeCode;

    private String deviceTypeName;

    /** JSON字符串数组，如["CAP_NAVIGATION","CAP_ESCORT"] */
    private String supportedCapabilityTypes;

    private String typeDescription;

    private String constraintRules;

    private String typicalScenarios;

    private LocalDateTime createdAt = LocalDateTime.now();

    private LocalDateTime updatedAt = LocalDateTime.now();

    private String updatedBy;

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public String getDeviceTypeCode() { return deviceTypeCode; }
    public void setDeviceTypeCode(String deviceTypeCode) { this.deviceTypeCode = deviceTypeCode; }
    public String getDeviceTypeName() { return deviceTypeName; }
    public void setDeviceTypeName(String deviceTypeName) { this.deviceTypeName = deviceTypeName; }
    public String getSupportedCapabilityTypes() { return supportedCapabilityTypes; }
    public void setSupportedCapabilityTypes(String supportedCapabilityTypes) { this.supportedCapabilityTypes = supportedCapabilityTypes; }
    public String getTypeDescription() { return typeDescription; }
    public void setTypeDescription(String typeDescription) { this.typeDescription = typeDescription; }
    public String getConstraintRules() { return constraintRules; }
    public void setConstraintRules(String constraintRules) { this.constraintRules = constraintRules; }
    public String getTypicalScenarios() { return typicalScenarios; }
    public void setTypicalScenarios(String typicalScenarios) { this.typicalScenarios = typicalScenarios; }
    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }
    public LocalDateTime getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(LocalDateTime updatedAt) { this.updatedAt = updatedAt; }
    public String getUpdatedBy() { return updatedBy; }
    public void setUpdatedBy(String updatedBy) { this.updatedBy = updatedBy; }
}
