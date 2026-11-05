package com.airport.ai.task;

import com.airport.ai.baseline.BaselineDryRunLifecycle;
import com.airport.ai.baseline.DryRunDeviceSelectionMapper;
import com.airport.ai.common.BusinessException;
import com.airport.ai.common.ErrorCode;
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
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * SRS_F016 步骤设备匹配与任务接受 业务规则与用例独立验证单测
 * 覆盖规则 R01 ~ R08，关联用例 TC-051, TC-052, TC-053
 */
class DeviceMatchingAndTaskAcceptanceF016Test {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private TaskMapper taskMapper;
    private PlanVersionMapper planVersionMapper;
    private TaskStepAssignmentMapper assignmentMapper;
    private DeviceAgentMapper deviceAgentMapper;
    private DeviceMapper deviceMapper;
    private DeviceCapabilityMapper deviceCapabilityMapper;
    private StepParameterResolver parameterResolver;
    private DeviceAgentMessagingService deviceAgentMessagingService;
    private TaskEventService taskEventService;
    private TaskExceptionService taskExceptionService;
    private BaselineDryRunLifecycle dryRunLifecycle;
    private DryRunDeviceSelectionMapper selections;

    private TaskExecutionOrchestrator orchestrator;

    private Task testTask;
    private PlanVersion testPlanVersion;
    private TaskStepAssignment testAssignment;

    @BeforeEach
    void setUp() throws Exception {
        taskMapper = mock(TaskMapper.class);
        planVersionMapper = mock(PlanVersionMapper.class);
        assignmentMapper = mock(TaskStepAssignmentMapper.class);
        deviceAgentMapper = mock(DeviceAgentMapper.class);
        deviceMapper = mock(DeviceMapper.class);
        deviceCapabilityMapper = mock(DeviceCapabilityMapper.class);
        parameterResolver = mock(StepParameterResolver.class);
        deviceAgentMessagingService = mock(DeviceAgentMessagingService.class);
        taskEventService = mock(TaskEventService.class);
        taskExceptionService = mock(TaskExceptionService.class);
        dryRunLifecycle = mock(BaselineDryRunLifecycle.class);
        selections = mock(DryRunDeviceSelectionMapper.class);

        orchestrator = new TaskExecutionOrchestrator(
                taskMapper, planVersionMapper, assignmentMapper,
                deviceAgentMapper, deviceMapper, deviceCapabilityMapper,
                taskEventService, taskExceptionService, deviceAgentMessagingService,
                dryRunLifecycle, selections, parameterResolver
        );

        testTask = new Task();
        testTask.setId(100L);
        testTask.setTaskCode("TASK-F016-100");
        testTask.setTaskFamily("FLIGHT_CHANGE_RESPONSE");
        testTask.setStatus(TaskStatus.PENDING_ASSIGNMENT);
        testTask.setCurrentPlanVersionId(200L);
        testTask.setIsDryRun(false);

        List<Map<String, Object>> steps = List.of(
                Map.of(
                        "stepSeq", 1,
                        "stepGoal", "在F2_TEST_GATE显示航班更新信息",
                        "capabilityType", "CAP_FLIGHT_UPDATE",
                        "targetX", 800.0,
                        "targetY", 4000.0,
                        "inputParams", Map.of(
                                "flightNumber", "CA1234",
                                "targetX", 800.0,
                                "targetY", 4000.0
                        )
                ),
                Map.of(
                        "stepSeq", 2,
                        "stepGoal", "在F2_TEST_GATE进行引导广播",
                        "capabilityType", "CAP_NOTIFICATION",
                        "inputParams", Map.of("content", "请前往登机口")
                )
        );

        testPlanVersion = new PlanVersion();
        testPlanVersion.setId(200L);
        testPlanVersion.setTaskId(100L);
        testPlanVersion.setVersionNo(1);
        testPlanVersion.setPlanSteps(MAPPER.writeValueAsString(steps));

        testAssignment = new TaskStepAssignment();
        testAssignment.setId(301L);
        testAssignment.setTaskId(100L);
        testAssignment.setPlanVersionId(200L);
        testAssignment.setStepSeq(1);
        testAssignment.setStepStatus("PENDING_ASSIGNMENT");
        testAssignment.setRejectedAgentIds("[]");

        when(taskMapper.findById(100L)).thenReturn(Optional.of(testTask));
        when(planVersionMapper.findById(200L)).thenReturn(Optional.of(testPlanVersion));
        when(assignmentMapper.findByPlanVersionIdAndStepSeq(200L, 1)).thenReturn(Optional.of(testAssignment));

        when(deviceAgentMapper.findByIdForUpdate(anyLong())).thenAnswer(inv -> deviceAgentMapper.findById(inv.getArgument(0)));
        when(deviceAgentMapper.findByAgentCodeForUpdate(anyString())).thenAnswer(inv -> deviceAgentMapper.findByAgentCode(inv.getArgument(0)));
        when(deviceAgentMapper.claimAgent(anyLong(), anyLong(), anyInt())).thenReturn(1);
    }

