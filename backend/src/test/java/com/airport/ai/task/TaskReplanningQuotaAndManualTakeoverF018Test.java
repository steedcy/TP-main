package com.airport.ai.task;

import com.airport.ai.baseline.BaselineTemplateService;
import com.airport.ai.device.DeviceAgent;
import com.airport.ai.device.DeviceAgentMapper;
import com.airport.ai.device.DeviceAgentMessagingService;
import com.airport.ai.device.DeviceCommandMapper;
import com.airport.ai.event.TaskEventService;
import com.airport.ai.planning.PlanningModelService;
import com.airport.ai.planning.PlanningResponse;
import com.airport.ai.risk.RiskAssessmentService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.test.util.ReflectionTestUtils;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * SRS_F018 专项单元测试：
 * 1. 执行超时与硬件报错识别 (TC-058.S2 / SRS_F018.R01/R07)
 * 2. 局部单次重规划配额消耗控制 (TC-059.S1 / SRS_F018.R03 / SRS_F019.R01)
 * 3. 局部重规划二次失败后直接触发转人工接管 (TC-059.S1 / SRS_F018.R03)
 */
class TaskReplanningQuotaAndManualTakeoverF018Test {

    private TaskMapper taskMapper;
    private TaskStepAssignmentMapper assignmentMapper;
    private TaskExceptionMapper taskExceptionMapper;
    private TaskEventService taskEventService;
    private DeviceAgentMapper deviceAgentMapper;
    private TaskExecutionOrchestrator orchestrator;
    private ReplanningService replanningService;
    private PlanVersionMapper planVersionMapper;
    private TaskExceptionService exceptionService;
    private DeviceAgentMessagingService messagingService;
    private PlanningModelService planningModelService;

    @BeforeEach
    void setUp() {
        taskMapper = mock(TaskMapper.class);
        assignmentMapper = mock(TaskStepAssignmentMapper.class);
        taskExceptionMapper = mock(TaskExceptionMapper.class);
        taskEventService = mock(TaskEventService.class);
        deviceAgentMapper = mock(DeviceAgentMapper.class);
        orchestrator = mock(TaskExecutionOrchestrator.class);
        replanningService = mock(ReplanningService.class);
        planVersionMapper = mock(PlanVersionMapper.class);
        messagingService = mock(DeviceAgentMessagingService.class);
        planningModelService = mock(PlanningModelService.class);

        exceptionService = new TaskExceptionService(
                taskMapper, assignmentMapper, taskExceptionMapper,
                deviceAgentMapper, taskEventService, orchestrator,
                replanningService, planVersionMapper);
    }

    // ==========================================
    // 1. 执行超时与硬件报错识别
    // ==========================================

