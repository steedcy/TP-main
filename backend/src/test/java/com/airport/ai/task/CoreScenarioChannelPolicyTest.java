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
    void missingPlannedChannelStillFailsEvenWhenAnotherPublisherExists() {
        DeviceCapabilityMapper capabilities = mock(DeviceCapabilityMapper.class);
        when(capabilities.existsByCapabilityTypeAndCapabilityStatus(anyString(), eq("ENABLED"))).thenReturn(true);
        PlanValidationService validation = new PlanValidationService(capabilities);
        Map<String, Object> flightBoard = Map.of("deviceTypeCode", "SIMULATOR", "simulatedDeviceType", "FLIGHT_DELAY_BOARD",
                "capabilities", List.of("CAP_FLIGHT_UPDATE", "CAP_INFO_DISPLAY"));
        Map<String, Object> displayStep = Map.of("stepSeq", 1, "stepGoal", "展示变更", "capabilityType", "CAP_INFO_DISPLAY",
                "completionCondition", "展示成功", "inputParams", Map.of());
        PlanValidationResult result = validation.validate(List.of(displayStep), List.of(flightBoard), null, "FLIGHT_CHANGE_RESPONSE");
        assertTrue(result.isAllPassed(), "错误物理渠道不能承接展示，但可保留为待标记未覆盖的步骤");
        validation.requireCoreScenarioCoverage(List.of(displayStep), "FLIGHT_CHANGE_RESPONSE", result);
        assertEquals("FAIL", result.getCapabilityCheckResult());
        assertTrue(result.getErrors().stream().anyMatch(e -> "ERR_REQUIRED_CHANNEL_MISSING".equals(e.getReasonCode())));
    }

    @Test
    void flightPlanKeepsUnavailableChannelsOnlyWhenARealPublicationChannelExists() {
        DeviceCapabilityMapper capabilities = mock(DeviceCapabilityMapper.class);
        when(capabilities.existsByCapabilityTypeAndCapabilityStatus(anyString(), eq("ENABLED"))).thenReturn(true);
        PlanValidationService validation = new PlanValidationService(capabilities);
        List<Map<String, Object>> steps = List.of(
                flightStep(1, "CAP_FLIGHT_UPDATE"), flightStep(2, "CAP_INFO_DISPLAY"),
                flightStep(3, "CAP_NOTIFICATION"));
        Map<String, Object> flightBoard = Map.of("deviceTypeCode", "SIMULATOR", "simulatedDeviceType", "FLIGHT_DELAY_BOARD",
                "capabilities", List.of("CAP_FLIGHT_UPDATE", "CAP_INFO_DISPLAY"));
        PlanValidationResult partial = validation.validate(steps, List.of(flightBoard), null, "FLIGHT_CHANGE_RESPONSE");
        validation.requireCoreScenarioCoverage(steps, "FLIGHT_CHANGE_RESPONSE", partial);
        assertTrue(partial.isAllPassed(), "缺席渠道由执行阶段标记未覆盖，不能借用航延屏作为智慧航显");

        Map<String, Object> robotNavigationOnly = Map.of("deviceTypeCode", "SIMULATOR", "simulatedDeviceType", "MOBILE_ROBOT",
                "capabilities", List.of("CAP_NAVIGATION"));
        PlanValidationResult noPublisher = validation.validate(steps, List.of(robotNavigationOnly), null, "FLIGHT_CHANGE_RESPONSE");
        assertFalse(noPublisher.isAllPassed(), "无任何可用发布渠道不得放行计划");

        when(capabilities.existsByCapabilityTypeAndCapabilityStatus("CAP_UNKNOWN", "ENABLED")).thenReturn(false);
        PlanValidationResult unknownCapability = validation.validate(
                List.of(flightStep(4, "CAP_UNKNOWN")), List.of(flightBoard), null, "FLIGHT_CHANGE_RESPONSE");
        assertFalse(unknownCapability.isAllPassed(), "部分渠道规则不得放行未知能力");
    }

    private Map<String, Object> flightStep(int seq, String capability) {
        return Map.of("stepSeq", seq, "stepGoal", "发布虚构航班信息", "capabilityType", capability,
                "completionCondition", "SUCCESS", "inputParams", Map.of());
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
