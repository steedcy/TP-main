package com.airport.ai.task;

import com.airport.ai.baseline.BaselineDryRunLifecycle;
import com.airport.ai.baseline.BaselineTemplateService;
import com.airport.ai.baseline.DryRunDeviceSelectionMapper;
import com.airport.ai.device.Device;
import com.airport.ai.device.DeviceAgent;
import com.airport.ai.device.DeviceAgentMapper;
import com.airport.ai.device.DeviceAgentMessagingService;
import com.airport.ai.device.DeviceCapabilityMapper;
import com.airport.ai.device.DeviceCommandMapper;
import com.airport.ai.device.DeviceMapper;
import com.airport.ai.event.TaskEventService;
import com.airport.ai.planning.PlanningModelService;
import com.airport.ai.planning.PlanningRequest;
import com.airport.ai.planning.PlanningResponse;
import com.airport.ai.risk.RiskAssessmentResult;
import com.airport.ai.risk.RiskAssessmentService;
import com.airport.ai.taskdef.TaskDefinitionMapper;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.test.util.ReflectionTestUtils;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.atomic.AtomicLong;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * SRS_F019 前置预研专项测试：指令下发超时与状态回滚机制
 * 覆盖场景与规则：
 * 1. 指令状态机流转与留痕 (TC-054.S2)
 * 2. 设备应答 ACK / NACK 与候选轮询回滚 (TC-055.S1)
 * 3. 执行失败单次重试幂等性与超时回滚 (TC-055.S1 / TC-055.S2)
 * 4. 指令执行超时检测、下游步骤冻结(FROZEN)与设备占用释放 (TC-055.S2)
 * 5. 候选切换恢复失败的事件真实性与不误发恢复成功 (DEF-S3-066 / TC-055.S2)
 * 6. 超时触发局部重新规划：保留原目标与已完成结果，替换超时及后续步骤 (SRS_F019.R01-R03 / TC-060.S1)
 * 7. 局部重规划五步剩余额度校验与超限回滚待人工 (SRS_F019.R04 / TC-061.S1)
 * 8. 重规划调用模型超时/异常回滚待人工且保留原始信息 (SRS_F019.R08 / TC-062.S1)
 * 9. 重规划后新计划再次发生超时，直接转待人工，严禁二次重规划 (SRS_F018.R03 / SRS_F019.R01 / TC-062.S2)
 * 10. 超时后迟到设备反馈幂等忽略，杜绝状态篡改 (TC-055.S2)
 */
class InstructionTimeoutAndRollbackF019Test {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private TaskMapper taskMapper;
    private PlanVersionMapper planVersionMapper;
    private TaskStepAssignmentMapper assignmentMapper;
    private DeviceAgentMapper deviceAgentMapper;
    private DeviceMapper deviceMapper;
    private DeviceCapabilityMapper deviceCapabilityMapper;
    private DeviceCommandMapper deviceCommandMapper;
    private StepParameterResolver parameterResolver;
    private DeviceAgentMessagingService messagingService;
    private TaskEventService taskEventService;
    private TaskExceptionMapper taskExceptionMapper;
    private TaskExceptionService exceptionService;
    private ReplanningService replanningService;
    private PlanningModelService planningModelService;
    private PlanValidationService planValidationService;
    private RiskAssessmentService riskAssessmentService;
    private ContextSnapshotService contextSnapshotService;
    private BaselineTemplateService baselineTemplateService;
    private TaskDefinitionMapper taskDefinitionMapper;

    private TaskExecutionOrchestrator orchestrator;
    private StepTimeoutMonitorTask timeoutMonitorTask;

    private Task testTask;
    private PlanVersion planV1;
    private TaskStepAssignment step1;
    private TaskStepAssignment step2;
    private TaskStepAssignment step3;
    private TaskStepAssignment newVersionStep2;
    private DeviceAgent agent1;
    private DeviceAgent agent2;
    private Device device1;
    private Device device2;

