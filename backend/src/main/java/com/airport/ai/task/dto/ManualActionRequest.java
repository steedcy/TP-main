package com.airport.ai.task.dto;

import jakarta.validation.constraints.NotBlank;

/**
 * 对应5.4.5/5.4.6任务待人工处理阶段的处置动作，取值SWITCH_TO_BASELINE/RETRY_PLANNING/MARK_FAILED
 */
public class ManualActionRequest {

    @NotBlank(message = "请指定处置动作")
    private String action;

    public String getAction() { return action; }
    public void setAction(String action) { this.action = action; }
}
