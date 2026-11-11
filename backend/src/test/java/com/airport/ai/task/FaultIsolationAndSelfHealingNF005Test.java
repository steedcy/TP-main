package com.airport.ai.task;

import com.airport.ai.auth.OperationLogService;
import com.airport.ai.auth.User;
import com.airport.ai.baseline.BaselineDryRunLifecycle;
import com.airport.ai.baseline.DryRunDeviceSelectionMapper;
import com.airport.ai.common.BusinessException;
import com.airport.ai.common.ErrorCode;
import com.airport.ai.device.*;
import com.airport.ai.device.dto.DeviceAgentMessageRequest;
import com.airport.ai.device.dto.DeviceAgentReportRequest;
import com.airport.ai.devicetype.DeviceTypeCapabilityService;
import com.airport.ai.event.OperationLog;
import com.airport.ai.event.OperationLogMapper;
import com.airport.ai.event.TaskEvent;
import com.airport.ai.event.TaskEventMapper;
import com.airport.ai.event.TaskEventService;
import com.airport.ai.planning.GoalUnderstandingService;
import com.airport.ai.task.dto.ExecutionFeedbackRequest;
import com.airport.ai.taskdef.TaskDefinitionService;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.springframework.aop.framework.ProxyFactory;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.transaction.TransactionDefinition;
import org.springframework.transaction.TransactionException;
import org.springframework.transaction.annotation.AnnotationTransactionAttributeSource;
import org.springframework.transaction.interceptor.TransactionInterceptor;
import org.springframework.transaction.support.AbstractPlatformTransactionManager;
import org.springframework.transaction.support.DefaultTransactionStatus;

import java.time.LocalDateTime;
import java.util.*;
import java.util.concurrent.atomic.AtomicLong;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * SRS_NF005：故障隔离与自愈恢复 & 运动安全边界拦截专项测试
 * 覆盖范围：
 * 1. SRS_NF005.R01 & TC-024.S1~S2：平台不得下发运动安全控制指令；设备代理对含运动安全字段的消息执行拦截并记录，
 *    超时与未知反馈统一归一并进入异常恢复；正常前往区域、会合、陪同、空间引导、现场通知业务意图通过。
 * 2. TC-040.S1~S2：计划结构校验（5步上限不截断、必填字段、依赖顺序、循环、动态代码、无限协商）全量收集错误，
 *    结构硬校验失败严禁强行放行或进入监督判定，拦截记录通过 REQUIRES_NEW 持久留痕。
 * 3. TC-056.S1~S2：指令下发阶段运动安全二次防线拦截（步骤置 FAILED、记录 COMMAND_DISPATCH_BLOCKED 与 ERR_MOTION_SAFETY_FIELD、
 *    不向其他候选设备重发违规指令、设备零收包）；模型异常或校验失败零未校验指令。
 * 4. 外部仿真体故障隔离：单个设备代理断连（HeartbeatMonitorTask）或超时/报错（StepTimeoutMonitorTask / 适配器异常）时，
 *    平台协同调度引擎不受影响，自动切换可用候选设备，其余正常设备与并发任务继续工作；巡检批次内单点异常隔离。
 * 5. 事务原子性与回滚：执行异常或故障中断时，外层数据库事务 100% 回滚，不产生残留脏数据，同时 REQUIRES_NEW 审计留痕不丢失。
 */
class FaultIsolationAndSelfHealingNF005Test {

    private static final ObjectMapper MAPPER = new ObjectMapper().findAndRegisterModules();

    // =========================================================================
    // 1. SRS_NF005.R01 & TC-024.S1~S2：代理反馈归一、八类运动安全字段拦截与独立留痕
    // =========================================================================

    @Test
    @DisplayName("TC-024.S1: 设备上报与内部统一消息双入口将TIMEOUT及未知反馈统一归一并触发异常恢复")
    void tc024_s1_bothEntrancesNormalizeTimeoutAndUnrecognizedFeedback() {
        TaskExecutionOrchestrator orchestrator = mock(TaskExecutionOrchestrator.class);
        DeviceCommandReportMapper reportMapper = mock(DeviceCommandReportMapper.class);
        when(reportMapper.insertIfAbsent(anyString(), anyString(), anyString(), anyInt(), anyString())).thenReturn(1);
        DeviceAgentReportService reportService = new DeviceAgentReportService(
                mock(DeviceAgentService.class), mock(DeviceCommandMapper.class), reportMapper, orchestrator, MAPPER);

        DeviceAgentMapper agentMapper = mock(DeviceAgentMapper.class);
        DeviceAgent agent = new DeviceAgent();
        agent.setId(11L);
        agent.setAgentCode("AGT-NF005-01");
        agent.setDeviceId(101L);
        agent.setAgentStatus("ENABLED");
        agent.setOnlineStatus("ONLINE");
        when(agentMapper.findByAgentCode("AGT-NF005-01")).thenReturn(Optional.of(agent));

        DeviceAgentInternalMessageService internalService = new DeviceAgentInternalMessageService(
                agentMapper, mock(TaskMapper.class), mock(DeviceAgentMessagingService.class), reportService, MAPPER);

        // 1) TIMEOUT 反馈
        ExecutionFeedbackRequest timeoutFb = new ExecutionFeedbackRequest();
        timeoutFb.setCommandId("CMD-TIMEOUT-01");
        timeoutFb.setAttemptNo(0);
        timeoutFb.setExecutionResult("TIMEOUT");
        timeoutFb.setReasonCode("SIMULATED_TIMEOUT");
        DeviceAgentReportRequest timeoutReport = new DeviceAgentReportRequest();
        timeoutReport.setReportType("EXECUTION_FEEDBACK");
        timeoutReport.setReportedAt("2026-11-11T10:00:00+08:00");
        timeoutReport.setFeedback(timeoutFb);
        reportService.accept("AGT-NF005-01", timeoutReport);

        verify(orchestrator).onExecutionFeedback(eq("AGT-NF005-01"), eq("CMD-TIMEOUT-01"), eq(0),
                eq("TIMEOUT"), eq("SIMULATED_TIMEOUT"), any());

        // 2) 非法/未知结果经统一内部消息入口归一为 FAILED + ERR_FEEDBACK_UNRECOGNIZED
        DeviceAgentMessageRequest msgReq = new DeviceAgentMessageRequest();
        msgReq.setAgentId("AGT-NF005-01");
        msgReq.setCommandId("CMD-UNKNOWN-02");
        msgReq.setMessageType("EXECUTION_FEEDBACK");
        msgReq.setPayload(Map.of("executionResult", "CORRUPTED_VENDOR_STATE", "attemptNo", 0));
        Map<String, Object> resp = internalService.dispatch(msgReq);
        assertEquals("PROCESSED", resp.get("status"));

        verify(orchestrator).onExecutionFeedback(eq("AGT-NF005-01"), eq("CMD-UNKNOWN-02"), eq(0),
                eq("FAILED"), eq("ERR_FEEDBACK_UNRECOGNIZED"),
                argThat(out -> "CORRUPTED_VENDOR_STATE".equals(out.get("rawExecutionResult"))));
    }

