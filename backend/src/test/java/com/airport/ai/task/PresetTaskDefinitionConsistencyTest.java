package com.airport.ai.task;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import static org.junit.jupiter.api.Assertions.*;

/**
 * DEF-S3-069 / SRS_F013.R03、F024.R04：预置任务定义允许的能力必须覆盖核心场景要求的全部能力，
 * 否则按定义约束校验时，必需渠道的步骤会被判定超出任务定义。
 * 迁移脚本与演示复位种子（scenarios.json）两处来源都要满足。
 */
class PresetTaskDefinitionConsistencyTest {
    private static final ObjectMapper JSON = new ObjectMapper();

    // 核心场景计划必须含的能力，与 PlanValidationService.requireCoreScenarioCoverage 保持一致
    private static final Map<String, List<String>> REQUIRED = Map.of(
            "OVERSIZE_BAGGAGE_HANDLING", List.of("CAP_BAGGAGE_MEASURE", "CAP_OVERSIZE_ALERT", "CAP_INFO_DISPLAY", "CAP_NAVIGATION"),
            "SPECIAL_PASSENGER_SERVICE", List.of("CAP_INFO_DISPLAY", "CAP_NOTIFICATION", "CAP_ESCORT"),
            "FLIGHT_CHANGE_RESPONSE", List.of("CAP_FLIGHT_UPDATE", "CAP_INFO_DISPLAY"));

    private static String resource(String path) throws Exception {
        try (InputStream in = PresetTaskDefinitionConsistencyTest.class.getResourceAsStream(path)) {
            assertNotNull(in, path);
            return new String(in.readAllBytes(), StandardCharsets.UTF_8);
        }
    }

    private static List<String> list(String json) throws Exception {
        List<String> out = new ArrayList<>();
        JSON.readTree(json).forEach(n -> out.add(n.asText()));
        return out;
    }

    @Test
    void demoSeedAllowsEveryCapabilityTheCoreScenarioRequires() throws Exception {
        JsonNode scenarios = JSON.readTree(resource("/demo-f2/scenarios.json"));
        int checked = 0;
        for (JsonNode scenario : scenarios) {
            String code = scenario.path("definitionCode").asText();
            List<String> required = REQUIRED.get(code);
            if (required == null) continue;
            List<String> allowed = new ArrayList<>();
            scenario.path("availableCapabilityTypes").forEach(n -> allowed.add(n.asText()));
            assertTrue(allowed.containsAll(required), code + " 种子允许 " + allowed + " 缺 " + required);
            checked++;
        }
        assertEquals(3, checked, "三类核心场景都应被检查到");
    }

    @Test
    void migrationsLeaveTheOversizeDefinitionAllowingTheDisplayChannel() throws Exception {
        String v11 = resource("/db/migration/V11__task_definitions.sql");
        Matcher m = Pattern.compile("\\('OVERSIZE_BAGGAGE_HANDLING'.*?'(\\[\"CAP_[^']*\\])'", Pattern.DOTALL).matcher(v11);
        assertTrue(m.find());
        // V11 里第一个以 [\"CAP_ 开头的 JSON 数组是 scene_params 之后的 available_capability_types
        List<String> original = list(m.group(1));
        assertFalse(original.contains("CAP_INFO_DISPLAY"), "V11 原始值缺少 CAP_INFO_DISPLAY，这是 DEF-S3-069 的成因");

        String v25 = resource("/db/migration/V25__oversize_baggage_allows_info_display.sql");
        Matcher fix = Pattern.compile("available_capability_types = '(\\[[^']*\\])'").matcher(v25);
        assertTrue(fix.find());
        List<String> fixed = list(fix.group(1));
        assertTrue(fixed.containsAll(REQUIRED.get("OVERSIZE_BAGGAGE_HANDLING")), "V25 修正后的允许能力 " + fixed);
        assertTrue(fixed.containsAll(original), "不应丢掉原有允许能力");
        assertTrue(v25.contains("definition_code = 'OVERSIZE_BAGGAGE_HANDLING'") && v25.contains("is_preset = TRUE"),
                "只改预置超规行李定义");
    }

    @Test
    void otherPresetDefinitionsWereAlreadyConsistent() throws Exception {
        String v11 = resource("/db/migration/V11__task_definitions.sql");
        for (String code : List.of("SPECIAL_PASSENGER_SERVICE", "FLIGHT_CHANGE_RESPONSE")) {
            Matcher m = Pattern.compile("\\('" + code + "'.*?'(\\[\"CAP_[^']*\\])'", Pattern.DOTALL).matcher(v11);
            assertTrue(m.find(), code);
            assertTrue(list(m.group(1)).containsAll(REQUIRED.get(code)), code + " " + list(m.group(1)));
        }
    }
}
