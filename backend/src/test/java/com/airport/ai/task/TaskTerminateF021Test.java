package com.airport.ai.task;

import com.airport.ai.auth.OperationLogService;
import com.airport.ai.auth.User;
import com.airport.ai.common.BusinessException;
import com.airport.ai.common.ErrorCode;
import com.airport.ai.device.*;
import com.airport.ai.event.TaskEvent;
import com.airport.ai.event.TaskEventService;
import com.airport.ai.planning.GoalUnderstandingService;
import com.airport.ai.taskdef.TaskDefinitionService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

import java.util.*;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * SRS_F021 人工终止与安全制动（TC-066、TC-067、DEF-S3-059 专项测试集）
 * 覆盖 R01~R08 全部业务规则：
 * R01: 原因必填（1~200字）与二次确认
 * R02: 业务安全制动，未完成步骤冻结，不再下发新指令
 * R03/R04: 收集设备取消响应，联动安全释放占用
 * R05: 安全边界提示
 * R06: 阶段性成果完整保留归档
 * R07: MANUAL_TERMINATED 终态硬拦截，不可逆
 * R08 / DEF-S3-059: 操作审计 operation_log 与事件必须包含结构化取消响应摘要、cancelCommandId，严禁为空
 * TC-067: 多状态人工终止覆盖与取消超时兜底
 */
class TaskTerminateF021Test {

    private TaskMapper taskMapper;
    private PlanVersionMapper planVersionMapper;
    private ContextSnapshotMapper contextSnapshotMapper;
    private DeviceAgentMapper deviceAgentMapper;
    private GoalUnderstandingService goalUnderstandingService;
    private TaskCodeGenerator taskCodeGenerator;
    private TaskEventService taskEventService;
    private OperationLogService operationLogService;
    private TaskPlanningOrchestrator taskPlanningOrchestrator;
    private TaskStepAssignmentMapper assignmentMapper;
    private TaskDefinitionService taskDefinitionService;
    private DeviceAgentMessagingService messagingService;
    private DeviceMapper deviceMapper;
    private ForceBypassAuditRecorder forceBypassAuditRecorder;

    private TaskService taskService;
    private User operator;

    @BeforeEach
    void setUp() {
        taskMapper = mock(TaskMapper.class);
        planVersionMapper = mock(PlanVersionMapper.class);
        contextSnapshotMapper = mock(ContextSnapshotMapper.class);
        deviceAgentMapper = mock(DeviceAgentMapper.class);
        goalUnderstandingService = mock(GoalUnderstandingService.class);
        taskCodeGenerator = mock(TaskCodeGenerator.class);
        taskEventService = mock(TaskEventService.class);
        operationLogService = mock(OperationLogService.class);
        taskPlanningOrchestrator = mock(TaskPlanningOrchestrator.class);
        assignmentMapper = mock(TaskStepAssignmentMapper.class);
        taskDefinitionService = mock(TaskDefinitionService.class);
        messagingService = mock(DeviceAgentMessagingService.class);
        deviceMapper = mock(DeviceMapper.class);
        forceBypassAuditRecorder = mock(ForceBypassAuditRecorder.class);

        taskService = new TaskService(
                taskMapper, planVersionMapper, contextSnapshotMapper, deviceAgentMapper,
                goalUnderstandingService, taskCodeGenerator, taskEventService,
                operationLogService, taskPlanningOrchestrator, assignmentMapper,
                taskDefinitionService, messagingService, forceBypassAuditRecorder, deviceMapper
        );

        operator = new User();
        operator.setId(10L);
        operator.setUsername("op_test");
        operator.setRole("OPERATOR");
    }

