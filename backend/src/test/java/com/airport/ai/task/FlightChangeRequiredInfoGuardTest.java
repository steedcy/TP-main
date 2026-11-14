package com.airport.ai.task;

import org.junit.jupiter.api.Test;

import java.util.HashMap;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

class FlightChangeRequiredInfoGuardTest {
    @Test
    void latestCorrectionOverridesOldAnswersAndOriginalSceneValue() {
        Map<String, Object> scene = base("UNKNOWN");
        scene.put("newTime", "2026-11-09T12:30:00");
        String question = "请补充有效的航班变更类型";
        scene.put("clarificationAnswers", java.util.List.of(
                Map.of("answers", Map.of(question, "INVALID")),
                Map.of("answers", Map.of(question, "DELAY")),
                Map.of("answers", Map.of("其他问题", "其他回答"))));
        assertTrue(FlightChangeRequiredInfoGuard.check(scene).complete());
    }

    @Test
    void chineseDelayStillRequiresNewFlightTimeAndSupportsLegacyAnswerMap() {
        Map<String, Object> scene = base("UNKNOWN");
        scene.put("clarificationAnswers", Map.of("请补充有效的航班变更类型", "延误"));
        assertEquals(java.util.List.of("newTime"), FlightChangeRequiredInfoGuard.check(scene).missing());
    }

    private Map<String, Object> base(String changeType) {
        Map<String, Object> scene = new HashMap<>();
        scene.put("flightNumber", "CA1234");
        scene.put("changeType", changeType);
        scene.put("originalTime", "2026-11-09T12:00:00");
        scene.put("changeDescription", "虚构航班变更说明");
        return scene;
    }

    @Test
    void completeGateChangeDoesNotRequireOperatorToChooseRobotOrRoute() {
        Map<String, Object> scene = base("GATE_CHANGE");
        scene.put("newGate", "F2_TEST_GATE");
        scene.put("newTime", ""); // Optional for a gate change.
        scene.put("robotId", "");
        scene.put("routeCode", "");

        var verdict = FlightChangeRequiredInfoGuard.check(scene);

        assertTrue(verdict.complete());
        assertTrue(verdict.questions().isEmpty());
    }

    @Test
    void delayAndEarlyRequireNewTime() {
        for (String type : new String[]{"DELAY", "EARLY"}) {
            var missing = FlightChangeRequiredInfoGuard.check(base(type));
            assertFalse(missing.complete(), type);
            assertEquals(java.util.List.of("newTime"), missing.missing());

            Map<String, Object> complete = base(type);
            complete.put("newTime", "2026-11-09T12:30:00");
            assertTrue(FlightChangeRequiredInfoGuard.check(complete).complete(), type);
        }
    }

    @Test
    void gateChangeRequiresNewGateButCancelDoesNotRequireNewTimeOrGate() {
        assertEquals(java.util.List.of("newGate"), FlightChangeRequiredInfoGuard.check(base("GATE_CHANGE")).missing());
        assertTrue(FlightChangeRequiredInfoGuard.check(base("CANCEL")).complete());
    }

    @Test
    void missingOrInvalidBaseFieldsAreAskedWithoutDeviceOrRouteDetails() {
        var missing = FlightChangeRequiredInfoGuard.check(Map.of("changeType", "DELAY"));
        assertEquals(java.util.List.of("flightNumber", "originalTime", "changeDescription", "newTime"), missing.missing());
        assertEquals(4, missing.questions().size());
        assertTrue(missing.questions().stream().noneMatch(q -> q.contains("机器人") || q.contains("路线")));

        Map<String, Object> invalid = base("UNKNOWN");
        assertFalse(FlightChangeRequiredInfoGuard.check(invalid).complete());
    }

    @Test
    void whitespaceDoesNotSatisfyRequiredFields() {
        Map<String, Object> scene = base("GATE_CHANGE");
        scene.put("newGate", "  ");
        assertEquals(java.util.List.of("newGate"), FlightChangeRequiredInfoGuard.check(scene).missing());
    }
}
