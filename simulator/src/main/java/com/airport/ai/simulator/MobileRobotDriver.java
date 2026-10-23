package com.airport.ai.simulator;

import org.springframework.stereotype.Component;

import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Set;

@Component
public class MobileRobotDriver implements CapabilityDriver {
    @org.springframework.beans.factory.annotation.Autowired
    private SimulatorProperties properties = new SimulatorProperties();
    @Override public String deviceType() { return "MOBILE_ROBOT"; }
    @Override public Set<String> capabilities() { return Set.of("CAP_NAVIGATION", "CAP_ESCORT", "CAP_NOTIFICATION", "CAP_INFO_DISPLAY"); }

    @Override
    public Map<String, Object> execute(String capabilityType, Map<String, Object> input) {
        return switch (capabilityType) {
            case "CAP_NAVIGATION" -> navigation(input);
            case "CAP_ESCORT" -> escort(input);
            case "CAP_NOTIFICATION" -> notification(input);
            case "CAP_INFO_DISPLAY" -> display(input);
            default -> throw new IllegalArgumentException("移动服务机器人不支持能力 " + capabilityType);
        };
    }

    @Override
    public List<SimulatorProtocol.Location> routeLocations(String capabilityType, Map<String, Object> input,
                                                           SimulatorProtocol.Location current, Map<String, Object> output) {
        if (!Set.of("CAP_NAVIGATION", "CAP_ESCORT").contains(capabilityType)) return List.of();
        String target = required(input, "targetLocation");
        var point=properties.getLandmarks().get(target);
        if (point==null || point.size()!=2) throw new IllegalArgumentException("目标位置未标定: " + target);
        double targetX=point.get(0), targetY=point.get(1);
        if (targetX<0 || targetX>1260 || targetY<0 || targetY>6895) throw new IllegalArgumentException("目标坐标超出F2底图");
        List<SimulatorProtocol.Location> path = new ArrayList<>();
        for (int i = 1; i <= 4; i++) {
            double ratio = i / 4.0;
            path.add(new SimulatorProtocol.Location(
                    java.math.BigDecimal.valueOf(current.x().doubleValue() + (targetX - current.x().doubleValue()) * ratio),
                    java.math.BigDecimal.valueOf(current.y().doubleValue() + (targetY - current.y().doubleValue()) * ratio),
                    current.zone()));
        }
        return path;
    }

    private Map<String, Object> navigation(Map<String, Object> input) {
        String target = required(input, "targetLocation");
        String preference = String.valueOf(input.getOrDefault("routePreference", "SHORTEST"));
        if (!Set.of("SHORTEST", "BARRIER_FREE").contains(preference)) throw new IllegalArgumentException("routePreference取值非法");
        int seed = target.hashCode() & 0x7fffffff;
        return Map.of("routeGenerated", true, "estimatedDistance", 25.0 + seed % 476,
                "estimatedDuration", 30 + seed % 571, "waypointCount", 2 + seed % 12);
    }

    private Map<String, Object> escort(Map<String, Object> input) {
        required(input, "targetLocation");
        String mode = required(input, "escortMode");
        if (!Set.of("LEAD", "FOLLOW").contains(mode)) throw new IllegalArgumentException("escortMode必须为LEAD/FOLLOW");
        int duration = range(input, "maxDuration", 60, 1800);
        return Map.of("arrivalStatus", "ARRIVED", "actualDistance", 85.2, "actualDuration", Math.min(420, duration));
    }

    private Map<String, Object> notification(Map<String, Object> input) {
        String type = required(input, "notificationType");
        if (!Set.of("VOICE", "TEXT", "BOTH").contains(type)) throw new IllegalArgumentException("notificationType取值非法");
        required(input, "notificationContent");
        int repeats = range(input, "repeatCount", 1, 5);
        return Map.of("notificationStatus", "SUCCESS", "actualRepeatCount", repeats);
    }

    private Map<String, Object> display(Map<String, Object> input) {
        String type = required(input, "contentType");
        if (!Set.of("TEXT", "IMAGE", "VIDEO", "HTML").contains(type)) throw new IllegalArgumentException("contentType取值非法");
        required(input, "contentData");
        int duration = range(input, "displayDuration", 5, 300);
        return Map.of("displayStatus", "SUCCESS", "actualDuration", duration, "errorMessage", "");
    }

    private String required(Map<String, Object> input, String field) {
        Object value = input.get(field);
        if (value == null || value.toString().isBlank()) throw new IllegalArgumentException(field + "不能为空");
        return value.toString();
    }
    private int range(Map<String, Object> input, String field, int min, int max) {
        Object value = input.get(field);
        if (!(value instanceof Number n) || n.doubleValue() != n.intValue() || n.intValue() < min || n.intValue() > max)
            throw new IllegalArgumentException(field + "范围必须为" + min + "~" + max);
        return n.intValue();
    }
}
