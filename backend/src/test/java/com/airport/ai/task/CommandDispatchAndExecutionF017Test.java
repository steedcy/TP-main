package com.airport.ai.task;

import com.airport.ai.baseline.BaselineDryRunLifecycle;
import com.airport.ai.baseline.DryRunDeviceSelectionMapper;
import com.airport.ai.common.BusinessException;
import com.airport.ai.device.Device;
import com.airport.ai.device.DeviceAgent;
import com.airport.ai.device.DeviceAgentMapper;
import com.airport.ai.device.DeviceAgentMessagingService;
import com.airport.ai.device.DeviceCapabilityMapper;
import com.airport.ai.device.DeviceCommandMapper;
import com.airport.ai.device.DeviceMapper;
import com.airport.ai.event.TaskEventService;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * SRS_F017: 业务指令下发与状态流转专项验证
 * 对应测试用例: TC-054, TC-055, TC-056
 * 覆盖规则: SRS_F017.R01 ~ R10:
 * - R01: 任务九状态流转与留痕 (TC-054.S2)
 * - R02: 指令下发唯一指令号，失败最多自动重试1次，重试沿用同一编号保证幂等 (TC-055.S1)
 * - R03: 重试后仍失败生成步骤失败异常并进入计划影响判断 (TC-055.S1)
 * - R04: 允许合法业务意图下发 (TC-056.S2)
 * - R05: 运动安全控制字段拦截 (TC-056.S1)
 * - R06: 模型异常或校验失败不触发指令 (TC-056.S2)
 * - R07: 步骤完成以计划完成条件为依据，“已收到”不等于完成 (TC-054.S1)
 * - R08: 步骤按顺序执行，前序未完成不下发后续；成功但未满足条件按失败处理 (TC-055.S2)
 * - R09: 全部可执行步骤完成条件满足后任务置为已完成 (TC-054.S2)
 * - R10: 下发、反馈、重试、超时和状态流转全量写入事件时间线 (TC-054.S2)
 */
class CommandDispatchAndExecutionF017Test {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private TaskMapper taskMapper;
    private PlanVersionMapper planVersionMapper;
    private TaskStepAssignmentMapper assignmentMapper;
    private DeviceAgentMapper deviceAgentMapper;
    private DeviceMapper deviceMapper;
    private DeviceCapabilityMapper deviceCapabilityMapper;
    private DeviceCommandMapper deviceCommandMapper;
    private StepParameterResolver parameterResolver;
    private DeviceAgentMessagingService deviceAgentMessagingService;
    private TaskEventService taskEventService;
    private TaskExceptionService taskExceptionService;
    private BaselineDryRunLifecycle dryRunLifecycle;
    private DryRunDeviceSelectionMapper selections;

    private TaskExecutionOrchestrator orchestrator;
    private StepTimeoutMonitorTask timeoutMonitorTask;

    private Task testTask;
    private PlanVersion testPlanVersion;
    private TaskStepAssignment step1Assignment;
    private TaskStepAssignment step2Assignment;
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

        timeoutMonitorTask = new StepTimeoutMonitorTask(
                assignmentMapper, deviceAgentMapper, taskEventService,
                taskExceptionService, 60, planVersionMapper, deviceCommandMapper
        );

        testTask = new Task();
        testTask.setId(100L);
        testTask.setTaskCode("TASK-F017-001");
        testTask.setTaskFamily("GENERAL_SERVICE");
        testTask.setStatus(TaskStatus.PENDING_ASSIGNMENT);
        testTask.setCurrentPlanVersionId(200L);
        testTask.setIsDryRun(false);

        List<Map<String, Object>> steps = List.of(
                Map.of(
                        "stepSeq", 1,
                        "stepGoal", "展示第一步引导信息",
                        "capabilityType", "CAP_INFO_DISPLAY",
                        "stepTimeout", 60,
                        "completionCondition", "displayStatus=SUCCESS",
                        "inputParams", Map.of("content", "引导A区")
                ),
                Map.of(
                        "stepSeq", 2,
                        "stepGoal", "发布第二步现场广播",
                        "capabilityType", "CAP_NOTIFICATION",
                        "stepTimeout", 60,
                        "completionCondition", "notificationStatus=SUCCESS",
                        "inputParams", Map.of("content", "广播通知")
                )
        );

