package com.airport.ai.simulator;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;

@Component
@ConfigurationProperties(prefix = "simulator")
public class SimulatorProperties {
    // Calibrated 2000 x 600 terminal map POIs (codes + Chinese names) with legacy F2 test aliases preserved.
    private java.util.Map<String, java.util.List<Double>> landmarks = new java.util.LinkedHashMap<>(java.util.Map.<String, java.util.List<Double>>ofEntries(
        // Current 2000 x 600 terminal map POIs (V36)
        java.util.Map.entry("GATE_01", java.util.List.of(239.0, 56.0)),
        java.util.Map.entry("1号登机口", java.util.List.of(239.0, 56.0)),
        java.util.Map.entry("GATE_02", java.util.List.of(482.0, 57.0)),
        java.util.Map.entry("2号登机口", java.util.List.of(482.0, 57.0)),
        java.util.Map.entry("GATE_03", java.util.List.of(719.0, 56.0)),
        java.util.Map.entry("3号登机口", java.util.List.of(719.0, 56.0)),
        java.util.Map.entry("GATE_04", java.util.List.of(1022.0, 57.0)),
        java.util.Map.entry("4号登机口", java.util.List.of(1022.0, 57.0)),
        java.util.Map.entry("GATE_05", java.util.List.of(1257.0, 56.0)),
        java.util.Map.entry("5号登机口", java.util.List.of(1257.0, 56.0)),
        java.util.Map.entry("GATE_06", java.util.List.of(1685.0, 56.0)),
        java.util.Map.entry("6号登机口", java.util.List.of(1685.0, 56.0)),
        java.util.Map.entry("ENTRANCE_01", java.util.List.of(311.0, 520.0)),
        java.util.Map.entry("1号门", java.util.List.of(311.0, 520.0)),
        java.util.Map.entry("ENTRANCE_02", java.util.List.of(1036.0, 520.0)),
        java.util.Map.entry("2号门", java.util.List.of(1036.0, 520.0)),
        java.util.Map.entry("ENTRANCE_03", java.util.List.of(1877.0, 520.0)),
        java.util.Map.entry("3号门", java.util.List.of(1877.0, 520.0)),
        java.util.Map.entry("SERVICE_DESK", java.util.List.of(1028.0, 135.0)),
        java.util.Map.entry("服务台", java.util.List.of(1028.0, 135.0)),
        java.util.Map.entry("候机区服务台", java.util.List.of(1028.0, 135.0)),
        java.util.Map.entry("SECURITY_MAIN", java.util.List.of(1037.0, 286.0)),
        java.util.Map.entry("安全检查", java.util.List.of(1037.0, 286.0)),
        java.util.Map.entry("CHECKIN_WEST", java.util.List.of(896.0, 435.0)),
        java.util.Map.entry("售票", java.util.List.of(896.0, 435.0)),
        java.util.Map.entry("值机办理区(西)", java.util.List.of(896.0, 435.0)),
        java.util.Map.entry("CHECKIN_EAST", java.util.List.of(1123.0, 435.0)),
        java.util.Map.entry("问询", java.util.List.of(1123.0, 435.0)),
        java.util.Map.entry("值机办理区(东)", java.util.List.of(1123.0, 435.0)),
        java.util.Map.entry("MEASURE_WEST", java.util.List.of(520.0, 425.0)),
        java.util.Map.entry("智能行李测量点01", java.util.List.of(520.0, 425.0)),
        java.util.Map.entry("MEASURE_EAST", java.util.List.of(1420.0, 425.0)),
        java.util.Map.entry("智能行李测量点02", java.util.List.of(1420.0, 425.0)),
        java.util.Map.entry("BAGGAGE_CLAIM_W", java.util.List.of(850.0, 318.0)),
        java.util.Map.entry("BAGGAGE_CLAIM_E", java.util.List.of(1228.0, 317.0)),
        java.util.Map.entry("行李开包间", java.util.List.of(850.0, 318.0)),
        java.util.Map.entry("LOUNGE_VIP", java.util.List.of(1720.0, 264.0)),
        java.util.Map.entry("头等舱候机厅", java.util.List.of(1720.0, 264.0)),
        java.util.Map.entry("FAC_FIRSTAID", java.util.List.of(681.0, 254.0)),
        java.util.Map.entry("急救中心", java.util.List.of(681.0, 254.0)),
        java.util.Map.entry("FAC_NURSERY_MW", java.util.List.of(418.0, 259.0)),
        java.util.Map.entry("FAC_NURSERY_ME", java.util.List.of(1535.0, 263.0)),
        java.util.Map.entry("母婴候机室", java.util.List.of(418.0, 259.0)),
        java.util.Map.entry("FAC_LOUNGE_MW", java.util.List.of(740.0, 318.0)),
        java.util.Map.entry("FAC_LOUNGE_ME", java.util.List.of(1301.0, 318.0)),
        java.util.Map.entry("候机厅", java.util.List.of(740.0, 318.0)),
        java.util.Map.entry("FAC_GUARD_ME", java.util.List.of(1379.0, 318.0)),
        java.util.Map.entry("安全保卫", java.util.List.of(1379.0, 318.0)),
        java.util.Map.entry("FAC_WATER_N1", java.util.List.of(719.0, 138.0)),
        java.util.Map.entry("FAC_WATER_N2", java.util.List.of(1257.0, 149.0)),
        java.util.Map.entry("FAC_ELEV_N1", java.util.List.of(477.0, 179.0)),
        java.util.Map.entry("FAC_ESC_DN_N1", java.util.List.of(515.0, 179.0)),
        java.util.Map.entry("FAC_ESC_UP_N1", java.util.List.of(556.0, 178.0)),
        java.util.Map.entry("FAC_ELEV_N2", java.util.List.of(1502.0, 179.0)),
        java.util.Map.entry("FAC_ESC_UP_N2", java.util.List.of(1543.0, 179.0)),
        java.util.Map.entry("FAC_ESC_DN_N2", java.util.List.of(1581.0, 179.0)),
        java.util.Map.entry("FAC_ELEV_S1", java.util.List.of(821.0, 434.0)),
        java.util.Map.entry("FAC_WC_S1", java.util.List.of(858.0, 434.0)),
        java.util.Map.entry("FAC_ESC_UP_S1", java.util.List.of(896.0, 472.0)),
        java.util.Map.entry("FAC_STAIRS_S1", java.util.List.of(934.0, 470.0)),
        java.util.Map.entry("FAC_ELEV_S2", java.util.List.of(1164.0, 434.0)),
        java.util.Map.entry("FAC_WC_S2", java.util.List.of(1202.0, 434.0)),
        java.util.Map.entry("FAC_ESC_UP_S2", java.util.List.of(1123.0, 472.0)),
        java.util.Map.entry("FAC_STAIRS_S2", java.util.List.of(1164.0, 470.0)),
        java.util.Map.entry("SHOP_FOOD_S1", java.util.List.of(578.0, 407.0)),
        java.util.Map.entry("SHOP_S2", java.util.List.of(1479.0, 403.0)),
        java.util.Map.entry("PET_CHANNEL", java.util.List.of(260.0, 260.0)),
        java.util.Map.entry("宠物托运专用通道", java.util.List.of(260.0, 260.0)),
        java.util.Map.entry("OVERSIZE_PACKING", java.util.List.of(180.0, 318.0)),
        java.util.Map.entry("超规行李打包处", java.util.List.of(180.0, 318.0)),
        java.util.Map.entry("OVERSIZE_CHECKIN", java.util.List.of(310.0, 318.0)),
        java.util.Map.entry("超规行李托运处", java.util.List.of(310.0, 318.0)),
        java.util.Map.entry("OVERSIZE_STORAGE", java.util.List.of(450.0, 318.0)),
        java.util.Map.entry("超规行李寄存处", java.util.List.of(450.0, 318.0)),
        java.util.Map.entry("SPECIAL_SERVICE_DESK", java.util.List.of(1600.0, 318.0)),
        java.util.Map.entry("特殊旅客服务台", java.util.List.of(1600.0, 318.0)),
        java.util.Map.entry("REBOOK_COUNTER", java.util.List.of(1720.0, 318.0)),
        java.util.Map.entry("改签退票柜台", java.util.List.of(1720.0, 318.0)),
        java.util.Map.entry("TRANSFER_COUNTER", java.util.List.of(1830.0, 318.0)),
        java.util.Map.entry("中转柜台", java.util.List.of(1830.0, 318.0)),
        java.util.Map.entry("DUTY_MANAGER_DESK", java.util.List.of(1810.0, 260.0)),
        java.util.Map.entry("值班经理接待点", java.util.List.of(1810.0, 260.0)),
        java.util.Map.entry("MEAL_VOUCHER_POINT", java.util.List.of(1905.0, 260.0)),
        java.util.Map.entry("餐食发放登记处", java.util.List.of(1905.0, 260.0)),
        java.util.Map.entry("SHUTTLE_GATE", java.util.List.of(1820.0, 115.0)),
        java.util.Map.entry("远机位摆渡点", java.util.List.of(1820.0, 115.0)),
        java.util.Map.entry("SHOP_FOOD_MW1", java.util.List.of(380.0, 261.0)),
        java.util.Map.entry("SHOP_MW1", java.util.List.of(536.0, 261.0)),
        java.util.Map.entry("SHOP_MW2", java.util.List.of(745.0, 257.0)),
        java.util.Map.entry("SHOP_ME1", java.util.List.of(1273.0, 257.0)),
        java.util.Map.entry("SHOP_ME2", java.util.List.of(1346.0, 259.0)),
        java.util.Map.entry("SHOP_FOOD_ME1", java.util.List.of(1668.0, 263.0)),
        java.util.Map.entry("FAC_WC_MW1", java.util.List.of(151.0, 258.0)),
        java.util.Map.entry("FAC_WC_MW2", java.util.List.of(578.0, 260.0)),
        java.util.Map.entry("FAC_WC_MW3", java.util.List.of(596.0, 318.0)),
        java.util.Map.entry("FAC_WC_ME1", java.util.List.of(1423.0, 260.0)),
        java.util.Map.entry("FAC_WC_ME2", java.util.List.of(1431.0, 319.0)),
        java.util.Map.entry("FAC_WATER_MW1", java.util.List.of(193.0, 261.0)),
        java.util.Map.entry("FAC_WATER_MW2", java.util.List.of(625.0, 260.0)),
        java.util.Map.entry("FAC_WATER_MW3", java.util.List.of(633.0, 319.0)),
        java.util.Map.entry("FAC_WATER_ME1", java.util.List.of(1470.0, 260.0)),
        java.util.Map.entry("FAC_WATER_ME2", java.util.List.of(1470.0, 319.0)),
        // Legacy test fixture landmarks kept for unit test compatibility
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
        java.util.Map.entry("智能行李测量点B", java.util.List.of(456.0, 2508.0)),
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
    private int minRouteDurationMs = 0;
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
    public int getMinRouteDurationMs() { return minRouteDurationMs; }
    public void setMinRouteDurationMs(int value) { this.minRouteDurationMs = value; }
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