    @BeforeEach
    void setUp() throws Exception {
        taskMapper = mock(TaskMapper.class);
        planVersionMapper = mock(PlanVersionMapper.class);
        assignmentMapper = mock(TaskStepAssignmentMapper.class);
        deviceAgentMapper = mock(DeviceAgentMapper.class);
        deviceMapper = mock(DeviceMapper.class);
        deviceCapabilityMapper = mock(DeviceCapabilityMapper.class);
        deviceCommandMapper = mock(DeviceCommandMapper.class);
        parameterResolver = mock(StepParameterResolver.class);
        messagingService = mock(DeviceAgentMessagingService.class);
        taskEventService = mock(TaskEventService.class);
        taskExceptionMapper = mock(TaskExceptionMapper.class);
        planningModelService = mock(PlanningModelService.class);
        planValidationService = mock(PlanValidationService.class);
        riskAssessmentService = mock(RiskAssessmentService.class);
        contextSnapshotService = mock(ContextSnapshotService.class);
        baselineTemplateService = mock(BaselineTemplateService.class);
        taskDefinitionMapper = mock(TaskDefinitionMapper.class);

        orchestrator = spy(new TaskExecutionOrchestrator(
                taskMapper, planVersionMapper, assignmentMapper,
                deviceAgentMapper, deviceMapper, deviceCapabilityMapper,
                taskEventService, null, messagingService,
                mock(BaselineDryRunLifecycle.class),
                mock(DryRunDeviceSelectionMapper.class),
                parameterResolver
        ));

        replanningService = spy(new ReplanningService(
                taskMapper, planVersionMapper, assignmentMapper,
                contextSnapshotService, planValidationService, planningModelService,
                riskAssessmentService, orchestrator, taskEventService, baselineTemplateService
        ));
        ReflectionTestUtils.setField(replanningService, "taskExceptionMapper", taskExceptionMapper);
        ReflectionTestUtils.setField(replanningService, "definitions", taskDefinitionMapper);

        exceptionService = new TaskExceptionService(
                taskMapper, assignmentMapper, taskExceptionMapper,
                deviceAgentMapper, taskEventService, orchestrator,
                replanningService, planVersionMapper
        );
        ReflectionTestUtils.setField(orchestrator, "taskExceptionService", exceptionService);

        timeoutMonitorTask = new StepTimeoutMonitorTask(
                assignmentMapper, deviceAgentMapper, taskEventService,
                exceptionService, 60, planVersionMapper, deviceCommandMapper
        );

        // 默认快照与上下文 Stub
        ContextSnapshot defaultSnapshot = new ContextSnapshot();
        defaultSnapshot.setSnapshotCode("SNAP-DEFAULT");
        defaultSnapshot.setAgents("[]");
        when(contextSnapshotService.buildSnapshot(anyLong(), anyList())).thenReturn(defaultSnapshot);
        when(contextSnapshotService.parseAgents(anyString())).thenReturn(List.of());
        when(contextSnapshotService.capabilityContext(any(), anyList())).thenReturn(List.of());
        when(contextSnapshotService.countAvailableCandidates(any(), anyString(), anyString())).thenReturn(1);

        // 默认三类校验与风险判定放行
        when(planValidationService.validate(anyList(), anyList(), any(), anyString(), anyInt(), anyLong())).thenReturn(new PlanValidationResult());
        when(planValidationService.validate(anyList(), anyList(), any(), anyString(), anyInt(), anyLong(), anyString())).thenReturn(new PlanValidationResult());
        when(riskAssessmentService.assess(any(), anyString(), any(), anyBoolean(), anyInt()))
                .thenReturn(new RiskAssessmentResult("LOW", "RULE_PASS", "低风险放行", BigDecimal.valueOf(0.9), "EXECUTE", "V1.0"));

        // 模拟 PlanVersion insert 自动生成 ID 并注册到 findById
        AtomicLong planIdGen = new AtomicLong(20L);
        doAnswer(inv -> {
            PlanVersion pv = inv.getArgument(0);
            if (pv.getId() == null) {
                pv.setId(planIdGen.getAndIncrement());
            }
            when(planVersionMapper.findById(pv.getId())).thenReturn(Optional.of(pv));
            return 1;
        }).when(planVersionMapper).insert(any(PlanVersion.class));

        // 初始化任务与步骤
        testTask = new Task();
        testTask.setId(500L);
        testTask.setTaskCode("TASK-F019-001");
        testTask.setTaskFamily("GENERAL_SERVICE");
        testTask.setTaskGoal("执行全流程引导广播并在超时回滚后重新规划; passengerName=FICTIONAL_PASSENGER_NAME_CANARY");
        testTask.setSceneParams("{\"flightNo\":\"MU5101\"}");
        testTask.setStatus(TaskStatus.PENDING_ASSIGNMENT);
        testTask.setCurrentPlanVersionId(10L);
        testTask.setIsDryRun(false);
        testTask.setReplanUsed(false);

        List<Map<String, Object>> steps = List.of(
                Map.of("stepSeq", 1, "stepGoal", "展示引导信息", "capabilityType", "CAP_INFO_DISPLAY",
                        "stepTimeout", 60, "completionCondition", "displayStatus=SUCCESS"),
                Map.of("stepSeq", 2, "stepGoal", "现场广播通知", "capabilityType", "CAP_NOTIFICATION",
                        "stepTimeout", 60, "completionCondition", "broadcastStatus=SUCCESS"),
                Map.of("stepSeq", 3, "stepGoal", "服务结果确认", "capabilityType", "CAP_CONFIRMATION",
                        "stepTimeout", 60, "completionCondition", "confirmed=true")
        );

        planV1 = new PlanVersion();
        planV1.setId(10L);
        planV1.setTaskId(500L);
        planV1.setVersionNo(1);
        planV1.setSource("AUTONOMOUS");
        planV1.setPlanSteps(MAPPER.writeValueAsString(steps));

        step1 = new TaskStepAssignment();
        step1.setId(1001L);
        step1.setTaskId(500L);
        step1.setPlanVersionId(10L);
        step1.setStepSeq(1);
        step1.setStepStatus("PENDING_ASSIGNMENT");
        step1.setRetryCount(0);
        step1.setRejectedAgentIds("[]");

        step2 = new TaskStepAssignment();
        step2.setId(1002L);
        step2.setTaskId(500L);
        step2.setPlanVersionId(10L);
        step2.setStepSeq(2);
        step2.setStepStatus("PENDING_ASSIGNMENT");
        step2.setRetryCount(0);
        step2.setRejectedAgentIds("[]");

        step3 = new TaskStepAssignment();
        step3.setId(1003L);
        step3.setTaskId(500L);
        step3.setPlanVersionId(10L);
        step3.setStepSeq(3);
        step3.setStepStatus("PENDING_ASSIGNMENT");
        step3.setRetryCount(0);
        step3.setRejectedAgentIds("[]");

        newVersionStep2 = new TaskStepAssignment();
        newVersionStep2.setId(2002L);
        newVersionStep2.setTaskId(500L);
        newVersionStep2.setPlanVersionId(20L);
        newVersionStep2.setStepSeq(2);
        newVersionStep2.setStepStatus("PENDING_ASSIGNMENT");
        newVersionStep2.setRetryCount(0);
        newVersionStep2.setRejectedAgentIds("[]");

        device1 = new Device();
        device1.setId(1L);
        device1.setDeviceCode("DEV-01");
        device1.setDeviceStatus("ACTIVE");

        device2 = new Device();
        device2.setId(2L);
        device2.setDeviceCode("DEV-02");
        device2.setDeviceStatus("ACTIVE");

        agent1 = new DeviceAgent();
        agent1.setId(10L);
        agent1.setAgentCode("AGT-01");
        agent1.setDeviceId(1L);
        agent1.setAgentStatus("ENABLED");
        agent1.setOnlineStatus("ONLINE");
        agent1.setWorkStatus("IDLE");

        agent2 = new DeviceAgent();
        agent2.setId(20L);
        agent2.setAgentCode("AGT-02");
        agent2.setDeviceId(2L);
        agent2.setAgentStatus("ENABLED");
        agent2.setOnlineStatus("ONLINE");
        agent2.setWorkStatus("IDLE");

        when(taskMapper.findById(500L)).thenReturn(Optional.of(testTask));
        when(planVersionMapper.findById(10L)).thenReturn(Optional.of(planV1));

        when(assignmentMapper.findByPlanVersionIdAndStepSeq(anyLong(), anyInt())).thenAnswer(inv -> {
            Long pvid = inv.getArgument(0);
            Integer seq = inv.getArgument(1);
            if (Long.valueOf(10L).equals(pvid)) {
                if (seq == 1) return Optional.of(step1);
                if (seq == 2) return Optional.of(step2);
                if (seq == 3) return Optional.of(step3);
            } else {
                if (seq == 2) return Optional.of(newVersionStep2);
            }
            return Optional.empty();
        });
        when(assignmentMapper.findByPlanVersionIdOrderByStepSeqAsc(eq(10L))).thenReturn(List.of(step1, step2, step3));
        when(assignmentMapper.findByPlanVersionIdOrderByStepSeqAsc(eq(20L))).thenReturn(List.of(newVersionStep2));

        when(deviceAgentMapper.findById(10L)).thenReturn(Optional.of(agent1));
        when(deviceAgentMapper.findByAgentCode("AGT-01")).thenReturn(Optional.of(agent1));
        when(deviceAgentMapper.findById(20L)).thenReturn(Optional.of(agent2));
        when(deviceAgentMapper.findByAgentCode("AGT-02")).thenReturn(Optional.of(agent2));
        when(deviceAgentMapper.findByAgentStatusAndOnlineStatus("ENABLED", "ONLINE")).thenReturn(List.of(agent1, agent2));

        when(deviceMapper.findById(1L)).thenReturn(Optional.of(device1));
        when(deviceMapper.findById(2L)).thenReturn(Optional.of(device2));
        when(deviceMapper.findByIds(anyList())).thenReturn(List.of(device1, device2));

        when(deviceCapabilityMapper.existsByDeviceIdAndCapabilityTypeAndCapabilityStatus(1L, "CAP_INFO_DISPLAY", "ENABLED")).thenReturn(true);
        when(deviceCapabilityMapper.existsByDeviceIdAndCapabilityTypeAndCapabilityStatus(1L, "CAP_NOTIFICATION", "ENABLED")).thenReturn(true);
        when(deviceCapabilityMapper.existsByDeviceIdAndCapabilityTypeAndCapabilityStatus(2L, "CAP_CONFIRMATION", "ENABLED")).thenReturn(true);

        when(assignmentMapper.findByCommandId(anyString())).thenAnswer(inv -> {
            String cid = inv.getArgument(0);
            if (cid.equals(step1.getCommandId())) return Optional.of(step1);
            if (cid.equals(step2.getCommandId())) return Optional.of(step2);
            if (cid.equals(step3.getCommandId())) return Optional.of(step3);
            if (cid.equals(newVersionStep2.getCommandId())) return Optional.of(newVersionStep2);
            return Optional.empty();
        });

        when(assignmentMapper.findByExecuteCommandId(anyString())).thenAnswer(inv -> {
            String cid = inv.getArgument(0);
            if (cid.equals(step1.getExecuteCommandId())) return Optional.of(step1);
            if (cid.equals(step2.getExecuteCommandId())) return Optional.of(step2);
            if (cid.equals(step3.getExecuteCommandId())) return Optional.of(step3);
            if (cid.equals(newVersionStep2.getExecuteCommandId())) return Optional.of(newVersionStep2);
            return Optional.empty();
        });
    }

