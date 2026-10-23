package com.airport.ai.task.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

/**
 * 对应附录B 4.1节设备代理统一消息接口TASK_ACCEPT设备响应payload：accepted、rejectReason。
 * 对应5.5.1业务规则3/8：设备代理对任务承接请求的接受/拒绝响应。
 */
public class TaskResponseRequest {

    @NotBlank(message = "commandId不可为空")
    private String commandId;

    @NotNull(message = "accepted不可为空")
    private Boolean accepted;

    private String rejectReason;

    public String getCommandId() { return commandId; }
    public void setCommandId(String commandId) { this.commandId = commandId; }
    public Boolean getAccepted() { return accepted; }
    public void setAccepted(Boolean accepted) { this.accepted = accepted; }
    public String getRejectReason() { return rejectReason; }
    public void setRejectReason(String rejectReason) { this.rejectReason = rejectReason; }
}
