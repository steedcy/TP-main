package com.airport.ai.simulator;

import org.springframework.stereotype.Component;

import java.time.OffsetDateTime;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

@Component
public class SmartDisplayDriver implements CapabilityDriver {
    private static final Set<String> CONTENT_TYPES = Set.of("TEXT", "IMAGE", "VIDEO", "HTML");
    private static final Set<String> UPDATE_TYPES = Set.of("DELAY", "EARLY", "GATE_CHANGE", "CANCEL");
    private static final Set<String> ROUTE_PREFERENCES = Set.of("SHORTEST", "BARRIER_FREE");

    @Override public String deviceType() { return "SMART_DISPLAY"; }
    @Override public Set<String> capabilities() {
        return Set.of("CAP_INFO_DISPLAY", "CAP_FLIGHT_UPDATE", "CAP_NAVIGATION");
    }

    @Override
    public Map<String, Object> execute(String capabilityType, Map<String, Object> input) {
        return switch (capabilityType) {
            case "CAP_INFO_DISPLAY" -> display(input);
            case "CAP_FLIGHT_UPDATE" -> flightUpdate(input);
            case "CAP_NAVIGATION" -> navigation(input);
            default -> throw new IllegalArgumentException("智慧航显不支持能力 " + capabilityType);
        };
    }

    private Map<String, Object> display(Map<String, Object> input) {
        String type = requiredText(input, "contentType");
        if (!CONTENT_TYPES.contains(type)) throw invalid("contentType必须为TEXT/IMAGE/VIDEO/HTML");
        requiredText(input, "contentData");
        int duration = integer(input, "displayDuration", 5, 300);
        return Map.of("displayStatus", "SUCCESS", "actualDuration", duration, "errorMessage", "");
    }

    private Map<String, Object> flightUpdate(Map<String, Object> input) {
        requiredText(input, "flightNumber");
        String updateType = requiredText(input, "updateType");
        if (!UPDATE_TYPES.contains(updateType)) throw invalid("updateType必须为DELAY/EARLY/GATE_CHANGE/CANCEL");
        requiredText(input, "updateContent");
        integer(input, "displayDuration", 10, 600);
        return Map.of("publishStatus", "SUCCESS", "publishTime", OffsetDateTime.now().toString());
    }

    private Map<String, Object> navigation(Map<String, Object> input) {
        String target = requiredText(input, "targetLocation");
        String preference = String.valueOf(input.getOrDefault("routePreference", "SHORTEST"));
        if (!ROUTE_PREFERENCES.contains(preference)) throw invalid("routePreference必须为SHORTEST/BARRIER_FREE");
        int seed = target.hashCode() & 0x7fffffff;
        Map<String, Object> output = new LinkedHashMap<>();
        output.put("routeGenerated", true);
        output.put("estimatedDistance", 25.0 + seed % 476);
        output.put("estimatedDuration", 30 + seed % 571);
        output.put("waypointCount", 2 + seed % 12);
        return output;
    }

    private String requiredText(Map<String, Object> input, String key) {
        Object value = input.get(key);
        if (value == null || value.toString().isBlank()) throw invalid(key + "不能为空");
        return value.toString();
    }

    private int integer(Map<String, Object> input, String key, int min, int max) {
        Object value = input.get(key);
        if (!(value instanceof Number number)) throw invalid(key + "必须为整数");
        int result = number.intValue();
        if (result != number.doubleValue() || result < min || result > max) {
            throw invalid(key + "范围必须为" + min + "~" + max);
        }
        return result;
    }

    private IllegalArgumentException invalid(String message) { return new IllegalArgumentException(message); }
}