    @Test
    @DisplayName("TC-054.S2 & TC-055.S2 & F019: 指令执行超时扫描、下游步骤冻结(FROZEN)、设备释放与成功触发局部重新规划")
    void testExecutionTimeout_freezesDownstreamSteps_releasesDevice_andTriggersReplanning() {
        // 1. 第1步正常完成
        step1.setStepStatus("COMPLETED");
        step1.setExecutionResult("SUCCESS");
        step1.setOutputParams("{\"displayStatus\":\"SUCCESS\"}");
        step1.setCommandId("CMD-STEP-1");

        // 2. 第2步正在执行
        testTask.setStatus(TaskStatus.EXECUTING);
        step2.setStepStatus("EXECUTING");
        step2.setDeviceAgentId(10L);
        step2.setExecuteCommandId("CMD-EXEC-STEP-2");
        step2.setDispatchedAt(LocalDateTime.now().minusSeconds(70)); // 已过 60s 超时
        agent1.setWorkStatus("BUSY");
        agent1.setCurrentTaskId(500L);
        agent1.setCurrentStepSeq(2);

        // 第3步仍在待分配状态
        step3.setStepStatus("PENDING_ASSIGNMENT");

        when(assignmentMapper.findByStepStatusAndDispatchedAtBefore(eq("EXECUTING"), any(LocalDateTime.class)))
                .thenReturn(List.of(step2));

        // 模拟第2步无其他候选设备可切换 -> 恢复失败 -> 触发局部重新规划
        when(deviceCapabilityMapper.existsByDeviceIdAndCapabilityTypeAndCapabilityStatus(2L, "CAP_NOTIFICATION", "ENABLED")).thenReturn(false);
        when(taskMapper.claimReplan(eq(500L), anyString())).thenReturn(1);

        // 模型返回新计划步骤 (替换步骤2及后续)
        PlanningResponse modelResp = new PlanningResponse();
        modelResp.setResultCode("0");
        modelResp.setConfidence(BigDecimal.valueOf(0.95));
        modelResp.setPlanSteps(List.of(
                Map.of("stepSeq", 1, "stepGoal", "新广播步骤", "capabilityType", "CAP_NOTIFICATION", "completionCondition", "broadcastStatus=SUCCESS"),
                Map.of("stepSeq", 2, "stepGoal", "新确认步骤", "capabilityType", "CAP_CONFIRMATION", "completionCondition", "confirmed=true")
        ));
        when(planningModelService.generatePlan(any(PlanningRequest.class))).thenReturn(modelResp);
        when(planVersionMapper.countByTaskId(500L)).thenReturn(1L);

        // 执行超时扫描
        timeoutMonitorTask.checkStepTimeout();

        // 验证 1: 原版本步骤2被置为 FAILED, TIMEOUT, ERR_EXECUTION_TIMEOUT
        assertEquals("FAILED", step2.getStepStatus());
        assertEquals("TIMEOUT", step2.getExecutionResult());
        assertEquals("ERR_EXECUTION_TIMEOUT", step2.getReasonCode());

        // 验证 2: 设备占用被彻底释放
        assertEquals("IDLE", agent1.getWorkStatus());
        assertNull(agent1.getCurrentTaskId());
        assertNull(agent1.getCurrentStepSeq());
        verify(deviceCommandMapper).updateStatus(eq("AGT-01"), eq("CMD-EXEC-STEP-2"), eq("EXECUTE_CAPABILITY"), eq(0), eq("TIMED_OUT"), anyString());

        // 验证 3: 原版本下游待分配步骤3被冻结 (FROZEN)
        assertEquals("FROZEN", step3.getStepStatus());

        // 验证 4: 时间线记录超时与重规划触发
        verify(taskEventService).append(eq(500L), eq("STEP_TIMEOUT_DETECTED"), eq("SYSTEM"), eq("ERR_EXECUTION_TIMEOUT"), contains("判定执行超时"));
        verify(taskEventService).append(eq(500L), eq("REPLANNING_TRIGGERED"), eq("SYSTEM"), isNull(), contains("触发5.5.4局部重新规划"));

        // 验证 5: 重规划调用模型时原目标保留且脱敏，已完成的第1步结果保留
        ArgumentCaptor<PlanningRequest> reqCaptor = ArgumentCaptor.forClass(PlanningRequest.class);
        verify(planningModelService).generatePlan(reqCaptor.capture());
        PlanningRequest sentReq = reqCaptor.getValue();
        assertFalse(sentReq.getTaskGoal().contains("FICTIONAL_PASSENGER_NAME_CANARY"), "敏感信息必须脱敏");
        assertFalse(sentReq.getTaskGoal().contains("passengerName"), "身份字段名须移除");
        assertTrue(sentReq.getTaskGoal().contains("全流程引导广播"), "原始业务目标完整保留");
        assertEquals(1, sentReq.getCompletedSteps().size(), "已完成步骤保留");
        assertEquals("CMD-STEP-1", sentReq.getCompletedSteps().get(0).get("originalCommandId"));
        assertEquals(4, sentReq.getRemainingStepQuota(), "剩余额度 = 5 - 1 = 4");

        // 验证 6: 新版本冻结，任务状态回到 PENDING_ASSIGNMENT，配额已消耗
        assertTrue(testTask.getReplanUsed());
        assertEquals(TaskStatus.PENDING_ASSIGNMENT, testTask.getStatus());
        verify(taskEventService).append(eq(500L), eq("REPLAN_SUCCEEDED"), eq("SYSTEM"), isNull(), contains("局部重新规划成功"));
    }