    @Test
    @DisplayName("执行反馈返回TIMEOUT结果时，正确识别为EXECUTION_TIMEOUT异常并记录时间线")
    void executionFeedbackTimeoutIsIdentifiedAsExecutionTimeoutException() {
        var orchestratorReal = new TaskExecutionOrchestrator(
                taskMapper, planVersionMapper, assignmentMapper,
                deviceAgentMapper, mock(com.airport.ai.device.DeviceMapper.class),
                mock(com.airport.ai.device.DeviceCapabilityMapper.class),
                taskEventService, exceptionService, messagingService,
                mock(com.airport.ai.baseline.BaselineDryRunLifecycle.class),
                mock(com.airport.ai.baseline.DryRunDeviceSelectionMapper.class),
                mock(StepParameterResolver.class));

        TaskStepAssignment assignment = new TaskStepAssignment();
        assignment.setId(101L);
        assignment.setTaskId(200L);
        assignment.setPlanVersionId(10L);
        assignment.setStepSeq(1);
        assignment.setExecuteCommandId("EXEC-CMD-TIMEOUT-1");
        assignment.setDeviceAgentId(1L);
        assignment.setStepStatus("EXECUTING");
        assignment.setRetryCount(1); // 重试已耗尽

        when(assignmentMapper.findByExecuteCommandId("EXEC-CMD-TIMEOUT-1")).thenReturn(Optional.of(assignment));

        DeviceAgent agent = new DeviceAgent();
        agent.setId(1L);
        agent.setAgentCode("ROBOT-01");
        when(deviceAgentMapper.findByAgentCode("ROBOT-01")).thenReturn(Optional.of(agent));

        PlanVersion plan = new PlanVersion();
        plan.setId(10L);
        plan.setPlanSteps("[{\"stepSeq\":1,\"capabilityType\":\"CAP_CLEAN\",\"completionCondition\":\"status=SUCCESS\"}]");
        when(planVersionMapper.findById(10L)).thenReturn(Optional.of(plan));

        Task task = new Task();
        task.setId(200L);
        task.setStatus(TaskStatus.EXECUTING);
        task.setCurrentPlanVersionId(10L);
        when(taskMapper.findById(200L)).thenReturn(Optional.of(task));

        // 反馈为 TIMEOUT
        orchestratorReal.onExecutionFeedback("ROBOT-01", "EXEC-CMD-TIMEOUT-1", 1, "TIMEOUT", "ERR_EXECUTION_TIMEOUT", Map.of());

        // 验证记录了 STEP_TIMEOUT_DETECTED 事件并进入 handleException("EXECUTION_TIMEOUT")
        verify(taskEventService).append(eq(200L), eq("STEP_TIMEOUT_DETECTED"), eq("SYSTEM"), eq("ERR_EXECUTION_TIMEOUT"), contains("重试后仍失败"));
        ArgumentCaptor<TaskException> exCaptor = ArgumentCaptor.forClass(TaskException.class);
        verify(taskExceptionMapper).insert(exCaptor.capture());
        assertEquals("EXECUTION_TIMEOUT", exCaptor.getValue().getExceptionType());
    }

    @Test
    @DisplayName("设备反馈硬件报错(HARDWARE_ERROR)时，识别为STEP_FAILED并包含硬件报错原因码")
    void executionFeedbackHardwareErrorIsIdentifiedAsStepFailedWithReasonCode() {
        var orchestratorReal = new TaskExecutionOrchestrator(
                taskMapper, planVersionMapper, assignmentMapper,
                deviceAgentMapper, mock(com.airport.ai.device.DeviceMapper.class),
                mock(com.airport.ai.device.DeviceCapabilityMapper.class),
                taskEventService, exceptionService, messagingService,
                mock(com.airport.ai.baseline.BaselineDryRunLifecycle.class),
                mock(com.airport.ai.baseline.DryRunDeviceSelectionMapper.class),
                mock(StepParameterResolver.class));

        TaskStepAssignment assignment = new TaskStepAssignment();
        assignment.setId(102L);
        assignment.setTaskId(201L);
        assignment.setPlanVersionId(10L);
        assignment.setStepSeq(2);
        assignment.setExecuteCommandId("EXEC-CMD-HW-1");
        assignment.setDeviceAgentId(2L);
        assignment.setStepStatus("EXECUTING");
        assignment.setRetryCount(1); // 重试已耗尽

        when(assignmentMapper.findByExecuteCommandId("EXEC-CMD-HW-1")).thenReturn(Optional.of(assignment));

        DeviceAgent agent = new DeviceAgent();
        agent.setId(2L);
        agent.setAgentCode("ROBOT-02");
        when(deviceAgentMapper.findByAgentCode("ROBOT-02")).thenReturn(Optional.of(agent));

        PlanVersion plan = new PlanVersion();
        plan.setId(10L);
        plan.setPlanSteps("[{\"stepSeq\":2,\"capabilityType\":\"CAP_TRANSPORT\",\"completionCondition\":\"status=SUCCESS\"}]");
        when(planVersionMapper.findById(10L)).thenReturn(Optional.of(plan));

        Task task = new Task();
        task.setId(201L);
        task.setStatus(TaskStatus.EXECUTING);
        task.setCurrentPlanVersionId(10L);
        when(taskMapper.findById(201L)).thenReturn(Optional.of(task));

        // 反馈为 FAILED, HARDWARE_ERROR
        orchestratorReal.onExecutionFeedback("ROBOT-02", "EXEC-CMD-HW-1", 1, "FAILED", "HARDWARE_ERROR", Map.of("error", "chassis motor fault"));

        verify(taskEventService).append(eq(201L), eq("STEP_FAILED"), eq("SYSTEM"), eq("HARDWARE_ERROR"), contains("重试后仍失败"));
        ArgumentCaptor<TaskException> exCaptor = ArgumentCaptor.forClass(TaskException.class);
        verify(taskExceptionMapper).insert(exCaptor.capture());
        assertEquals("STEP_FAILED", exCaptor.getValue().getExceptionType());
        assertTrue(exCaptor.getValue().getReasonCode().contains("HARDWARE_ERROR"));
    }