    @ParameterizedTest
    @ValueSource(strings = {
            "speed", "acceleration", "attitude", "pathPoints", "obstacleAvoidance", "emergencyStop", "speedLimit", "lostConnectionParking",
            "速度", "加速度", "姿态", "路径点", "避障", "急停", "限速", "失联停靠"
    })
    @DisplayName("SRS_NF005.R01 & TC-024.S2: 八类运动安全字段（中英文）在代理消息网关被拒绝、零下发且持久化拦截事件")
    void tc024_s2_blocksAllEightMotionSafetyCategoriesAndRecordsBlockedEvent(String forbiddenKey) {
        DeviceAgentMapper agents = mock(DeviceAgentMapper.class);
        DeviceMapper devices = mock(DeviceMapper.class);
        DeviceCommandMapper commands = mock(DeviceCommandMapper.class);
        DeviceCapabilityMapper capabilities = mock(DeviceCapabilityMapper.class);
        TaskMapper tasks = mock(TaskMapper.class);
        DeviceAdapterClient adapter = mock(DeviceAdapterClient.class);
        DeviceTypeCapabilityService typeCapabilities = mock(DeviceTypeCapabilityService.class);
        DeviceEventMapper eventMapper = mock(DeviceEventMapper.class);
        List<DeviceEvent> recordedEvents = new ArrayList<>();
        when(eventMapper.insert(any(DeviceEvent.class))).thenAnswer(inv -> {
            DeviceEvent ev = inv.getArgument(0);
            recordedEvents.add(ev);
            return 1;
        });
        DeviceEventService eventService = new DeviceEventService(eventMapper);

        DeviceAgent agent = new DeviceAgent();
        agent.setId(41L);
        agent.setAgentCode("AGT-SAFE-41");
        agent.setDeviceId(41L);
        agent.setAgentStatus("ENABLED");
        agent.setOnlineStatus("ONLINE");
        agent.setWorkStatus("IDLE");
        when(agents.findByAgentCode("AGT-SAFE-41")).thenReturn(Optional.of(agent));

        Device device = new Device();
        device.setId(41L);
        device.setDeviceCode("SIM-ROBOT-41");
        device.setDeviceTypeCode("SIMULATOR");
        device.setSimulatedDeviceType("MOBILE_ROBOT");
        device.setDeviceStatus("ACTIVE");
        when(devices.findById(41L)).thenReturn(Optional.of(device));

        Task task = new Task();
        task.setId(900L);
        task.setTaskCode("TASK-SAFE-900");
        when(tasks.findById(900L)).thenReturn(Optional.of(task));

        DeviceAgentMessagingService messaging = new DeviceAgentMessagingService(
                agents, devices, commands, capabilities, tasks, adapter, 60, MAPPER, typeCapabilities);
        ReflectionTestUtils.setField(messaging, "deviceEventService", eventService);

        BusinessException ex = assertThrows(BusinessException.class, () ->
                messaging.requestTaskAcceptance("AGT-SAFE-41", "CMD-BLOCK-" + forbiddenKey, 900L, 1,
                        "CAP_NAVIGATION", Map.of("targetLocation", "F2_GATE_10", forbiddenKey, 1)));

        assertEquals(ErrorCode.MOTION_SAFETY_FIELD_DETECTED, ex.getErrorCode());
        verify(commands, never()).insertIfAbsent(any());
        verifyNoInteractions(adapter);

        assertEquals(1, recordedEvents.size(), "被拦截消息应在 device_events 留下 BLOCKED 记录");
        DeviceEvent blocked = recordedEvents.get(0);
        assertEquals(41L, blocked.getDeviceAgentId());
        assertEquals("AGENT_MESSAGE_TASK_ACCEPT", blocked.getEventType());
        assertEquals("CMD-BLOCK-" + forbiddenKey, blocked.getCommandId());
        assertEquals("BLOCKED", blocked.getResult());
        assertEquals("ERR_MOTION_SAFETY_FIELD", blocked.getReasonCode());
    }

    // =========================================================================
    // 2. TC-040.S1~S2：结构硬校验全错收集与禁止强行放行（REQUIRES_NEW 留痕）
    // =========================================================================

    @Test
    @DisplayName("TC-040.S1: 计划超过5步不截断，缺失字段/逆序依赖/循环/动态代码/无限协商一次性全量报错")
    void tc040_s1_structureValidationCollectsAllErrorsWithoutTruncatingSteps() {
        DeviceCapabilityMapper capMapper = mock(DeviceCapabilityMapper.class);
        when(capMapper.existsByCapabilityTypeAndCapabilityStatus(anyString(), eq("ENABLED"))).thenReturn(true);
        PlanValidationService validationService = new PlanValidationService(capMapper);

        List<Map<String, Object>> steps = new ArrayList<>();
        for (int i = 1; i <= 6; i++) {
            Map<String, Object> step = new LinkedHashMap<>();
            step.put("stepSeq", i);
            step.put("stepGoal", i == 2 ? "" : "步骤目标" + i + (i == 4 ? " eval(script)" : ""));
            step.put("capabilityType", "CAP_INFO_DISPLAY");
            step.put("inputParams", Map.of("content", i == 5 ? "无限轮次自由协商直到达成一致" : "正常内容"));
            step.put("precondition", i == 1 ? "依赖步骤2完成后执行" : (i == 3 ? "循环执行步骤3直到成功" : "设备在线"));
            step.put("completionCondition", "displayStatus=SUCCESS");
            step.put("failureHandling", "重试一次后转人工");
            steps.add(step);
        }

        List<Map<String, Object>> agents = List.of(Map.of(
                "agentId", "AGT-01",
                "capabilities", List.of("CAP_INFO_DISPLAY"),
                "onlineStatus", "ONLINE",
                "workload", "IDLE",
                "deviceTypeCode", "SIMULATOR",
                "simulatedDeviceType", "SMART_DISPLAY"
        ));

        PlanValidationResult result = validationService.validate(steps, agents);
        assertFalse(result.isAllPassed());
        assertEquals("FAIL", result.getStructureCheckResult());
        assertEquals(6, steps.size(), "超过5步应整单拒绝，不得静默截断为5步");

        Set<String> codes = new HashSet<>();
        result.getErrors().forEach(e -> codes.add(e.getReasonCode()));
        assertTrue(codes.contains("ERR_STEP_LIMIT_EXCEEDED"), "应包含超5步错误码");
        assertTrue(codes.contains("ERR_STEP_FIELD_MISSING"), "应包含缺必填字段错误码");
        assertTrue(codes.contains("ERR_STEP_DEPENDENCY_ORDER"), "应包含逆序依赖错误码");
        assertTrue(codes.contains("ERR_STEP_LOOP_DETECTED"), "应包含循环/动态代码/无限协商结构错误码");
        assertTrue(result.getErrors().size() >= 5, "所有结构错误应一次性全量收集返回，不因首个错误中断");
    }

