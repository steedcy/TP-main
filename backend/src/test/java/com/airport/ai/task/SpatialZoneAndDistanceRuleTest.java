package com.airport.ai.task;

import com.airport.ai.baseline.BaselineDryRunLifecycle;
import com.airport.ai.baseline.DryRunDeviceSelectionMapper;
import com.airport.ai.device.Device;
import com.airport.ai.device.DeviceAgent;
import com.airport.ai.device.DeviceAgentMapper;
import com.airport.ai.device.DeviceAgentMessagingService;
import com.airport.ai.device.DeviceCapabilityMapper;
import com.airport.ai.device.DeviceMapper;
import com.airport.ai.event.TaskEventService;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * 验证区域硬隔离规则（固定设备禁止跨隔离区、仅机器人允许跨区且陪同后可调用目标区固定设备）与最大服务距离规则（650px / 1600px）
 */
class SpatialZoneAndDistanceRuleTest {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private DeviceCapabilityMapper capabilityMapper;
    private TaskMapper taskMapper;
    private TerminalMapMapper terminalMapMapper;
    private PlanValidationService validationService;

    @BeforeEach
    void setUp() {
        capabilityMapper = mock(DeviceCapabilityMapper.class);
        taskMapper = mock(TaskMapper.class);
        terminalMapMapper = mock(TerminalMapMapper.class);
        when(capabilityMapper.existsByCapabilityTypeAndCapabilityStatus(anyString(), eq("ENABLED"))).thenReturn(true);

        when(terminalMapMapper.findAllPois()).thenReturn(List.of(
                Map.of("poiCode", "ENTRANCE_01", "poiName", "1号门", "category", "FACILITY", "x", 311.0, "y", 520.0, "zone", "值机区-南"),
                Map.of("poiCode", "MEASURE_WEST", "poiName", "智能行李测量点01", "category", "MEASURE", "x", 520.0, "y", 425.0, "zone", "值机区-西"),
                Map.of("poiCode", "GATE_04", "poiName", "4号登机口", "category", "GATE", "x", 1022.0, "y", 57.0, "zone", "候机区-中"),
                Map.of("poiCode", "SERVICE_DESK", "poiName", "服务台", "category", "SERVICE", "x", 1028.0, "y", 135.0, "zone", "候机区-中")
        ));
        when(terminalMapMapper.findAllRegions()).thenReturn(List.of(
                Map.of("regionCode", "REG_SECURITY_PASS", "regionType", "SECURITY_AREA")
        ));

        validationService = new PlanValidationService(capabilityMapper, null, taskMapper);
        validationService.setTerminalMapMapper(terminalMapMapper);
    }

    private Map<String, Object> step(int seq, String cap, Map<String, Object> inputs) {
        return Map.of(
                "stepSeq", seq,
                "stepGoal", "执行步骤" + seq,
                "capabilityType", cap,
                "precondition", "设备在线空闲",
                "completionCondition", "SUCCESS",
                "failureHandling", "转人工处理",
                "inputParams", inputs
        );
    }

    private Map<String, Object> snapshotAgent(String code, String simType, List<String> caps, double x, double y, String zone) {
        return Map.of(
                "agentId", "AGENT_" + code,
                "deviceCode", code,
                "deviceTypeCode", "SIMULATOR",
                "simulatedDeviceType", simType,
                "onlineStatus", "ONLINE",
                "workload", "IDLE",
                "capabilities", caps,
                "location", Map.of("x", x, "y", y, "zone", zone)
        );
    }

    @Test
    @DisplayName("区域硬隔离：旅客在隔离区内时禁止直接跨区调用隔离区外的固定行李测量设备；由机器人先陪同前往隔离区外则放行")
    void fixedDeviceCrossZoneBlockedUnlessEscortedByRobot() {
        Task task = new Task();
        task.setId(501L);
        task.setSceneParams("{\"origin\":\"SERVICE_DESK\"}");
        when(taskMapper.findById(501L)).thenReturn(Optional.of(task));

        Map<String, Object> scannerWest = snapshotAgent("SIM_SCANNER_W", "BAGGAGE_SCANNER",
                List.of("CAP_BAGGAGE_MEASURE"), 520.0, 425.0, "隔离区外");
        Map<String, Object> robotHold = snapshotAgent("SIM_ROBOT_H2", "MOBILE_ROBOT",
                List.of("CAP_ESCORT", "CAP_NAVIGATION"), 780.0, 145.0, "隔离区内");

        // 1. 未经机器人陪同直接调用隔离区外固定测量设备 -> 拦截 ERR_CROSS_ZONE_FIXED_DEVICE
        PlanValidationResult blocked = validationService.validate(
                List.of(step(1, "CAP_BAGGAGE_MEASURE", Map.of())),
                List.of(scannerWest, robotHold), null, null, 0, 501L, null);
        assertFalse(blocked.isAllPassed());
        assertTrue(blocked.getErrors().stream().anyMatch(e -> "ERR_CROSS_ZONE_FIXED_DEVICE".equals(e.getReasonCode())));

        // 2. 先由移动服务机器人陪同旅客前往隔离区外 MEASURE_WEST，再调用固定测量设备 -> 通过
        PlanValidationResult allowed = validationService.validate(
                List.of(
                        step(1, "CAP_ESCORT", Map.of("targetLocation", "MEASURE_WEST", "escortMode", "LEAD", "maxDuration", 600)),
                        step(2, "CAP_BAGGAGE_MEASURE", Map.of())
                ),
                List.of(scannerWest, robotHold), null, null, 0, 501L, null);
        assertTrue(allowed.isAllPassed(), () -> "Errors: " + allowed.getErrors());
    }

