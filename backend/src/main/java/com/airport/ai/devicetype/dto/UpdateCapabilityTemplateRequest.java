package com.airport.ai.devicetype.dto;

import jakarta.validation.Valid;
import jakarta.validation.constraints.*;

import java.util.List;

/**
 * 编辑能力模板，不允许修改templateCode（唯一标识）和capabilityType（能力类型变更等同于换了一个模板，
 * 应新建而非编辑）。保存后自动分配新版本号（对应5.2.4A业务规则12）。
 */
public class UpdateCapabilityTemplateRequest {

    @NotBlank(message = "请输入模板名称")
    @Size(min = 1, max = 64, message = "模板名称长度需为1~64位")
    private String templateName;

    @NotEmpty(message = "请定义至少1个输入参数")
    @Valid
    private List<ParamDefinition> inputParams;

    @NotEmpty(message = "请定义至少1个输出参数")
    @Valid
    private List<ParamDefinition> outputParams;

    @Size(max = 500, message = "模板说明最长500位")
    private String templateDescription;

    public String getTemplateName() { return templateName; }
    public void setTemplateName(String templateName) { this.templateName = templateName; }
    public List<ParamDefinition> getInputParams() { return inputParams; }
    public void setInputParams(List<ParamDefinition> inputParams) { this.inputParams = inputParams; }
    public List<ParamDefinition> getOutputParams() { return outputParams; }
    public void setOutputParams(List<ParamDefinition> outputParams) { this.outputParams = outputParams; }
    public String getTemplateDescription() { return templateDescription; }
    public void setTemplateDescription(String templateDescription) { this.templateDescription = templateDescription; }
}
