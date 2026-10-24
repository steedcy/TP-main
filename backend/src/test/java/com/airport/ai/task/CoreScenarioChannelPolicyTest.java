package com.airport.ai.task;

import com.airport.ai.device.DeviceCapabilityMapper;
import org.junit.jupiter.api.Test;
import java.util.List;
import java.util.Map;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class CoreScenarioChannelPolicyTest {
    @Test
    void flightDisplayRequiresSmartDisplayAndCannotBeCoveredByFlightBoard() {
        assertFalse(CoreScenarioChannelPolicy.matches("FLIGHT_CHANGE_RESPONSE", "CAP_INFO_DISPLAY", "SIMULATOR", "FLIGHT_DELAY_BOARD"));
        assertTrue(CoreScenarioChannelPolicy.matches("FLIGHT_CHANGE_RESPONSE", "CAP_INFO_DISPLAY", "SIMULATOR", "SMART_DISPLAY"));
        assertFalse(CoreScenarioChannelPolicy.matches("FLIGHT_CHANGE_RESPONSE", "CAP_FLIGHT_UPDATE", "SIMULATOR", "SMART_DISPLAY"));
    }

    @Test
    void validationRejectsWrongChannelAndMissingChannelStep() {
        DeviceCapabilityMapper capabilities = mock(DeviceCapabilityMapper.class);
        when(capabilities.existsByCapabilityTypeAndCapabilityStatus(anyString(), eq("ENABLED"))).thenReturn(true);
        PlanValidationService validation = new PlanValidationService(capabilities);
        Map<String, Object> flightBoard = Map.of("deviceTypeCode", "SIMULATOR", "simulatedDeviceType", "FLIGHT_DELAY_BOARD",
                "capabilities", List.of("CAP_FLIGHT_UPDATE", "CAP_INFO_DISPLAY"));
        Map<String, Object> displayStep = Map.of("stepSeq", 1, "stepGoal", "展示变更", "capabilityType", "CAP_INFO_DISPLAY",
                "completionCondition", "展示成功", "inputParams", Map.of());
        PlanValidationResult result = validation.validate(List.of(displayStep), List.of(flightBoard), null, "FLIGHT_CHANGE_RESPONSE");
        assertEquals("FAIL", result.getCapabilityCheckResult());
        validation.requireCoreScenarioCoverage(List.of(displayStep), "FLIGHT_CHANGE_RESPONSE", result);
        assertTrue(result.getErrors().stream().anyMatch(e -> "ERR_REQUIRED_CHANNEL_MISSING".equals(e.getReasonCode())));
    }

    @Test
    void oversizeAndSpecialPlansCannotOmitTheirRequiredActions() {
        PlanValidationService validation = new PlanValidationService(mock(DeviceCapabilityMapper.class));
        PlanValidationResult baggage = new PlanValidationResult();
        validation.requireCoreScenarioCoverage(List.of(Map.of("capabilityType", "CAP_BAGGAGE_MEASURE", "stepSeq", 1)),
                "OVERSIZE_BAGGAGE_HANDLING", baggage);
        assertEquals("FAIL", baggage.getCapabilityCheckResult());
        PlanValidationResult special = new PlanValidationResult();
        validation.requireCoreScenarioCoverage(List.of(Map.of("capabilityType", "CAP_ESCORT", "stepSeq", 1)),
                "SPECIAL_PASSENGER_SERVICE", special);
        assertEquals("FAIL", special.getCapabilityCheckResult());
    }
}
