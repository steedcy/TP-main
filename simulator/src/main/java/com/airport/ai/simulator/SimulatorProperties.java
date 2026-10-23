package com.airport.ai.simulator;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;

@Component
@ConfigurationProperties(prefix = "simulator")
public class SimulatorProperties {
    // Synthetic fixture landmarks in F2 pixel coordinates; not a calibrated physical map.
    private java.util.Map<String, java.util.List<Double>> landmarks = new java.util.LinkedHashMap<>(java.util.Map.of(
        "F2_SERVICE_POINT", java.util.List.of(810.0,4200.0),
        "F2_BAGGAGE_POINT", java.util.List.of(805.0,4050.0),
        "F2_TEST_GATE", java.util.List.of(815.0,4600.0),
        "GATE_A05", java.util.List.of(815.0,4600.0)));
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