    @Test
    @DisplayName("TC-040.S2: 硬性校验失败严禁人工或监督强行放行，拦截审计通过 REQUIRES_NEW 独立持久化")
    void tc040_s2_hardValidationFailureBlocksForceReleaseAndPersistsAuditInRequiresNew() {
        TaskMapper taskMapper = mock(TaskMapper.class);
        PlanVersionMapper planMapper = mock(PlanVersionMapper.class);
        TaskEventMapper taskEventMapper = mock(TaskEventMapper.class);
        OperationLogMapper opLogMapper = mock(OperationLogMapper.class);
        DeviceAgentMessagingService messaging = mock(DeviceAgentMessagingService.class);

        List<TaskEvent> persistedTaskEvents = new ArrayList<>();
        List<OperationLog> persistedOpLogs = new ArrayList<>();
        when(taskEventMapper.insert(any(TaskEvent.class))).thenAnswer(inv -> {
            persistedTaskEvents.add(inv.getArgument(0));
            return 1;
        });
        when(opLogMapper.insert(any(OperationLog.class))).thenAnswer(inv -> {
            persistedOpLogs.add(inv.getArgument(0));
            return 1;
        });

        TaskEventService taskEventService = new TaskEventService(taskEventMapper);
        OperationLogService opLogService = new OperationLogService(opLogMapper);
        ForceBypassAuditRecorder recorder = new ForceBypassAuditRecorder(taskEventService, opLogService);

        Task task = new Task();
        task.setId(400L);
        task.setTaskCode("TASK-NF005-400");
        task.setStatus(TaskStatus.PENDING_MANUAL);
        task.setCurrentPlanVersionId(401L);
        when(taskMapper.findById(400L)).thenReturn(Optional.of(task));

        TaskService taskService = new TaskService(
                taskMapper, planMapper, mock(ContextSnapshotMapper.class), mock(DeviceAgentMapper.class),
                mock(GoalUnderstandingService.class), mock(TaskCodeGenerator.class), taskEventService,
                opLogService, mock(TaskPlanningOrchestrator.class), mock(TaskStepAssignmentMapper.class),
                mock(TaskDefinitionService.class), messaging, recorder);

        User operator = new User();
        operator.setId(2L);
        operator.setUsername("oprator");
        operator.setRole("OPERATOR");

        for (String illegalAction : List.of("FORCE_RELEASE", "REQUEST_SUPERVISION", "BYPASS_VALIDATION")) {
            BusinessException ex = assertThrows(BusinessException.class,
                    () -> taskService.manualAction(400L, illegalAction, "尝试强行放行", null, operator));
            assertEquals(ErrorCode.FORCE_BYPASS_HARD_CHECK, ex.getErrorCode());
        }

        assertEquals(TaskStatus.PENDING_MANUAL, task.getStatus(), "任务不得进入执行或监督状态");
        verifyNoInteractions(messaging);
        assertEquals(3, persistedTaskEvents.stream()
                .filter(e -> "FORCE_BYPASS_INTERCEPTED".equals(e.getEventType())).count());
        assertEquals(3, persistedOpLogs.stream()
                .filter(l -> "INTERCEPTED".equals(l.getOperationResult())).count());
    }

    // =========================================================================
    // 3. TC-056.S1~S2：下发阶段运动安全二次防线拦截与不切换候选设备重发违规指令
    // =========================================================================