    @Test
    @DisplayName("StepTimeoutMonitorTask超时扫描触发时，正确识别EXECUTION_TIMEOUT并调用异常识别处理")
    void stepTimeoutMonitorTaskIdentifiesTimeoutAndInvokesExceptionService() {
        TaskStepAssignment assignment = new TaskStepAssignment();
        assignment.setId(103L);
        assignment.setTaskId(202L);
        assignment.setPlanVersionId(10L);
        assignment.setStepSeq(3);
        assignment.setCommandId("CMD-TIMEOUT-SCAN-1");
        assignment.setDeviceAgentId(3L);
        assignment.setStepStatus("EXECUTING");
        assignment.setDispatchedAt(LocalDateTime.now().minusSeconds(120));

        when(assignmentMapper.findByStepStatusAndDispatchedAtBefore(eq("EXECUTING"), any(LocalDateTime.class)))
                .thenReturn(List.of(assignment));

        DeviceAgent agent = new DeviceAgent();
        agent.setId(3L);
        agent.setCurrentTaskId(202L);
        when(deviceAgentMapper.findById(3L)).thenReturn(Optional.of(agent));

        StepTimeoutMonitorTask monitorTask = new StepTimeoutMonitorTask(
                assignmentMapper, deviceAgentMapper, taskEventService, exceptionService,
                60, planVersionMapper, mock(DeviceCommandMapper.class));

        Task task = new Task();
        task.setId(202L);
        task.setStatus(TaskStatus.EXECUTING);
        task.setCurrentPlanVersionId(10L);
        when(taskMapper.findById(202L)).thenReturn(Optional.of(task));

        monitorTask.checkStepTimeout();

        verify(taskEventService).append(eq(202L), eq("STEP_TIMEOUT_DETECTED"), eq("SYSTEM"), eq("ERR_EXECUTION_TIMEOUT"), contains("判定执行超时"));
        ArgumentCaptor<TaskException> exCaptor = ArgumentCaptor.forClass(TaskException.class);
        verify(taskExceptionMapper).insert(exCaptor.capture());
        assertEquals("EXECUTION_TIMEOUT", exCaptor.getValue().getExceptionType());
    }

    // ==========================================
    // 2. 局部单次重规划配额消耗控制
    // ==========================================

    @Test
    @DisplayName("首次重规划且恢复失败时，触发单次局部重规划(REPLANNING_TRIGGERED)")
    void firstFailureWithUnusedQuotaTriggersReplanning() {
        Task task = new Task();
        task.setId(301L);
        task.setStatus(TaskStatus.EXECUTING);
        task.setReplanUsed(false);
        task.setCurrentPlanVersionId(20L);
        when(taskMapper.findById(301L)).thenReturn(Optional.of(task));

        PlanVersion plan = new PlanVersion();
        plan.setId(20L);
        plan.setSource("AUTONOMOUS");
        when(planVersionMapper.findById(20L)).thenReturn(Optional.of(plan));

        // 候选设备不可用，计划不可继续
        when(orchestrator.hasAvailableCandidate(anyLong(), anyInt(), anyList())).thenReturn(false);

        exceptionService.handleException(301L, 1, "STEP_FAILED", "执行结果: FAILED，原因: HARDWARE_ERROR");

        verify(taskEventService).append(eq(301L), eq("REPLANNING_TRIGGERED"), eq("SYSTEM"), isNull(), contains("触发5.5.4局部重新规划"));
        verify(replanningService).replan(eq(301L), eq(1), contains("STEP_FAILED"));
    }