    @Test
    @DisplayName("R01: 终止原因必填（1~200字），缺失、纯空白、超长严格拒绝抛出 400 业务异常")
    void testReasonValidation_blankNullOver200_rejectedWith400() {
        Task task = new Task();
        task.setId(1L);
        task.setStatus(TaskStatus.EXECUTING);
        when(taskMapper.findById(1L)).thenReturn(Optional.of(task));

        // 1. null 原因
        BusinessException exNull = assertThrows(BusinessException.class, () ->
                taskService.terminate(1L, null, operator));
        assertEquals(ErrorCode.TERMINATE_REASON_REQUIRED, exNull.getErrorCode());

        // 2. 纯空白原因
        BusinessException exBlank = assertThrows(BusinessException.class, () ->
                taskService.terminate(1L, "    ", operator));
        assertEquals(ErrorCode.TERMINATE_REASON_REQUIRED, exBlank.getErrorCode());

        // 3. 超过 200 字符原因
        String over200 = "A".repeat(201);
        BusinessException exOver = assertThrows(BusinessException.class, () ->
                taskService.terminate(1L, over200, operator));
        assertEquals(ErrorCode.PARAM_FORMAT_ERROR, exOver.getErrorCode());

        // 验证未进行任何状态更新或审计记录
        verify(taskMapper, never()).update(any());
        verify(operationLogService, never()).record(any(), any(), any(), eq("TASK_TERMINATE"), any(), any(), any(), any());
    }

