package com.airport.ai.task.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

import java.util.Map;

/**
 * 对应5.4.1界面元素"任务目标""任务族""场景参数"。taskFamily不再用硬编码枚举@Pattern校验
 * （5.6.1任务定义管理上线后任务族可由配置管理员扩展），改为TaskService.submit()里
 * 查询TaskDefinitionService校验是否为已启用任务定义编码，见该方法注释。
 */
public class SubmitTaskRequest {

    @NotBlank(message = "请输入任务目标")
    @Size(min = 1, max = 500, message = "任务目标长度需为1~500位")
    private String taskGoal;

    private String taskFamily;

    private Map<String, Object> sceneParams;

    public String getTaskGoal() { return taskGoal; }
    public void setTaskGoal(String taskGoal) { this.taskGoal = taskGoal; }
    public String getTaskFamily() { return taskFamily; }
    public void setTaskFamily(String taskFamily) { this.taskFamily = taskFamily; }
    public Map<String, Object> getSceneParams() { return sceneParams; }
    public void setSceneParams(Map<String, Object> sceneParams) { this.sceneParams = sceneParams; }
}