    @Test
    @DisplayName("重规划额度已消耗(replanUsed=true)的任务，再次调用replan直接被拒并转待人工，不重复调用模型")
    void replanServiceRejectsWhenReplanUsedIsTrue() {
        Task task = new Task();
        task.setId(302L);
        task.setStatus(TaskStatus.EXECUTING);
        task.setReplanUsed(true);
        task.setCurrentPlanVersionId(21L);
        when(taskMapper.findById(302L)).thenReturn(Optional.of(task));

        var realReplanningService = new ReplanningService(
                taskMapper, planVersionMapper, assignmentMapper,
                mock(ContextSnapshotService.class), mock(PlanValidationService.class),
                planningModelService, mock(RiskAssessmentService.class),
                orchestrator, taskEventService, mock(BaselineTemplateService.class));
        ReflectionTestUtils.setField(realReplanningService, "taskExceptionMapper", taskExceptionMapper);

        realReplanningService.replan(302L, 2, "STEP_FAILED");

        // 验证模型未被调用
        verifyNoInteractions(planningModelService);
        // 验证任务被置为待人工处理
        assertEquals(TaskStatus.PENDING_MANUAL, task.getStatus());
        assertTrue(task.getFailureReason().contains("重新规划机会已使用"));
        verify(taskEventService).append(eq(302L), eq("TASK_PENDING_MANUAL"), eq("SYSTEM"), eq("ERR_REPLAN_LIMIT_EXCEEDED"), contains("重新规划机会已使用"));

        // 验证写入了 REPLAN_FAILED 异常
        ArgumentCaptor<TaskException> exCaptor = ArgumentCaptor.forClass(TaskException.class);
        verify(taskExceptionMapper).insert(exCaptor.capture());
        assertEquals("REPLAN_FAILED", exCaptor.getValue().getExceptionType());
        assertEquals("ERR_REPLAN_LIMIT_EXCEEDED", exCaptor.getValue().getReasonCode());
        assertEquals("RESOLVED", exCaptor.getValue().getExceptionStatus());
    }

    @Test
    @DisplayName("已完成5步上限导致剩余额度为0时，重规划直接失败且消耗配额，转待人工")
    void replanningZeroQuotaConsumesQuotaAndGoesToPendingManual() {
        Task task = new Task();
        task.setId(303L);
        task.setStatus(TaskStatus.EXECUTING);
        task.setReplanUsed(false);
        task.setCurrentPlanVersionId(22L);
        when(taskMapper.findById(303L)).thenReturn(Optional.of(task));

        List<TaskStepAssignment> assignments = List.of(
                createAssignment(1, "COMPLETED"),
                createAssignment(2, "COMPLETED"),
                createAssignment(3, "COMPLETED"),
                createAssignment(4, "COMPLETED"),
                createAssignment(5, "COMPLETED")
        );
        when(assignmentMapper.findByPlanVersionIdOrderByStepSeqAsc(22L)).thenReturn(assignments);

        var realReplanningService = new ReplanningService(
                taskMapper, planVersionMapper, assignmentMapper,
                mock(ContextSnapshotService.class), mock(PlanValidationService.class),
                planningModelService, mock(RiskAssessmentService.class),
                orchestrator, taskEventService, mock(BaselineTemplateService.class));
        ReflectionTestUtils.setField(realReplanningService, "taskExceptionMapper", taskExceptionMapper);

        realReplanningService.replan(303L, 6, "STEP_FAILED");

        assertTrue(task.getReplanUsed(), "配额必须被标记为已消耗");
        assertEquals(TaskStatus.PENDING_MANUAL, task.getStatus());
        verify(taskEventService).append(eq(303L), eq("REPLAN_FAILED"), eq("SYSTEM"), eq("ERR_STEP_QUOTA_EXHAUSTED"), contains("无剩余步骤额度"));
        verify(taskEventService).append(eq(303L), eq("TASK_PENDING_MANUAL"), eq("SYSTEM"), eq("ERR_STEP_QUOTA_EXHAUSTED"), contains("无剩余额度"));
        verifyNoInteractions(planningModelService);

        ArgumentCaptor<TaskException> exCaptor = ArgumentCaptor.forClass(TaskException.class);
        verify(taskExceptionMapper).insert(exCaptor.capture());
        assertEquals("REPLAN_FAILED", exCaptor.getValue().getExceptionType());
        assertEquals("ERR_STEP_QUOTA_EXHAUSTED", exCaptor.getValue().getReasonCode());
    }