    private Device createDevice(Long id, String code, String typeCode, String simType, double x, double y) {
        Device d = new Device();
        d.setId(id);
        d.setDeviceCode(code);
        d.setDeviceTypeCode(typeCode);
        d.setSimulatedDeviceType(simType);
        d.setDeviceStatus("ACTIVE");
        d.setPositionX(BigDecimal.valueOf(x));
        d.setPositionY(BigDecimal.valueOf(y));
        return d;
    }

    private DeviceAgent createAgent(Long id, String code, Long deviceId, String online, String work, String bizStatus) {
        DeviceAgent a = new DeviceAgent();
        a.setId(id);
        a.setAgentCode(code);
        a.setDeviceId(deviceId);
        a.setAgentStatus("ENABLED");
        a.setOnlineStatus(online);
        a.setWorkStatus(work);
        a.setBusinessStatus(bizStatus);
        return a;
    }

    @Test
    @DisplayName("SRS_F016.R01: 只有具备所需能力、在线且空闲的设备可作为候选 (TC-051.S1)")
    void testR01_onlyEnabledOnlineIdleAgentWithCapabilityCanBeCandidate() {
        Device d1 = createDevice(1L, "DEV-01", "FLIGHT_DELAY_BOARD", null, 800.0, 4000.0);
        DeviceAgent a1 = createAgent(10L, "AGT-01", 1L, "ONLINE", "IDLE", null);

        // 离线代理
        Device d2 = createDevice(2L, "DEV-02", "FLIGHT_DELAY_BOARD", null, 800.0, 4000.0);
        DeviceAgent a2 = createAgent(20L, "AGT-02", 2L, "OFFLINE", "IDLE", null);

        // 忙碌代理
        Device d3 = createDevice(3L, "DEV-03", "FLIGHT_DELAY_BOARD", null, 800.0, 4000.0);
        DeviceAgent a3 = createAgent(30L, "AGT-03", 3L, "ONLINE", "BUSY", null);

        // 能力未启用的设备
        Device d4 = createDevice(4L, "DEV-04", "FLIGHT_DELAY_BOARD", null, 800.0, 4000.0);
        DeviceAgent a4 = createAgent(40L, "AGT-04", 4L, "ONLINE", "IDLE", null);

        when(deviceAgentMapper.findByAgentStatusAndOnlineStatus("ENABLED", "ONLINE"))
                .thenReturn(List.of(a1, a3, a4));
        when(deviceMapper.findByIds(anyList())).thenReturn(List.of(d1, d3, d4));
        when(deviceCapabilityMapper.existsByDeviceIdAndCapabilityTypeAndCapabilityStatus(1L, "CAP_FLIGHT_UPDATE", "ENABLED"))
                .thenReturn(true);
        when(deviceCapabilityMapper.existsByDeviceIdAndCapabilityTypeAndCapabilityStatus(3L, "CAP_FLIGHT_UPDATE", "ENABLED"))
                .thenReturn(true);
        when(deviceCapabilityMapper.existsByDeviceIdAndCapabilityTypeAndCapabilityStatus(4L, "CAP_FLIGHT_UPDATE", "ENABLED"))
                .thenReturn(false); // 能力未启用

        orchestrator.assignStep(100L, 200L, 1);

        // 只有 a1 符合条件被请求
        verify(deviceAgentMessagingService).requestTaskAcceptance(eq("AGT-01"), anyString(), eq(100L), eq(1), eq("CAP_FLIGHT_UPDATE"), any());
        verify(deviceAgentMessagingService, never()).requestTaskAcceptance(eq("AGT-02"), any(), any(), any(), any(), any());
        verify(deviceAgentMessagingService, never()).requestTaskAcceptance(eq("AGT-03"), any(), any(), any(), any(), any());
        verify(deviceAgentMessagingService, never()).requestTaskAcceptance(eq("AGT-04"), any(), any(), any(), any(), any());
    }

