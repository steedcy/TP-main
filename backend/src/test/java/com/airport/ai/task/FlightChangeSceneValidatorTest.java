package com.airport.ai.task;

import com.airport.ai.common.BusinessException;
import org.junit.jupiter.api.Test;
import java.util.HashMap;
import java.util.Map;
import static org.junit.jupiter.api.Assertions.*;

class FlightChangeSceneValidatorTest {
    private Map<String, Object> valid() {
        return new HashMap<>(Map.of("eventSource", "MANUAL_FORM", "flightNumber", "TEST81",
                "changeType", "GATE_CHANGE", "originalTime", "2026-10-25T12:00:00",
                "newGate", "F2_TEST_GATE", "changeDescription", "虚构测试登机口变更"));
    }

    @Test
    void validatesConditionalGateAndTimeBeforeTaskCreation() {
        Map<String, Object> gateChange = valid();
        assertDoesNotThrow(() -> FlightChangeSceneValidator.validate("FLIGHT_CHANGE_RESPONSE", gateChange));
        gateChange.remove("newGate");
        assertThrows(BusinessException.class, () -> FlightChangeSceneValidator.validate("FLIGHT_CHANGE_RESPONSE", gateChange));
        Map<String, Object> early = valid();
        early.put("changeType", "EARLY");
        assertThrows(BusinessException.class, () -> FlightChangeSceneValidator.validate("FLIGHT_CHANGE_RESPONSE", early));
        early.put("newTime", "2026-10-25T11:30:00");
        assertDoesNotThrow(() -> FlightChangeSceneValidator.validate("FLIGHT_CHANGE_RESPONSE", early));
    }
}
