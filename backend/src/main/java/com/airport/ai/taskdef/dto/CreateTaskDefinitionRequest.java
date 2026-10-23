package com.airport.ai.taskdef.dto;

import com.airport.ai.devicetype.dto.ParamDefinition;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.Size;

import java.util.List;

/**
 * 对应5.6.1界面元素"任务定义编辑"。definitionCode由后端根据taskName自动生成扩展任务族标识，
 * 不对外暴露为可填字段——预置任务族的definitionCode与既有Task.taskFamily历史枚举值一致，
 * 扩展任务族则须保证不与预置及已有扩展任务族冲突。
 */
public class CreateTaskDefinitionRequest {

    @NotBlank(message = "请输入任务名称")
    @Size(min = 1, max = 64, message = "任务名称长度需为1~64位")
    private String taskName;

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

    public String getTaskName() { return taskName; }
    public void setTaskName(String taskName) { this.taskName = taskName; }
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