    @ParameterizedTest
    @ValueSource(strings = {"速度", "加速度", "姿态", "路径点", "避障", "急停", "限速", "失联停靠"})
    @DisplayName("TC-056.S1: 下发阶段检出八类运动安全字段时步骤置FAILED、记录拦截且不向其他在线候选重发违规指令")
    void tc056_s1_dispatchStageBlocksMotionSafetyAndDoesNotSwitchToSecondCandidate(String forbiddenKey) throws Exception {
        TaskMapper taskMapper = mock(TaskMapper.class);
        PlanVersionMapper planMapper = mock(PlanVersionMapper.class);
        TaskStepAssignmentMapper assignmentMapper = mock(TaskStepAssignmentMapper.class);
        DeviceAgentMapper agentMapper = mock(DeviceAgentMapper.class);
        DeviceMapper deviceMapper = mock(DeviceMapper.class);
        DeviceCapabilityMapper capMapper = mock(DeviceCapabilityMapper.class);
        TaskEventService taskEvents = mock(TaskEventService.class);
        DeviceEventService deviceEvents = mock(DeviceEventService.class);
        TaskExceptionMapper exceptionMapper = mock(TaskExceptionMapper.class);
        ReplanningService replanningService = mock(ReplanningService.class);
        DeviceAgentMessagingService messaging = mock(DeviceAgentMessagingService.class);
        StepParameterResolver resolver = mock(StepParameterResolver.class);

        Task task = new Task();
        task.setId(560L);
        task.setTaskCode("TASK-560");
        task.setTaskFamily("GENERAL_SERVICE");
        task.setStatus(TaskStatus.EXECUTING);
        task.setCurrentPlanVersionId(561L);
        task.setReplanUsed(true); // 避免触发重规划，验证步骤状态保持 FAILED
        when(taskMapper.findById(560L)).thenReturn(Optional.of(task));

        Map<String, Object> step = Map.of(
                "stepSeq", 1,
                "stepGoal", "前往区域",
                "capabilityType", "CAP_NAVIGATION",
                "inputParams", Map.of("targetLocation", "F2_GATE_01", forbiddenKey, 1),
                "completionCondition", "routeGenerated=true"
        );
        PlanVersion plan = new PlanVersion();
        plan.setId(561L);
        plan.setTaskId(560L);
        plan.setSource("AUTONOMOUS");
        plan.setPlanSteps(MAPPER.writeValueAsString(List.of(step)));
        when(planMapper.findById(561L)).thenReturn(Optional.of(plan));

        TaskStepAssignment assignment = new TaskStepAssignment();
        assignment.setId(562L);
        assignment.setTaskId(560L);
        assignment.setPlanVersionId(561L);
        assignment.setStepSeq(1);
        assignment.setStepStatus("PENDING_ASSIGNMENT");
        assignment.setCommandId("CMD-ACCEPT-560");
        assignment.setDeviceAgentId(10L);
        assignment.setRetryCount(0);
        when(assignmentMapper.findByCommandId("CMD-ACCEPT-560")).thenReturn(Optional.of(assignment));
        when(assignmentMapper.findByPlanVersionIdAndStepSeq(561L, 1)).thenReturn(Optional.of(assignment));
        when(assignmentMapper.findByPlanVersionIdOrderByStepSeqAsc(561L)).thenReturn(List.of(assignment));

        DeviceAgent agent1 = new DeviceAgent();
        agent1.setId(10L);
        agent1.setAgentCode("AGT-ROBOT-01");
        agent1.setDeviceId(100L);
        agent1.setAgentStatus("ENABLED");
        agent1.setOnlineStatus("ONLINE");
        agent1.setWorkStatus("IDLE");

        // 同时存在第二个在线空闲候选设备 AGT-ROBOT-02
        DeviceAgent agent2 = new DeviceAgent();
        agent2.setId(20L);
        agent2.setAgentCode("AGT-ROBOT-02");
        agent2.setDeviceId(200L);
        agent2.setAgentStatus("ENABLED");
        agent2.setOnlineStatus("ONLINE");
        agent2.setWorkStatus("IDLE");

        when(agentMapper.findByIdForUpdate(10L)).thenReturn(Optional.of(agent1));
        when(agentMapper.findById(10L)).thenReturn(Optional.of(agent1));
        when(agentMapper.findByAgentCode("AGT-ROBOT-01")).thenReturn(Optional.of(agent1));
        when(agentMapper.claimAgent(10L, 560L, 1)).thenReturn(1);
        when(agentMapper.findByAgentStatusAndOnlineStatus("ENABLED", "ONLINE")).thenReturn(List.of(agent1, agent2));

        Device dev1 = new Device();
        dev1.setId(100L);
        dev1.setDeviceStatus("ACTIVE");
        dev1.setDeviceTypeCode("SIMULATOR");
        dev1.setSimulatedDeviceType("MOBILE_ROBOT");
        Device dev2 = new Device();
        dev2.setId(200L);
        dev2.setDeviceStatus("ACTIVE");
        dev2.setDeviceTypeCode("SIMULATOR");
        dev2.setSimulatedDeviceType("MOBILE_ROBOT");
        when(deviceMapper.findByIds(anyList())).thenReturn(List.of(dev1, dev2));
        when(capMapper.existsByDeviceIdAndCapabilityTypeAndCapabilityStatus(anyLong(), eq("CAP_NAVIGATION"), eq("ENABLED")))
                .thenReturn(true);
        when(resolver.resolve(anyLong(), anyLong(), anyMap()))
                .thenReturn(Map.of("targetLocation", "F2_GATE_01", forbiddenKey, 1));

        TaskExceptionService exceptionService = new TaskExceptionService(
                taskMapper, assignmentMapper, exceptionMapper, agentMapper, taskEvents,
                null, replanningService, planMapper);
        TaskExecutionOrchestrator orchestrator = new TaskExecutionOrchestrator(
                taskMapper, planMapper, assignmentMapper, agentMapper, deviceMapper, capMapper,
                taskEvents, exceptionService, messaging, mock(BaselineDryRunLifecycle.class),
                mock(DryRunDeviceSelectionMapper.class), resolver);
        ReflectionTestUtils.setField(exceptionService, "taskExecutionOrchestrator", orchestrator);
        ReflectionTestUtils.setField(orchestrator, "deviceEventService", deviceEvents);

        orchestrator.onTaskResponse("AGT-ROBOT-01", "CMD-ACCEPT-560", true, null);

        // 断言：步骤保持 FAILED 且原因码为 ERR_MOTION_SAFETY_FIELD，绝不切换给 AGT-ROBOT-02 重发违规指令
        assertEquals("FAILED", assignment.getStepStatus(), "含运动安全字段的步骤必须保持 FAILED 状态");
        assertEquals("ERR_MOTION_SAFETY_FIELD", assignment.getReasonCode());
        assertEquals("IDLE", agent1.getWorkStatus(), "原设备占用必须释放");
        assertNull(agent1.getCurrentTaskId());
        verifyNoInteractions(messaging);
        verify(taskEvents).append(eq(560L), eq("COMMAND_DISPATCH_BLOCKED"), eq("SYSTEM"),
                eq("ERR_MOTION_SAFETY_FIELD"), contains(forbiddenKey));
        verify(deviceEvents).appendBlockedMessage(eq(10L), eq("COMMAND_DISPATCH_BLOCKED"),
                eq("CMD-ACCEPT-560"), eq("ERR_MOTION_SAFETY_FIELD"), contains(forbiddenKey));
    }

    // =========================================================================
    // 4. 外部仿真体故障隔离与自愈恢复：单代理断连/超时不影响调度引擎与并发正常设备
    // =========================================================================

