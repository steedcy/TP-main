package com.airport.ai.task;

import com.airport.ai.device.DeviceCapabilityMapper;
import org.junit.jupiter.api.Test;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.*;

/** DEF-S3-069：超规行李预置定义允许 CAP_INFO_DISPLAY 后，含智慧航显步骤的完整计划能通过三类校验与核心场景覆盖。 */
class OversizeBaggagePlanF013Test {
    private final DeviceCapabilityMapper capabilities = mock(DeviceCapabilityMapper.class);
    private final PlanValidationService validation = new PlanValidationService(capabilities);

    OversizeBaggagePlanF013Test() {
        when(capabilities.existsByCapabilityTypeAndCapabilityStatus(anyString(), anyString())).thenReturn(true);
    }

    private Map<String, Object> step(int seq, String capability) {
        Map<String, Object> s = new LinkedHashMap<>();
        s.put("stepSeq", seq);
        s.put("stepGoal", "执行" + capability);
        s.put("capabilityType", capability);
        s.put("inputParams", new LinkedHashMap<>());
        s.put("precondition", "候选设备在线且空闲");
        s.put("completionCondition", "完成");
        s.put("failureHandling", "重试一次或转人工处理");
        return s;
    }

    private Map<String, Object> agent(String simulatedType, String... caps) {
        return Map.of("agentId", simulatedType, "capabilities", List.of(caps), "onlineStatus", "ONLINE", "workload", "IDLE",
                "deviceTypeCode", "SIMULATOR", "simulatedDeviceType", simulatedType, "location", Map.of());
    }

    private List<Map<String, Object>> agents() {
        return List.of(agent("BAGGAGE_SCANNER", "CAP_BAGGAGE_MEASURE", "CAP_OVERSIZE_ALERT"),
                agent("SMART_DISPLAY", "CAP_INFO_DISPLAY"), agent("MOBILE_ROBOT", "CAP_NAVIGATION", "CAP_NOTIFICATION"));
    }

    private List<Map<String, Object>> fullPlan() {
        return List.of(step(1, "CAP_BAGGAGE_MEASURE"), step(2, "CAP_OVERSIZE_ALERT"),
                step(3, "CAP_INFO_DISPLAY"), step(4, "CAP_NAVIGATION"));
    }

    private PlanValidationResult validate(List<String> allowed) {
        List<Map<String, Object>> steps = fullPlan();
        PlanValidationResult r = validation.validate(steps, agents(), allowed, "OVERSIZE_BAGGAGE_HANDLING");
        validation.requireCoreScenarioCoverage(steps, "OVERSIZE_BAGGAGE_HANDLING", r);
        return r;
    }

    @Test
    void definitionWithTheDisplayChannelLetsTheCoreScenarioPlanPass() {
        PlanValidationResult r = validate(List.of("CAP_BAGGAGE_MEASURE", "CAP_OVERSIZE_ALERT", "CAP_NAVIGATION",
                "CAP_NOTIFICATION", "CAP_INFO_DISPLAY"));
        assertTrue(r.isAllPassed(), String.valueOf(r.getErrors()));
    }

    @Test
    void theOldDefinitionRejectedTheRequiredDisplayStepWhichWasTheDefect() {
        PlanValidationResult r = validate(List.of("CAP_BAGGAGE_MEASURE", "CAP_OVERSIZE_ALERT", "CAP_NAVIGATION", "CAP_NOTIFICATION"));
        assertFalse(r.isAllPassed());
        assertTrue(r.getErrors().stream().anyMatch(e -> "ERR_CAPABILITY_NOT_IN_TASK_DEFINITION".equals(e.getReasonCode())),
                String.valueOf(r.getErrors()));
    }

    @Test
    void aCapabilityOutsideTheDefinitionIsStillRejected() {
        List<Map<String, Object>> steps = new java.util.ArrayList<>(fullPlan());
        steps.add(step(5, "CAP_ESCORT"));
        PlanValidationResult r = validation.validate(steps, agents(),
                List.of("CAP_BAGGAGE_MEASURE", "CAP_OVERSIZE_ALERT", "CAP_NAVIGATION", "CAP_NOTIFICATION", "CAP_INFO_DISPLAY"),
                "OVERSIZE_BAGGAGE_HANDLING");
        assertFalse(r.isAllPassed());
        assertTrue(r.getErrors().stream().anyMatch(e -> "ERR_CAPABILITY_NOT_IN_TASK_DEFINITION".equals(e.getReasonCode())));
    }

    @Test
    void missingTheDisplayChannelInThePlanStillFailsCoreCoverage() {
        List<Map<String, Object>> steps = List.of(step(1, "CAP_BAGGAGE_MEASURE"), step(2, "CAP_OVERSIZE_ALERT"),
                step(3, "CAP_NOTIFICATION"), step(4, "CAP_NAVIGATION"));
        PlanValidationResult r = validation.validate(steps, agents(),
                List.of("CAP_BAGGAGE_MEASURE", "CAP_OVERSIZE_ALERT", "CAP_NAVIGATION", "CAP_NOTIFICATION", "CAP_INFO_DISPLAY"),
                "OVERSIZE_BAGGAGE_HANDLING");
        validation.requireCoreScenarioCoverage(steps, "OVERSIZE_BAGGAGE_HANDLING", r);
        assertTrue(r.getErrors().stream().anyMatch(e -> "ERR_REQUIRED_CHANNEL_MISSING".equals(e.getReasonCode())));
    }
}
