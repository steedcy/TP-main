package com.airport.ai.baseline.dto;

import jakarta.validation.Valid;
import jakarta.validation.constraints.*;

import java.util.List;

/**
 * 模板步骤（对应5.3.1界面元素、附录B 6.6节steps数组元素）
 */
public class TemplateStep {

    /** 按添加顺序自动编号，由Service层赋值，前端提交时按数组顺序即为顺序，无需手填 */
    private Integer stepSeq;

    @NotBlank(message = "请选择步骤所需能力")
    private String capabilityType;

    @NotEmpty(message = "请配置参数映射")
    @Valid
    private List<ParamMapping> paramMapping;

    @NotNull(message = "请输入步骤超时时间")
    @Min(10) @Max(600)
    private Integer stepTimeout = 60;

    @NotBlank(message = "请输入步骤完成条件")
    private String completionCondition;

    public Integer getStepSeq() { return stepSeq; }
    public void setStepSeq(Integer stepSeq) { this.stepSeq = stepSeq; }
    public String getCapabilityType() { return capabilityType; }
    public void setCapabilityType(String capabilityType) { this.capabilityType = capabilityType; }
    public List<ParamMapping> getParamMapping() { return paramMapping; }
    public void setParamMapping(List<ParamMapping> paramMapping) { this.paramMapping = paramMapping; }
    public Integer getStepTimeout() { return stepTimeout; }
    public void setStepTimeout(Integer stepTimeout) { this.stepTimeout = stepTimeout; }
    public String getCompletionCondition() { return completionCondition; }
    public void setCompletionCondition(String completionCondition) { this.completionCondition = completionCondition; }
}
