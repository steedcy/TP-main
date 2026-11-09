package com.airport.ai.task;

import com.airport.ai.device.DeviceCapabilityMapper;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

/**
 * TC-078.S1 / SRS_F025.R04: 无可用移动服务设备时降级为信息提示并转人工协助
 */
class SpecialPassengerNoMobileRobotTest {

    @Test
    void validationAllowsDisplayStepWhenMobileRobotsOffline() {
        DeviceCapabilityMapper capabilityMapper = mock(DeviceCapabilityMapper.class);
        when(capabilityMapper.existsByCapabilityTypeAndCapabilityStatus(anyString(), eq("ENABLED"))).thenReturn(true);

        PlanValidationService service = new PlanValidationService(capabilityMapper);

        List<Map<String, Object>> templateSteps = List.of(
                makeStep(1, "CAP_INFO_DISPLAY"),
                makeStep(2, "CAP_NOTIFICATION"),
                makeStep(3, "CAP_ESCORT")
        );

        // 仅智慧航显在线，两台移动机器人离线
        List<Map<String, Object>> snapshotAgents = List.of(
                Map.of("agentCode", "AGT-DISPLAY", "onlineStatus", "ONLINE", "workStatus", "IDLE",
                        "deviceTypeCode", "SMART_DISPLAY", "capabilities", List.of("CAP_INFO_DISPLAY"))
        );

        PlanValidationResult result = service.validate(
                templateSteps, snapshotAgents, null, "SPECIAL_PASSENGER_SERVICE");
        service.requireCoreScenarioCoverage(templateSteps, "SPECIAL_PASSENGER_SERVICE", result);

        assertTrue(result.isAllPassed(), "无移动机器人时应允许航显提示步骤执行，不阻断降级链路: " + result.getErrors());
    }

    private Map<String, Object> makeStep(int seq, String cap) {
        return Map.of(
                "stepSeq", seq,
                "stepGoal", "执行" + cap,
                "capabilityType", cap,
                "inputParams", Map.of("key", "val"),
                "precondition", "前置就绪",
                "completionCondition", "执行完成",
                "failureHandling", "转人工"
        );
    }
}