    @Test
    @DisplayName("重规划调用模型超时/不可用时，消耗配额并记录REPLAN_FAILED异常与转人工事件")
    void replanningModelFailureConsumesQuotaAndRecordsReplanFailedException() {
        Task task = new Task();
        task.setId(304L);
        task.setStatus(TaskStatus.EXECUTING);
        task.setReplanUsed(false);
        task.setCurrentPlanVersionId(23L);
        when(taskMapper.findById(304L)).thenReturn(Optional.of(task));
        when(taskMapper.claimReplan(eq(304L), anyString())).thenReturn(1);

        PlanVersion plan = new PlanVersion();
        plan.setId(23L);
        plan.setPlanSteps("[{\"stepSeq\":1,\"capabilityType\":\"CAP_CLEAN\"}]");
        when(planVersionMapper.findById(23L)).thenReturn(Optional.of(plan));

        when(assignmentMapper.findByPlanVersionIdOrderByStepSeqAsc(23L)).thenReturn(List.of());

        var contextSnapshotService = mock(ContextSnapshotService.class);
        ContextSnapshot snap = new ContextSnapshot();
        snap.setSnapshotCode("SNAP-304");
        when(contextSnapshotService.buildSnapshot(eq(304L), anyList())).thenReturn(snap);
        when(contextSnapshotService.capabilityContext(any(), anyList())).thenReturn(List.of());

        // 模型返回失败
        PlanningResponse failResponse = new PlanningResponse();
        failResponse.setResultCode("500");
        failResponse.setErrorMessage("Model service unavailable");
        when(planningModelService.generatePlan(any())).thenReturn(failResponse);

        var realReplanningService = new ReplanningService(
                taskMapper, planVersionMapper, assignmentMapper,
                contextSnapshotService, mock(PlanValidationService.class),
                planningModelService, mock(RiskAssessmentService.class),
                orchestrator, taskEventService, mock(BaselineTemplateService.class));
        ReflectionTestUtils.setField(realReplanningService, "taskExceptionMapper", taskExceptionMapper);

        realReplanningService.replan(304L, 1, "STEP_FAILED");

        assertTrue(task.getReplanUsed(), "模型调用失败时重规划配额仍须消耗");
        assertEquals(TaskStatus.PENDING_MANUAL, task.getStatus());
        verify(taskEventService).append(eq(304L), eq("REPLAN_FAILED"), eq("SYSTEM"), eq("ERR_REPLANNING_MODEL_FAILED"), contains("调用模型失败"));
        verify(taskEventService).append(eq(304L), eq("TASK_PENDING_MANUAL"), eq("SYSTEM"), eq("ERR_REPLANNING_MODEL_FAILED"), contains("规划模型服务不可用或超时"));

        ArgumentCaptor<TaskException> exCaptor = ArgumentCaptor.forClass(TaskException.class);
        verify(taskExceptionMapper).insert(exCaptor.capture());
        assertEquals("REPLAN_FAILED", exCaptor.getValue().getExceptionType());
        assertEquals("ERR_REPLANNING_MODEL_FAILED", exCaptor.getValue().getReasonCode());
    }