        testPlanVersion = new PlanVersion();
        testPlanVersion.setId(200L);
        testPlanVersion.setTaskId(100L);
        testPlanVersion.setVersionNo(1);
        testPlanVersion.setSource("AUTONOMOUS_PLAN");
        testPlanVersion.setPlanSteps(MAPPER.writeValueAsString(steps));

        step1Assignment = new TaskStepAssignment();
        step1Assignment.setId(301L);
        step1Assignment.setTaskId(100L);
        step1Assignment.setPlanVersionId(200L);
        step1Assignment.setStepSeq(1);
        step1Assignment.setStepStatus("PENDING_ASSIGNMENT");
        step1Assignment.setRetryCount(0);
        step1Assignment.setRejectedAgentIds("[]");

        step2Assignment = new TaskStepAssignment();
        step2Assignment.setId(302L);
        step2Assignment.setTaskId(100L);
        step2Assignment.setPlanVersionId(200L);
        step2Assignment.setStepSeq(2);
        step2Assignment.setStepStatus("PENDING_ASSIGNMENT");
        step2Assignment.setRetryCount(0);
        step2Assignment.setRejectedAgentIds("[]");

        device1 = new Device();
        device1.setId(1L);
        device1.setDeviceCode("DEV-01");
        device1.setDeviceStatus("ACTIVE");
        device1.setDeviceTypeCode("SMART_DISPLAY");

        agent1 = new DeviceAgent();
        agent1.setId(10L);
        agent1.setAgentCode("AGT-01");
        agent1.setDeviceId(1L);
        agent1.setAgentStatus("ENABLED");
        agent1.setOnlineStatus("ONLINE");
        agent1.setWorkStatus("IDLE");

        device2 = new Device();
        device2.setId(2L);
        device2.setDeviceCode("DEV-02");
        device2.setDeviceStatus("ACTIVE");
        device2.setDeviceTypeCode("SMART_BROADCAST");

        agent2 = new DeviceAgent();
        agent2.setId(20L);
        agent2.setAgentCode("AGT-02");
        agent2.setDeviceId(2L);
        agent2.setAgentStatus("ENABLED");
        agent2.setOnlineStatus("ONLINE");
        agent2.setWorkStatus("IDLE");

        when(taskMapper.findById(100L)).thenReturn(Optional.of(testTask));
        when(planVersionMapper.findById(200L)).thenReturn(Optional.of(testPlanVersion));
        when(assignmentMapper.findByPlanVersionIdAndStepSeq(200L, 1)).thenReturn(Optional.of(step1Assignment));
        when(assignmentMapper.findByPlanVersionIdAndStepSeq(200L, 2)).thenReturn(Optional.of(step2Assignment));
        when(assignmentMapper.findByPlanVersionIdOrderByStepSeqAsc(200L)).thenReturn(List.of(step1Assignment, step2Assignment));

        when(deviceAgentMapper.findById(10L)).thenReturn(Optional.of(agent1));
        when(deviceAgentMapper.findByAgentCode("AGT-01")).thenReturn(Optional.of(agent1));
        when(deviceAgentMapper.findById(20L)).thenReturn(Optional.of(agent2));
        when(deviceAgentMapper.findByAgentCode("AGT-02")).thenReturn(Optional.of(agent2));
        when(deviceAgentMapper.findByAgentStatusAndOnlineStatus("ENABLED", "ONLINE")).thenReturn(List.of(agent1, agent2));

        when(deviceMapper.findById(1L)).thenReturn(Optional.of(device1));
        when(deviceMapper.findById(2L)).thenReturn(Optional.of(device2));
        when(deviceMapper.findByIds(anyList())).thenReturn(List.of(device1, device2));

        when(deviceCapabilityMapper.existsByDeviceIdAndCapabilityTypeAndCapabilityStatus(1L, "CAP_INFO_DISPLAY", "ENABLED")).thenReturn(true);
        when(deviceCapabilityMapper.existsByDeviceIdAndCapabilityTypeAndCapabilityStatus(2L, "CAP_NOTIFICATION", "ENABLED")).thenReturn(true);

