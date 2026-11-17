package com.airport.ai.simulator;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;

@Component
@ConfigurationProperties(prefix = "simulator")
public class SimulatorProperties {
    // Calibrated F2 terminal landmarks (1260 x 6895 floorplan); codes + Chinese names synced with live POIs.
    private java.util.Map<String, java.util.List<Double>> landmarks = new java.util.LinkedHashMap<>(java.util.Map.ofEntries(
        java.util.Map.entry("F2_SERVICE_POINT", java.util.List.of(600.0, 3743.0)),
        java.util.Map.entry("F2_BAGGAGE_POINT", java.util.List.of(575.0, 2575.0)),
        java.util.Map.entry("T2值机岛A01", java.util.List.of(556.0, 3552.0)),
        java.util.Map.entry("国内值机柜台01", java.util.List.of(556.0, 3552.0)),
        java.util.Map.entry("T2值机岛A02", java.util.List.of(556.0, 3552.0)),
        java.util.Map.entry("T2值机岛A03", java.util.List.of(575.0, 2575.0)),
        java.util.Map.entry("国内值机柜台02", java.util.List.of(575.0, 2575.0)),
        java.util.Map.entry("T2值机区", java.util.List.of(556.0, 3382.0)),
        java.util.Map.entry("VIP值机柜台", java.util.List.of(556.0, 3382.0)),
        java.util.Map.entry("行李托运柜台A01", java.util.List.of(560.0, 3330.0)),
        java.util.Map.entry("行李托运柜台", java.util.List.of(560.0, 3330.0)),
        java.util.Map.entry("超规行李专柜B01", java.util.List.of(600.0, 3743.0)),
        java.util.Map.entry("超规行李托运", java.util.List.of(600.0, 3743.0)),
        java.util.Map.entry("智能行李测量点A", java.util.List.of(365.0, 3108.0)),
        java.util.Map.entry("智能行李测量点01", java.util.List.of(365.0, 3108.0)),
        java.util.Map.entry("智能行李测量点B", java.util.List.of(456.0, 2508.0)),
        java.util.Map.entry("智能行李测量点02", java.util.List.of(456.0, 2508.0)),
        java.util.Map.entry("安检通道01", java.util.List.of(622.0, 2970.0)),
        java.util.Map.entry("国内安检通道", java.util.List.of(622.0, 2970.0)),
        java.util.Map.entry("VIP安检通道", java.util.List.of(622.0, 3232.0)),
        java.util.Map.entry("头等舱/无障碍通道", java.util.List.of(622.0, 3232.0)),
        java.util.Map.entry("旅客服务中心", java.util.List.of(408.0, 3012.0)),
        java.util.Map.entry("问询柜台", java.util.List.of(408.0, 3012.0)),
        java.util.Map.entry("GATE_A01", java.util.List.of(960.0, 2176.0)),
        java.util.Map.entry("登机口14", java.util.List.of(960.0, 2176.0)),
        java.util.Map.entry("F2_TEST_GATE", java.util.List.of(960.0, 2506.0)),
        java.util.Map.entry("GATE_A05", java.util.List.of(960.0, 2506.0)),
        java.util.Map.entry("登机口13", java.util.List.of(960.0, 2506.0)),
        java.util.Map.entry("GATE_B01", java.util.List.of(960.0, 2768.0)),
        java.util.Map.entry("登机口12", java.util.List.of(960.0, 2768.0)),
        java.util.Map.entry("GATE_011", java.util.List.of(960.0, 3242.0)),
        java.util.Map.entry("登机口11", java.util.List.of(960.0, 3242.0)),
        java.util.Map.entry("GATE_010", java.util.List.of(960.0, 3582.0)),
        java.util.Map.entry("登机口10", java.util.List.of(960.0, 3582.0))));
    public java.util.Map<String,java.util.List<Double>> getLandmarks() { return landmarks; }
    public void setLandmarks(java.util.Map<String,java.util.List<Double>> value) { landmarks=value; }
    private String deviceCode = "SIM_DISPLAY_001";
    private String deviceType = "SIMULATOR";
    private String simulatedDeviceType = "SMART_DISPLAY";
    private String token = "";
    private String agentCode = "";
    private String platformReportUrl = "";
    private int heartbeatIntervalSeconds = 15;
    private int heartbeatTimeoutSeconds = 30;
    private int executionDelayMilliseconds = 500;
    private volatile String scenarioResult = "SUCCESS";
    private BigDecimal x = new BigDecimal("120.5");
    private BigDecimal y = new BigDecimal("88.2");
    private String zone = "T2-B区";
    private double baggageLengthCm = 55;
    private double baggageWidthCm = 40;
    private double baggageHeightCm = 20;
    private double baggageWeightKg = 10;

    public String getDeviceCode() { return deviceCode; }
    public void setDeviceCode(String deviceCode) { this.deviceCode = deviceCode; }
    public String getDeviceType() { return deviceType; }
    public void setDeviceType(String deviceType) { this.deviceType = deviceType; }
    public String getSimulatedDeviceType() { return simulatedDeviceType; }
    public void setSimulatedDeviceType(String simulatedDeviceType) { this.simulatedDeviceType = simulatedDeviceType; }
    public String getToken() { return token; }
    public void setToken(String token) { this.token = token; }
    public String getAgentCode() { return agentCode; }
    public void setAgentCode(String agentCode) { this.agentCode = agentCode; }
    public String getPlatformReportUrl() { return platformReportUrl; }
    public void setPlatformReportUrl(String platformReportUrl) { this.platformReportUrl = platformReportUrl; }
    public int getHeartbeatIntervalSeconds() { return heartbeatIntervalSeconds; }
    public void setHeartbeatIntervalSeconds(int value) { this.heartbeatIntervalSeconds = value; }
    public int getHeartbeatTimeoutSeconds() { return heartbeatTimeoutSeconds; }
    public void setHeartbeatTimeoutSeconds(int value) { this.heartbeatTimeoutSeconds = value; }
    public int getExecutionDelayMilliseconds() { return executionDelayMilliseconds; }
    public void setExecutionDelayMilliseconds(int value) { this.executionDelayMilliseconds = value; }
    public String getScenarioResult() { return scenarioResult; }
    public void setScenarioResult(String scenarioResult) { this.scenarioResult = scenarioResult; }
    public BigDecimal getX() { return x; }
    public void setX(BigDecimal x) { this.x = x; }
    public BigDecimal getY() { return y; }
    public void setY(BigDecimal y) { this.y = y; }
    public String getZone() { return zone; }
    public void setZone(String zone) { this.zone = zone; }
    public double getBaggageLengthCm() { return baggageLengthCm; }
    public void setBaggageLengthCm(double value) { this.baggageLengthCm = value; }
    public double getBaggageWidthCm() { return baggageWidthCm; }
    public void setBaggageWidthCm(double value) { this.baggageWidthCm = value; }
    public double getBaggageHeightCm() { return baggageHeightCm; }
    public void setBaggageHeightCm(double value) { this.baggageHeightCm = value; }
    public double getBaggageWeightKg() { return baggageWeightKg; }
    public void setBaggageWeightKg(double value) { this.baggageWeightKg = value; }
}
