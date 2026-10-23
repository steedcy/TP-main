package com.airport.ai.device.dto;

import jakarta.validation.constraints.*;
import java.math.BigDecimal;

/**
 * 编辑设备档案，不允许修改deviceCode（唯一标识）和deviceTypeCode（类型变更影响能力边界，
 * 需先停用重建而非直接编辑）。对应5.2.1备选路径3a：修改接入参数后连接测试结果重置为未测试。
 */
public class UpdateDeviceRequest {

    @NotBlank(message = "请输入设备名称")
    @Size(min = 1, max = 64, message = "设备名称长度需为1~64位")
    private String deviceName;

    @NotBlank(message = "请选择所属区域")
    private String areaCode;

    @NotNull(message = "请输入位置坐标X")
    private BigDecimal positionX;

    @NotNull(message = "请输入位置坐标Y")
    private BigDecimal positionY;

    @NotBlank(message = "请输入接入接口地址")
    private String accessEndpoint;

    /** 留空表示不修改凭据（对应5.2.1业务规则8：凭据不回显原值，故不强制每次编辑都重新输入） */
    @Size(max = 128, message = "凭据标识最长128位")
    private String accessCredentialRef;

    @NotNull(message = "请输入状态上报周期")
    @Min(5) @Max(60)
    private Integer statusReportInterval;

    @Size(max = 200, message = "备注最长200位")
    private String remark;

    public String getDeviceName() { return deviceName; }
    public void setDeviceName(String deviceName) { this.deviceName = deviceName; }
    public String getAreaCode() { return areaCode; }
    public void setAreaCode(String areaCode) { this.areaCode = areaCode; }
    public BigDecimal getPositionX() { return positionX; }
    public void setPositionX(BigDecimal positionX) { this.positionX = positionX; }
    public BigDecimal getPositionY() { return positionY; }
    public void setPositionY(BigDecimal positionY) { this.positionY = positionY; }
    public String getAccessEndpoint() { return accessEndpoint; }
    public void setAccessEndpoint(String accessEndpoint) { this.accessEndpoint = accessEndpoint; }
    public String getAccessCredentialRef() { return accessCredentialRef; }
    public void setAccessCredentialRef(String accessCredentialRef) { this.accessCredentialRef = accessCredentialRef; }
    public Integer getStatusReportInterval() { return statusReportInterval; }
    public void setStatusReportInterval(Integer statusReportInterval) { this.statusReportInterval = statusReportInterval; }
    public String getRemark() { return remark; }
    public void setRemark(String remark) { this.remark = remark; }
}
