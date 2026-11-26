package com.airport.ai.demo;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Component;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.List;

/** Immutable V1.5 standard demo dataset; the digest identifies the exact bundled source files. */
@Component
public class DemoDataset {
    public static final String VERSION = "V1.5-DEMO-20261126";
    public static final String GENERATED_AT = "2026-11-26T16:40:00+08:00";
    public static final String CONFIRM_PHRASE = "恢复F2标准演示数据";

    private final JsonNode devices;
    private final JsonNode mapRegions;
    private final JsonNode mapPois;
    private final JsonNode baselines;
    private final JsonNode scenarios;
    private final JsonNode riskRules;
    private final JsonNode validationRules;
    private final String sourceDigest;

    public DemoDataset(ObjectMapper mapper) {
        try {
            byte[] deviceBytes = new ClassPathResource("demo-f2/devices.json").getInputStream().readAllBytes();
            byte[] regionBytes = new ClassPathResource("demo-f2/map-regions.json").getInputStream().readAllBytes();
            byte[] poiBytes = new ClassPathResource("demo-f2/map-pois.json").getInputStream().readAllBytes();
            byte[] baselineBytes = new ClassPathResource("demo-f2/baselines.json").getInputStream().readAllBytes();
            byte[] scenarioBytes = new ClassPathResource("demo-f2/scenarios.json").getInputStream().readAllBytes();
            byte[] riskRuleBytes = new ClassPathResource("demo-f2/risk-rules.json").getInputStream().readAllBytes();
            byte[] validationRuleBytes = new ClassPathResource("demo-f2/validation-rules.json").getInputStream().readAllBytes();

            devices = mapper.readTree(deviceBytes);
            mapRegions = mapper.readTree(regionBytes);
            mapPois = mapper.readTree(poiBytes);
            baselines = mapper.readTree(baselineBytes);
            scenarios = mapper.readTree(scenarioBytes);
            riskRules = mapper.readTree(riskRuleBytes);
            validationRules = mapper.readTree(validationRuleBytes);

            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            for (byte[] bytes : List.of(deviceBytes, regionBytes, poiBytes, baselineBytes, scenarioBytes,
                    riskRuleBytes, validationRuleBytes)) {
                digest.update(bytes);
                digest.update((byte) '\n');
            }
            sourceDigest = HexFormat.of().formatHex(digest.digest());
            if (devices.size() != 20 || mapRegions.size() != 18 || mapPois.size() != 68
                    || baselines.size() != 3 || scenarios.size() != 4 || riskRules.size() != 3) {
                throw new IllegalStateException("V1.5 标准演示数据集条目数不符合预期");
            }
        } catch (Exception ex) {
            throw new IllegalStateException("无法加载 V1.5 标准演示数据集", ex);
        }
    }

    public JsonNode devices() { return devices; }
    public JsonNode mapRegions() { return mapRegions; }
    public JsonNode mapPois() { return mapPois; }
    public JsonNode baselines() { return baselines; }
    public JsonNode scenarios() { return scenarios; }
    public JsonNode riskRules() { return riskRules; }
    public JsonNode validationRules() { return validationRules; }
    public String sourceDigest() { return sourceDigest; }

    public List<String> deviceCodes() {
        return java.util.stream.StreamSupport.stream(devices.spliterator(), false)
                .map(row -> row.path("deviceCode").asText()).toList();
    }

    public static String sha256(String text) {
        try {
            return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256")
                    .digest(text.getBytes(StandardCharsets.UTF_8)));
        } catch (Exception ex) {
            throw new IllegalStateException("摘要计算失败", ex);
        }
    }
}
