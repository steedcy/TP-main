package com.airport.ai.device.dto;

import com.airport.ai.devicetype.dto.ParamDefinition;
import jakarta.validation.Valid;
import jakarta.validation.constraints.*;

import java.util.List;

/**
 * 对应5.2.4界面元素、附录B 6.5节请求体
 */
public class CreateDeviceCapabilityRequest {

    @NotBlank(message = "请输入能力编码")
    @Size(min = 1, max = 32, message = "能力编码长度需为1~32位")
    private String capabilityCode;

    @NotBlank(message = "请输入能力名称")
    @Size(min = 1, max = 64, message = "能力名称长度需为1~64位")
    private String capabilityName;

    @NotBlank(message = "请选择能力类型")
    private String capabilityType;

    @NotEmpty(message = "请定义至少1个输入参数")
    @Valid
    private List<ParamDefinition> inputParams;

    @NotEmpty(message = "请定义至少1个输出参数")
    @Valid
    private List<ParamDefinition> outputParams;

    private String applicableCondition;

    @Size(max = 500, message = "能力说明最长500位")
    private String capabilityDescription;

    /** 基于5.2.4A标准能力模板预填时传入，非必填 */
    private Long templateId;

    public String getCapabilityCode() { return capabilityCode; }
    public void setCapabilityCode(String capabilityCode) { this.capabilityCode = capabilityCode; }
    public String getCapabilityName() { return capabilityName; }
    public void setCapabilityName(String capabilityName) { this.capabilityName = capabilityName; }
    public String getCapabilityType() { return capabilityType; }
    public void setCapabilityType(String capabilityType) { this.capabilityType = capabilityType; }
    public List<ParamDefinition> getInputParams() { return inputParams; }
    public void setInputParams(List<ParamDefinition> inputParams) { this.inputParams = inputParams; }
    public List<ParamDefinition> getOutputParams() { return outputParams; }
    public void setOutputParams(List<ParamDefinition> outputParams) { this.outputParams = outputParams; }
    public String getApplicableCondition() { return applicableCondition; }
    public void setApplicableCondition(String applicableCondition) { this.applicableCondition = applicableCondition; }
    public String getCapabilityDescription() { return capabilityDescription; }
    public void setCapabilityDescription(String capabilityDescription) { this.capabilityDescription = capabilityDescription; }
    public Long getTemplateId() { return templateId; }
    public void setTemplateId(Long templateId) { this.templateId = templateId; }
}
