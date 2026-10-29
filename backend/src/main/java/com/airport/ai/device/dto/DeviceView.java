package com.airport.ai.device.dto;

import com.airport.ai.device.Device;
import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * 设备档案对外展示视图，接入凭据以掩码返回，不回显原值（对应5.2.1业务规则8）
 */
public class DeviceView {

    private Long id;
    private String deviceCode;
    private String deviceName;
    private String deviceTypeCode;
    private Boolean isSimulator;
    private String simulatedDeviceType;
    private String areaCode;
    private BigDecimal positionX;
    private BigDecimal positionY;
    private String accessEndpoint;
    private String accessCredentialRefMasked;
    private Integer statusReportInterval;
    private String connectionTestStatus;
    private String connectionTestResult;
    private String remark;
    private String deviceStatus;
    private String agentStatus;
    private String onlineStatus;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;

    public static DeviceView from(Device d) {
        DeviceView v = new DeviceView();
        v.id = d.getId();
        v.deviceCode = d.getDeviceCode();
        v.deviceName = d.getDeviceName();
        v.deviceTypeCode = d.getDeviceTypeCode();
        v.isSimulator = d.getIsSimulator();
        v.simulatedDeviceType = d.getSimulatedDeviceType();
        v.areaCode = d.getAreaCode();
        v.positionX = d.getPositionX();
        v.positionY = d.getPositionY();
        v.accessEndpoint = d.getAccessEndpoint();
        v.accessCredentialRefMasked = mask(d.getAccessCredentialRef());
        v.statusReportInterval = d.getStatusReportInterval();
        v.connectionTestStatus = d.getConnectionTestStatus();
        v.connectionTestResult = d.getConnectionTestResult();
        v.remark = d.getRemark();
        v.deviceStatus = d.getDeviceStatus();
        v.agentStatus = d.getAgentStatus();
        v.onlineStatus = d.getOnlineStatus();
        v.createdAt = d.getCreatedAt();
        v.updatedAt = d.getUpdatedAt();
        return v;
    }

    private static String mask(String raw) {
        return com.airport.ai.common.CredentialMasker.mask(raw);
    }

    public String getAgentStatus() { return agentStatus; }
    public String getOnlineStatus() { return onlineStatus; }
    public Long getId() { return id; }
    public String getDeviceCode() { return deviceCode; }
    public String getDeviceName() { return deviceName; }
    public String getDeviceTypeCode() { return deviceTypeCode; }
    public Boolean getIsSimulator() { return isSimulator; }
    public String getSimulatedDeviceType() { return simulatedDeviceType; }
    public String getAreaCode() { return areaCode; }
    public BigDecimal getPositionX() { return positionX; }
    public BigDecimal getPositionY() { return positionY; }
    public String getAccessEndpoint() { return accessEndpoint; }
    public String getAccessCredentialRefMasked() { return accessCredentialRefMasked; }
    public Integer getStatusReportInterval() { return statusReportInterval; }
    public String getConnectionTestStatus() { return connectionTestStatus; }
    public String getConnectionTestResult() { return connectionTestResult; }
    public String getRemark() { return remark; }
    public String getDeviceStatus() { return deviceStatus; }
    public LocalDateTime getCreatedAt() { return createdAt; }
    public LocalDateTime getUpdatedAt() { return updatedAt; }
}