    @Test
    @DisplayName("R08 & DEF-S3-059: 终止审计与事件完整记录取消响应摘要、cancelCommandId、deviceCode，严禁 detail 为 null")
    void testTerminateDetailContainsDeviceCancelResultsAndCancelCommandId_DEF_S3_059() throws Exception {
        Long taskId = 64L;
        Task task = new Task();
        task.setId(taskId);
        task.setTaskCode("TASK-20261027-0064");
        task.setStatus(TaskStatus.EXECUTING);
        task.setCurrentPlanVersionId(10L);
        when(taskMapper.findById(taskId)).thenReturn(Optional.of(task));

        // 步骤 1 正在执行中
        TaskStepAssignment assignment = new TaskStepAssignment();
        assignment.setId(101L);
        assignment.setTaskId(taskId);
        assignment.setPlanVersionId(10L);
        assignment.setStepSeq(1);
        assignment.setStepStatus("EXECUTING");
        assignment.setDeviceAgentId(3L);
        when(assignmentMapper.findByPlanVersionIdOrderByStepSeqAsc(10L)).thenReturn(List.of(assignment));

        // 关联设备代理与物理设备
        DeviceAgent agent = new DeviceAgent();
        agent.setId(3L);
        agent.setAgentCode("AGT-0158A712");
        agent.setDeviceId(200L);
        agent.setWorkStatus("BUSY");
        agent.setCurrentTaskId(taskId);
        agent.setCurrentStepSeq(1);

        Device device = new Device();
        device.setId(200L);
        device.setDeviceCode("SIM_F2_DISPLAY");
        when(deviceMapper.findById(200L)).thenReturn(Optional.of(device));

        when(deviceAgentMapper.findByCurrentTaskId(taskId)).thenReturn(List.of(agent));
        when(deviceAgentMapper.findById(3L)).thenReturn(Optional.of(agent));
        when(deviceAgentMapper.findByIdForUpdate(3L)).thenReturn(Optional.of(agent));

        // 执行终止
        Task terminated = taskService.terminate(taskId, "阶段3人工终止边界复测", operator);

        // 1. 任务终态核验
        assertEquals(TaskStatus.MANUAL_TERMINATED, terminated.getStatus());
        assertEquals("阶段3人工终止边界复测", terminated.getManualTerminateReason());

        // 2. 步骤冻结核验 (R02)
        assertEquals("FROZEN", assignment.getStepStatus());
        verify(assignmentMapper).update(assignment);

        // 3. 联动下发取消指令核验 (R03/R04)
        ArgumentCaptor<String> cancelCmdCaptor = ArgumentCaptor.forClass(String.class);
        verify(messagingService).cancelTask(eq("AGT-0158A712"), cancelCmdCaptor.capture(), eq(taskId), eq(1));
        String capturedCancelCmdId = cancelCmdCaptor.getValue();
        assertNotNull(capturedCancelCmdId);
        assertTrue(capturedCancelCmdId.startsWith("CMD-"), "取消指令ID必须具备全局唯一 CMD- 前缀");

        // 4. 核心缺陷闭环核验 DEF-S3-059: operation_logs.detail 必须包含完整设备取消摘要与 cancelCommandId
        ArgumentCaptor<Map<String, Object>> detailCaptor = ArgumentCaptor.forClass(Map.class);
        verify(operationLogService).record(
                eq(10L), eq("op_test"), eq("OPERATOR"),
                eq("TASK_TERMINATE"), eq("TASK-20261027-0064"), eq("SUCCESS"), isNull(),
                detailCaptor.capture()
        );

        Map<String, Object> auditDetail = detailCaptor.getValue();
        assertNotNull(auditDetail, "TASK_TERMINATE 操作记录 detail 严禁为 null！");
        assertEquals("阶段3人工终止边界复测", auditDetail.get("reason"));
        assertEquals("EXECUTING", auditDetail.get("previousStatus"));
        assertEquals("op_test", auditDetail.get("operator"));

        @SuppressWarnings("unchecked")
        List<Map<String, Object>> deviceCancelResults = (List<Map<String, Object>>) auditDetail.get("deviceCancelResults");
        assertNotNull(deviceCancelResults, "必须包含 deviceCancelResults 设备取消摘要列表");
        assertEquals(1, deviceCancelResults.size());

        Map<String, Object> devResult = deviceCancelResults.get(0);
        assertEquals("AGT-0158A712", devResult.get("agentId"));
        assertEquals("AGT-0158A712", devResult.get("agentCode"));
        assertEquals("SIM_F2_DISPLAY", devResult.get("deviceCode"), "必须解析到关联物理设备编码 SIM_F2_DISPLAY");
        assertEquals(capturedCancelCmdId, devResult.get("cancelCommandId"), "取消结果中必须记录下发的 cancelCommandId");
        assertEquals("CANCEL_QUEUED", devResult.get("result"));
        assertEquals("CANCEL_QUEUED", devResult.get("cancelStatus"));

        // 5. 事件留痕核验 (task_events) 必须为完整 JSON 结构且包含取消指令编号及原因
        verify(taskEventService).append(eq(taskId), eq("TASK_CANCEL_REQUESTED"), eq("OPERATOR"), isNull(), contains("AGT-0158A712"));
        ArgumentCaptor<String> eventDetailCaptor = ArgumentCaptor.forClass(String.class);
        verify(taskEventService).append(eq(taskId), eq("TASK_TERMINATED"), eq("OPERATOR"), eq("NORMAL_MANUAL_TERMINATED"), eventDetailCaptor.capture());
        String eventDetailJson = eventDetailCaptor.getValue();
        assertNotNull(eventDetailJson);
        assertTrue(eventDetailJson.startsWith("{") && eventDetailJson.endsWith("}"), "TASK_TERMINATED.detail 必须为有效 JSON 对象字符串");
        com.fasterxml.jackson.databind.ObjectMapper mapper = new com.fasterxml.jackson.databind.ObjectMapper();
        com.fasterxml.jackson.databind.JsonNode eventJson = mapper.readTree(eventDetailJson);
        assertEquals("阶段3人工终止边界复测", eventJson.get("reason").asText());
        assertEquals("EXECUTING", eventJson.get("previousStatus").asText());
        assertEquals("op_test", eventJson.get("operator").asText());
        assertTrue(eventJson.has("deviceCancelResults"));
        assertEquals(capturedCancelCmdId, eventJson.get("deviceCancelResults").get(0).get("cancelCommandId").asText());
    }

