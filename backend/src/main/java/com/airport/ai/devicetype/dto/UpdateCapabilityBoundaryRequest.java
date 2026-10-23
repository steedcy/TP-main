package com.airport.ai.devicetype.dto;

import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.Size;

import java.util.List;

/**
 * 对应附录B 6.4.1节请求体，5.2.4A业务规则3：每类设备类型至少支持1个能力类型
 */
public class UpdateCapabilityBoundaryRequest {

    @NotEmpty(message = "请至少选择1个支持的能力类型")
    private List<String> supportedCapabilityTypes;

    @Size(max = 500, message = "类型描述最长500位")
    private String typeDescription;

    @Size(max = 1000, message = "约束规则最长1000位")
    private String constraintRules;

    @Size(max = 1000, message = "典型应用场景最长1000位")
    private String typicalScenarios;

    public List<String> getSupportedCapabilityTypes() { return supportedCapabilityTypes; }
    public void setSupportedCapabilityTypes(List<String> supportedCapabilityTypes) { this.supportedCapabilityTypes = supportedCapabilityTypes; }
    public String getTypeDescription() { return typeDescription; }
    public void setTypeDescription(String typeDescription) { this.typeDescription = typeDescription; }
    public String getConstraintRules() { return constraintRules; }
    public void setConstraintRules(String constraintRules) { this.constraintRules = constraintRules; }
    public String getTypicalScenarios() { return typicalScenarios; }
    public void setTypicalScenarios(String typicalScenarios) { this.typicalScenarios = typicalScenarios; }
}