    @Test
    @DisplayName("TC-055.S1: 设备应答 NACK 拒绝承接，状态回滚、记录拒绝并自动路由至下一候选")
    void testDeviceNack_rollsBackAndRoutesToNextCandidate() {
        when(deviceCapabilityMapper.existsByDeviceIdAndCapabilityTypeAndCapabilityStatus(2L, "CAP_INFO_DISPLAY", "ENABLED")).thenReturn(true);

        orchestrator.assignStep(500L, 10L, 1);
        String acceptCmd1 = step1.getCommandId();
        assertNotNull(acceptCmd1);

        // 候选1 AGT-01 拒绝承接 (NACK)
        orchestrator.onTaskResponse("AGT-01", acceptCmd1, false, "BATTERY_TOO_LOW");

        // 验证 AGT-01 记录入 rejectedAgentIds
        assertTrue(step1.getRejectedAgentIds().contains("AGT-01"));
        assertEquals("IDLE", agent1.getWorkStatus());
        verify(taskEventService).append(eq(500L), eq("AGENT_REJECTED"), eq("SYSTEM"), isNull(), contains("BATTERY_TOO_LOW"));

        // 验证自动为候选2 AGT-02 发起承接请求
        verify(messagingService).requestTaskAcceptance(eq("AGT-02"), anyString(), eq(500L), eq(1), eq("CAP_INFO_DISPLAY"), any());

        // 候选2 AGT-02 接受承接 (ACK)
        String acceptCmd2 = step1.getCommandId();
        orchestrator.onTaskResponse("AGT-02", acceptCmd2, true, null);

        // 验证 AGT-02 被原子置为 BUSY，任务状态转入 EXECUTING，指令下发
        assertEquals("BUSY", agent2.getWorkStatus());
        assertEquals(500L, agent2.getCurrentTaskId());
        assertEquals(1, agent2.getCurrentStepSeq());
        assertEquals(TaskStatus.EXECUTING, testTask.getStatus());
        assertEquals("EXECUTING", step1.getStepStatus());
        verify(taskEventService).append(eq(500L), eq("AGENT_ASSIGNED"), eq("SYSTEM"), isNull(), contains("AGT-02"));
        verify(messagingService).executeCapability(eq("AGT-02"), eq(step1.getExecuteCommandId()), eq(500L), eq(1), eq("CAP_INFO_DISPLAY"), eq(0), any());
    }

