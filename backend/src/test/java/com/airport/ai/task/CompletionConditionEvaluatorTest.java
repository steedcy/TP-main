package com.airport.ai.task;

import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

class CompletionConditionEvaluatorTest {
    @Test
    void explicitFalseMustMatchActualEvenWhenDeviceReportsCompleted() {
        Map<String, Object> step = Map.of("capabilityType", "CAP_NAVIGATION", "completionCondition", "routeGenerated=false");
        assertFalse(CompletionConditionEvaluator.satisfied(step, Map.of("routeGenerated", true, "completed", true)));
        assertTrue(CompletionConditionEvaluator.satisfied(step, Map.of("routeGenerated", false, "completed", true)));
    }

    @Test
    void receiptAndPartialPredicatesCannotAdvanceBusinessStep() {
        Map<String, Object> step = Map.of("capabilityType", "CAP_FLIGHT_UPDATE",
                "completionCondition", "publishStatus=SUCCESS and accepted=true");
        assertFalse(CompletionConditionEvaluator.satisfied(step, Map.of("accepted", true, "completed", true)));
        assertFalse(CompletionConditionEvaluator.satisfied(step, Map.of("publishStatus", "SUCCESS", "accepted", false)));
        assertTrue(CompletionConditionEvaluator.satisfied(step, Map.of("publishStatus", "SUCCESS", "accepted", true)));
    }

    @Test
    void proseStillNeedsCapabilityBusinessResult() {
        Map<String, Object> step = Map.of("capabilityType", "CAP_ESCORT", "completionCondition", "旅客安全抵达目标地点");
        assertFalse(CompletionConditionEvaluator.satisfied(step, Map.of("completed", true)));
        assertTrue(CompletionConditionEvaluator.satisfied(step, Map.of("arrivalStatus", "ARRIVED")));
    }
}
