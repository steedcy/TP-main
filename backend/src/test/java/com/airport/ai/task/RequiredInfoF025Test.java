package com.airport.ai.task;

import org.junit.jupiter.api.Test;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

/** F025.R01/R02：必要信息由系统固定核对，模型不得扩大追问范围。 */
class RequiredInfoF025Test {

    private RequiredInfoGuard.Verdict check(Map<String, Object> scene, Map<String, Object> parsed) {
        return RequiredInfoGuard.check(
                RequiredInfoGuard.requirementsFor("SPECIAL_PASSENGER_SERVICE"), scene, parsed);
    }

    @Test
    void completeSpecialPassengerSceneNeedsOnlyBusinessFields() {
        var verdict = check(Map.of(
                "assistanceType", "WHEELCHAIR",
                "origin", "F2_GATE_A",
                "destination", "F2_SERVICE_POINT"), Map.of());

        assertTrue(verdict.complete());
        assertTrue(verdict.questions().isEmpty());
    }

    @Test
    void parsedOriginAndDestinationCountAsProvided() {
        var verdict = check(Map.of("assistanceType", "WHEELCHAIR"), Map.of(
                "origin", "F2_GATE_A", "destination", "F2_SERVICE_POINT"));

        assertTrue(verdict.complete());
    }

    @Test
    void missingFieldsProduceOnlySystemQuestions() {
        var verdict = check(Map.of(), Map.of());

        assertEquals(List.of("协助类型", "起点", "目的地"), verdict.missing());
        assertEquals(List.of(
                "请补充协助类型（如轮椅、视障或听障陪同）",
                "请补充服务起点",
                "请补充服务目的地"), verdict.questions());
        String questions = String.join("|", verdict.questions());
        for (String forbidden : List.of("姓名", "证件", "身份", "护照", "电话", "机器人", "路线")) {
            assertFalse(questions.contains(forbidden), "不应追问: " + forbidden);
        }
    }

    @Test
    void answeredSystemQuestionSatisfiesOnlyThatRequirement() {
        Map<String, Object> scene = new HashMap<>();
        scene.put("assistanceType", "WHEELCHAIR");
        scene.put("clarificationAnswers", List.of(Map.of(
                "answers", Map.of("请补充服务起点", "F2_GATE_A"))));

        var verdict = check(scene, Map.of());

        assertEquals(List.of("目的地"), verdict.missing());
    }

    @Test
    void anAnswerRedactedToAnIdentityPlaceholderDoesNotCountAsTheRequiredField() {
        String redacted = SceneParamsPrivacyGuard.sanitizeGoal("passengerName=FICTIONAL_CANARY");
        Map<String, Object> scene = Map.of("clarificationAnswers", List.of(Map.of(
                "answers", Map.of("请补充服务起点", redacted))));

        var verdict = check(scene, Map.of());

        assertEquals(List.of("协助类型", "起点", "目的地"), verdict.missing());
    }
}
