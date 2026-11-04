package com.airport.ai.task;

import com.airport.ai.device.DeviceAgent;
import com.airport.ai.device.DeviceAgentMapper;
import com.airport.ai.event.TaskEventService;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/** DEF-S3-066：恢复结果以重新分配之后的任务实际状态为准，不在任务已转人工后追加“恢复成功”。 */
class RecoveryEventTruthF015Test {
    private final TaskMapper tasks = mock(TaskMapper.class);
    private final TaskStepAssignmentMapper assignments = mock(TaskStepAssignmentMapper.class);
    private final TaskExceptionMapper exceptions = mock(TaskExceptionMapper.class);
    private final TaskEventService events = mock(TaskEventService.class);
    private final TaskExecutionOrchestrator orchestrator = mock(TaskExecutionOrchestrator.class);
    private final DeviceAgentMapper agents = mock(DeviceAgentMapper.class);
    private final TaskExceptionService service = new TaskExceptionService(tasks, assignments, exceptions, agents, events,
            orchestrator, mock(ReplanningService.class));
    private final Task task = new Task();

    RecoveryEventTruthF015Test() {
        task.setId(83L);
        task.setStatus(TaskStatus.EXECUTING);
        task.setCurrentPlanVersionId(7L);
        when(tasks.findById(83L)).thenReturn(Optional.of(task));
        when(assignments.findByPlanVersionIdOrderByStepSeqAsc(7L)).thenReturn(List.of());
        when(assignments.findByPlanVersionIdAndStepSeq(anyLong(), anyInt())).thenReturn(Optional.empty());
        when(orchestrator.hasAvailableCandidate(anyLong(), anyInt(), anyList())).thenReturn(true);
    }

    private TaskException lastException() {
        ArgumentCaptor<TaskException> c = ArgumentCaptor.forClass(TaskException.class);
        verify(exceptions).insert(c.capture());
        return c.getValue();
    }

    @Test
    void successfulReassignmentRecordsRecoveryWithTypeAndImpact() {
        service.handleException(83L, 2, "STEP_FAILED", "设备失败");
        verify(orchestrator).retryAssignmentExcluding(eq(83L), eq(7L), eq(2), any());
        // 候选切换下发后，尚未收到执行成功反馈前，不应过早确认恢复成功
        verify(events, never()).append(eq(83L), eq("EXCEPTION_RECOVERED"), any(), any(), any());
        TaskException inProgress = lastException();
        assertNull(inProgress.getRecoveryResult());
        assertEquals("PROCESSING", inProgress.getExceptionStatus());

        // 新设备承接并执行成功后，确认恢复成功
        service.onStepRecovered(83L, 2);
        ArgumentCaptor<String> msg = ArgumentCaptor.forClass(String.class);
        verify(events).append(eq(83L), eq("EXCEPTION_RECOVERED"), eq("SYSTEM"), eq("STEP_FAILED"), msg.capture());
        assertTrue(msg.getValue().contains("STEP_FAILED") && msg.getValue().contains("影响结论"));
        assertEquals("SUCCESS", inProgress.getRecoveryResult());
        assertEquals("RESOLVED", inProgress.getExceptionStatus());
    }

    @Test
    void reassignmentThatEndsInManualDoesNotClaimRecovery() {
        doAnswer(i -> { task.setStatus(TaskStatus.PENDING_MANUAL); return null; })
                .when(orchestrator).retryAssignmentExcluding(anyLong(), anyLong(), anyInt(), any());
        service.handleException(83L, 2, "STEP_FAILED", "设备失败");
        verify(events, never()).append(eq(83L), eq("EXCEPTION_RECOVERED"), any(), any(), any());
        verify(events).append(eq(83L), eq("EXCEPTION_RECOVERY_FAILED"), eq("SYSTEM"), eq("STEP_FAILED"), contains("PENDING_MANUAL"));
        TaskException e = lastException();
        assertEquals("FAILED", e.getRecoveryResult(), "异常记录的恢复结果也不能写成功");
        assertTrue(e.getImpactConclusion().contains("恢复未成功"));
    }

    @Test
    void reassignmentThatEndsTheTaskDoesNotClaimRecoveryEither() {
        doAnswer(i -> { task.setStatus(TaskStatus.FAILED); return null; })
                .when(orchestrator).retryAssignmentExcluding(anyLong(), anyLong(), anyInt(), any());
        service.handleException(83L, 2, "AGENT_OFFLINE", "离线");
        verify(events, never()).append(eq(83L), eq("EXCEPTION_RECOVERED"), any(), any(), any());
    }

    @Test
    void recoveryEventKeepsAgentOfflineTypeAsItsReasonCode() {
        service.handleException(83L, 1, "AGENT_OFFLINE", "离线");
        service.onStepRecovered(83L, 1);
        verify(events).append(eq(83L), eq("EXCEPTION_RECOVERED"), eq("SYSTEM"), eq("AGENT_OFFLINE"), anyString());
    }
}
