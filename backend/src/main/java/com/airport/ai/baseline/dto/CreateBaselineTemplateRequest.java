package com.airport.ai.baseline.dto;

import com.airport.ai.devicetype.dto.ParamDefinition;
import jakarta.validation.Valid;
import jakarta.validation.constraints.*;

import java.util.List;

/**
 * 对应5.3.1界面元素、附录B 6.6节请求体。templateIntent不再用硬编码枚举@Pattern校验
 * （5.6.1任务定义管理上线后任务族可扩展），改为BaselineTemplateService.create()里
 * 查询TaskDefinitionService校验是否为已存在的任务定义编码，见该方法注释。
 */
public class CreateBaselineTemplateRequest {

    @NotBlank(message = "请输入模板名称")
    @Size(min = 1, max = 64, message = "模板名称长度需为1~64位")
    private String templateName;

    @NotBlank(message = "请选择模板意图")
    private String templateIntent;

    @NotEmpty(message = "请定义至少1个输入参数")
    @Valid
    private List<ParamDefinition> inputParams;

    @NotEmpty(message = "请添加至少1个步骤")
    @Valid
    private List<TemplateStep> steps;

    public String getTemplateName() { return templateName; }
    public void setTemplateName(String templateName) { this.templateName = templateName; }
    public String getTemplateIntent() { return templateIntent; }
    public void setTemplateIntent(String templateIntent) { this.templateIntent = templateIntent; }
    public List<ParamDefinition> getInputParams() { return inputParams; }
    public void setInputParams(List<ParamDefinition> inputParams) { this.inputParams = inputParams; }
    public List<TemplateStep> getSteps() { return steps; }
    public void setSteps(List<TemplateStep> steps) { this.steps = steps; }
}