    @Test
    @DisplayName("TC-055.S1 / TC-055.S2: 首次执行失败自动重试1次保证幂等，重试超时后状态回滚并进入异常处理")
    void testExecutionFailure_singleRetryIdempotent_thenTimeoutRollback() {
        orchestrator.assignStep(500L, 10L, 1);
        orchestrator.onTaskResponse("AGT-01", step1.getCommandId(), true, null);
        String executeCmdId = step1.getExecuteCommandId();
        assertNotNull(executeCmdId);

        // 首次反馈 FAILED (attemptNo = 0)
        orchestrator.onExecutionFeedback("AGT-01", executeCmdId, 0, "FAILED", "ERR_TRANSIENT_BUSY", Map.of());

        // 验证自动重试 1 次，沿用完全相同的 executeCommandId，attemptNo = 1
        assertEquals(1, step1.getRetryCount());
        assertEquals("EXECUTING", step1.getStepStatus());
        verify(taskEventService).append(eq(500L), eq("STEP_RETRY_DISPATCHED"), eq("SYSTEM"), eq("ERR_TRANSIENT_BUSY"), contains("自动重试1次"));
        verify(messagingService).executeCapability(eq("AGT-01"), eq(executeCmdId), eq(500L), eq(1), eq("CAP_INFO_DISPLAY"), eq(1), any());

        // 模拟重试下发后发生执行反馈超时
        step1.setDispatchedAt(LocalDateTime.now().minusSeconds(75));
        when(assignmentMapper.findByStepStatusAndDispatchedAtBefore(eq("EXECUTING"), any(LocalDateTime.class)))
                .thenReturn(List.of(step1));
        when(taskMapper.claimReplan(eq(500L), anyString())).thenReturn(1);

        timeoutMonitorTask.checkStepTimeout();

        // 验证步骤置 FAILED，结果 TIMEOUT
        assertEquals("FAILED", step1.getStepStatus());
        assertEquals("TIMEOUT", step1.getExecutionResult());
        // 验证设备占用被释放
        assertEquals("IDLE", agent1.getWorkStatus());
        assertNull(agent1.getCurrentTaskId());
        // 验证下游步骤被冻结
        assertEquals("FROZEN", step2.getStepStatus());
        assertEquals("FROZEN", step3.getStepStatus());
    }

