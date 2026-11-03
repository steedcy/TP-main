package com.airport.ai.task.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/**
 * 对应5.4.5/5.4.6任务待人工处理阶段的处置动作，取值SWITCH_TO_BASELINE/RETRY_PLANNING/MARK_FAILED。
 * reason为本次处置原因：置为失败必填（不可逆），转基线/重试规划可选；会写入操作记录与任务事件（DEF-S3-062）。
 * taskGoal可选：修改目标重试规划时可传入更新后的目标（TC-042.S1）。
 */
public class ManualActionRequest {

    @NotBlank(message = "请指定处置动作")
    private String action;

    @Size(max = 200, message = "处置原因不得超过200字")
    private String reason;

    @Size(max = 500, message = "修改后的目标不得超过500字")
    private String taskGoal;

    public String getAction() { return action; }
    public void setAction(String action) { this.action = action; }
    public String getReason() { return reason; }
    public void setReason(String reason) { this.reason = reason; }
    public String getTaskGoal() { return taskGoal; }
    public void setTaskGoal(String taskGoal) { this.taskGoal = taskGoal; }
}
