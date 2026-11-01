package com.airport.ai.task;

import com.airport.ai.device.DeviceAgentMapper;
import com.airport.ai.event.TaskEventService;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/** DEF-S3-065 / SRS_F015.R08：基线计划执行失败且恢复穷尽后直接待人工，不再触发局部重新规划。 */
class BaselineFailureNoReplanF015Test {
    private final TaskMapper tasks = mock(TaskMapper.class);
    private final TaskStepAssignmentMapper assignments = mock(TaskStepAssignmentMapper.class);
    private final TaskExceptionMapper exceptions = mock(TaskExceptionMapper.class);
    private final TaskEventService events = mock(TaskEventService.class);
    private final TaskExecutionOrchestrator orchestrator = mock(TaskExecutionOrchestrator.class);
    private final ReplanningService replanning = mock(ReplanningService.class);
    private final PlanVersionMapper plans = mock(PlanVersionMapper.class);
    private final TaskExceptionService service = new TaskExceptionService(tasks, assignments, exceptions,
            mock(DeviceAgentMapper.class), events, orchestrator, replanning);

    BaselineFailureNoReplanF015Test() {
        ReflectionTestUtils.setField(service, "planVersionMapper", plans);
        when(orchestrator.hasAvailableCandidate(anyLong(), anyInt(), anyList())).thenReturn(false);
    }

    private Task task(TaskStatus status, boolean replanUsed, String planSource) {
        Task t = new Task();
        t.setId(83L);
        t.setStatus(status);
        t.setReplanUsed(replanUsed);
        t.setCurrentPlanVersionId(7L);
        when(tasks.findById(83L)).thenReturn(Optional.of(t));
        PlanVersion plan = new PlanVersion();
        plan.setSource(planSource);
        when(plans.findById(7L)).thenReturn(Optional.of(plan));
        when(assignments.findByPlanVersionIdOrderByStepSeqAsc(7L)).thenReturn(List.of());
        when(assignments.findByPlanVersionIdAndStepSeq(anyLong(), anyInt())).thenReturn(Optional.empty());
        return t;
    }

    private void fail() {
        service.handleException(83L, 1, "STEP_FAILED", "两台机器人执行失败");
    }

    @Test
    void executingBaselineTaskGoesStraightToManualWithoutReplanning() {
        Task t = task(TaskStatus.EXECUTING, false, "BASELINE_TEMPLATE");
        fail();
        verify(replanning, never()).replan(anyLong(), anyInt(), anyString());
        assertEquals(TaskStatus.PENDING_MANUAL, t.getStatus());
        assertTrue(t.getFailureReason().contains("基线"));
        verify(events).append(eq(83L), eq("TASK_PENDING_MANUAL"), any(), any(), any());
        verify(events, never()).append(eq(83L), eq("REPLANNING_TRIGGERED"), any(), any(), any());
    }

    @Test
    void autonomousPlanStillGetsOneReplanningChance() {
        Task t = task(TaskStatus.EXECUTING, false, "AUTONOMOUS");
        fail();
        verify(replanning).replan(eq(83L), eq(1), contains("STEP_FAILED"));
        assertNotEquals(TaskStatus.PENDING_MANUAL, t.getStatus());
    }

    @Test
    void usedReplanQuotaStillGoesToManualForAutonomousPlans() {
        Task t = task(TaskStatus.EXECUTING, true, "AUTONOMOUS");
        fail();
        verify(replanning, never()).replan(anyLong(), anyInt(), anyString());
        assertEquals(TaskStatus.PENDING_MANUAL, t.getStatus());
    }

    @Test
    void downgradingStatusStillCountsAsADowngradedTaskEvenWithoutPlanLookup() {
        Task t = task(TaskStatus.DOWNGRADING, false, "AUTONOMOUS");
        fail();
        verify(replanning, never()).replan(anyLong(), anyInt(), anyString());
        assertEquals(TaskStatus.PENDING_MANUAL, t.getStatus());
    }

    @Test
    void missingPlanMapperFallsBackToTheStatusRuleAndDoesNotBreak() {
        ReflectionTestUtils.setField(service, "planVersionMapper", null);
        Task t = task(TaskStatus.EXECUTING, false, "BASELINE_TEMPLATE");
        fail();
        verify(replanning).replan(eq(83L), eq(1), anyString());
    }
}