    @Test
    @DisplayName("DEF-S3-066 / TC-055.S2: 候选设备切换恢复尝试但二次失败时，严禁误报恢复成功，事件真实性记录为失败")
    void testCandidateSwitchRecoveryFails_preservesEventTruth() {
        step1.setStepStatus("EXECUTING");
        step1.setDeviceAgentId(10L);
        step1.setExecuteCommandId("CMD-EXEC-01");
        agent1.setWorkStatus("BUSY");
        agent1.setCurrentTaskId(500L);
        agent1.setCurrentStepSeq(1);

        // 候选2支持该能力
        when(deviceCapabilityMapper.existsByDeviceIdAndCapabilityTypeAndCapabilityStatus(2L, "CAP_INFO_DISPLAY", "ENABLED")).thenReturn(true);

        // 模拟重新分配时候选2拒绝或发生异常导致任务直接被置为待人工处理
        doAnswer(inv -> {
            testTask.setStatus(TaskStatus.PENDING_MANUAL);
            testTask.setFailureReason("候选设备切换后重新分配仍失败");
            return null;
        }).when(orchestrator).retryAssignmentExcluding(anyLong(), anyLong(), anyInt(), any());

        // 触发异常处理
        exceptionService.handleException(500L, 1, "EXECUTION_TIMEOUT", "指令CMD-EXEC-01超时");

        // 验证记录了 EXCEPTION_RECOVERY_FAILED，绝对严禁记录 EXCEPTION_RECOVERED
        verify(taskEventService).append(eq(500L), eq("EXCEPTION_RECOVERY_FAILED"), eq("SYSTEM"), eq("EXECUTION_TIMEOUT"), contains("恢复失败"));
        verify(taskEventService, never()).append(eq(500L), eq("EXCEPTION_RECOVERED"), any(), any(), any());
        assertEquals(TaskStatus.PENDING_MANUAL, testTask.getStatus());
    }

