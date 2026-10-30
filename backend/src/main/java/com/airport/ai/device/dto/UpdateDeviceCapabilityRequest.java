package com.airport.ai.device.dto;

import com.airport.ai.devicetype.dto.ParamDefinition;
import jakarta.validation.Valid;
import jakarta.validation.constraints.*;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;

/**
 * 编辑能力：不允许修改capabilityCode（同设备内唯一标识）和capabilityType
 * （能力类型变更等同于换了一个能力，应删除重建而非编辑）。
 * 已启用能力被修改输入输出参数时，可用状态重置为未测试（对应5.2.4业务规则5）。
 */
@JsonIgnoreProperties(ignoreUnknown = false)
public class UpdateDeviceCapabilityRequest {

    @NotBlank(message = "请输入能力名称")
    @Size(min = 1, max = 64, message = "能力名称长度需为1~64位")
    private String capabilityName;

    @NotEmpty(message = "请定义至少1个输入参数")
    @Valid
    private List<ParamDefinition> inputParams;

    @NotEmpty(message = "请定义至少1个输出参数")
    @Valid
    private List<ParamDefinition> outputParams;

    private String applicableCondition;

    @Size(max = 500, message = "能力说明最长500位")
    private String capabilityDescription;

    public String getCapabilityName() { return capabilityName; }
    public void setCapabilityName(String capabilityName) { this.capabilityName = capabilityName; }
    public List<ParamDefinition> getInputParams() { return inputParams; }
    public void setInputParams(List<ParamDefinition> inputParams) { this.inputParams = inputParams; }
    public List<ParamDefinition> getOutputParams() { return outputParams; }
    public void setOutputParams(List<ParamDefinition> outputParams) { this.outputParams = outputParams; }
    public String getApplicableCondition() { return applicableCondition; }
    public void setApplicableCondition(String applicableCondition) { this.applicableCondition = applicableCondition; }
    public String getCapabilityDescription() { return capabilityDescription; }
    public void setCapabilityDescription(String capabilityDescription) { this.capabilityDescription = capabilityDescription; }
}
