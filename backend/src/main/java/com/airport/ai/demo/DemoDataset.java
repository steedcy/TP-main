package com.airport.ai.demo;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Component;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.List;

/** Immutable fictional F2 data; the digest identifies the exact bundled source files. */
@Component
public class DemoDataset {
    public static final String VERSION = "F2-DEMO-20261024";
    public static final String GENERATED_AT = "2026-10-24T21:10:00+08:00";
    public static final String CONFIRM_PHRASE = "恢复F2标准演示数据";

    private final JsonNode devices;
    private final JsonNode baselines;
    private final JsonNode scenarios;
    private final String sourceDigest;

    public DemoDataset(ObjectMapper mapper) {
        try {
            byte[] deviceBytes = new ClassPathResource("demo-f2/devices.json").getInputStream().readAllBytes();
            byte[] baselineBytes = new ClassPathResource("demo-f2/baselines.json").getInputStream().readAllBytes();
            byte[] scenarioBytes = new ClassPathResource("demo-f2/scenarios.json").getInputStream().readAllBytes();
            devices = mapper.readTree(deviceBytes);
            baselines = mapper.readTree(baselineBytes);
            scenarios = mapper.readTree(scenarioBytes);
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            for (byte[] bytes : List.of(deviceBytes, baselineBytes, scenarioBytes)) {
                digest.update(bytes);
                digest.update((byte) '\n');
            }
            sourceDigest = HexFormat.of().formatHex(digest.digest());
            if (devices.size() != 6 || baselines.size() != 3 || scenarios.size() != 3)
                throw new IllegalStateException("F2 演示数据集条目数不符合预期");
        } catch (Exception ex) {
            throw new IllegalStateException("无法加载 F2 标准演示数据集", ex);
        }
    }

    public JsonNode devices() { return devices; }
    public JsonNode baselines() { return baselines; }
    public JsonNode scenarios() { return scenarios; }
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