    // ==========================================
    // 3. 局部重规划二次失败后直接触发转人工接管
    // ==========================================

    @Test
    @DisplayName("已消耗重规划额度(replanUsed=true)的任务再次发生步骤失败且无候选时，直接转待人工，严禁二次重规划")
    void secondFailureAfterReplanGoesStraightToManualTakeover() {
        Task task = new Task();
        task.setId(401L);
        task.setStatus(TaskStatus.EXECUTING);
        task.setReplanUsed(true); // 已消耗重规划配额
        task.setCurrentPlanVersionId(30L);
        when(taskMapper.findById(401L)).thenReturn(Optional.of(task));

        PlanVersion plan = new PlanVersion();
        plan.setId(30L);
        plan.setSource("AUTONOMOUS");
        when(planVersionMapper.findById(30L)).thenReturn(Optional.of(plan));

        // 无可用候选设备，恢复动作直接失败
        when(orchestrator.hasAvailableCandidate(anyLong(), anyInt(), anyList())).thenReturn(false);

        exceptionService.handleException(401L, 2, "STEP_FAILED", "执行结果: FAILED，原因: HARDWARE_ERROR");

        // 严禁二次触发重规划
        verify(replanningService, never()).replan(anyLong(), anyInt(), anyString());
        verify(taskEventService, never()).append(eq(401L), eq("REPLANNING_TRIGGERED"), any(), any(), any());

        // 必须直接进入 TASK_PENDING_MANUAL
        assertEquals(TaskStatus.PENDING_MANUAL, task.getStatus());
        assertTrue(task.getFailureReason().contains("重新规划机会已用，恢复失败，转人工处理"));
        verify(taskEventService).append(eq(401L), eq("TASK_PENDING_MANUAL"), eq("SYSTEM"), eq("STEP_FAILED"), contains("重新规划机会已用"));
    }

    @Test
    @DisplayName("已消耗重规划额度的任务再次发生执行超时且无候选时，直接转待人工，记录EXECUTION_TIMEOUT转人工事件")
    void secondFailureWithExecutionTimeoutGoesStraightToManualTakeover() {
        Task task = new Task();
        task.setId(402L);
        task.setStatus(TaskStatus.EXECUTING);
        task.setReplanUsed(true);
        task.setCurrentPlanVersionId(31L);
        when(taskMapper.findById(402L)).thenReturn(Optional.of(task));

        PlanVersion plan = new PlanVersion();
        plan.setId(31L);
        plan.setSource("AUTONOMOUS");
        when(planVersionMapper.findById(31L)).thenReturn(Optional.of(plan));

        when(orchestrator.hasAvailableCandidate(anyLong(), anyInt(), anyList())).thenReturn(false);

        exceptionService.handleException(402L, 2, "EXECUTION_TIMEOUT", "指令EXEC-CMD-TIMEOUT-2执行超时未收到");

        verify(replanningService, never()).replan(anyLong(), anyInt(), anyString());
        verify(taskEventService, never()).append(eq(402L), eq("REPLANNING_TRIGGERED"), any(), any(), any());

        assertEquals(TaskStatus.PENDING_MANUAL, task.getStatus());
        verify(taskEventService).append(eq(402L), eq("TASK_PENDING_MANUAL"), eq("SYSTEM"), eq("EXECUTION_TIMEOUT"), contains("重新规划机会已用"));
    }