    @Test
    @DisplayName("SRS_F018.R03 / SRS_F019.R01 / TC-062.S2: 局部重规划后新计划再次执行超时，直接转待人工处理，严禁二次重规划")
    void testSecondaryTimeoutAfterReplanning_rollsBackStraightToManualTakeover() {
        // 任务已使用过重规划 (replanUsed = true)
        testTask.setReplanUsed(true);
        testTask.setStatus(TaskStatus.EXECUTING);
        testTask.setCurrentPlanVersionId(20L);

        PlanVersion planV2 = new PlanVersion();
        planV2.setId(20L);
        planV2.setSource("AUTONOMOUS");
        when(planVersionMapper.findById(20L)).thenReturn(Optional.of(planV2));

        // 无其他可用候选
        doReturn(false).when(orchestrator).hasAvailableCandidate(anyLong(), anyInt(), anyList());

        // 新计划版本第2步发生超时
        exceptionService.handleException(500L, 2, "EXECUTION_TIMEOUT", "新版本步骤2执行超时");

        // 严禁二次触发重规划
        verify(replanningService, never()).replan(anyLong(), anyInt(), anyString());
        verify(taskEventService, never()).append(eq(500L), eq("REPLANNING_TRIGGERED"), any(), any(), any());

        // 任务状态直接转为 PENDING_MANUAL 并记录时间线
        assertEquals(TaskStatus.PENDING_MANUAL, testTask.getStatus());
        assertTrue(testTask.getFailureReason().contains("重新规划机会已用"));
        verify(taskEventService).append(eq(500L), eq("TASK_PENDING_MANUAL"), eq("SYSTEM"), eq("EXECUTION_TIMEOUT"), contains("重新规划机会已用"));
    }

    @Test
    @DisplayName("SRS_F019.R08 / TC-062.S1: 局部重新规划过程中模型调用超时或异常，消耗配额并回滚转待人工，保留原始信息供追溯")
    void testReplanningModelCallTimeout_rollsBackToPendingManualAndPreservesGoal() {
        step1.setStepStatus("COMPLETED");
        step1.setExecutionResult("SUCCESS");
        step1.setOutputParams("{\"displayStatus\":\"SUCCESS\"}");
        step1.setCommandId("CMD-ORIG-1");

        when(taskMapper.claimReplan(eq(500L), anyString())).thenReturn(1);

        // 模拟模型调用超时抛出异常
        when(planningModelService.generatePlan(any(PlanningRequest.class))).thenThrow(new RuntimeException("SocketTimeoutException: model timeout 60s"));

        replanningService.replan(500L, 2, "EXECUTION_TIMEOUT: step 2 timed out");

        // 验证配额被消耗
        assertTrue(testTask.getReplanUsed());
        assertEquals(TaskStatus.PENDING_MANUAL, testTask.getStatus());
        assertTrue(testTask.getFailureReason().contains("规划模型服务不可用或超时"));

        // 验证时间线记录 REPLAN_FAILED 与 TASK_PENDING_MANUAL
        verify(taskEventService).append(eq(500L), eq("REPLAN_FAILED"), eq("SYSTEM"), eq("ERR_REPLANNING_MODEL_FAILED"), contains("调用模型失败"));
        verify(taskEventService).append(eq(500L), eq("TASK_PENDING_MANUAL"), eq("SYSTEM"), eq("ERR_REPLANNING_MODEL_FAILED"), contains("规划模型服务不可用或超时"));

        // 验证原始任务目标与数据完整保留供追溯
        assertTrue(testTask.getTaskGoal().contains("执行全流程引导广播"));
        assertEquals("{\"flightNo\":\"MU5101\"}", testTask.getSceneParams());
    }