    @Test
    @DisplayName("SRS_F016.R02: 同一设备同一时刻只执行一个任务步骤；已占用设备不得分配新步骤 (TC-052.S1)")
    void testR02_singleStepOccupationAndBusyAgentExcluded() {
        Device d1 = createDevice(1L, "DEV-01", "FLIGHT_DELAY_BOARD", null, 800.0, 4000.0);
        DeviceAgent a1 = createAgent(10L, "AGT-01", 1L, "ONLINE", "IDLE", null);

        testAssignment.setDeviceAgentId(10L);
        testAssignment.setCommandId("CMD-ACCEPT-01");
        when(assignmentMapper.findByCommandId("CMD-ACCEPT-01")).thenReturn(Optional.of(testAssignment));
        when(deviceAgentMapper.findByAgentCode("AGT-01")).thenReturn(Optional.of(a1));
        when(deviceAgentMapper.findById(10L)).thenReturn(Optional.of(a1));

        // 模拟接受步骤承接请求
        orchestrator.onTaskResponse("AGT-01", "CMD-ACCEPT-01", true, null);

        // a1 状态更新为 BUSY，记录当前任务和步骤
        assertEquals("BUSY", a1.getWorkStatus());
        assertEquals(100L, a1.getCurrentTaskId());
        assertEquals(1, a1.getCurrentStepSeq());
        verify(deviceAgentMapper).update(a1);

        // 任务状态转为 EXECUTING
        assertEquals(TaskStatus.EXECUTING, testTask.getStatus());
        verify(taskMapper).update(testTask);

        // 此时 a1 处于 BUSY，查询可用候选时应被排除
        when(deviceAgentMapper.findByAgentStatusAndOnlineStatus("ENABLED", "ONLINE"))
                .thenReturn(List.of(a1));
        boolean available = orchestrator.hasAvailableCandidate(200L, 1, List.of());
        assertFalse(available, "BUSY状态的设备不得作为可用候选");
    }

    @Test
    @DisplayName("SRS_F016.R03: 设备拒绝时按候选顺序选择下一候选，并记录拒绝原因 (TC-051.S1)")
    void testR03_deviceRejectSelectsNextCandidateAndRecordsReason() {
        Device d1 = createDevice(1L, "DEV-01", "FLIGHT_DELAY_BOARD", null, 800.0, 4000.0);
        DeviceAgent a1 = createAgent(10L, "AGT-01", 1L, "ONLINE", "IDLE", null);
        Device d2 = createDevice(2L, "DEV-02", "FLIGHT_DELAY_BOARD", null, 810.0, 4010.0);
        DeviceAgent a2 = createAgent(20L, "AGT-02", 2L, "ONLINE", "IDLE", null);

        when(deviceAgentMapper.findByAgentStatusAndOnlineStatus("ENABLED", "ONLINE"))
                .thenReturn(List.of(a1, a2));
        when(deviceMapper.findByIds(anyList())).thenReturn(List.of(d1, d2));
        when(deviceCapabilityMapper.existsByDeviceIdAndCapabilityTypeAndCapabilityStatus(anyLong(), eq("CAP_FLIGHT_UPDATE"), eq("ENABLED")))
                .thenReturn(true);

        when(assignmentMapper.findByCommandId("CMD-ACCEPT-01")).thenReturn(Optional.of(testAssignment));
        when(deviceAgentMapper.findByAgentCode("AGT-01")).thenReturn(Optional.of(a1));
        when(deviceAgentMapper.findByAgentCode("AGT-02")).thenReturn(Optional.of(a2));

        testAssignment.setCommandId("CMD-ACCEPT-01");
        testAssignment.setDeviceAgentId(10L);

        // a1 拒绝承接，原因: LOCAL_MAINTENANCE
        orchestrator.onTaskResponse("AGT-01", "CMD-ACCEPT-01", false, "LOCAL_MAINTENANCE");

        // 验证已将 AGT-01 记录到 rejectedAgentIds
        assertTrue(testAssignment.getRejectedAgentIds().contains("AGT-01"));
        // 验证事件时间线记录拒绝事件和原因
        verify(taskEventService).append(eq(100L), eq("AGENT_REJECTED"), eq("SYSTEM"), isNull(),
                contains("设备代理AGT-01拒绝步骤1承接请求，原因: LOCAL_MAINTENANCE"));

        // 验证自动选择下一候选 a2 发起承接请求
        verify(deviceAgentMessagingService).requestTaskAcceptance(eq("AGT-02"), anyString(), eq(100L), eq(1), eq("CAP_FLIGHT_UPDATE"), any());
    }

