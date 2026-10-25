package com.airport.ai.task;

import com.airport.ai.device.DeviceCapabilityMapper;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class PlanValidationDependencyTest {
    @Test
    void forwardReferenceFromHistoricalCycleCannotPassFreezeGate() {
        DeviceCapabilityMapper capabilities = mock(DeviceCapabilityMapper.class);
        when(capabilities.existsByCapabilityTypeAndCapabilityStatus(anyString(), eq("ENABLED"))).thenReturn(true);
        PlanValidationService validator = new PlanValidationService(capabilities);
        List<Map<String, Object>> steps = List.of(
                Map.of("stepSeq", 1, "stepGoal", "发布", "capabilityType", "CAP_FLIGHT_UPDATE",
                        "completionCondition", "步骤2完成后才可完成步骤1"),
                Map.of("stepSeq", 2, "stepGoal", "展示", "capabilityType", "CAP_INFO_DISPLAY",
                        "completionCondition", "步骤1完成后才可完成步骤2"));
        List<Map<String, Object>> agents = List.of(Map.of("capabilities", List.of("CAP_FLIGHT_UPDATE", "CAP_INFO_DISPLAY")));

        PlanValidationResult result = validator.validate(steps, agents);
        assertEquals("FAIL", result.getStructureCheckResult());
        assertTrue(result.getErrors().stream().anyMatch(e -> "ERR_STEP_DEPENDENCY_ORDER".equals(e.getReasonCode())));
    }
}
