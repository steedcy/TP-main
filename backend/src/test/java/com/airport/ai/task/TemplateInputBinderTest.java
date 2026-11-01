package com.airport.ai.task;

import org.junit.jupiter.api.Test;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

/** DEF-S3-085 / TC-025.S2：基线降级的模板输入取值优先级为 显式场景参数 > 目标理解解析值 > 模板默认值。 */
class TemplateInputBinderTest {
    // 与预置“特殊旅客服务”模板同形：targetLocation 有默认值 F2_TEST_GATE，数值参数有默认值
    private static final String INPUTS = "["
            + "{\"name\":\"assistanceType\",\"type\":\"String\",\"required\":true,\"defaultValue\":\"WHEELCHAIR\"},"
            + "{\"name\":\"targetLocation\",\"type\":\"String\",\"required\":true,\"defaultValue\":\"F2_TEST_GATE\"},"
            + "{\"name\":\"repeatCount\",\"type\":\"Integer\",\"required\":true,\"defaultValue\":\"1\"}]";

    private TemplateInputBinder.Result bind(Map<String, Object> scene, Map<String, Object> parsed) throws Exception {
        return TemplateInputBinder.bind(INPUTS, scene, parsed);
    }

    @Test
    void parsedDestinationReplacesTheTemplateDefaultWhenNoExplicitValueWasGiven() throws Exception {
        // GPT 复现：sceneParams 为空，目标理解解析出 destination=F2_SERVICE_POINT
        var r = bind(Map.of(), Map.of("destination", "F2_SERVICE_POINT"));
        assertEquals("F2_SERVICE_POINT", r.values().get("targetLocation"));
        assertEquals(List.of("targetLocation"), r.fromParsedGoal());
        assertTrue(r.defaultedLocations().isEmpty(), "已有解析值，不算套用默认地点");
    }

    @Test
    void explicitSceneParameterStillWinsOverTheParsedValue() throws Exception {
        var r = bind(Map.of("targetLocation", "GATE_B7"), Map.of("destination", "F2_SERVICE_POINT"));
        assertEquals("GATE_B7", r.values().get("targetLocation"));
        assertTrue(r.fromParsedGoal().isEmpty());
        assertTrue(r.defaultedLocations().isEmpty());
    }

    @Test
    void blankExplicitValueIsTreatedAsMissingSoTheParsedValueIsUsed() throws Exception {
        for (String blank : new String[]{"", "   "}) {
            var scene = new HashMap<String, Object>();
            scene.put("targetLocation", blank);
            assertEquals("F2_SERVICE_POINT", bind(scene, Map.of("destination", "F2_SERVICE_POINT")).values().get("targetLocation"));
        }
        var nulled = new HashMap<String, Object>();
        nulled.put("targetLocation", null);
        assertEquals("F2_SERVICE_POINT", bind(nulled, Map.of("destination", "F2_SERVICE_POINT")).values().get("targetLocation"));
    }

    @Test
    void missingEverywhereFallsBackToTheDefaultButIsReportedNotSilent() throws Exception {
        for (Map<String, Object> parsed : List.<Map<String, Object>>of(Map.of(), new HashMap<>() {{ put("destination", null); }},
                Map.of("destination", " "), Map.of("origin", "A"))) {
            var r = bind(Map.of(), parsed);
            assertEquals("F2_TEST_GATE", r.values().get("targetLocation"));
            assertEquals(List.of("targetLocation"), r.defaultedLocations(), "套用默认地点必须留下记录: " + parsed);
        }
        var noParsedAtAll = TemplateInputBinder.bind(INPUTS, Map.of(), null);
        assertEquals("F2_TEST_GATE", noParsedAtAll.values().get("targetLocation"));
        assertEquals(List.of("targetLocation"), noParsedAtAll.defaultedLocations());
    }

    @Test
    void nonLocationInputsKeepTheirDefaultsAndAreNotReportedAsDefaultedLocations() throws Exception {
        var r = bind(Map.of(), Map.of("destination", "F2_SERVICE_POINT"));
        assertEquals("WHEELCHAIR", r.values().get("assistanceType"));
        assertEquals(1, r.values().get("repeatCount"));
        assertFalse(r.defaultedLocations().contains("assistanceType"));
    }

    @Test
    void originMapsToOriginLocationInputsButNeverToTheDestinationInput() throws Exception {
        String inputs = "[{\"name\":\"originLocation\",\"type\":\"String\",\"required\":true,\"defaultValue\":\"F2_HALL\"},"
                + "{\"name\":\"targetLocation\",\"type\":\"String\",\"required\":true,\"defaultValue\":\"F2_TEST_GATE\"}]";
        var r = TemplateInputBinder.bind(inputs, Map.of(), Map.of("origin", "F2_ENTRANCE", "destination", "F2_SERVICE_POINT"));
        assertEquals("F2_ENTRANCE", r.values().get("originLocation"));
        assertEquals("F2_SERVICE_POINT", r.values().get("targetLocation"));
    }

    @Test
    void parsedValueIsTrimmedAndGoesThroughTheSameTypeValidation() throws Exception {
        assertEquals("F2_SERVICE_POINT", bind(Map.of(), Map.of("destination", "  F2_SERVICE_POINT  ")).values().get("targetLocation"));
        // 数值型模板输入收到不合法值仍被拒（沿用 ParameterValues 的校验）
        assertThrows(IllegalArgumentException.class, () -> bind(Map.of("repeatCount", "abc"), Map.of()));
    }

    @Test
    void requiredInputWithNeitherValueNorDefaultStillFails() {
        String inputs = "[{\"name\":\"targetLocation\",\"type\":\"String\",\"required\":true}]";
        assertThrows(IllegalArgumentException.class, () -> TemplateInputBinder.bind(inputs, Map.of(), Map.of()));
    }
}
