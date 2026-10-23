package com.airport.ai.device.dto;

import jakarta.validation.constraints.*;
import java.math.BigDecimal;

/**
 * 对应5.2.1界面元素与附录B 6.3.1节字段约束
 */
public class CreateDeviceRequest {

    @NotBlank(message = "请输入设备编码")
    @Pattern(regexp = "^[A-Za-z0-9_-]{1,32}$", message = "设备编码1~32位，仅允许字母、数字、下划线和短横线")
    private String deviceCode;

    @NotBlank(message = "请输入设备名称")
    @Size(min = 1, max = 64, message = "设备名称长度需为1~64位")
    private String deviceName;

    @NotBlank(message = "请选择设备类型")
    @Pattern(regexp = "SMART_DISPLAY|BAGGAGE_SCANNER|FLIGHT_DELAY_BOARD|MOBILE_ROBOT|SIMULATOR",
            message = "设备类型不在5类范围内")
    private String deviceTypeCode;

    @NotNull(message = "请选择虚实属性")
    private Boolean isSimulator;

    /** 仿真体必须指定所模拟的设备类型（对应5.2.1业务规则4），由Service层校验非空 */
    private String simulatedDeviceType;

    @NotBlank(message = "请选择所属区域")
    private String areaCode;

    @NotNull(message = "请输入位置坐标X")
    private BigDecimal positionX;

    @NotNull(message = "请输入位置坐标Y")
    private BigDecimal positionY;

    @NotBlank(message = "请输入接入接口地址")
    private String accessEndpoint;

    @NotBlank(message = "请输入接入凭据标识")
    @Size(max = 128, message = "凭据标识最长128位")
    private String accessCredentialRef;

    @NotNull(message = "请输入状态上报周期")
    @Min(5) @Max(60)
    private Integer statusReportInterval = 15;

    @Size(max = 200, message = "备注最长200位")
    private String remark;

    public String getDeviceCode() { return deviceCode; }
    public void setDeviceCode(String deviceCode) { this.deviceCode = deviceCode; }
    public String getDeviceName() { return deviceName; }
    public void setDeviceName(String deviceName) { this.deviceName = deviceName; }
    public String getDeviceTypeCode() { return deviceTypeCode; }
    public void setDeviceTypeCode(String deviceTypeCode) { this.deviceTypeCode = deviceTypeCode; }
    public Boolean getIsSimulator() { return isSimulator; }
    public void setIsSimulator(Boolean isSimulator) { this.isSimulator = isSimulator; }
    public String getSimulatedDeviceType() { return simulatedDeviceType; }
    public void setSimulatedDeviceType(String simulatedDeviceType) { this.simulatedDeviceType = simulatedDeviceType; }
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
