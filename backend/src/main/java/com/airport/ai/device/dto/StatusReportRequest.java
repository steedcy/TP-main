package com.airport.ai.device.dto;

import jakarta.validation.constraints.NotBlank;
import java.math.BigDecimal;

/**
 * 对应5.2.3业务规则1：设备按周期上报在线状态、工作状态、位置和必要业务状态。
 * 格式非法（必填字段缺失/工作状态取值非法）时丢弃并记录格式异常事件，不影响在线判断之外的业务状态（业务规则8）。
 */
public class StatusReportRequest {

    @NotBlank(message = "workStatus不可为空")
    private String workStatus;

    private BigDecimal positionX;
    private BigDecimal positionY;

    public String getWorkStatus() { return workStatus; }
    public void setWorkStatus(String workStatus) { this.workStatus = workStatus; }
    public BigDecimal getPositionX() { return positionX; }
    public void setPositionX(BigDecimal positionX) { this.positionX = positionX; }
    public BigDecimal getPositionY() { return positionY; }
    public void setPositionY(BigDecimal positionY) { this.positionY = positionY; }
}
