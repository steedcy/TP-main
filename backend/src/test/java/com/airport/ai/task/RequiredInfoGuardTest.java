package com.airport.ai.task;

import com.airport.ai.taskdef.TaskDefinition;
import org.junit.jupiter.api.Test;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

/**
 * DEF-S3-003/004/005：必要信息由系统按任务族核对，已提供的不再追问，缺失时只问缺的几项，
 * 不问旅客身份、机器人ID、路线编码等系统自己决定的内容。
 */
class RequiredInfoGuardTest {

    private RequiredInfoGuard.Verdict check(String family, Map<String, Object> scene, Map<String, Object> parsed) {
        return RequiredInfoGuard.check(RequiredInfoGuard.requirementsFor(family, null), scene, parsed);
    }

    // ---- DEF-S3-003：非超规路径/超规路径已提交 baggageLocation 不再被追问 ----
    @Test
    void submittedBaggageLocationIsNeverAskedAgain() {
        var v = check("OVERSIZE_BAGGAGE_HANDLING", Map.of("baggageLocation", "F2_BAGGAGE_POINT"), Map.of());
        assertTrue(v.complete());
        assertTrue(v.questions().isEmpty());
    }

    @Test
    void missingBaggageLocationIsAskedAsOneSystemQuestion() {
        for (Map<String, Object> scene : List.<Map<String, Object>>of(Map.of(), Map.of("baggageLocation", ""),
                Map.of("baggageLocation", "   "))) {
            var v = check("OVERSIZE_BAGGAGE_HANDLING", scene, Map.of());
            assertFalse(v.complete(), scene.toString());
            assertEquals(List.of("请补充行李当前所在位置"), v.questions());
        }
    }

    // ---- DEF-S3-004：特殊旅客只检查协助类型、起点、目的地，不问身份 ----
    @Test
    void specialPassengerNeedsOnlyAssistanceTypeOriginAndDestination() {
        var scene = Map.<String, Object>of("assistanceType", "WHEELCHAIR", "origin", "F2_GATE_A", "destination", "F2_SERVICE_POINT");
        assertTrue(check("SPECIAL_PASSENGER_SERVICE", scene, Map.of()).complete());
    }

    @Test
    void parsedOriginAndDestinationFromTheGoalCountAsProvided() {
        var scene = Map.<String, Object>of("assistanceType", "WHEELCHAIR");
        var parsed = Map.<String, Object>of("origin", "F2_GATE_A", "destination", "F2_SERVICE_POINT");
        assertTrue(check("SPECIAL_PASSENGER_SERVICE", scene, parsed).complete());
        var half = check("SPECIAL_PASSENGER_SERVICE", scene, Map.of("origin", "F2_GATE_A"));
        assertEquals(List.of("目的地"), half.missing());
    }

    @Test
    void specialPassengerQuestionsNeverAskForIdentityOrDevices() {
        var v = check("SPECIAL_PASSENGER_SERVICE", Map.of(), Map.of());
        assertEquals(List.of("协助类型", "起点", "目的地"), v.missing());
        String all = String.join("|", v.questions());
        for (String forbidden : new String[]{"姓名", "证件", "身份", "护照", "电话", "服务编号", "机器人", "路线"}) {
            assertFalse(all.contains(forbidden), "不应追问: " + forbidden);
        }
    }

    // ---- DEF-S3-005：航班变更只要航班号与变更内容，不问机器人ID/路线编码 ----
    @Test
    void flightChangeWithFlightNumberAndChangeFactsIsCompleteWithoutDeviceOrRouteInfo() {
        var scene = Map.<String, Object>of("flightNumber", "CA1234", "changeType", "GATE_CHANGE",
                "newGate", "B7", "changeDescription", "登机口由A1改为B7");
        var v = check("FLIGHT_CHANGE_RESPONSE", scene, Map.of());
        assertTrue(v.complete());
    }

    @Test
    void flightChangeQuestionsNeverAskForRobotIdOrRoute() {
        var v = check("FLIGHT_CHANGE_RESPONSE", Map.of(), Map.of());
        assertEquals(List.of("航班号", "变更内容"), v.missing());
        String all = String.join("|", v.questions());
        for (String forbidden : new String[]{"机器人", "路线", "设备", "ID", "编码"}) {
            assertFalse(all.contains(forbidden), "不应追问: " + forbidden);
        }
    }

    // ---- 操作员已回答系统问题后不再重复追问 ----
    @Test
    void anAnsweredSystemQuestionIsNotAskedAgain() {
        Map<String, Object> scene = new HashMap<>();
        scene.put("clarificationAnswers", List.of(Map.of("questions", List.of("请补充行李当前所在位置"),
                "answers", Map.of("请补充行李当前所在位置", "F2_BAGGAGE_POINT"))));
        assertTrue(check("OVERSIZE_BAGGAGE_HANDLING", scene, Map.of()).complete());
        // 只回答了一项，另一项仍会被问
        scene.put("clarificationAnswers", List.of(Map.of("answers", Map.of("请补充协助类型（如轮椅、视障或听障陪同）", "WHEELCHAIR"))));
        var v = check("SPECIAL_PASSENGER_SERVICE", scene, Map.of());
        assertEquals(List.of("起点", "目的地"), v.missing());
    }

    @Test
    void blankClarificationAnswerDoesNotCount() {
        Map<String, Object> scene = new HashMap<>();
        scene.put("clarificationAnswers", List.of(Map.of("answers", Map.of("请补充行李当前所在位置", "  "))));
        assertFalse(check("OVERSIZE_BAGGAGE_HANDLING", scene, Map.of()).complete());
    }

    // ---- 无法核对的情形：返回 null，沿用模型判断 ----
    @Test
    void openEndedGoalsWithoutAFamilyCannotBeChecked() {
        assertNull(RequiredInfoGuard.requirementsFor(null, null));
        assertNull(RequiredInfoGuard.requirementsFor("  ", null));
        assertNull(RequiredInfoGuard.check(null, Map.of(), Map.of()));
        assertNull(RequiredInfoGuard.requirementsFor("UNKNOWN_FAMILY", null), "未知任务族且无定义，无法核对");
    }

    @Test
    void extensionDefinitionsUseTheirDeclaredRequiredSceneParams() {
        TaskDefinition def = new TaskDefinition();
        def.setSceneParams("[{\"name\":\"sampleLocation\",\"type\":\"String\",\"required\":true},"
                + "{\"name\":\"note\",\"type\":\"String\",\"required\":false}]");
        var req = RequiredInfoGuard.requirementsFor("MY_EXT", def);
        assertEquals(1, req.size(), "只有必填项才是必要信息");
        assertFalse(RequiredInfoGuard.check(req, Map.of(), Map.of()).complete());
        assertTrue(RequiredInfoGuard.check(req, Map.of("sampleLocation", "A"), Map.of()).complete());
        assertTrue(RequiredInfoGuard.check(RequiredInfoGuard.requirementsFor("MY_EXT", brokenDefinition()), Map.of(), Map.of()) == null);
    }

    private TaskDefinition brokenDefinition() {
        TaskDefinition d = new TaskDefinition();
        d.setSceneParams("not json");
        return d;
    }

    @Test
    void nullSceneAndParsedAreTreatedAsEmpty() {
        assertFalse(check("OVERSIZE_BAGGAGE_HANDLING", null, null).complete());
    }
}