    @Test
    @DisplayName("SRS_F016.R04: 候选顺序按能力匹配度、与步骤目标区域的距离、当前负载依次排序，排序依据写入事件 (TC-051.S1)")
    void testR04_threeDimensionalCandidateSorting() {
        // 构造三台设备：
        // d1: 精确匹配物理通道FLIGHT_DELAY_BOARD(匹配度1.0)，距离较远(50.0)，负载0
        // d2: 泛化模拟体(匹配度0.8)，距离最近(10.0)，负载0
        // d3: 精确匹配(匹配度1.0)，距离较远(50.0)，负载1(businessStatus注明workloadScore: 1)
        Device d1 = createDevice(1L, "DEV-01", "FLIGHT_DELAY_BOARD", null, 850.0, 4000.0); // distance 50.0
        DeviceAgent a1 = createAgent(10L, "AGT-A1", 1L, "ONLINE", "IDLE", "{\"capabilityMatch\":1.0,\"workloadScore\":0}");

        Device d2 = createDevice(2L, "DEV-02", "FLIGHT_DELAY_BOARD", null, 810.0, 4000.0); // distance 10.0
        DeviceAgent a2 = createAgent(20L, "AGT-A2", 2L, "ONLINE", "IDLE", "{\"capabilityMatch\":0.8,\"workloadScore\":0}");

        Device d3 = createDevice(3L, "DEV-03", "FLIGHT_DELAY_BOARD", null, 850.0, 4000.0); // distance 50.0
        DeviceAgent a3 = createAgent(30L, "AGT-A3", 3L, "ONLINE", "IDLE", "{\"capabilityMatch\":1.0,\"workloadScore\":1}");

        when(deviceAgentMapper.findByAgentStatusAndOnlineStatus("ENABLED", "ONLINE"))
                .thenReturn(List.of(a2, a3, a1)); // 乱序返回
        when(deviceMapper.findByIds(anyList())).thenReturn(List.of(d1, d2, d3));
        when(deviceCapabilityMapper.existsByDeviceIdAndCapabilityTypeAndCapabilityStatus(anyLong(), eq("CAP_FLIGHT_UPDATE"), eq("ENABLED")))
                .thenReturn(true);

        orchestrator.assignStep(100L, 200L, 1);

        // 能力匹配度维度: a1(1.0) 和 a3(1.0) 优先于 a2(0.8)；
        // 距离维度: a1 与 a3 距离同为 50.0；
        // 负载维度: a1(负载0) 优于 a3(负载1)；
        // 最终综合排名首选为 a1
        verify(deviceAgentMessagingService).requestTaskAcceptance(eq("AGT-A1"), anyString(), eq(100L), eq(1), eq("CAP_FLIGHT_UPDATE"), any());

        // 验证候选排序依据（匹配度->距离->负载）写入事件时间线
        ArgumentCaptor<String> detailCaptor = ArgumentCaptor.forClass(String.class);
        verify(taskEventService).append(eq(100L), eq("AGENT_ASSIGNMENT_REQUESTED"), eq("SYSTEM"), isNull(), detailCaptor.capture());
        String eventDetail = detailCaptor.getValue();
        assertTrue(eventDetail.contains("候选排序（能力匹配->距离->负载）"));
        assertTrue(eventDetail.contains("AGT-A1(匹配度1.0,距离50.0,负载0)"));
        assertTrue(eventDetail.contains("AGT-A3(匹配度1.0,距离50.0,负载1)"));
        assertTrue(eventDetail.contains("AGT-A2(匹配度0.8,距离10.0,负载0)"));
        // 确认首位指向 AGT-A1
        assertTrue(eventDetail.indexOf("AGT-A1") < eventDetail.indexOf("AGT-A3"));
        assertTrue(eventDetail.indexOf("AGT-A3") < eventDetail.indexOf("AGT-A2"));
    }