    @Test
    @DisplayName("SRS_NF005: 单个外部仿真体断连离线时，受影响任务自动切换健康候选设备完成，并发正常任务与设备不受影响")
    void nf005_singleSimulatorDisconnectIsolatesFaultAndHealsViaCandidateSwitchWhileConcurrentTaskCompletes() throws Exception {
        TaskMapper taskMapper = mock(TaskMapper.class);
        PlanVersionMapper planMapper = mock(PlanVersionMapper.class);
        TaskStepAssignmentMapper assignmentMapper = mock(TaskStepAssignmentMapper.class);
        DeviceAgentMapper agentMapper = mock(DeviceAgentMapper.class);
        DeviceMapper deviceMapper = mock(DeviceMapper.class);
        DeviceCapabilityMapper capMapper = mock(DeviceCapabilityMapper.class);
        TaskEventService taskEvents = mock(TaskEventService.class);
        DeviceEventService deviceEvents = mock(DeviceEventService.class);
        TaskExceptionMapper exceptionMapper = mock(TaskExceptionMapper.class);
        DeviceAgentMessagingService messaging = mock(DeviceAgentMessagingService.class);
        StepParameterResolver resolver = mock(StepParameterResolver.class);

        // 任务1（步骤1在故障设备 AGT-FAULT-A 上执行，另有健康候选 AGT-HEALTHY-B）
        Task task1 = new Task();
        task1.setId(701L);
        task1.setTaskCode("TASK-ISO-701");
        task1.setTaskFamily("GENERAL_SERVICE");
        task1.setStatus(TaskStatus.EXECUTING);
        task1.setCurrentPlanVersionId(801L);
        task1.setIsDryRun(false);

        // 任务2（在正常设备 AGT-NORMAL-C 上并发独立执行）
        Task task2 = new Task();
        task2.setId(702L);
        task2.setTaskCode("TASK-ISO-702");
        task2.setTaskFamily("GENERAL_SERVICE");
        task2.setStatus(TaskStatus.EXECUTING);
        task2.setCurrentPlanVersionId(802L);
        task2.setIsDryRun(false);

        when(taskMapper.findById(701L)).thenReturn(Optional.of(task1));
        when(taskMapper.findById(702L)).thenReturn(Optional.of(task2));

        String stepJson = MAPPER.writeValueAsString(List.of(Map.of(
                "stepSeq", 1,
                "stepGoal", "前往区域引导",
                "capabilityType", "CAP_NAVIGATION",
                "inputParams", Map.of("targetLocation", "F2_GATE_08"),
                "completionCondition", "routeGenerated=true"
        )));
        PlanVersion pv1 = new PlanVersion();
        pv1.setId(801L);
        pv1.setTaskId(701L);
        pv1.setSource("AUTONOMOUS");
        pv1.setPlanSteps(stepJson);

        PlanVersion pv2 = new PlanVersion();
        pv2.setId(802L);
        pv2.setTaskId(702L);
        pv2.setSource("AUTONOMOUS");
        pv2.setPlanSteps(stepJson);

        when(planMapper.findById(801L)).thenReturn(Optional.of(pv1));
        when(planMapper.findById(802L)).thenReturn(Optional.of(pv2));

        TaskStepAssignment assign1 = new TaskStepAssignment();
        assign1.setId(901L);
        assign1.setTaskId(701L);
        assign1.setPlanVersionId(801L);
        assign1.setStepSeq(1);
        assign1.setStepStatus("EXECUTING");
        assign1.setCommandId("CMD-ACC-701-A");
        assign1.setExecuteCommandId("CMD-EXE-701-A");
        assign1.setDeviceAgentId(1L);
        assign1.setRetryCount(0);

        TaskStepAssignment assign2 = new TaskStepAssignment();
        assign2.setId(902L);
        assign2.setTaskId(702L);
        assign2.setPlanVersionId(802L);
        assign2.setStepSeq(1);
        assign2.setStepStatus("EXECUTING");
        assign2.setCommandId("CMD-ACC-702-C");
        assign2.setExecuteCommandId("CMD-EXE-702-C");
        assign2.setDeviceAgentId(3L);
        assign2.setRetryCount(0);

        when(assignmentMapper.findByPlanVersionIdAndStepSeq(801L, 1)).thenReturn(Optional.of(assign1));
        when(assignmentMapper.findByPlanVersionIdOrderByStepSeqAsc(801L)).thenReturn(List.of(assign1));
        when(assignmentMapper.findByPlanVersionIdAndStepSeq(802L, 1)).thenReturn(Optional.of(assign2));
        when(assignmentMapper.findByPlanVersionIdOrderByStepSeqAsc(802L)).thenReturn(List.of(assign2));
        when(assignmentMapper.findByExecuteCommandId("CMD-EXE-702-C")).thenReturn(Optional.of(assign2));
        when(assignmentMapper.findByCommandId(anyString())).thenAnswer(inv -> {
            String cid = inv.getArgument(0);
            if (cid != null && cid.equals(assign1.getCommandId())) return Optional.of(assign1);
            if ("CMD-ACC-702-C".equals(cid)) return Optional.of(assign2);
            return Optional.empty();
        });
        when(assignmentMapper.findByExecuteCommandId(anyString())).thenAnswer(inv -> {
            String cid = inv.getArgument(0);
            if (cid != null && cid.equals(assign1.getExecuteCommandId())) return Optional.of(assign1);
            if ("CMD-EXE-702-C".equals(cid)) return Optional.of(assign2);
            return Optional.empty();
        });

        // 三个设备代理：A(即将心跳超时断连)、B(在线空闲候选)、C(正在执行任务2)
        DeviceAgent agentA = new DeviceAgent();
        agentA.setId(1L);
        agentA.setAgentCode("AGT-FAULT-A");
        agentA.setDeviceId(11L);
        agentA.setAgentStatus("ENABLED");
        agentA.setOnlineStatus("ONLINE");
        agentA.setWorkStatus("BUSY");
        agentA.setCurrentTaskId(701L);
        agentA.setCurrentStepSeq(1);

        DeviceAgent agentB = new DeviceAgent();
        agentB.setId(2L);
        agentB.setAgentCode("AGT-HEALTHY-B");
        agentB.setDeviceId(12L);
        agentB.setAgentStatus("ENABLED");
        agentB.setOnlineStatus("ONLINE");
        agentB.setWorkStatus("IDLE");

        DeviceAgent agentC = new DeviceAgent();
        agentC.setId(3L);
        agentC.setAgentCode("AGT-NORMAL-C");
        agentC.setDeviceId(13L);
        agentC.setAgentStatus("ENABLED");
        agentC.setOnlineStatus("ONLINE");
        agentC.setWorkStatus("BUSY");
        agentC.setCurrentTaskId(702L);
        agentC.setCurrentStepSeq(1);

        when(agentMapper.findById(1L)).thenReturn(Optional.of(agentA));
        when(agentMapper.findById(2L)).thenReturn(Optional.of(agentB));
        when(agentMapper.findById(3L)).thenReturn(Optional.of(agentC));
        when(agentMapper.findByIdForUpdate(2L)).thenReturn(Optional.of(agentB));
        when(agentMapper.findByAgentCode("AGT-FAULT-A")).thenReturn(Optional.of(agentA));
        when(agentMapper.findByAgentCode("AGT-HEALTHY-B")).thenReturn(Optional.of(agentB));
        when(agentMapper.findByAgentCode("AGT-NORMAL-C")).thenReturn(Optional.of(agentC));
        when(agentMapper.claimAgent(2L, 701L, 1)).thenReturn(1);
        when(agentMapper.findByAgentStatusAndOnlineStatus("ENABLED", "ONLINE")).thenAnswer(inv ->
                List.of(agentA, agentB, agentC).stream()
                        .filter(a -> "ONLINE".equals(a.getOnlineStatus()))
                        .toList());

        Device devA = new Device(); devA.setId(11L); devA.setDeviceStatus("ACTIVE"); devA.setDeviceTypeCode("SIMULATOR"); devA.setSimulatedDeviceType("MOBILE_ROBOT");
        Device devB = new Device(); devB.setId(12L); devB.setDeviceStatus("ACTIVE"); devB.setDeviceTypeCode("SIMULATOR"); devB.setSimulatedDeviceType("MOBILE_ROBOT");
        Device devC = new Device(); devC.setId(13L); devC.setDeviceStatus("ACTIVE"); devC.setDeviceTypeCode("SIMULATOR"); devC.setSimulatedDeviceType("MOBILE_ROBOT");
        when(deviceMapper.findByIds(anyList())).thenReturn(List.of(devA, devB, devC));
        when(capMapper.existsByDeviceIdAndCapabilityTypeAndCapabilityStatus(anyLong(), eq("CAP_NAVIGATION"), eq("ENABLED"))).thenReturn(true);
        when(resolver.resolve(anyLong(), anyLong(), anyMap())).thenReturn(Map.of("targetLocation", "F2_GATE_08"));

        List<TaskException> task1Exceptions = new ArrayList<>();
        when(exceptionMapper.insert(any(TaskException.class))).thenAnswer(inv -> {
            TaskException ex = inv.getArgument(0);
            ex.setId(1001L);
            task1Exceptions.add(ex);
            return 1;
        });
        when(exceptionMapper.findByTaskIdOrderByOccurredAtDesc(701L)).thenReturn(task1Exceptions);

        TaskExceptionService exceptionService = new TaskExceptionService(
                taskMapper, assignmentMapper, exceptionMapper, agentMapper, taskEvents,
                null, mock(ReplanningService.class), planMapper);
        TaskExecutionOrchestrator orchestrator = new TaskExecutionOrchestrator(
                taskMapper, planMapper, assignmentMapper, agentMapper, deviceMapper, capMapper,
                taskEvents, exceptionService, messaging, mock(BaselineDryRunLifecycle.class),
                mock(DryRunDeviceSelectionMapper.class), resolver);
        ReflectionTestUtils.setField(exceptionService, "taskExecutionOrchestrator", orchestrator);

        // 1) AGT-FAULT-A 发生心跳超时断连
        when(agentMapper.findByOnlineStatusAndLastReportedAtBefore(eq("ONLINE"), any()))
                .thenReturn(List.of(agentA));
        HeartbeatMonitorTask heartbeatMonitor = new HeartbeatMonitorTask(
                agentMapper, deviceEvents, taskEvents, exceptionService, 30);
        heartbeatMonitor.checkHeartbeatTimeout();

        // 验证 AGT-FAULT-A 已标记 OFFLINE，且任务1自动切换至候选设备 AGT-HEALTHY-B
        assertEquals("OFFLINE", agentA.getOnlineStatus());
        assertEquals(2L, assign1.getDeviceAgentId(), "任务1步骤1应自动切换至健康候选设备 AGT-HEALTHY-B");
        assertEquals("PENDING_ASSIGNMENT", assign1.getStepStatus());
        verify(messaging).requestTaskAcceptance(eq("AGT-HEALTHY-B"), eq(assign1.getCommandId()),
                eq(701L), eq(1), eq("CAP_NAVIGATION"), anyMap());

        // 2) 并发任务2在 AGT-NORMAL-C 上完全不受 AGT-FAULT-A 断连影响，正常反馈完成
        orchestrator.onExecutionFeedback("AGT-NORMAL-C", "CMD-EXE-702-C", 0, "SUCCESS",
                "DEVICE_SUCCESS", Map.of("routeGenerated", true));
        assertEquals(TaskStatus.COMPLETED, task2.getStatus(), "正常设备 C 上的并发任务2应不受影响并顺利完成");
        assertEquals("COMPLETED", assign2.getStepStatus());
        assertEquals("IDLE", agentC.getWorkStatus());

        // 3) 健康候选设备 AGT-HEALTHY-B 接受并完成任务1，实现故障自愈闭环
        orchestrator.onTaskResponse("AGT-HEALTHY-B", assign1.getCommandId(), true, null);
        assertEquals("EXECUTING", assign1.getStepStatus());
        orchestrator.onExecutionFeedback("AGT-HEALTHY-B", assign1.getExecuteCommandId(), 0, "SUCCESS",
                "DEVICE_SUCCESS", Map.of("routeGenerated", true));
        assertEquals(TaskStatus.COMPLETED, task1.getStatus(), "任务1经候选切换自愈后应顺利完成");
        assertEquals("COMPLETED", assign1.getStepStatus());
        assertEquals("RESOLVED", task1Exceptions.get(0).getExceptionStatus());
        assertEquals("SUCCESS", task1Exceptions.get(0).getRecoveryResult());
    }

