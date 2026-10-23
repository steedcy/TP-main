package com.airport.ai.device;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * 对应数据库设计说明书V2.0 4.3.1节 devices表。纯POJO，持久化映射见 mapper/DeviceMapper.xml。
 */
public class Device {

    private Long id;
    private String deviceCode;
    private String deviceName;
    private String deviceTypeCode;
    private Boolean isSimulator = false;
    private String simulatedDeviceType;
    private String areaCode;
    private BigDecimal positionX;
    private BigDecimal positionY;
    private String accessEndpoint;
    private String accessCredentialRef;
    /** SHA-256 lookup hash and AES-GCM encrypted token; plaintext is only returned once at rotation. */
    private String deviceTokenHash;
    private String deviceTokenCiphertext;
    private LocalDateTime deviceTokenIssuedAt;
    private Integer statusReportInterval = 15;
    /** UNTESTED / PASSED / FAILED */
    private String connectionTestStatus = "UNTESTED";
    private String connectionTestResult;
    private String remark;
    /** ACTIVE / INACTIVE，对应5.2.1业务规则6设备档案启用/停用，与代理侧agent_status语义不同 */
    private String deviceStatus = "ACTIVE";
    private LocalDateTime createdAt = LocalDateTime.now();
    private LocalDateTime updatedAt = LocalDateTime.now();
    private String createdBy;
    private String updatedBy;

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
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
    public String getDeviceTokenHash() { return deviceTokenHash; }
    public void setDeviceTokenHash(String deviceTokenHash) { this.deviceTokenHash = deviceTokenHash; }
    public String getDeviceTokenCiphertext() { return deviceTokenCiphertext; }
    public void setDeviceTokenCiphertext(String deviceTokenCiphertext) { this.deviceTokenCiphertext = deviceTokenCiphertext; }
    public LocalDateTime getDeviceTokenIssuedAt() { return deviceTokenIssuedAt; }
    public void setDeviceTokenIssuedAt(LocalDateTime deviceTokenIssuedAt) { this.deviceTokenIssuedAt = deviceTokenIssuedAt; }
    public Integer getStatusReportInterval() { return statusReportInterval; }
    public void setStatusReportInterval(Integer statusReportInterval) { this.statusReportInterval = statusReportInterval; }
    public String getConnectionTestStatus() { return connectionTestStatus; }
    public void setConnectionTestStatus(String connectionTestStatus) { this.connectionTestStatus = connectionTestStatus; }
    public String getConnectionTestResult() { return connectionTestResult; }
    public void setConnectionTestResult(String connectionTestResult) { this.connectionTestResult = connectionTestResult; }
    public String getRemark() { return remark; }
    public void setRemark(String remark) { this.remark = remark; }
    public String getDeviceStatus() { return deviceStatus; }
    public void setDeviceStatus(String deviceStatus) { this.deviceStatus = deviceStatus; }
    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }
    public LocalDateTime getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(LocalDateTime updatedAt) { this.updatedAt = updatedAt; }
    public String getCreatedBy() { return createdBy; }
    public void setCreatedBy(String createdBy) { this.createdBy = createdBy; }
    public String getUpdatedBy() { return updatedBy; }
    public void setUpdatedBy(String updatedBy) { this.updatedBy = updatedBy; }
}
