package com.airport.ai.task;

import com.airport.ai.auth.OperationLogService;
import com.airport.ai.auth.User;
import com.airport.ai.common.BusinessException;
import com.airport.ai.common.ErrorCode;
import com.airport.ai.device.DeviceAgent;
import com.airport.ai.device.DeviceAgentMapper;
import com.airport.ai.device.DeviceAgentMessagingService;
import com.airport.ai.event.TaskEventService;
import com.airport.ai.planning.GoalUnderstandingService;
import com.airport.ai.taskdef.TaskDefinitionService;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

import java.util.List;
import java.util.Map;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/** DEF-S3-062（人工处置原因）与 DEF-S3-059（终止日志详情）：操作记录与任务事件都要有原因和设备取消结果。 */
class ManualActionAuditF020Test {
    private final TaskMapper tasks = mock(TaskMapper.class);
    private final TaskEventService events = mock(TaskEventService.class);
    private final OperationLogService audit = mock(OperationLogService.class);
    private final DeviceAgentMapper agents = mock(DeviceAgentMapper.class);
    private final DeviceAgentMessagingService messaging = mock(DeviceAgentMessagingService.class);
    private final TaskStepAssignmentMapper assignments = mock(TaskStepAssignmentMapper.class);
    private final TaskPlanningOrchestrator planning = mock(TaskPlanningOrchestrator.class);
    private final TaskService service = new TaskService(tasks, mock(PlanVersionMapper.class), mock(ContextSnapshotMapper.class),
            agents, mock(GoalUnderstandingService.class), mock(TaskCodeGenerator.class), events, audit, planning,
            assignments, mock(TaskDefinitionService.class), messaging);

    private User operator() {
        User u = new User();
        u.setId(4L);
        u.setUsername("op");
        u.setRole("OPERATOR");
        return u;
    }

    private Task task(TaskStatus status) {
        Task t = new Task();
        t.setId(20L);
        t.setTaskCode("TASK-20");
        t.setStatus(status);
        t.setCurrentPlanVersionId(7L);
        when(tasks.findById(20L)).thenReturn(Optional.of(t));
        return t;
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> lastAuditDetail() {
        ArgumentCaptor<Map<String, Object>> detail = ArgumentCaptor.forClass(Map.class);
        verify(audit).record(any(), any(), any(), any(), any(), any(), any(), detail.capture());
        return detail.getValue();
    }

    @Test
    void markFailedRequiresAReasonAndChangesNothingWithout() {
        Task t = task(TaskStatus.PENDING_MANUAL);
        for (String reason : new String[]{null, "", "   "}) {
            BusinessException ex = assertThrows(BusinessException.class, () -> service.manualAction(20L, "MARK_FAILED", reason, operator()));
            assertEquals(ErrorCode.PARAM_MISSING, ex.getErrorCode());
        }
        assertEquals(TaskStatus.PENDING_MANUAL, t.getStatus());
        verify(tasks, never()).update(any());
        verifyNoInteractions(audit);
    }

    @Test
    void markFailedWithAReasonPutsItInTheTaskTheEventAndTheOperationRecord() {
        Task t = task(TaskStatus.PENDING_MANUAL);
        service.manualAction(20L, "MARK_FAILED", "  现场确认无法继续  ", operator());
        assertEquals(TaskStatus.FAILED, t.getStatus());
        assertTrue(t.getFailureReason().contains("现场确认无法继续"));
        verify(events).append(eq(20L), eq("TASK_FAILED"), eq("OPERATOR"), eq("MANUAL_MARK_FAILED"), contains("现场确认无法继续"));
        Map<String, Object> detail = lastAuditDetail();
        assertEquals("MARK_FAILED", detail.get("action"));
        assertEquals("现场确认无法继续", detail.get("reason"));
        assertEquals("FAILED", detail.get("resultStatus"));
    }

    @Test
    void tooLongReasonIsRejected() {
        task(TaskStatus.PENDING_MANUAL);
        BusinessException ex = assertThrows(BusinessException.class,
                () -> service.manualAction(20L, "MARK_FAILED", "x".repeat(201), operator()));
        assertEquals(ErrorCode.PARAM_FORMAT_ERROR, ex.getErrorCode());
    }

    @Test
    void baselineAndRetryWorkWithoutAReasonAndRecordOneWhenGiven() {
        task(TaskStatus.PENDING_MANUAL);
        service.manualAction(20L, "SWITCH_TO_BASELINE", null, operator());
        verify(planning).switchToBaseline(20L);
        assertNull(lastAuditDetail().get("reason"));

        reset(audit, events);
        task(TaskStatus.PENDING_MANUAL);
        service.manualAction(20L, "RETRY_PLANNING", "模型已恢复", operator());
        verify(events).append(eq(20L), eq("REPLANNING_TRIGGERED"), eq("OPERATOR"), isNull(), contains("模型已恢复"));
        assertEquals("模型已恢复", lastAuditDetail().get("reason"));
    }

    @Test
    void threeArgumentOverloadStillWorksForExistingCallers() {
        task(TaskStatus.PENDING_MANUAL);
        service.manualAction(20L, "SWITCH_TO_BASELINE", operator());
        verify(planning).switchToBaseline(20L);
    }

    @Test
    void terminationOperationRecordCarriesReasonPreviousStatusAndEveryDeviceCancelResult() {
        Task t = task(TaskStatus.EXECUTING);
        DeviceAgent ok = new DeviceAgent();
        ok.setId(1L);
        ok.setAgentCode("AGT-OK");
        DeviceAgent bad = new DeviceAgent();
        bad.setId(2L);
        bad.setAgentCode("AGT-BAD");
        when(agents.findByCurrentTaskId(20L)).thenReturn(List.of(ok, bad));
        when(assignments.findByPlanVersionIdOrderByStepSeqAsc(7L)).thenReturn(List.of());
        doThrow(new RuntimeException("设备不可达")).when(messaging).cancelTask(eq("AGT-BAD"), anyString(), anyLong(), any());

        service.terminate(20L, "航班取消，终止服务", operator());

        assertEquals(TaskStatus.MANUAL_TERMINATED, t.getStatus());
        Map<String, Object> detail = lastAuditDetail();
        assertEquals("航班取消，终止服务", detail.get("reason"));
        assertEquals("EXECUTING", detail.get("previousStatus"));
        @SuppressWarnings("unchecked")
        List<Map<String, String>> results = (List<Map<String, String>>) detail.get("deviceCancelResults");
        assertEquals(2, results.size());
        Map<String, String> okResult = results.stream().filter(r -> "AGT-OK".equals(r.get("agentId"))).findFirst().orElseThrow();
        Map<String, String> badResult = results.stream().filter(r -> "AGT-BAD".equals(r.get("agentId"))).findFirst().orElseThrow();
        assertEquals("CANCEL_QUEUED", okResult.get("result"));
        assertEquals("CANCEL_FAILED", badResult.get("result"));
        assertNotNull(okResult.get("cancelCommandId"), "要能和取消命令/确认事件对上");
        assertNotNull(badResult.get("cancelCommandId"));
    }

    @Test
    void terminationWithNoDevicesStillRecordsTheReasonAndAnEmptyResultList() {
        task(TaskStatus.PLANNING);
        when(agents.findByCurrentTaskId(20L)).thenReturn(List.of());
        service.terminate(20L, "操作员取消", operator());
        Map<String, Object> detail = lastAuditDetail();
        assertEquals("操作员取消", detail.get("reason"));
        assertEquals(List.of(), detail.get("deviceCancelResults"));
    }
}
