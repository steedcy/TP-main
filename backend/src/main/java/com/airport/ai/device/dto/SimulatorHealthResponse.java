package com.airport.ai.device.dto;

import java.math.BigDecimal;
import java.util.List;

public class SimulatorHealthResponse {
    private String protocolVersion;
    private String nonce;
    private String deviceCode;
    private String deviceTypeCode;
    private String simulatedDeviceType;
    private String onlineStatus;
    private String workStatus;
    private Location location;
    private List<String> capabilities;
    private String reportedAt;

    public String getProtocolVersion() { return protocolVersion; }
    public void setProtocolVersion(String protocolVersion) { this.protocolVersion = protocolVersion; }
    public String getNonce() { return nonce; }
    public void setNonce(String nonce) { this.nonce = nonce; }
    public String getDeviceCode() { return deviceCode; }
    public void setDeviceCode(String deviceCode) { this.deviceCode = deviceCode; }
    public String getDeviceTypeCode() { return deviceTypeCode; }
    public void setDeviceTypeCode(String deviceTypeCode) { this.deviceTypeCode = deviceTypeCode; }
    public String getSimulatedDeviceType() { return simulatedDeviceType; }
    public void setSimulatedDeviceType(String simulatedDeviceType) { this.simulatedDeviceType = simulatedDeviceType; }
    public String getOnlineStatus() { return onlineStatus; }
    public void setOnlineStatus(String onlineStatus) { this.onlineStatus = onlineStatus; }
    public String getWorkStatus() { return workStatus; }
    public void setWorkStatus(String workStatus) { this.workStatus = workStatus; }
    public Location getLocation() { return location; }
    public void setLocation(Location location) { this.location = location; }
    public List<String> getCapabilities() { return capabilities; }
    public void setCapabilities(List<String> capabilities) { this.capabilities = capabilities; }
    public String getReportedAt() { return reportedAt; }
    public void setReportedAt(String reportedAt) { this.reportedAt = reportedAt; }

    public static class Location {
        private BigDecimal x;
        private BigDecimal y;
        private String zone;
        public BigDecimal getX() { return x; }
        public void setX(BigDecimal x) { this.x = x; }
        public BigDecimal getY() { return y; }
        public void setY(BigDecimal y) { this.y = y; }
        public String getZone() { return zone; }
        public void setZone(String zone) { this.zone = zone; }
    }
}
