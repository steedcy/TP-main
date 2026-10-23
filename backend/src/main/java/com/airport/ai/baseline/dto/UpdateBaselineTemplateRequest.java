package com.airport.ai.baseline.dto;

import com.airport.ai.devicetype.dto.ParamDefinition;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotEmpty;

import java.util.List;

/**
 * 编辑模板：不允许修改templateName（唯一标识）和templateIntent（意图变更等同于换了模板，应新建而非编辑）。
 * 已启用模板被修改时生成新版本（对应5.3.1业务规则7）。
 */
public class UpdateBaselineTemplateRequest {

    @NotEmpty(message = "请定义至少1个输入参数")
    @Valid
    private List<ParamDefinition> inputParams;

    @NotEmpty(message = "请添加至少1个步骤")
    @Valid
    private List<TemplateStep> steps;

    public List<ParamDefinition> getInputParams() { return inputParams; }
    public void setInputParams(List<ParamDefinition> inputParams) { this.inputParams = inputParams; }
    public List<TemplateStep> getSteps() { return steps; }
    public void setSteps(List<TemplateStep> steps) { this.steps = steps; }
}