    @Test
    @DisplayName("R07: 终态硬拦截，处于 MANUAL_TERMINATED 的任务严禁再次终止、转基线、重试规划或补充信息")
    void testTerminalStateHardBlocking_R07() {
        Long taskId = 88L;
        Task task = new Task();
        task.setId(taskId);
        task.setTaskCode("TASK-88");
        task.setStatus(TaskStatus.MANUAL_TERMINATED);
        task.setManualTerminateReason("已终止");
        when(taskMapper.findById(taskId)).thenReturn(Optional.of(task));

        // 1. 尝试再次人工终止 -> 409 TASK_TERMINATE_NOT_ALLOWED
        BusinessException exTerm = assertThrows(BusinessException.class, () ->
                taskService.terminate(taskId, "再次终止", operator));
        assertEquals(ErrorCode.TASK_TERMINATE_NOT_ALLOWED, exTerm.getErrorCode());

        // 2. 尝试计划前取消 -> 409 TASK_CANNOT_CANCEL_AFTER_PLANNING
        BusinessException exCancel = assertThrows(BusinessException.class, () ->
                taskService.cancel(taskId, "尝试取消", operator));
        assertEquals(ErrorCode.TASK_CANNOT_CANCEL_AFTER_PLANNING, exCancel.getErrorCode());

        // 3. 尝试待人工处置（转基线/重试规划/置为失败） -> 409 TASK_STATUS_NOT_ALLOWED
        BusinessException exAction = assertThrows(BusinessException.class, () ->
                taskService.manualAction(taskId, "RETRY_PLANNING", "处置原因", operator));
        assertEquals(ErrorCode.TASK_STATUS_NOT_ALLOWED, exAction.getErrorCode());

        BusinessException exBase = assertThrows(BusinessException.class, () ->
                taskService.manualAction(taskId, "SWITCH_TO_BASELINE", "处置原因", operator));
        assertEquals(ErrorCode.TASK_STATUS_NOT_ALLOWED, exBase.getErrorCode());

        // 4. 尝试补充信息 clarify -> 409 TASK_STATUS_NOT_ALLOWED
        com.airport.ai.task.dto.ClarifyTaskRequest clarifyReq = new com.airport.ai.task.dto.ClarifyTaskRequest();
        clarifyReq.setAnswers(Map.of("q1", "a1"));
        BusinessException exClarify = assertThrows(BusinessException.class, () ->
                taskService.clarify(taskId, clarifyReq, operator));
        assertEquals(ErrorCode.TASK_STATUS_NOT_ALLOWED, exClarify.getErrorCode());
    }

    @Test
    @DisplayName("TC-067.S1: 支持 6 种运行期状态合法人工终止，已处终态（COMPLETED/FAILED/MANUAL_TERMINATED）硬拦截")
    void testMultiStatusTermination_TC_067_S1() {
        TaskStatus[] validStatuses = {
                TaskStatus.PLANNING,
                TaskStatus.SUPERVISING,
                TaskStatus.PENDING_ASSIGNMENT,
                TaskStatus.DOWNGRADING,
                TaskStatus.EXECUTING,
                TaskStatus.PENDING_MANUAL
        };

        for (TaskStatus status : validStatuses) {
            Task task = new Task();
            task.setId(100L + status.ordinal());
            task.setTaskCode("TASK-" + status.name());
            task.setStatus(status);
            when(taskMapper.findById(task.getId())).thenReturn(Optional.of(task));

            Task result = taskService.terminate(task.getId(), "多状态合法终止测试", operator);
            assertEquals(TaskStatus.MANUAL_TERMINATED, result.getStatus());
        }

        TaskStatus[] terminalStatuses = {
                TaskStatus.COMPLETED,
                TaskStatus.FAILED,
                TaskStatus.MANUAL_TERMINATED
        };

        for (TaskStatus status : terminalStatuses) {
            Task task = new Task();
            task.setId(200L + status.ordinal());
            task.setTaskCode("TASK-TERM-" + status.name());
            task.setStatus(status);
            when(taskMapper.findById(task.getId())).thenReturn(Optional.of(task));

            BusinessException ex = assertThrows(BusinessException.class, () ->
                    taskService.terminate(task.getId(), "终态拦截测试", operator));
            assertEquals(ErrorCode.TASK_TERMINATE_NOT_ALLOWED, ex.getErrorCode());
        }
    }