    @Test
    @DisplayName("已消耗重规划配额的任务再次发生异常时，尝试候选设备切换但切换后重新分配仍失败，直接进入待人工")
    void secondFailureReassignmentFailsEndsInManualTakeover() {
        Task task = new Task();
        task.setId(403L);
        task.setStatus(TaskStatus.EXECUTING);
        task.setReplanUsed(true);
        task.setCurrentPlanVersionId(32L);
        when(taskMapper.findById(403L)).thenReturn(Optional.of(task));

        PlanVersion plan = new PlanVersion();
        plan.setId(32L);
        plan.setSource("AUTONOMOUS");
        when(planVersionMapper.findById(32L)).thenReturn(Optional.of(plan));

        // 初始认为有候选
        when(orchestrator.hasAvailableCandidate(anyLong(), anyInt(), anyList())).thenReturn(true);

        // 重新分配触发后模拟全部候选拒绝或转人工
        doAnswer(inv -> {
            task.setStatus(TaskStatus.PENDING_MANUAL);
            task.setFailureReason("步骤2全部候选设备均已拒绝承接");
            return null;
        }).when(orchestrator).retryAssignmentExcluding(anyLong(), anyLong(), anyInt(), any());

        exceptionService.handleException(403L, 2, "STEP_FAILED", "执行结果: FAILED，原因: HARDWARE_ERROR");

        verify(replanningService, never()).replan(anyLong(), anyInt(), anyString());
        verify(taskEventService, never()).append(eq(403L), eq("REPLANNING_TRIGGERED"), any(), any(), any());
        verify(taskEventService).append(eq(403L), eq("EXCEPTION_RECOVERY_FAILED"), eq("SYSTEM"), eq("STEP_FAILED"), contains("PENDING_MANUAL"));
        assertEquals(TaskStatus.PENDING_MANUAL, task.getStatus());
    }

    @Test
    @DisplayName("DEF-S3-105: 首次失败后重试成功留痕，异常表记录指令重试并RESOLVED，发出EXCEPTION_RECOVERED事件")
    void testStepFirstFailureRetrySuccessRecordsExceptionAndRecoveredEvent() {
        Task task = new Task();
        task.setId(493L);
        task.setStatus(TaskStatus.EXECUTING);
        task.setCurrentPlanVersionId(10L);
        when(taskMapper.findById(493L)).thenReturn(Optional.of(task));

        // 模拟步骤2首次执行失败，触发指令重试
        exceptionService.onStepFirstFailure(493L, 2, "STEP_FAILED", "ERR_SYNTHETIC_HARDWARE", "执行结果: FAILED，原因: ERR_SYNTHETIC_HARDWARE");

        ArgumentCaptor<TaskException> exCaptor = ArgumentCaptor.forClass(TaskException.class);
        verify(taskExceptionMapper).insert(exCaptor.capture());
        TaskException inserted = exCaptor.getValue();
        assertEquals(493L, inserted.getTaskId());
        assertEquals(2, inserted.getStepSeq());
        assertEquals("STEP_FAILED", inserted.getExceptionType());
        assertEquals("ERR_SYNTHETIC_HARDWARE", inserted.getReasonCode());
        assertEquals("指令重试", inserted.getRecoveryAction());
        assertEquals("PROCESSING", inserted.getExceptionStatus());
        assertNull(inserted.getRecoveryResult());

        verify(taskEventService).append(eq(493L), eq("EXCEPTION_DETECTED"), any(), eq("ERR_SYNTHETIC_HARDWARE"), contains("ERR_SYNTHETIC_HARDWARE"));

        // 模拟同号指令重试成功反馈到达，触发 onStepRecovered
        when(taskExceptionMapper.findByTaskIdOrderByOccurredAtDesc(493L)).thenReturn(List.of(inserted));
        exceptionService.onStepRecovered(493L, 2);

        assertEquals("SUCCESS", inserted.getRecoveryResult());
        assertEquals("RESOLVED", inserted.getExceptionStatus());
        assertTrue(inserted.getImpactConclusion().contains("自动重试成功"));
        verify(taskExceptionMapper).update(inserted);

        verify(taskEventService).append(eq(493L), eq("EXCEPTION_RECOVERED"), eq("SYSTEM"), eq("STEP_FAILED"), contains("重试成功"));
    }

