package com.airport.ai.task;

import com.airport.ai.baseline.BaselineTemplateService;
import com.airport.ai.event.TaskEventService;
import com.airport.ai.planning.PlanningModelService;
import com.airport.ai.risk.RiskAssessmentService;
import com.airport.ai.taskdef.TaskDefinitionService;
import org.junit.jupiter.api.Test;

import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

/** DEF-S3-033：目标理解超时/异常后任务不停在PLANNING，无可用基线时转待人工且不下发指令。 */
class UnderstandingFailureDowngradeTest {
    @Test void noBaselineTemplateGoesToPendingManualInsteadOfStayingInPlanning() {
        var tasks = mock(TaskMapper.class);
        var baseline = mock(BaselineTemplateService.class);
        var events = mock(TaskEventService.class);
        var execution = mock(TaskExecutionOrchestrator.class);
        var task = new Task(); task.setId(7L); task.setStatus(TaskStatus.PLANNING); task.setTaskFamily("OVERSIZE_BAGGAGE");
        when(tasks.findById(7L)).thenReturn(Optional.of(task));
        when(baseline.matchForDowngrade("OVERSIZE_BAGGAGE")).thenReturn(Optional.empty());
        var orchestrator = new TaskPlanningOrchestrator(tasks, mock(PlanVersionMapper.class), mock(ContextSnapshotService.class),
                mock(PlanValidationService.class), mock(PlanningModelService.class), mock(RiskAssessmentService.class),
                baseline, events, execution, mock(TaskDefinitionService.class));

        orchestrator.downgradeAfterUnderstandingFailure(7L, "目标理解超时或异常: timeout");

        assertEquals(TaskStatus.PENDING_MANUAL, task.getStatus());
        assertTrue(task.getFailureReason().contains("目标理解超时"));
        verify(events).append(eq(7L), eq("BASELINE_DOWNGRADED"), eq("SYSTEM"), eq("ERR_NO_BASELINE_TEMPLATE"), any());
        verifyNoInteractions(execution);
    }
}
