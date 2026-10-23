package com.airport.ai.taskdef.dto;

import com.airport.ai.devicetype.dto.ParamDefinition;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.Size;

import java.util.List;

/**
 * 对应5.6.1备选路径2a：可编辑预置任务族的场景参数与约束等，但不允许改任务名称（预置任务族
 * 标识不可变）与definitionCode（既有Task记录靠该编码关联任务族，改名会破坏历史数据）。
 * 扩展任务族的任务名称同样不允许编辑，与新增时的唯一性约束保持一致，避免改名后与其它
 * 已提交任务的taskFamily引用产生歧义。
 */
public class UpdateTaskDefinitionRequest {

    @NotBlank(message = "请输入自然语言目标模板")
    @Size(min = 1, max = 500, message = "自然语言目标模板长度需为1~500位")
    private String goalTemplate;

    @NotEmpty(message = "请定义至少1个场景参数")
    @Valid
    private List<ParamDefinition> sceneParams;

    @NotEmpty(message = "请选择至少1个可用能力类型")
    private List<String> availableCapabilityTypes;

    private String constraintDescription;

    @NotBlank(message = "请输入预期完成条件")
    private String completionCondition;

    public String getGoalTemplate() { return goalTemplate; }
    public void setGoalTemplate(String goalTemplate) { this.goalTemplate = goalTemplate; }
    public List<ParamDefinition> getSceneParams() { return sceneParams; }
    public void setSceneParams(List<ParamDefinition> sceneParams) { this.sceneParams = sceneParams; }
    public List<String> getAvailableCapabilityTypes() { return availableCapabilityTypes; }
    public void setAvailableCapabilityTypes(List<String> availableCapabilityTypes) { this.availableCapabilityTypes = availableCapabilityTypes; }
    public String getConstraintDescription() { return constraintDescription; }
    public void setConstraintDescription(String constraintDescription) { this.constraintDescription = constraintDescription; }
    public String getCompletionCondition() { return completionCondition; }
    public void setCompletionCondition(String completionCondition) { this.completionCondition = completionCondition; }
}