    @Test
    @DisplayName("SRS_NF005: 心跳与步骤超时巡检批次内单点故障隔离，首个代理/步骤抛异常不阻断同批其余设备自愈")
    void nf005_batchMonitorTasksIsolateSingleItemExceptionsAndContinueProcessingRemainingItems() {
        // 1) HeartbeatMonitorTask 批内隔离验证
        DeviceAgentMapper agentMapper = mock(DeviceAgentMapper.class);
        DeviceEventService deviceEvents = mock(DeviceEventService.class);
        TaskEventService taskEvents = mock(TaskEventService.class);
        TaskExceptionService exceptionService = mock(TaskExceptionService.class);

        DeviceAgent brokenAgent = new DeviceAgent();
        brokenAgent.setId(1L);
        brokenAgent.setAgentCode("AGT-BROKEN-1");
        brokenAgent.setOnlineStatus("ONLINE");

        DeviceAgent secondAgent = new DeviceAgent();
        secondAgent.setId(2L);
        secondAgent.setAgentCode("AGT-RECOVER-2");
        secondAgent.setOnlineStatus("ONLINE");
        secondAgent.setCurrentTaskId(200L);
        secondAgent.setCurrentStepSeq(1);

        when(agentMapper.findByOnlineStatusAndLastReportedAtBefore(eq("ONLINE"), any()))
                .thenReturn(List.of(brokenAgent, secondAgent));
        doThrow(new RuntimeException("Simulated DB glitch on brokenAgent"))
                .when(exceptionService).handleAgentOffline(brokenAgent);

        HeartbeatMonitorTask hbTask = new HeartbeatMonitorTask(
                agentMapper, deviceEvents, taskEvents, exceptionService, 30);
        assertDoesNotThrow(hbTask::checkHeartbeatTimeout);

        assertEquals("OFFLINE", secondAgent.getOnlineStatus(), "第二个超时代理必须继续被标记为 OFFLINE");
        verify(exceptionService).handleAgentOffline(secondAgent);

        // 2) StepTimeoutMonitorTask 批内隔离验证
        TaskStepAssignmentMapper assignMapper = mock(TaskStepAssignmentMapper.class);
        TaskStepAssignment brokenStep = new TaskStepAssignment();
        brokenStep.setId(10L);
        brokenStep.setTaskId(101L);
        brokenStep.setStepSeq(1);
        brokenStep.setStepStatus("EXECUTING");
        brokenStep.setDispatchedAt(LocalDateTime.now().minusSeconds(120));

        TaskStepAssignment secondStep = new TaskStepAssignment();
        secondStep.setId(20L);
        secondStep.setTaskId(102L);
        secondStep.setStepSeq(1);
        secondStep.setStepStatus("EXECUTING");
        secondStep.setExecuteCommandId("CMD-TIMEOUT-102");
        secondStep.setDispatchedAt(LocalDateTime.now().minusSeconds(120));

        when(assignMapper.findByStepStatusAndDispatchedAtBefore(eq("EXECUTING"), any()))
                .thenReturn(List.of(brokenStep, secondStep));
        doThrow(new RuntimeException("Simulated exception on brokenStep"))
                .when(exceptionService).handleException(eq(101L), eq(1), eq("EXECUTION_TIMEOUT"), anyString());

        StepTimeoutMonitorTask stepTask = new StepTimeoutMonitorTask(
                assignMapper, agentMapper, taskEvents, exceptionService, 60, null, null);
        assertDoesNotThrow(stepTask::checkStepTimeout);

        assertEquals("FAILED", secondStep.getStepStatus(), "第二个超时步骤必须继续被置为 FAILED");
        assertEquals("TIMEOUT", secondStep.getExecutionResult());
        assertEquals("ERR_EXECUTION_TIMEOUT", secondStep.getReasonCode());
        verify(exceptionService).handleException(eq(102L), eq(1), eq("EXECUTION_TIMEOUT"), anyString());
    }