    @Test
    @DisplayName("R06 & R02: 阶段成果保留归档，已完成步骤保持 COMPLETED，未完成步骤置 FROZEN，停止后续下发")
    void testBusinessBrakeAndStepFreezing_R02_R06() {
        Long taskId = 65L;
        Task task = new Task();
        task.setId(taskId);
        task.setTaskCode("TASK-65");
        task.setStatus(TaskStatus.EXECUTING);
        task.setCurrentPlanVersionId(50L);
        when(taskMapper.findById(taskId)).thenReturn(Optional.of(task));

        // 步骤 1: COMPLETED (阶段成果)
        TaskStepAssignment step1 = new TaskStepAssignment();
        step1.setId(501L);
        step1.setStepSeq(1);
        step1.setStepStatus("COMPLETED");

        // 步骤 2: EXECUTING (正在执行)
        TaskStepAssignment step2 = new TaskStepAssignment();
        step2.setId(502L);
        step2.setStepSeq(2);
        step2.setStepStatus("EXECUTING");
        step2.setDeviceAgentId(7L);

        // 步骤 3: PENDING_ASSIGNMENT (尚未执行)
        TaskStepAssignment step3 = new TaskStepAssignment();
        step3.setId(503L);
        step3.setStepSeq(3);
        step3.setStepStatus("PENDING_ASSIGNMENT");

        when(assignmentMapper.findByPlanVersionIdOrderByStepSeqAsc(50L))
                .thenReturn(List.of(step1, step2, step3));

        DeviceAgent agent7 = new DeviceAgent();
        agent7.setId(7L);
        agent7.setAgentCode("AGT-7");
        agent7.setCurrentTaskId(taskId);
        when(deviceAgentMapper.findByCurrentTaskId(taskId)).thenReturn(List.of(agent7));
        when(deviceAgentMapper.findById(7L)).thenReturn(Optional.of(agent7));
        when(deviceAgentMapper.findByIdForUpdate(7L)).thenReturn(Optional.of(agent7));

        taskService.terminate(taskId, "阶段业务制动测试", operator);

        // 验证: 步骤 1 保持 COMPLETED，严禁被篡改为 FROZEN 或清空 (R06)
        assertEquals("COMPLETED", step1.getStepStatus());
        verify(assignmentMapper, never()).update(step1);

        // 验证: 步骤 2、3 被冻结为 FROZEN (R02)
        assertEquals("FROZEN", step2.getStepStatus());
        assertEquals("FROZEN", step3.getStepStatus());
        verify(assignmentMapper).update(step2);
        verify(assignmentMapper).update(step3);
    }

