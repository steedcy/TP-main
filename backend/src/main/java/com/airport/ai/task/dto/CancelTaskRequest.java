package com.airport.ai.task.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/**
 * 对应5.4.1界面元素"取消任务"，只允许在PLANNING状态（进入计划生成前）调用
 */
public class CancelTaskRequest {

    @NotBlank(message = "请填写取消原因")
    @Size(max = 200, message = "取消原因最长200位")
    private String reason;

    public String getReason() { return reason; }
    public void setReason(String reason) { this.reason = reason; }
}