    @Test
    @DisplayName("SRS_F016.R05: 全部候选均拒绝或无候选时，生成能力缺口或分配失败异常，进入5.5.3判断 (TC-052.S2)")
    void testR05_emptyCandidatesOrAllRejectedGeneratesAppropriateException() {
        // 使用非航班发布通用场景，验证标准的无候选/全拒绝异常逻辑
        testTask.setTaskFamily("GENERAL_SERVICE");
        // 情况 A: 初始无候选设备 (rejected 为空)
        when(deviceAgentMapper.findByAgentStatusAndOnlineStatus("ENABLED", "ONLINE"))
                .thenReturn(List.of());

        orchestrator.assignStep(100L, 200L, 1);

        // 验证产生 ERR_NO_CANDIDATE_AVAILABLE 事件与 CAPABILITY_GAP 异常
        verify(taskEventService).append(eq(100L), eq("STEP_ASSIGNMENT_FAILED"), eq("SYSTEM"),
                eq("ERR_NO_CANDIDATE_AVAILABLE"), contains("无可用候选设备"));
        verify(taskExceptionService).handleException(eq(100L), eq(1), eq("CAPABILITY_GAP"), contains("无可用候选设备"));

        // 情况 B: 全部候选已拒绝 (rejected 非空)
        testAssignment.setRejectedAgentIds("[\"AGT-01\",\"AGT-02\"]");
        orchestrator.assignStep(100L, 200L, 1);

        // 验证产生 ERR_ALL_CANDIDATES_REJECTED 事件与 ASSIGNMENT_FAILED 异常
        verify(taskEventService).append(eq(100L), eq("STEP_ASSIGNMENT_FAILED"), eq("SYSTEM"),
                eq("ERR_ALL_CANDIDATES_REJECTED"), contains("所有候选设备均已拒绝承接"));
        verify(taskExceptionService).handleException(eq(100L), eq(1), eq("ASSIGNMENT_FAILED"), contains("全部候选设备均已拒绝承接"));
    }

    @Test
    @DisplayName("SRS_F016.R06 & R07: 分配阶段仅确认承接不下发业务指令；设备响应写入事件时间线 (TC-051.S2)")
    void testR06_R07_allocationPhaseConfirmsAcceptanceWithoutBusinessCommand() {
        Device d1 = createDevice(1L, "DEV-01", "FLIGHT_DELAY_BOARD", null, 800.0, 4000.0);
        DeviceAgent a1 = createAgent(10L, "AGT-01", 1L, "ONLINE", "IDLE", null);

        when(deviceAgentMapper.findByAgentStatusAndOnlineStatus("ENABLED", "ONLINE"))
                .thenReturn(List.of(a1));
        when(deviceMapper.findByIds(anyList())).thenReturn(List.of(d1));
        when(deviceCapabilityMapper.existsByDeviceIdAndCapabilityTypeAndCapabilityStatus(anyLong(), eq("CAP_FLIGHT_UPDATE"), eq("ENABLED")))
                .thenReturn(true);

        orchestrator.assignStep(100L, 200L, 1);

        // 验证此时仅发送 TASK_ACCEPT 请求，绝不下发业务执行指令 EXECUTE_CAPABILITY
        verify(deviceAgentMessagingService, times(1)).requestTaskAcceptance(eq("AGT-01"), anyString(), eq(100L), eq(1), eq("CAP_FLIGHT_UPDATE"), any());
        verify(deviceAgentMessagingService, never()).executeCapability(any(), any(), any(), any(), any(), anyInt(), any());

        // 验证承接请求写入时间线
        verify(taskEventService).append(eq(100L), eq("AGENT_ASSIGNMENT_REQUESTED"), eq("SYSTEM"), isNull(), contains("向候选AGT-01发起承接请求"));
    }

    @Test
    @DisplayName("SRS_F016.R08: 计划步骤冻结时，立即释放相关设备占用 (TC-053.S1)")
    void testR08_stepFrozenReleasesAgentOccupation() {
        DeviceAgent a1 = createAgent(10L, "AGT-01", 1L, "ONLINE", "BUSY", null);
        a1.setCurrentTaskId(100L);
        a1.setCurrentStepSeq(2);
        when(deviceAgentMapper.findById(10L)).thenReturn(Optional.of(a1));

        // releaseAgent 释放占用
        orchestrator.releaseAgent(10L);

        assertEquals("IDLE", a1.getWorkStatus());
        assertNull(a1.getCurrentTaskId());
        assertNull(a1.getCurrentStepSeq());
        verify(deviceAgentMapper).update(a1);
    }



