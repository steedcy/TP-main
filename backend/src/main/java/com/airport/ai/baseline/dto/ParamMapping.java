package com.airport.ai.baseline.dto;

import jakarta.validation.constraints.NotBlank;

/**
 * 参数映射（对应5.3.1界面元素"参数映射"、附录B 6.6节paramMapping）。
 * source格式：TEMPLATE_INPUT.{paramName}（模板输入参数）或 STEP{n}_OUTPUT.{paramName}（前序步骤输出），
 * 不允许引用未定义变量（对应业务规则5）。
 */
public class ParamMapping {

    @NotBlank(message = "参数映射target不能为空")
    private String target;

    @NotBlank(message = "参数映射source不能为空")
    private String source;

    public String getTarget() { return target; }
    public void setTarget(String target) { this.target = target; }
    public String getSource() { return source; }
    public void setSource(String source) { this.source = source; }
}
