package com.airport.ai.task;

import com.airport.ai.device.SystemSettingMapper;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.util.Map;

/**
 * 统一空间校验与派单配置源：优先读取数据库 system_settings 中的 validation_baseline.* 配置，
 * 未配置时回退到 application.yml 默认参数，确保 PlanValidationService 与 TaskExecutionOrchestrator 规则一致。
 */
@Component
public class SpatialRuleConfig {
    public static final double HOLDING_ZONE_MAX_Y = 235.0;
    public static final double CHECKIN_HALL_MIN_Y = 341.0;
    private static final ObjectMapper MAPPER = new ObjectMapper();

    @Autowired(required = false)
    private SystemSettingMapper systemSettingMapper;

    @Value("${app.device.fixed-device-strict-zone:true}")
    private boolean defaultFixedDeviceStrictZone = true;

    @Value("${app.device.fixed-max-service-distance:650}")
    private double defaultFixedMaxServiceDistance = 650.0;

    @Value("${app.device.robot-max-service-distance:1600}")
    private double defaultRobotMaxServiceDistance = 1600.0;

    public boolean isFixedDeviceStrictZone() {
        String val = readSetting("validation_baseline.fixedDeviceStrictZone");
        return val != null ? Boolean.parseBoolean(val.trim()) : defaultFixedDeviceStrictZone;
    }

    public double getFixedMaxServiceDistance() {
        String val = readSetting("validation_baseline.fixedMaxServiceDistance");
        if (val != null) {
            try { return Double.parseDouble(val.trim()); } catch (NumberFormatException ignored) {}
        }
        return defaultFixedMaxServiceDistance;
    }

    public double getRobotMaxServiceDistance() {
        String val = readSetting("validation_baseline.robotMaxServiceDistance");
        if (val != null) {
            try { return Double.parseDouble(val.trim()); } catch (NumberFormatException ignored) {}
        }
        return defaultRobotMaxServiceDistance;
    }

    private String readSetting(String key) {
        if (systemSettingMapper == null) return null;
        try {
            String val = systemSettingMapper.findValue(key);
            return (val == null || val.isBlank()) ? null : val;
        } catch (Exception ignored) {
            return null;
        }
    }

    /**
     * 基于 POI 的矩形区域 (boundsJson) 与坐标判定其所属隔离区：
     * - 位于候机区 (y < 235) 或矩形北边与候机区相接相通 (y1 <= 235 且非跨区安检通道) -> 隔离区内
     * - 位于值机区 (y > 341) 或矩形南边与值机区相接相通 (y2 >= 341 且非跨区安检通道) -> 隔离区外
     */
    public static String resolveIsolationZone(Map<String, Object> poi) {
        if (poi == null) return null;
        String code = poi.get("poiCode") == null ? "" : String.valueOf(poi.get("poiCode")).trim().toUpperCase();
        if ("SECURITY_MAIN".equals(code)) return null;

        Object rawBounds = poi.get("boundsJson");
        if (rawBounds != null && !String.valueOf(rawBounds).isBlank()) {
            try {
                JsonNode b = MAPPER.readTree(String.valueOf(rawBounds));
                if (b.has("y1") && b.has("y2")) {
                    double y1 = b.get("y1").asDouble();
                    double y2 = b.get("y2").asDouble();
                    if (y1 <= HOLDING_ZONE_MAX_Y && y2 < CHECKIN_HALL_MIN_Y) return "隔离区内";
                    if (y2 >= CHECKIN_HALL_MIN_Y && y1 > HOLDING_ZONE_MAX_Y) return "隔离区外";
                }
            } catch (Exception ignored) {}
        }

        double py = poi.get("y") instanceof Number n ? n.doubleValue() : -1;
        if (py < 0) return null;
        if (py < HOLDING_ZONE_MAX_Y) return "隔离区内";
        if (py > CHECKIN_HALL_MIN_Y) return "隔离区外";
        return null;
    }
}