    @Test
    @DisplayName("最大服务距离：同区域固定设备距离超过650像素时拦截，650像素内放行")
    void fixedDeviceExceedingMaxDistanceIsRejected() {
        Task task = new Task();
        task.setId(502L);
        task.setSceneParams("{\"origin\":\"ENTRANCE_01\"}"); // (311, 520) 隔离区外
        when(taskMapper.findById(502L)).thenReturn(Optional.of(task));

        // 东侧测量设备 (1420, 425) 距离 ENTRANCE_01 约 1113px > 650px
        Map<String, Object> farScanner = snapshotAgent("SIM_SCANNER_E", "BAGGAGE_SCANNER",
                List.of("CAP_BAGGAGE_MEASURE"), 1420.0, 425.0, "隔离区外");
        PlanValidationResult tooFar = validationService.validate(
                List.of(step(1, "CAP_BAGGAGE_MEASURE", Map.of())),
                List.of(farScanner), null, null, 0, 502L, null);
        assertFalse(tooFar.isAllPassed());
        assertTrue(tooFar.getErrors().stream().anyMatch(e -> "ERR_MAX_DISTANCE_EXCEEDED".equals(e.getReasonCode())));

        // 西侧测量设备 (520, 425) 距离 ENTRANCE_01 约 230px <= 650px
        Map<String, Object> nearScanner = snapshotAgent("SIM_SCANNER_W", "BAGGAGE_SCANNER",
                List.of("CAP_BAGGAGE_MEASURE"), 520.0, 425.0, "隔离区外");
        PlanValidationResult inRange = validationService.validate(
                List.of(step(1, "CAP_BAGGAGE_MEASURE", Map.of())),
                List.of(nearScanner, farScanner), null, null, 0, 502L, null);
        assertTrue(inRange.isAllPassed());
    }

