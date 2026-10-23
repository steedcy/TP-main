package com.airport.ai.devicetype.dto;

import jakarta.validation.constraints.NotBlank;

/**
 * 参数定义（输入/输出参数表格每行），对应5.2.4A界面元素"参数表格"
 */
public class ParamDefinition {

    @NotBlank(message = "参数名不能为空")
    private String name;

    @NotBlank(message = "参数类型不能为空")
    private String type;

    private Boolean required;
    private String defaultValue;
    private String range;

    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    public String getType() { return type; }
    public void setType(String type) { this.type = type; }
    public Boolean getRequired() { return required; }
    public void setRequired(Boolean required) { this.required = required; }
    public String getDefaultValue() { return defaultValue; }
    public void setDefaultValue(String defaultValue) { this.defaultValue = defaultValue; }
    public String getRange() { return range; }
    public void setRange(String range) { this.range = range; }
}