    @Test
    @DisplayName("DEF-S3-106: 可继续的非关键失败不触发重规划，原目标已满足时步骤跳过并继续原计划")
    void testNonCriticalStepFailureContinuesOriginalPlanWithoutReplan() {
        Task task = new Task();
        task.setId(505L);
        task.setStatus(TaskStatus.EXECUTING);
        task.setCurrentPlanVersionId(20L);
        task.setReplanUsed(false);
        when(taskMapper.findById(505L)).thenReturn(Optional.of(task));

        PlanVersion plan = new PlanVersion();
        plan.setId(20L);
        plan.setSource("AUTONOMOUS");
        // 步骤2配置为非关键步骤
        String planStepsJson = """
                [
                  {"stepSeq": 1, "stepGoal": "前往区域", "completionCondition": "routeGenerated=true"},
                  {"stepSeq": 2, "stepGoal": "辅助确认", "failureHandling": "非关键步骤，失败可跳过；原目标完成条件已满足时继续后续步骤"},
                  {"stepSeq": 3, "stepGoal": "到达目标", "completionCondition": "routeGenerated=true"}
                ]
                """;
        plan.setPlanSteps(planStepsJson);
        when(planVersionMapper.findById(20L)).thenReturn(Optional.of(plan));

        // 步骤1已成功且输出满足 routeGenerated=true
        TaskStepAssignment step1 = new TaskStepAssignment();
        step1.setStepSeq(1);
        step1.setStepStatus("COMPLETED");
        step1.setOutputParams("{\"routeGenerated\":true}");

        TaskStepAssignment step2 = new TaskStepAssignment();
        step2.setStepSeq(2);
        step2.setStepStatus("FAILED");

        TaskStepAssignment step3 = new TaskStepAssignment();
        step3.setStepSeq(3);
        step3.setStepStatus("FROZEN");

        when(assignmentMapper.findByPlanVersionIdOrderByStepSeqAsc(20L)).thenReturn(List.of(step1, step2, step3));
        when(orchestrator.hasAvailableCandidate(eq(20L), eq(2), anyList())).thenReturn(false);

        // 触发异常处理，两候选穷尽
        exceptionService.handleException(505L, 2, "STEP_FAILED", "执行结果: FAILED，原因: ERR_SYNTHETIC_HARDWARE");

        // 绝不触发局部重规划，不消耗重规划额度
        verify(replanningService, never()).replan(anyLong(), anyInt(), anyString());
        verify(taskEventService, never()).append(eq(505L), eq("REPLANNING_TRIGGERED"), any(), any(), any());
        assertFalse(Boolean.TRUE.equals(task.getReplanUsed()));

        // 验证步骤2标记为 SKIPPED
        assertEquals("SKIPPED", step2.getStepStatus());
        assertEquals("NON_CRITICAL_SKIPPED", step2.getReasonCode());

        // 验证步骤3解冻为 PENDING_ASSIGNMENT
        assertEquals("PENDING_ASSIGNMENT", step3.getStepStatus());

        // 验证事件明确记录了“可继续”影响结论
        verify(taskEventService).append(eq(505L), eq("PLAN_CONTINUATION_JUDGED"), eq("SYSTEM"), eq("STEP_SKIPPED"), contains("可继续"));

        // 验证推进下一步
        verify(orchestrator).advanceAfterStepCompleted(eq(505L), eq(20L), eq(2));
    }

    @Test
    @DisplayName("DEF-S3-107: TaskExceptionService.countPending 统计未处置异常覆盖 PENDING 与 PROCESSING")
    void testCountPendingIncludesPendingAndProcessing() {
        when(taskExceptionMapper.countUnhandledExceptions()).thenReturn(15L);
        assertEquals(15L, exceptionService.countPending());
        verify(taskExceptionMapper).countUnhandledExceptions();
    }

    private TaskStepAssignment createAssignment(int seq, String status) {
        TaskStepAssignment a = new TaskStepAssignment();
        a.setStepSeq(seq);
        a.setStepStatus(status);
        a.setExecutionResult("SUCCESS");
        return a;
    }
}