    @Test
    @DisplayName("TC-067.S2 & 异常兜底: 设备取消下发异常（如离线/网络故障）记录 CANCEL_FAILED 并不影响任务安全终态化")
    void testDeviceCancelDeliveryFailureHandledGracefully() {
        Long taskId = 77L;
        Task task = new Task();
        task.setId(taskId);
        task.setTaskCode("TASK-77");
        task.setStatus(TaskStatus.EXECUTING);
        task.setCurrentPlanVersionId(70L);
        when(taskMapper.findById(taskId)).thenReturn(Optional.of(task));

        DeviceAgent agent = new DeviceAgent();
        agent.setId(9L);
        agent.setAgentCode("AGT-FAULT");
        agent.setCurrentTaskId(taskId);
        when(deviceAgentMapper.findByCurrentTaskId(taskId)).thenReturn(List.of(agent));
        when(deviceAgentMapper.findById(9L)).thenReturn(Optional.of(agent));
        when(deviceAgentMapper.findByIdForUpdate(9L)).thenReturn(Optional.of(agent));

        // 模拟设备取消指令下发抛出离线异常
        doThrow(new BusinessException(ErrorCode.DEVICE_OFFLINE, "设备离线"))
                .when(messagingService).cancelTask(eq("AGT-FAULT"), anyString(), eq(taskId), any());

        Task result = taskService.terminate(taskId, "离线设备终止容错", operator);

        // 1. 任务依然顺利置为 MANUAL_TERMINATED
        assertEquals(TaskStatus.MANUAL_TERMINATED, result.getStatus());

        // 2. 任务事件记录取消发送失败
        verify(taskEventService).append(eq(taskId), eq("TASK_CANCEL_DELIVERY_FAILED"), eq("OPERATOR"), eq("DEVICE_API_ERROR"), contains("AGT-FAULT"));

        // 3. 审计日志 detail 记录 CANCEL_FAILED
        ArgumentCaptor<Map<String, Object>> detailCaptor = ArgumentCaptor.forClass(Map.class);
        verify(operationLogService).record(any(), any(), any(), eq("TASK_TERMINATE"), any(), eq("SUCCESS"), isNull(), detailCaptor.capture());
        Map<String, Object> detail = detailCaptor.getValue();

        @SuppressWarnings("unchecked")
        List<Map<String, Object>> cancelResults = (List<Map<String, Object>>) detail.get("deviceCancelResults");
        assertEquals(1, cancelResults.size());
        assertEquals("CANCEL_FAILED", cancelResults.get(0).get("result"));
        assertEquals("CANCEL_FAILED", cancelResults.get(0).get("cancelStatus"));
        assertNotNull(cancelResults.get(0).get("cancelCommandId"));
    }

    @Test
    @DisplayName("TaskEvent getDetail 别名兼容：保证 detailSummary 与 detail 均可访问且内容一致")
    void testTaskEventDetailAccessor() {
        TaskEvent event = new TaskEvent();
        event.setDetailSummary("结构化取消信息");
        assertEquals("结构化取消信息", event.getDetailSummary());
        assertEquals("结构化取消信息", event.getDetail());

        event.setDetail("新结构化信息");
        assertEquals("结构化取消信息", event.getDetailSummary(), "已存在时不被覆盖");

        TaskEvent emptyEvent = new TaskEvent();
        emptyEvent.setDetail("首次写入详情");
        assertEquals("首次写入详情", emptyEvent.getDetailSummary());
        assertEquals("首次写入详情", emptyEvent.getDetail());
    }

    @Test
    @DisplayName("TaskEvent JSON detail: 结构化事件 detail 满足 json.loads 整体解析，detailSummary 保留时间线文字")
    void testTaskEventJsonDetailAndSummary() throws Exception {
        String jsonDetail = "{\"summary\":\"运行操作员人工终止任务，原因: 设备故障\",\"reason\":\"设备故障\",\"previousStatus\":\"EXECUTING\",\"operator\":\"admin\",\"deviceCancelResults\":[{\"deviceCode\":\"DEV_1\",\"cancelCommandId\":\"CMD-1\"}]}";
        TaskEvent event = new TaskEvent();
        event.setDetailSummary(jsonDetail);

        // detailSummary 保持人类可读时间线摘要
        assertEquals("运行操作员人工终止任务，原因: 设备故障", event.getDetailSummary());
        // detail 保持完整 JSON 字符串，可被 ObjectMapper / json.loads 整体解析
        assertEquals(jsonDetail, event.getDetail());
        assertEquals(jsonDetail, event.getRawDetailSummary());

        com.fasterxml.jackson.databind.ObjectMapper mapper = new com.fasterxml.jackson.databind.ObjectMapper();
        com.fasterxml.jackson.databind.JsonNode root = mapper.readTree(event.getDetail());
        assertEquals("设备故障", root.get("reason").asText());
        assertEquals("EXECUTING", root.get("previousStatus").asText());
        assertEquals("admin", root.get("operator").asText());
        assertTrue(root.has("deviceCancelResults"));
        assertEquals("DEV_1", root.get("deviceCancelResults").get(0).get("deviceCode").asText());
    }
}