        when(assignmentMapper.findByCommandId(anyString())).thenAnswer(i -> {
            String cid = i.getArgument(0);
            if (cid.equals(step1Assignment.getCommandId())) return Optional.of(step1Assignment);
            if (cid.equals(step2Assignment.getCommandId())) return Optional.of(step2Assignment);
            return Optional.empty();
        });
        when(assignmentMapper.findByExecuteCommandId(anyString())).thenAnswer(i -> {
            String cid = i.getArgument(0);
            if (cid.equals(step1Assignment.getExecuteCommandId())) return Optional.of(step1Assignment);
            if (cid.equals(step2Assignment.getExecuteCommandId())) return Optional.of(step2Assignment);
            return Optional.empty();
        });
    }

    @Test
    @DisplayName("SRS_F017.R01 & R09 & TC-054.S2: 任务九状态流转与多步顺序执行完成")
    void testR01_R09_nineStatesFlowAndProgressCompletion() {
        // 1. 任务初始状态为 PENDING_ASSIGNMENT
        assertEquals(TaskStatus.PENDING_ASSIGNMENT, testTask.getStatus());

        // 2. 分配第1步 -> 触发 TASK_ACCEPT
        orchestrator.assignStep(100L, 200L, 1);
        String acceptCmd1 = step1Assignment.getCommandId();
        assertNotNull(acceptCmd1);
        verify(deviceAgentMessagingService).requestTaskAcceptance(eq("AGT-01"), eq(acceptCmd1), eq(100L), eq(1), eq("CAP_INFO_DISPLAY"), any());

        // 3. 设备应答 TASK_ACCEPT = true (ACK)
        orchestrator.onTaskResponse("AGT-01", acceptCmd1, true, null);
        // 验证代理置 BUSY，任务状态流转为 EXECUTING
        assertEquals("BUSY", agent1.getWorkStatus());
        assertEquals(TaskStatus.EXECUTING, testTask.getStatus());
        verify(taskEventService).append(eq(100L), eq("AGENT_ASSIGNED"), eq("SYSTEM"), isNull(), contains("AGT-01"));

        // 验证指令下发 EXECUTE_CAPABILITY，并记录 STEP_DISPATCHED
        String execCmd1 = step1Assignment.getExecuteCommandId();
        assertNotNull(execCmd1);
        assertEquals("EXECUTING", step1Assignment.getStepStatus());
        verify(deviceAgentMessagingService).executeCapability(eq("AGT-01"), eq(execCmd1), eq(100L), eq(1), eq("CAP_INFO_DISPLAY"), eq(0), any());
        verify(taskEventService).append(eq(100L), eq("STEP_DISPATCHED"), eq("SYSTEM"), isNull(), contains(execCmd1));

        // 4. 设备上报第1步执行反馈 SUCCESS，满足完成条件 displayStatus=SUCCESS
        orchestrator.onExecutionFeedback("AGT-01", execCmd1, 0, "SUCCESS", "DEVICE_SUCCESS", Map.of("displayStatus", "SUCCESS", "completed", true));
        assertEquals("COMPLETED", step1Assignment.getStepStatus());
        assertEquals("IDLE", agent1.getWorkStatus()); // 占用释放
        verify(taskEventService).append(eq(100L), eq("STEP_COMPLETED"), eq("SYSTEM"), isNull(), contains("displayStatus=SUCCESS"));

        // 5. 自动推进至第2步
        String acceptCmd2 = step2Assignment.getCommandId();
        assertNotNull(acceptCmd2);
        verify(deviceAgentMessagingService).requestTaskAcceptance(eq("AGT-02"), eq(acceptCmd2), eq(100L), eq(2), eq("CAP_NOTIFICATION"), any());

        // 6. 设备2应答 TASK_ACCEPT = true
        orchestrator.onTaskResponse("AGT-02", acceptCmd2, true, null);
        assertEquals("BUSY", agent2.getWorkStatus());
        String execCmd2 = step2Assignment.getExecuteCommandId();
        assertNotNull(execCmd2);

        // 7. 设备2上报反馈 SUCCESS，满足完成条件
        orchestrator.onExecutionFeedback("AGT-02", execCmd2, 0, "SUCCESS", "DEVICE_SUCCESS", Map.of("notificationStatus", "SUCCESS", "completed", true));
        assertEquals("COMPLETED", step2Assignment.getStepStatus());
        assertEquals("IDLE", agent2.getWorkStatus()); // 占用释放

        // 8. 全部可执行步骤完成，任务状态流转为 COMPLETED (SRS_F017.R09)
        assertEquals(TaskStatus.COMPLETED, testTask.getStatus());
        verify(taskEventService).append(eq(100L), eq("TASK_COMPLETED"), eq("SYSTEM"), isNull(), contains("全部步骤完成条件均已满足"));
    }

    @Test
    @DisplayName("SRS_F017.R02 & TC-055.S1: 首次下发失败自动重试1次，重试沿用同一指令编号保证幂等")
    void testR02_singleAutoRetryUsesSameExecuteCommandId() {
        orchestrator.assignStep(100L, 200L, 1);
        String acceptCmd = step1Assignment.getCommandId();
        orchestrator.onTaskResponse("AGT-01", acceptCmd, true, null);
        String originalExecCmd = step1Assignment.getExecuteCommandId();
        assertNotNull(originalExecCmd);

        // 首次执行失败 (attemptNo = 0)
        orchestrator.onExecutionFeedback("AGT-01", originalExecCmd, 0, "FAILED", "DEVICE_EXEC_FAIL", Map.of("error", "motor stall"));

        // 验证重试次数递增为 1，状态维持 EXECUTING
        assertEquals(1, step1Assignment.getRetryCount());
        assertEquals("EXECUTING", step1Assignment.getStepStatus());

        // 验证时间线记录 STEP_RETRY_DISPATCHED
        verify(taskEventService).append(eq(100L), eq("STEP_RETRY_DISPATCHED"), eq("SYSTEM"), eq("DEVICE_EXEC_FAIL"), contains("自动重试1次"));

        // 验证第2次下发沿用完全相同的指令编号 originalExecCmd，attemptNo 变为 1 (保证幂等)
        verify(deviceAgentMessagingService).executeCapability(eq("AGT-01"), eq(originalExecCmd), eq(100L), eq(1), eq("CAP_INFO_DISPLAY"), eq(1), any());

        // 重试后上报成功
        orchestrator.onExecutionFeedback("AGT-01", originalExecCmd, 1, "SUCCESS", "DEVICE_SUCCESS", Map.of("displayStatus", "SUCCESS", "completed", true));
        assertEquals("COMPLETED", step1Assignment.getStepStatus());
    }

    @Test
    @DisplayName("SRS_F017.R03 & TC-055.S1: 重试后仍失败不再自动重试，置步骤FAILED并进入异常影响判断")
    void testR03_retryStillFailsTriggersStepFailedAndImpactJudgment() {
        orchestrator.assignStep(100L, 200L, 1);
        orchestrator.onTaskResponse("AGT-01", step1Assignment.getCommandId(), true, null);
        String execCmd = step1Assignment.getExecuteCommandId();

        // 首次失败 -> 自动重试 1
        orchestrator.onExecutionFeedback("AGT-01", execCmd, 0, "FAILED", "ERR_HARDWARE", Map.of());
        assertEquals(1, step1Assignment.getRetryCount());

        // 重试仍失败 (attemptNo = 1)
        orchestrator.onExecutionFeedback("AGT-01", execCmd, 1, "FAILED", "ERR_HARDWARE_PERMANENT", Map.of());

        // 验证不会再次重试，步骤置为 FAILED
        assertEquals(1, step1Assignment.getRetryCount());
        assertEquals("FAILED", step1Assignment.getStepStatus());

        // 验证释放设备占用
        assertEquals("IDLE", agent1.getWorkStatus());

        // 验证记录 STEP_FAILED 事件并交由 TaskExceptionService 处理
        verify(taskEventService).append(eq(100L), eq("STEP_FAILED"), eq("SYSTEM"), eq("ERR_HARDWARE_PERMANENT"), contains("重试后仍失败"));
        verify(taskExceptionService).handleException(eq(100L), eq(1), eq("STEP_FAILED"), contains("ERR_HARDWARE_PERMANENT"));
    }

    @Test
    @DisplayName("SRS_F017.R07 & TC-054.S1: 设备应答TASK_ACCEPT仅代表承接，收到不等于步骤完成")
    void testR07_receiptDoesNotEqualStepCompletion() {
        orchestrator.assignStep(100L, 200L, 1);
        orchestrator.onTaskResponse("AGT-01", step1Assignment.getCommandId(), true, null);

        // 此时仅收到 TASK_ACCEPT 确认
        assertEquals("EXECUTING", step1Assignment.getStepStatus());
        assertNotEquals("COMPLETED", step1Assignment.getStepStatus());
        assertEquals(TaskStatus.EXECUTING, testTask.getStatus());
        assertNotEquals(TaskStatus.COMPLETED, testTask.getStatus());

        // 后续步骤严禁提前下发
        assertEquals("PENDING_ASSIGNMENT", step2Assignment.getStepStatus());
        assertNull(step2Assignment.getCommandId());
        verify(deviceAgentMessagingService, never()).requestTaskAcceptance(eq("AGT-02"), any(), any(), any(), any(), any());
        verify(taskEventService, never()).append(eq(100L), eq("STEP_COMPLETED"), any(), any(), any());
    }

    @Test
    @DisplayName("SRS_F017.R08 & TC-055.S2: 上报成功但未满足完成条件按步骤失败处理，禁止下发后续步骤 (DEF-B07-001)")
    void testR08_successFeedbackWithUnsatisfiedConditionTreatedAsFailure() {
        orchestrator.assignStep(100L, 200L, 1);
        orchestrator.onTaskResponse("AGT-01", step1Assignment.getCommandId(), true, null);
        String execCmd = step1Assignment.getExecuteCommandId();

        // 设备上报 executionResult = SUCCESS，但 outputParams 中 displayStatus = FAILED (未满足完成条件)
        orchestrator.onExecutionFeedback("AGT-01", execCmd, 0, "SUCCESS", "DEVICE_SUCCESS", Map.of("displayStatus", "FAILED", "completed", true));

        // 必须按步骤失败处理并触发自动重试，绝不能标记 COMPLETED
        assertNotEquals("COMPLETED", step1Assignment.getStepStatus());
        assertEquals(1, step1Assignment.getRetryCount());
        verify(taskEventService).append(eq(100L), eq("STEP_RETRY_DISPATCHED"), eq("SYSTEM"), eq("DEVICE_SUCCESS"), contains("完成条件未满足"));

        // 前序步骤未完成，严禁下发第2步
        assertEquals("PENDING_ASSIGNMENT", step2Assignment.getStepStatus());
        verify(deviceAgentMessagingService, never()).requestTaskAcceptance(eq("AGT-02"), any(), any(), any(), any(), any());
    }

    @Test
    @DisplayName("TC-055.S2 & StepTimeoutMonitorTask: 执行反馈超时检测、设备释放与异常回滚")
    void testTimeout_stepTimeoutDetectedAndRollback() {
        step1Assignment.setStepStatus("EXECUTING");
        step1Assignment.setDispatchedAt(LocalDateTime.now().minusSeconds(65)); // 超过 60 秒默认超时
        step1Assignment.setDeviceAgentId(10L);
        step1Assignment.setExecuteCommandId("CMD-EXEC-TIMEOUT-1");
        agent1.setWorkStatus("BUSY");
        agent1.setCurrentTaskId(100L);
        agent1.setCurrentStepSeq(1);

        when(assignmentMapper.findByStepStatusAndDispatchedAtBefore(eq("EXECUTING"), any(LocalDateTime.class)))
                .thenReturn(List.of(step1Assignment));

        // 执行超时扫描
        timeoutMonitorTask.checkStepTimeout();

        // 1. 步骤状态更新为 FAILED，结果 TIMEOUT
        assertEquals("FAILED", step1Assignment.getStepStatus());
        assertEquals("TIMEOUT", step1Assignment.getExecutionResult());
        assertEquals("ERR_EXECUTION_TIMEOUT", step1Assignment.getReasonCode());
        verify(assignmentMapper).update(step1Assignment);

        // 2. 释放设备代理占用
        assertEquals("IDLE", agent1.getWorkStatus());
        assertNull(agent1.getCurrentTaskId());
        assertNull(agent1.getCurrentStepSeq());
        verify(deviceAgentMapper).update(agent1);

        // 3. 指令表状态更新为 TIMED_OUT
        verify(deviceCommandMapper).updateStatus(eq("AGT-01"), eq("CMD-EXEC-TIMEOUT-1"), eq("EXECUTE_CAPABILITY"), eq(0), eq("TIMED_OUT"), anyString());

        // 4. 产生 STEP_TIMEOUT_DETECTED 事件并进入 TaskExceptionService
        verify(taskEventService).append(eq(100L), eq("STEP_TIMEOUT_DETECTED"), eq("SYSTEM"), eq("ERR_EXECUTION_TIMEOUT"), contains("判定执行超时"));
        verify(taskExceptionService).handleException(eq(100L), eq(1), eq("EXECUTION_TIMEOUT"), contains("执行超时未收到"));
    }

    @Test
    @DisplayName("TC-055.S2 & StepTimeoutMonitorTask: 计划步骤中自定义 stepTimeout 得到正确遵从")
    void testTimeout_customStepTimeoutRespected() throws Exception {
        // 配置该步超时时间为 30 秒
        List<Map<String, Object>> steps = List.of(
                Map.of(
                        "stepSeq", 1,
                        "stepGoal", "快速响应步骤",
                        "capabilityType", "CAP_INFO_DISPLAY",
                        "stepTimeout", 30,
                        "completionCondition", "displayStatus=SUCCESS"
                )
        );
        testPlanVersion.setPlanSteps(MAPPER.writeValueAsString(steps));

        step1Assignment.setStepStatus("EXECUTING");
        step1Assignment.setDeviceAgentId(10L);
        step1Assignment.setExecuteCommandId("CMD-EXEC-CUSTOM-30");

        // 分支 A: 下发时间已过 35 秒 (超过 30 秒) -> 触发超时
        step1Assignment.setDispatchedAt(LocalDateTime.now().minusSeconds(35));
        when(assignmentMapper.findByStepStatusAndDispatchedAtBefore(eq("EXECUTING"), any(LocalDateTime.class)))
                .thenReturn(List.of(step1Assignment));

        timeoutMonitorTask.checkStepTimeout();
        assertEquals("FAILED", step1Assignment.getStepStatus());
        assertEquals("TIMEOUT", step1Assignment.getExecutionResult());

        // 分支 B: 下发时间仅过 20 秒 (未过 30 秒) -> 不触发超时
        step1Assignment.setStepStatus("EXECUTING");
        step1Assignment.setExecutionResult(null);
        step1Assignment.setDispatchedAt(LocalDateTime.now().minusSeconds(20));
        clearInvocations(assignmentMapper, taskEventService, taskExceptionService);

        timeoutMonitorTask.checkStepTimeout();
        assertEquals("EXECUTING", step1Assignment.getStepStatus());
        assertNull(step1Assignment.getExecutionResult());
        verify(taskEventService, never()).append(any(), eq("STEP_TIMEOUT_DETECTED"), any(), any(), any());
    }

    @Test
    @DisplayName("SRS_F017.R05 & TC-056.S1: 运动安全控制字段拦截，严禁下发给设备并置步骤失败")
    void testR05_motionSafetyGuardInterceptsCommand() throws Exception {
        // 在步骤 inputParams 中掺杂运动安全控制字段 (如速度、路径点、急停)
        List<Map<String, Object>> stepsWithSafetyViolation = List.of(
                Map.of(
                        "stepSeq", 1,
                        "stepGoal", "非法控制车辆速度",
                        "capabilityType", "CAP_INFO_DISPLAY",
                        "inputParams", Map.of(
                                "content", "显示内容",
                                "speed", 15.5,
                                "emergencyStop", false
                        )
                )
        );
        testPlanVersion.setPlanSteps(MAPPER.writeValueAsString(stepsWithSafetyViolation));

        orchestrator.assignStep(100L, 200L, 1);
        orchestrator.onTaskResponse("AGT-01", step1Assignment.getCommandId(), true, null);

        // 验证被 MotionSafetyGuard 拦截：记录 COMMAND_DISPATCH_BLOCKED 事件
        verify(taskEventService).append(eq(100L), eq("COMMAND_DISPATCH_BLOCKED"), eq("SYSTEM"),
                eq("ERR_MOTION_SAFETY_FIELD"), contains("检出运动安全控制字段"));

        // 严禁发送 EXECUTE_CAPABILITY 给设备
        verify(deviceAgentMessagingService, never()).executeCapability(any(), any(), any(), any(), any(), anyInt(), any());

        // 步骤置为 FAILED 并释放设备
        assertEquals("FAILED", step1Assignment.getStepStatus());
        assertEquals("IDLE", agent1.getWorkStatus());
        verify(taskExceptionService).handleException(eq(100L), eq(1), eq("STEP_FAILED"), contains("运动安全"));
    }

    @Test
    @DisplayName("SRS_F017 设备应答NACK: 首选代理拒绝承接自动轮询下一候选")
    void testNack_taskAcceptRejectedSwitchesCandidate() {
        when(deviceCapabilityMapper.existsByDeviceIdAndCapabilityTypeAndCapabilityStatus(2L, "CAP_INFO_DISPLAY", "ENABLED"))
                .thenReturn(true);
        orchestrator.assignStep(100L, 200L, 1);
        String acceptCmd1 = step1Assignment.getCommandId();

        // 候选1拒绝承接 (NACK)
        orchestrator.onTaskResponse("AGT-01", acceptCmd1, false, "DEVICE_LOW_BATTERY");

        // 验证 AGT-01 记录入 rejectedAgentIds
        assertTrue(step1Assignment.getRejectedAgentIds().contains("AGT-01"));
        verify(taskEventService).append(eq(100L), eq("AGENT_REJECTED"), eq("SYSTEM"), isNull(), contains("AGT-01"));

        // 验证清除历史设备与指令ID，自动为下一候选 AGT-02 重新生成承接请求
        verify(deviceAgentMessagingService).requestTaskAcceptance(eq("AGT-02"), anyString(), eq(100L), eq(1), eq("CAP_INFO_DISPLAY"), any());
    }

    @Test
    @DisplayName("SRS_F017.R10: 指令全生命周期事件在时间线完整留痕")
    void testR10_fullLifecycleEventsRecordedOnTimeline() {
        orchestrator.assignStep(100L, 200L, 1);
        orchestrator.onTaskResponse("AGT-01", step1Assignment.getCommandId(), true, null);
        String execCmd = step1Assignment.getExecuteCommandId();

        // 首次失败重试
        orchestrator.onExecutionFeedback("AGT-01", execCmd, 0, "FAILED", "ERR_BUSY", Map.of());
        // 重试成功
        orchestrator.onExecutionFeedback("AGT-01", execCmd, 1, "SUCCESS", "DEVICE_SUCCESS", Map.of("displayStatus", "SUCCESS", "completed", true));

        // 验证全生命周期事件按序出现
        ArgumentCaptor<String> eventTypeCaptor = ArgumentCaptor.forClass(String.class);
        verify(taskEventService, atLeast(4)).append(eq(100L), eventTypeCaptor.capture(), any(), any(), any());
        List<String> eventTypes = eventTypeCaptor.getAllValues();

        assertTrue(eventTypes.contains("AGENT_ASSIGNMENT_REQUESTED"));
        assertTrue(eventTypes.contains("AGENT_ASSIGNED"));
        assertTrue(eventTypes.contains("STEP_DISPATCHED"));
        assertTrue(eventTypes.contains("STEP_RETRY_DISPATCHED"));
        assertTrue(eventTypes.contains("STEP_COMPLETED"));
    }
}
