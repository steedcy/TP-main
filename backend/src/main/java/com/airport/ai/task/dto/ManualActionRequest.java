package com.airport.ai.task.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/**
 * 对应5.4.5/5.4.6任务待人工处理阶段的处置动作，取值SWITCH_TO_BASELINE/RETRY_PLANNING/MARK_FAILED。
 * reason为本次处置原因：置为失败必填（不可逆），转基线/重试规划可选；会写入操作记录与任务事件（DEF-S3-062）。
 */
public class ManualActionRequest {

    @NotBlank(message = "请指定处置动作")
    private String action;

    @Size(max = 200, message = "处置原因不得超过200字")
    private String reason;

    public String getAction() { return action; }
    public void setAction(String action) { this.action = action; }
    public String getReason() { return reason; }
    public void setReason(String reason) { this.reason = reason; }
}