    @Test
    @DisplayName("SRS_F016.R02 / DEF-S3-100: 待承接窗口期被其他任务抢占，响应到达时检测到冲突并自动切换下一候选")
    void testR02_acceptanceWindowConflictSwitchesCandidate() {
        Device d1 = createDevice(1L, "DEV-01", "FLIGHT_DELAY_BOARD", null, 800.0, 4000.0);
        DeviceAgent a1 = createAgent(10L, "AGT-01", 1L, "ONLINE", "IDLE", null);

        Device d2 = createDevice(2L, "DEV-02", "FLIGHT_DELAY_BOARD", null, 810.0, 4000.0);
        DeviceAgent a2 = createAgent(20L, "AGT-02", 2L, "ONLINE", "IDLE", null);

        when(deviceAgentMapper.findByAgentStatusAndOnlineStatus("ENABLED", "ONLINE"))
                .thenReturn(List.of(a1, a2));
        when(deviceMapper.findByIds(anyList())).thenReturn(List.of(d1, d2));
        when(deviceCapabilityMapper.existsByDeviceIdAndCapabilityTypeAndCapabilityStatus(anyLong(), eq("CAP_FLIGHT_UPDATE"), eq("ENABLED")))
                .thenReturn(true);
        when(deviceAgentMapper.findByAgentCode("AGT-01")).thenReturn(Optional.of(a1));
        when(deviceAgentMapper.findByAgentCode("AGT-02")).thenReturn(Optional.of(a2));
        when(deviceAgentMapper.findById(10L)).thenReturn(Optional.of(a1));
        when(deviceAgentMapper.findById(20L)).thenReturn(Optional.of(a2));
        when(assignmentMapper.findByCommandId(anyString())).thenReturn(Optional.of(testAssignment));

        // 步骤1发起分配
        orchestrator.assignStep(100L, 200L, 1);
        assertEquals(10L, testAssignment.getDeviceAgentId());
        String commandId = testAssignment.getCommandId();
        assertNotNull(commandId);

        // 模拟待承接窗口期：AGT-01 在响应到达前被其他任务抢占（变 BUSY，currentTaskId=999）
        a1.setWorkStatus("BUSY");
        a1.setCurrentTaskId(999L);

        // AGT-01 返回 accepted=true 响应
        orchestrator.onTaskResponse("AGT-01", commandId, true, null);

        // 验证检测到冲突，记录冲突事件，且不下发业务指令给 a1
        verify(taskEventService).append(eq(100L), eq("AGENT_ASSIGNMENT_CONFLICTED"), eq("SYSTEM"),
                eq("ERR_AGENT_ALREADY_BUSY"), contains("已被任务999占用"));
        verify(deviceAgentMessagingService, never()).executeCapability(eq("AGT-01"), any(), any(), any(), any(), anyInt(), any());

        // 验证自动切换到下一候选 a2 发起承接请求
        verify(deviceAgentMessagingService).requestTaskAcceptance(eq("AGT-02"), anyString(), eq(100L), eq(1), eq("CAP_FLIGHT_UPDATE"), any());
        assertTrue(testAssignment.getRejectedAgentIds().contains("AGT-01"));
    }