    @Test
    @DisplayName("SRS_F019.R04 / TC-061.S1: 重规划替换步骤超过五步剩余额度(5 - 已完成数)，三类校验超限拦截并回滚转待人工")
    void testReplanningOverQuota_rollsBackToPendingManual() {
        // 已完成2步
        step1.setStepStatus("COMPLETED");
        step2.setStepStatus("COMPLETED");
        // 步骤3超时触发重规划，此时已完成2步，剩余额度 = 5 - 2 = 3步

        when(taskMapper.claimReplan(eq(500L), anyString())).thenReturn(1);

        // 模型企图返回 4 个可执行动作 (2 + 4 = 6 > 5步上限)
        PlanningResponse overStepsResp = new PlanningResponse();
        overStepsResp.setResultCode("0");
        overStepsResp.setPlanSteps(List.of(
                Map.of("stepSeq", 1, "capabilityType", "CAP_NOTIFICATION"),
                Map.of("stepSeq", 2, "capabilityType", "CAP_NOTIFICATION"),
                Map.of("stepSeq", 3, "capabilityType", "CAP_CONFIRMATION"),
                Map.of("stepSeq", 4, "capabilityType", "CAP_CONFIRMATION")
        ));
        when(planningModelService.generatePlan(any(PlanningRequest.class))).thenReturn(overStepsResp);

        replanningService.replan(500L, 3, "EXECUTION_TIMEOUT: step 3 timed out");

        // 验证配额消耗并回滚转人工
        assertTrue(testTask.getReplanUsed());
        assertEquals(TaskStatus.PENDING_MANUAL, testTask.getStatus());
        verify(taskEventService).append(eq(500L), eq("REPLAN_FAILED"), eq("SYSTEM"), eq("ERR_STEP_LIMIT_EXCEEDED"), contains("超过剩余额度"));
        verify(taskEventService).append(eq(500L), eq("TASK_PENDING_MANUAL"), eq("SYSTEM"), eq("ERR_STEP_LIMIT_EXCEEDED"), contains("超过剩余额度"));
    }

    @Test
    @DisplayName("TC-055.S2: 超时标记FAILED后迟到的设备执行反馈被幂等忽略，杜绝状态篡改")
    void testLateExecutionFeedbackAfterTimeout_isSafelyIgnored() {
        step1.setStepStatus("FAILED");
        step1.setExecutionResult("TIMEOUT");
        step1.setReasonCode("ERR_EXECUTION_TIMEOUT");
        step1.setDeviceAgentId(10L);
        step1.setExecuteCommandId("CMD-EXEC-LATE");
        agent1.setWorkStatus("IDLE");

        // 模拟迟到的 SUCCESS 反馈到达
        orchestrator.onExecutionFeedback("AGT-01", "CMD-EXEC-LATE", 0, "SUCCESS", "DEVICE_SUCCESS", Map.of("displayStatus", "SUCCESS"));

        // 验证步骤状态保持 FAILED，绝不被篡改为 COMPLETED
        assertEquals("FAILED", step1.getStepStatus());
        assertEquals("TIMEOUT", step1.getExecutionResult());
        assertEquals("IDLE", agent1.getWorkStatus());

        // 严禁触发 STEP_COMPLETED 或任务推进
        verify(taskEventService, never()).append(any(), eq("STEP_COMPLETED"), any(), any(), any());
        verify(taskEventService, never()).append(any(), eq("TASK_COMPLETED"), any(), any(), any());
    }
}
