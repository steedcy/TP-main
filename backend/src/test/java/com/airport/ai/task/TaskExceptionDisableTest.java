package com.airport.ai.task;

import com.airport.ai.device.DeviceAgent;
import com.airport.ai.device.DeviceAgentMapper;
import com.airport.ai.event.TaskEventService;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.*;

/** DEF-S3-077：设备停用按步骤关联（而非agent.current_task_id）触发恢复流程。 */
class TaskExceptionDisableTest {

    private final TaskMapper taskMapper = mock(TaskMapper.class);
    private final TaskStepAssignmentMapper assignmentMapper = mock(TaskStepAssignmentMapper.class);
    private final TaskExceptionMapper exceptionMapper = mock(TaskExceptionMapper.class);
    private final TaskEventService eventService = mock(TaskEventService.class);
    private final TaskExecutionOrchestrator orchestrator = mock(TaskExecutionOrchestrator.class);
    private final TaskExceptionService service = new TaskExceptionService(taskMapper, assignmentMapper,
            exceptionMapper, mock(DeviceAgentMapper.class), eventService, orchestrator, mock(ReplanningService.class));

    private TaskStepAssignment assignment(long taskId, int seq) {
        TaskStepAssignment a = new TaskStepAssignment();
        a.setTaskId(taskId);
        a.setStepSeq(seq);
        a.setStepStatus("PENDING_ASSIGNMENT");
        Task t = new Task();
        t.setId(taskId);
        t.setStatus(TaskStatus.PENDING_ASSIGNMENT);
        t.setCurrentPlanVersionId(100L + taskId);
        when(taskMapper.findById(taskId)).thenReturn(Optional.of(t));
        return a;
    }

    private DeviceAgent agent() {
        DeviceAgent agent = new DeviceAgent();
        agent.setId(9L);
        agent.setAgentCode("AGT-9");
        agent.setCurrentTaskId(null); // 待分配阶段尚未占用
        return agent;
    }

    @Test
    void pendingAssignmentsWithNullCurrentTaskAreRecoveredPerStep() {
        DeviceAgent agent = agent();
        List<TaskStepAssignment> active = List.of(assignment(1L, 1), assignment(2L, 3));
        when(assignmentMapper.findActiveByAgentId(9L)).thenReturn(active);
        assertEquals(2, service.handleAgentDisabled(agent));
        ArgumentCaptor<TaskException> saved = ArgumentCaptor.forClass(TaskException.class);
        verify(exceptionMapper, times(2)).insert(saved.capture());
        assertTrue(saved.getAllValues().stream().allMatch(e -> "AGENT_OFFLINE".equals(e.getExceptionType())));
        verify(eventService, atLeastOnce()).append(anyLong(), eq("EXCEPTION_DETECTED"), any(), any(), any());
    }

    @Test
    void noActiveAssignmentsMeansNothingToRecover() {
        when(assignmentMapper.findActiveByAgentId(9L)).thenReturn(List.of());
        assertEquals(0, service.handleAgentDisabled(agent()));
        verifyNoInteractions(exceptionMapper);
    }

    @Test
    void freezeRemainingStepsPassesTaskIdToReleaseAgent_DEF_S3_103() {
        long taskId = 50L;
        Task t = new Task();
        t.setId(taskId);
        t.setStatus(TaskStatus.EXECUTING);
        t.setCurrentPlanVersionId(250L);
        when(taskMapper.findById(taskId)).thenReturn(Optional.of(t));

        TaskStepAssignment step1 = new TaskStepAssignment();
        step1.setTaskId(taskId);
        step1.setPlanVersionId(250L);
        step1.setStepSeq(1);
        step1.setStepStatus("FAILED");

        TaskStepAssignment step2 = new TaskStepAssignment();
        step2.setTaskId(taskId);
        step2.setPlanVersionId(250L);
        step2.setStepSeq(2);
        step2.setStepStatus("PENDING_ASSIGNMENT");
        step2.setDeviceAgentId(99L);

        when(assignmentMapper.findByPlanVersionIdOrderByStepSeqAsc(250L)).thenReturn(List.of(step1, step2));
        when(orchestrator.hasAvailableCandidate(anyLong(), anyInt(), anyList())).thenReturn(false);

        service.handleException(taskId, 1, "STEP_FAILED", "step failed");

        assertEquals("FROZEN", step2.getStepStatus());
        verify(assignmentMapper).update(step2);
        // DEF-S3-103: 必须携带 taskId 调用 releaseAgent(agentId, taskId)
        verify(orchestrator).releaseAgent(eq(99L), eq(taskId));
    }
}
