package com.airport.ai.devicetype.dto;

import jakarta.validation.Valid;
import jakarta.validation.constraints.*;

import java.util.List;

/**
 * 对应附录B 6.4.2节请求体、5.2.4A界面元素（图5.2.4A-3能力模板编辑）
 */
public class CreateCapabilityTemplateRequest {

    @NotBlank(message = "请输入模板编码")
    @Pattern(regexp = "^[A-Za-z0-9_]{1,32}$", message = "模板编码1~32位，仅允许字母、数字、下划线")
    private String templateCode;

    @NotBlank(message = "请输入模板名称")
    @Size(min = 1, max = 64, message = "模板名称长度需为1~64位")
    private String templateName;

    @NotBlank(message = "请选择能力类型")
    private String capabilityType;

    @NotEmpty(message = "请定义至少1个输入参数")
    @Valid
    private List<ParamDefinition> inputParams;

    @NotEmpty(message = "请定义至少1个输出参数")
    @Valid
    private List<ParamDefinition> outputParams;

    @Size(max = 500, message = "模板说明最长500位")
    private String templateDescription;

    public String getTemplateCode() { return templateCode; }
    public void setTemplateCode(String templateCode) { this.templateCode = templateCode; }
    public String getTemplateName() { return templateName; }
    public void setTemplateName(String templateName) { this.templateName = templateName; }
    public String getCapabilityType() { return capabilityType; }
    public void setCapabilityType(String capabilityType) { this.capabilityType = capabilityType; }
    public List<ParamDefinition> getInputParams() { return inputParams; }
    public void setInputParams(List<ParamDefinition> inputParams) { this.inputParams = inputParams; }
    public List<ParamDefinition> getOutputParams() { return outputParams; }
    public void setOutputParams(List<ParamDefinition> outputParams) { this.outputParams = outputParams; }
    public String getTemplateDescription() { return templateDescription; }
    public void setTemplateDescription(String templateDescription) { this.templateDescription = templateDescription; }
}
