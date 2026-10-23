package com.airport.ai.task.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

/**
 * 对应5.5.6人工终止业务规则1："终止须填原因（1~200字）+二次确认，缺一不可"
 */
public class TerminateTaskRequest {

    @NotBlank(message = "请填写终止原因")
    @Size(max = 200, message = "终止原因最长200位")
    private String reason;

    @NotNull(message = "请完成二次确认")
    private Boolean confirmed;

    public String getReason() { return reason; }
    public void setReason(String reason) { this.reason = reason; }
    public Boolean getConfirmed() { return confirmed; }
    public void setConfirmed(Boolean confirmed) { this.confirmed = confirmed; }
}