    @Test
    @DisplayName("SRS_F016.R02 / DEF-S3-100: 并发抢占原子CAS失败时，自动切换下一候选且不下发业务指令")
    void testR02_parallelAcceptanceAtomicConflictSwitchesCandidate() {
        Device d1 = createDevice(1L, "DEV-01", "FLIGHT_DELAY_BOARD", null, 800.0, 4000.0);
        DeviceAgent a1 = createAgent(10L, "AGT-01", 1L, "ONLINE", "IDLE", null);

        Device d2 = createDevice(2L, "DEV-02", "FLIGHT_DELAY_BOARD", null, 810.0, 4000.0);
        DeviceAgent a2 = createAgent(20L, "AGT-02", 2L, "ONLINE", "IDLE", null);

        when(deviceAgentMapper.findByAgentStatusAndOnlineStatus("ENABLED", "ONLINE"))
                .thenReturn(List.of(a1, a2));
        when(deviceMapper.findByIds(anyList())).thenReturn(List.of(d1, d2));
        when(deviceCapabilityMapper.existsByDeviceIdAndCapabilityTypeAndCapabilityStatus(anyLong(), eq("CAP_FLIGHT_UPDATE"), eq("ENABLED")))
                .thenReturn(true);
        when(deviceAgentMapper.findByAgentCode("AGT-01")).thenReturn(Optional.of(a1));
        when(deviceAgentMapper.findByAgentCode("AGT-02")).thenReturn(Optional.of(a2));
        when(deviceAgentMapper.findById(10L)).thenReturn(Optional.of(a1));
        when(deviceAgentMapper.findById(20L)).thenReturn(Optional.of(a2));
        when(assignmentMapper.findByCommandId(anyString())).thenReturn(Optional.of(testAssignment));

        orchestrator.assignStep(100L, 200L, 1);
        String commandId = testAssignment.getCommandId();

        // 模拟并发抢占：claimAgent 返回 0（已被其他并发事务先一步更新），recheck 查出已被任务 888 抢占
        when(deviceAgentMapper.claimAgent(10L, 100L, 1)).thenReturn(0);
        DeviceAgent claimedAgent = createAgent(10L, "AGT-01", 1L, "ONLINE", "BUSY", null);
        claimedAgent.setCurrentTaskId(888L);
        when(deviceAgentMapper.findById(10L)).thenReturn(Optional.of(claimedAgent));

        orchestrator.onTaskResponse("AGT-01", commandId, true, null);

        // 验证记录冲突事件
        verify(taskEventService).append(eq(100L), eq("AGENT_ASSIGNMENT_CONFLICTED"), eq("SYSTEM"),
                eq("ERR_AGENT_ALREADY_BUSY"), contains("已被任务888占用"));
        // 绝不下发业务指令给 a1
        verify(deviceAgentMessagingService, never()).executeCapability(eq("AGT-01"), any(), any(), any(), any(), anyInt(), any());
        // 自动切换至下一候选 a2
        verify(deviceAgentMessagingService).requestTaskAcceptance(eq("AGT-02"), anyString(), eq(100L), eq(1), eq("CAP_FLIGHT_UPDATE"), any());
    }

    @Test
    @DisplayName("SRS_F016.R06 / DEF-S3-102: 步骤承接请求记录发起时间，接受时记录完成时间与耗时毫秒数")
    void testR06_acceptanceTimingRecorded() {
        Device d1 = createDevice(1L, "DEV-01", "FLIGHT_DELAY_BOARD", null, 800.0, 4000.0);
        DeviceAgent a1 = createAgent(10L, "AGT-01", 1L, "ONLINE", "IDLE", null);

        when(deviceAgentMapper.findByAgentStatusAndOnlineStatus("ENABLED", "ONLINE"))
                .thenReturn(List.of(a1));
        when(deviceMapper.findByIds(anyList())).thenReturn(List.of(d1));
        when(deviceCapabilityMapper.existsByDeviceIdAndCapabilityTypeAndCapabilityStatus(anyLong(), eq("CAP_FLIGHT_UPDATE"), eq("ENABLED")))
                .thenReturn(true);
        when(deviceAgentMapper.findByAgentCode("AGT-01")).thenReturn(Optional.of(a1));
        when(deviceAgentMapper.findById(10L)).thenReturn(Optional.of(a1));
        when(assignmentMapper.findByCommandId(anyString())).thenReturn(Optional.of(testAssignment));

        orchestrator.assignStep(100L, 200L, 1);

        assertNotNull(testAssignment.getAcceptanceRequestedAt());
        assertNull(testAssignment.getAcceptedAt());
        assertNull(testAssignment.getAcceptanceDurationMs());

        String commandId = testAssignment.getCommandId();
        orchestrator.onTaskResponse("AGT-01", commandId, true, null);

        assertNotNull(testAssignment.getAcceptedAt());
        assertNotNull(testAssignment.getAcceptanceDurationMs());
        assertTrue(testAssignment.getAcceptanceDurationMs() >= 0);

        // 验证 DTO 视图格式化承接响应时间
        com.airport.ai.task.dto.TaskStepAssignmentView view = com.airport.ai.task.dto.TaskStepAssignmentView.from(testAssignment);
        assertNotNull(view.getAcceptanceResponseTime());
        assertTrue(view.getAcceptanceResponseTime().endsWith("ms"));
    }
}