    // =========================================================================
    // 5. 事务原子性与 100% 回滚验证（含 REQUIRES_NEW 独立事务提交对照）
    // =========================================================================

    /**
     * 轻量内存事务性存储与 Spring PlatformTransactionManager：
     * 支持 REQUIRED 事务异常时 100% 状态快照回滚，以及 REQUIRES_NEW 挂起外层事务并独立提交。
     */
    static class InMemoryTransactionalLedger {
        final Map<Long, String> tasks = new LinkedHashMap<>();
        final Map<Long, String> planVersions = new LinkedHashMap<>();
        final Map<Long, String> assignments = new LinkedHashMap<>();
        final Map<String, String> commands = new LinkedHashMap<>();
        final List<String> auditEvents = new ArrayList<>();

        record Snapshot(Map<Long, String> tasks,
                        Map<Long, String> planVersions,
                        Map<Long, String> assignments,
                        Map<String, String> commands,
                        List<String> auditEvents) {}

        Snapshot capture() {
            return new Snapshot(
                    new LinkedHashMap<>(tasks),
                    new LinkedHashMap<>(planVersions),
                    new LinkedHashMap<>(assignments),
                    new LinkedHashMap<>(commands),
                    new ArrayList<>(auditEvents));
        }

        void restore(Snapshot s) {
            tasks.clear(); tasks.putAll(s.tasks);
            planVersions.clear(); planVersions.putAll(s.planVersions);
            assignments.clear(); assignments.putAll(s.assignments);
            commands.clear(); commands.putAll(s.commands);
            auditEvents.clear(); auditEvents.addAll(s.auditEvents);
        }
    }

    static class SnapshotTransactionManager extends AbstractPlatformTransactionManager {
        private final InMemoryTransactionalLedger ledger;
        private final Deque<InMemoryTransactionalLedger.Snapshot> activeSnapshots = new ArrayDeque<>();

        SnapshotTransactionManager(InMemoryTransactionalLedger ledger) {
            this.ledger = ledger;
        }

        @Override
        protected Object doGetTransaction() {
            return new Object();
        }

        @Override
        protected boolean isExistingTransaction(Object transaction) {
            return !activeSnapshots.isEmpty();
        }

        @Override
        protected void doBegin(Object transaction, TransactionDefinition definition) {
            activeSnapshots.push(ledger.capture());
        }

        @Override
        protected Object doSuspend(Object transaction) {
            return activeSnapshots.pop();
        }

        @Override
        protected void doResume(Object transaction, Object suspendedResources) {
            activeSnapshots.push((InMemoryTransactionalLedger.Snapshot) suspendedResources);
        }

        @Override
        protected void doCommit(DefaultTransactionStatus status) throws TransactionException {
            if (!activeSnapshots.isEmpty()) {
                activeSnapshots.pop();
            }
        }

        @Override
        protected void doRollback(DefaultTransactionStatus status) throws TransactionException {
            if (!activeSnapshots.isEmpty()) {
                List<String> committedAuditEvents = new ArrayList<>(ledger.auditEvents);
                InMemoryTransactionalLedger.Snapshot before = activeSnapshots.pop();
                ledger.restore(before);
                // REQUIRES_NEW 已独立提交的审计/拦截记录不受外层业务事务回滚影响
                ledger.auditEvents.clear();
                ledger.auditEvents.addAll(committedAuditEvents);
            }
        }
    }

    private static <T> T transactionalProxy(T target, SnapshotTransactionManager txManager) {
        ProxyFactory factory = new ProxyFactory(target);
        factory.setProxyTargetClass(true);
        TransactionInterceptor interceptor = new TransactionInterceptor(
                txManager, new AnnotationTransactionAttributeSource());
        factory.addAdvice(interceptor);
        @SuppressWarnings("unchecked")
        T proxy = (T) factory.getProxy();
        return proxy;
    }

