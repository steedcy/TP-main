package com.airport.ai.simulator;

import org.springframework.stereotype.Component;

import java.time.OffsetDateTime;
import java.util.Map;
import java.util.Set;

@Component
public class FlightDelayBoardDriver implements CapabilityDriver {
    @Override public String deviceType() { return "FLIGHT_DELAY_BOARD"; }
    @Override public Set<String> capabilities() { return Set.of("CAP_FLIGHT_UPDATE", "CAP_INFO_DISPLAY"); }

    @Override
    public Map<String, Object> execute(String capabilityType, Map<String, Object> input) {
        if ("CAP_FLIGHT_UPDATE".equals(capabilityType)) {
            required(input, "flightNumber");
            String updateType = required(input, "updateType");
            if (!Set.of("DELAY", "GATE_CHANGE", "CANCEL").contains(updateType)) throw new IllegalArgumentException("updateType取值非法");
            required(input, "updateContent");
            range(input, "displayDuration", 10, 600);
            return Map.of("publishStatus", "SUCCESS", "publishTime", OffsetDateTime.now().toString());
        }
        if ("CAP_INFO_DISPLAY".equals(capabilityType)) {
            String type = required(input, "contentType");
            if (!Set.of("TEXT", "IMAGE", "VIDEO", "HTML").contains(type)) throw new IllegalArgumentException("contentType取值非法");
            required(input, "contentData");
            int duration = range(input, "displayDuration", 5, 300);
            return Map.of("displayStatus", "SUCCESS", "actualDuration", duration, "errorMessage", "");
        }
        throw new IllegalArgumentException("航延屏不支持能力 " + capabilityType);
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