    @Test
    @DisplayName("执行调度：过滤跨区固定设备与超距固定设备，仅向同区且距离上限内的固定设备派单")
    void executionOrchestratorFiltersOutCrossZoneAndOutOfRangeFixedDevices() throws Exception {
        PlanVersionMapper planMapper = mock(PlanVersionMapper.class);
        TaskStepAssignmentMapper assignMapper = mock(TaskStepAssignmentMapper.class);
        DeviceAgentMapper agentMapper = mock(DeviceAgentMapper.class);
        DeviceMapper devMapper = mock(DeviceMapper.class);
        DeviceAgentMessagingService messaging = mock(DeviceAgentMessagingService.class);

        TaskExecutionOrchestrator orchestrator = new TaskExecutionOrchestrator(
                taskMapper, planMapper, assignMapper, agentMapper, devMapper, capabilityMapper,
                mock(TaskEventService.class), mock(TaskExceptionService.class), messaging,
                mock(BaselineDryRunLifecycle.class), mock(DryRunDeviceSelectionMapper.class), mock(StepParameterResolver.class));
        orchestrator.setTerminalMapMapper(terminalMapMapper);

        Task t = new Task();
        t.setId(601L);
        t.setTaskFamily("SPECIAL_PASSENGER_SERVICE");
        t.setStatus(TaskStatus.PENDING_ASSIGNMENT);
        t.setSceneParams("{\"origin\":\"ENTRANCE_01\",\"targetLocation\":\"GATE_04\"}");
        when(taskMapper.findById(601L)).thenReturn(Optional.of(t));

        PlanVersion pv = new PlanVersion();
        pv.setId(701L);
        pv.setTaskId(601L);
        pv.setPlanSteps(MAPPER.writeValueAsString(List.of(
                Map.of("stepSeq", 1, "capabilityType", "CAP_INFO_DISPLAY", "inputParams", Map.of("contentType", "TEXT"))
        )));
        when(planMapper.findById(701L)).thenReturn(Optional.of(pv));

        TaskStepAssignment a1 = new TaskStepAssignment();
        a1.setId(801L); a1.setTaskId(601L); a1.setPlanVersionId(701L); a1.setStepSeq(1); a1.setStepStatus("PENDING_ASSIGNMENT");
        when(assignMapper.findByPlanVersionIdAndStepSeq(701L, 1)).thenReturn(Optional.of(a1));
        when(assignMapper.findByPlanVersionIdOrderByStepSeqAsc(701L)).thenReturn(List.of(a1));

        // 候选1：隔离区内航显（跨区，应被硬隔离过滤）
        Device dHold = new Device(); dHold.setId(1L); dHold.setDeviceCode("SIM_DISPLAY_H1");
        dHold.setDeviceTypeCode("SIMULATOR"); dHold.setSimulatedDeviceType("SMART_DISPLAY"); dHold.setDeviceStatus("ACTIVE");
        dHold.setPositionX(BigDecimal.valueOf(380)); dHold.setPositionY(BigDecimal.valueOf(145)); dHold.setAreaCode("隔离区内");
        DeviceAgent agHold = new DeviceAgent(); agHold.setId(11L); agHold.setAgentCode("AGENT_SIM_DISPLAY_H1");
        agHold.setDeviceId(1L); agHold.setAgentStatus("ENABLED"); agHold.setOnlineStatus("ONLINE"); agHold.setWorkStatus("IDLE");

        // 候选2：隔离区外东侧航显 (1280, 445)，距 ENTRANCE_01(311, 520) 约 972px > 650px（超距，应被过滤）
        Device dEast = new Device(); dEast.setId(2L); dEast.setDeviceCode("SIM_DISPLAY_C2");
        dEast.setDeviceTypeCode("SIMULATOR"); dEast.setSimulatedDeviceType("SMART_DISPLAY"); dEast.setDeviceStatus("ACTIVE");
        dEast.setPositionX(BigDecimal.valueOf(1280)); dEast.setPositionY(BigDecimal.valueOf(445)); dEast.setAreaCode("隔离区外");
        DeviceAgent agEast = new DeviceAgent(); agEast.setId(12L); agEast.setAgentCode("AGENT_SIM_DISPLAY_C2");
        agEast.setDeviceId(2L); agEast.setAgentStatus("ENABLED"); agEast.setOnlineStatus("ONLINE"); agEast.setWorkStatus("IDLE");

        // 候选3：隔离区外西侧航显 (680, 445)，距 ENTRANCE_01(311, 520) 约 376px <= 650px（唯一合法候选）
        Device dWest = new Device(); dWest.setId(3L); dWest.setDeviceCode("SIM_DISPLAY_C1");
        dWest.setDeviceTypeCode("SIMULATOR"); dWest.setSimulatedDeviceType("SMART_DISPLAY"); dWest.setDeviceStatus("ACTIVE");
        dWest.setPositionX(BigDecimal.valueOf(680)); dWest.setPositionY(BigDecimal.valueOf(445)); dWest.setAreaCode("隔离区外");
        DeviceAgent agWest = new DeviceAgent(); agWest.setId(13L); agWest.setAgentCode("AGENT_SIM_DISPLAY_C1");
        agWest.setDeviceId(3L); agWest.setAgentStatus("ENABLED"); agWest.setOnlineStatus("ONLINE"); agWest.setWorkStatus("IDLE");

        when(agentMapper.findByAgentStatusAndOnlineStatus("ENABLED", "ONLINE")).thenReturn(List.of(agHold, agEast, agWest));
        when(devMapper.findByIds(anyList())).thenReturn(List.of(dHold, dEast, dWest));
        when(capabilityMapper.existsByDeviceIdAndCapabilityTypeAndCapabilityStatus(anyLong(), eq("CAP_INFO_DISPLAY"), eq("ENABLED"))).thenReturn(true);

        orchestrator.startExecution(601L, 701L);

        ArgumentCaptor<String> chosenAgent = ArgumentCaptor.forClass(String.class);
        verify(messaging).requestTaskAcceptance(chosenAgent.capture(), anyString(), eq(601L), eq(1), eq("CAP_INFO_DISPLAY"), any());
        assertEquals("AGENT_SIM_DISPLAY_C1", chosenAgent.getValue());
    }
}
