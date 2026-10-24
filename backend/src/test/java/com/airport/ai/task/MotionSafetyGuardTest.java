package com.airport.ai.task;

import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class MotionSafetyGuardTest {
    @Test
    void outputWaypointCountDoesNotBlockAValidNavigationPlan() {
        assertTrue(MotionSafetyGuard.detect(Map.of(
                "capabilityType", "CAP_NAVIGATION",
                "completionCondition", "routeGenerated=true and waypointCount reported",
                "inputParams", Map.of("targetLocation", "F2_TEST_GATE"))).isEmpty());
    }

    @Test
    void devicePathPointInputsAndCommandsRemainBlocked() {
        assertFalse(MotionSafetyGuard.detect(Map.of(
                "capabilityType", "CAP_NAVIGATION",
                "inputParams", Map.of("waypointList", "A,B"))).isEmpty());
        assertFalse(MotionSafetyGuard.detect(Map.of(
                "capabilityType", "CAP_NAVIGATION",
                "completionCondition", "set speed=5" )).isEmpty());
    }
}
