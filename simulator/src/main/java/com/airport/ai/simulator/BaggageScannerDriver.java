package com.airport.ai.simulator;

import org.springframework.stereotype.Component;

import java.time.OffsetDateTime;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

@Component
public class BaggageScannerDriver implements CapabilityDriver {
    private final SimulatorProperties properties;
    public BaggageScannerDriver(SimulatorProperties properties) { this.properties = properties; }

    @Override public String deviceType() { return "BAGGAGE_SCANNER"; }
    @Override public Set<String> capabilities() { return Set.of("CAP_BAGGAGE_MEASURE", "CAP_OVERSIZE_ALERT"); }

    @Override
    public Map<String, Object> execute(String capabilityType, Map<String, Object> input) {
        return switch (capabilityType) {
            case "CAP_BAGGAGE_MEASURE" -> measure(input);
            case "CAP_OVERSIZE_ALERT" -> alert(input);
            default -> throw new IllegalArgumentException("行李测量设备不支持能力 " + capabilityType);
        };
    }

    private Map<String, Object> measure(Map<String, Object> input) {
        String mode = required(input, "measureMode");
        if (!Set.of("AUTO", "MANUAL").contains(mode)) throw new IllegalArgumentException("measureMode必须为AUTO/MANUAL");
        range(input, "timeout", 10, 60);
        double length = properties.getBaggageLengthCm();
        double width = properties.getBaggageWidthCm();
        double height = properties.getBaggageHeightCm();
        double weight = properties.getBaggageWeightKg();
        boolean oversize = length + width + height > 158 || weight > 32;
        Map<String, Object> result = new java.util.LinkedHashMap<>(Map.of("length", length, "width", width, "height", height, "weight", weight,
                "isOversize", oversize, "measureStatus", "SUCCESS"));
        try { result.put("baggageInfo", new com.fasterxml.jackson.databind.ObjectMapper().writeValueAsString(result)); }
        catch (Exception ex) { throw new IllegalStateException("行李测量结果编码失败", ex); }
        return result;
    }

    private Map<String, Object> alert(Map<String, Object> input) {
        if (input.get("baggageInfo") instanceof String text) {
            try {
                input = new java.util.LinkedHashMap<>(input);
                input.put("baggageInfo", new com.fasterxml.jackson.databind.ObjectMapper().readValue(text, Map.class));
            } catch (Exception ex) { throw new IllegalArgumentException("baggageInfo不是有效JSON对象"); }
        }
        if (!(input.get("baggageInfo") instanceof Map<?, ?> baggageInfo)) throw new IllegalArgumentException("baggageInfo必须为对象");
        for (String field : Set.of("length", "width", "height", "weight")) {
            Object value = baggageInfo.get(field);
            if (!(value instanceof Number number) || !Double.isFinite(number.doubleValue()) || number.doubleValue() < 0) {
                throw new IllegalArgumentException("baggageInfo." + field + "必须为非负数");
            }
        }
        String level = required(input, "alertLevel");
        if (!Set.of("WARNING", "ERROR").contains(level)) throw new IllegalArgumentException("alertLevel必须为WARNING/ERROR");
        if (input.containsKey("passengerInfo") && !(input.get("passengerInfo") instanceof Map<?, ?>)) {
            throw new IllegalArgumentException("passengerInfo必须为对象");
        }
        return Map.of("alertId", "ALERT-" + UUID.randomUUID(), "reportStatus", "SUCCESS",
                "reportTime", OffsetDateTime.now().toString());
    }

    private String required(Map<String, Object> input, String field) {
        Object value = input.get(field);
        if (value == null || value.toString().isBlank()) throw new IllegalArgumentException(field + "不能为空");
        return value.toString();
    }

    private int range(Map<String, Object> input, String field, int min, int max) {
        Object value = input.get(field);
        if (!(value instanceof Number number) || number.doubleValue() != number.intValue()
                || number.intValue() < min || number.intValue() > max) {
            throw new IllegalArgumentException(field + "范围必须为" + min + "~" + max);
        }
        return number.intValue();
    }
}