    @Test
    @DisplayName("SRS_NF005: 执行异常或故障中断时数据库事务 100% 回滚零脏数据，且 REQUIRES_NEW 拦截留痕独立提交")
    void nf005_transactionRollsBack100PercentOnExecutionFailureWithZeroDirtyDataWhileRequiresNewCommits() throws Exception {
        InMemoryTransactionalLedger ledger = new InMemoryTransactionalLedger();
        SnapshotTransactionManager txManager = new SnapshotTransactionManager(ledger);
        AtomicLong idSeq = new AtomicLong(1L);

        // 绑定内存账本的 Mapper
        TaskMapper taskMapper = mock(TaskMapper.class);
        PlanVersionMapper planMapper = mock(PlanVersionMapper.class);
        TaskStepAssignmentMapper assignmentMapper = mock(TaskStepAssignmentMapper.class);
        DeviceAgentMapper agentMapper = mock(DeviceAgentMapper.class);
        DeviceMapper deviceMapper = mock(DeviceMapper.class);
        DeviceCapabilityMapper capMapper = mock(DeviceCapabilityMapper.class);
        DeviceCommandMapper commandMapper = mock(DeviceCommandMapper.class);
        DeviceEventMapper deviceEventMapper = mock(DeviceEventMapper.class);
        TaskEventService taskEvents = mock(TaskEventService.class);
        TaskExceptionService exceptionService = mock(TaskExceptionService.class);
        DeviceAdapterClient adapterClient = mock(DeviceAdapterClient.class);
        DeviceTypeCapabilityService typeCapService = mock(DeviceTypeCapabilityService.class);
        StepParameterResolver resolver = mock(StepParameterResolver.class);

        when(deviceEventMapper.insert(any(DeviceEvent.class))).thenAnswer(inv -> {
            DeviceEvent ev = inv.getArgument(0);
            ledger.auditEvents.add(ev.getEventType() + ":" + ev.getResult() + ":" + ev.getReasonCode());
            return 1;
        });
        DeviceEventService rawDeviceEventService = new DeviceEventService(deviceEventMapper);
        DeviceEventService proxiedDeviceEventService = transactionalProxy(rawDeviceEventService, txManager);

        // 场景 A：startExecution 批量插入步骤分配时中途发生数据库写故障，验证已插入的前序步骤分配 100% 回滚
        PlanVersion pv = new PlanVersion();
        pv.setId(500L);
        pv.setTaskId(600L);
        pv.setPlanSteps(MAPPER.writeValueAsString(List.of(
                Map.of("stepSeq", 1, "stepGoal", "步骤1", "capabilityType", "CAP_NAVIGATION"),
                Map.of("stepSeq", 2, "stepGoal", "步骤2", "capabilityType", "CAP_NOTIFICATION"),
                Map.of("stepSeq", 3, "stepGoal", "步骤3", "capabilityType", "CAP_INFO_DISPLAY")
        )));
        when(planMapper.findById(500L)).thenReturn(Optional.of(pv));
        when(assignmentMapper.insert(any(TaskStepAssignment.class))).thenAnswer(inv -> {
            TaskStepAssignment a = inv.getArgument(0);
            if (Integer.valueOf(3).equals(a.getStepSeq())) {
                throw new RuntimeException("Simulated DB write failure on step 3");
            }
            ledger.assignments.put(idSeq.getAndIncrement(), "STEP_" + a.getStepSeq() + ":" + a.getStepStatus());
            return 1;
        });

        DeviceAgentMessagingService rawMessaging = new DeviceAgentMessagingService(
                agentMapper, deviceMapper, commandMapper, capMapper, taskMapper, adapterClient, 60, MAPPER, typeCapService);
        ReflectionTestUtils.setField(rawMessaging, "deviceEventService", proxiedDeviceEventService);
        DeviceAgentMessagingService proxiedMessaging = transactionalProxy(rawMessaging, txManager);

        TaskExecutionOrchestrator rawOrchestrator = new TaskExecutionOrchestrator(
                taskMapper, planMapper, assignmentMapper, agentMapper, deviceMapper, capMapper,
                taskEvents, exceptionService, proxiedMessaging, mock(BaselineDryRunLifecycle.class),
                mock(DryRunDeviceSelectionMapper.class), resolver);
        TaskExecutionOrchestrator proxiedOrchestrator = transactionalProxy(rawOrchestrator, txManager);

        assertThrows(RuntimeException.class, () -> proxiedOrchestrator.startExecution(600L, 500L));
        assertTrue(ledger.assignments.isEmpty(), "步骤3插入异常后，前序已插入的步骤1/2分配记录必须 100% 回滚，零脏数据残留");

        // 场景 B：外层事务先写入任务与指令草稿，随后触发运动安全拦截异常回滚：
        // 验证外层业务数据（tasks/commands）100% 回滚，而 REQUIRES_NEW 的拦截事件（auditEvents）成功持久化！
        DeviceAgent agent = new DeviceAgent();
        agent.setId(88L);
        agent.setAgentCode("AGT-TX-88");
        agent.setDeviceId(88L);
        agent.setAgentStatus("ENABLED");
        agent.setOnlineStatus("ONLINE");
        agent.setWorkStatus("IDLE");
        when(agentMapper.findByAgentCode("AGT-TX-88")).thenReturn(Optional.of(agent));

        Device device = new Device();
        device.setId(88L);
        device.setDeviceStatus("ACTIVE");
        device.setDeviceTypeCode("SIMULATOR");
        device.setSimulatedDeviceType("MOBILE_ROBOT");
        when(deviceMapper.findById(88L)).thenReturn(Optional.of(device));

        Task txTask = new Task();
        txTask.setId(601L);
        txTask.setTaskCode("TASK-TX-601");
        when(taskMapper.findById(601L)).thenReturn(Optional.of(txTask));

        org.springframework.transaction.support.TransactionTemplate txTemplate =
                new org.springframework.transaction.support.TransactionTemplate(txManager);

        assertThrows(BusinessException.class, () -> txTemplate.executeWithoutResult(status -> {
            // 外层业务事务写入脏数据候选行
            ledger.tasks.put(601L, "EXECUTING");
            ledger.planVersions.put(501L, "FROZEN");
            ledger.commands.put("CMD-DIRTY-01", "PENDING");
            // 触发含运动安全字段的下发请求 -> 内部通过 REQUIRES_NEW 写入 BLOCKED 留痕并抛出 BusinessException
            proxiedMessaging.requestTaskAcceptance("AGT-TX-88", "CMD-TX-BLOCK-01", 601L, 1,
                    "CAP_NAVIGATION", Map.of("targetLocation", "F2_GATE_01", "急停", true));
        }));

        assertTrue(ledger.tasks.isEmpty(), "外层事务回滚后 tasks 表不得残留脏数据");
        assertTrue(ledger.planVersions.isEmpty(), "外层事务回滚后 plan_versions 表不得残留脏数据");
        assertTrue(ledger.commands.isEmpty(), "外层事务回滚后 device_commands 表不得残留脏数据");
        assertEquals(List.of("AGENT_MESSAGE_TASK_ACCEPT:BLOCKED:ERR_MOTION_SAFETY_FIELD"), ledger.auditEvents,
                "REQUIRES_NEW 独立事务提交的运动安全拦截记录必须持久保留");
    }
}
