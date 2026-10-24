package com.airport.ai.task;

import com.airport.ai.auth.*;
import com.airport.ai.device.*;
import com.airport.ai.event.TaskEventService;
import com.airport.ai.planning.GoalUnderstandingService;
import com.airport.ai.taskdef.TaskDefinitionService;
import org.junit.jupiter.api.Test;
import java.util.Optional;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class ManualActionSafetyTest {
    @Test void choosingBaselineSkipsAutonomousModelAndAuditsFailedFallback() {
        TaskMapper tasks = mock(TaskMapper.class);
        TaskPlanningOrchestrator planning = mock(TaskPlanningOrchestrator.class);
        TaskEventService events = mock(TaskEventService.class);
        OperationLogService audit = mock(OperationLogService.class);
        Task task = new Task();
        task.setId(7L);
        task.setTaskCode("TASK-7");
        task.setStatus(TaskStatus.PENDING_MANUAL);
        when(tasks.findById(7L)).thenReturn(Optional.of(task));
        doAnswer(invocation -> {
            task.setStatus(TaskStatus.PENDING_MANUAL);
            task.setFailureReason("baseline validation failed");
            return null;
        }).when(planning).switchToBaseline(7L);
        TaskService service = new TaskService(tasks, mock(PlanVersionMapper.class),
                mock(ContextSnapshotMapper.class), mock(DeviceAgentMapper.class),
                mock(GoalUnderstandingService.class), mock(TaskCodeGenerator.class), events, audit,
                planning, mock(TaskStepAssignmentMapper.class), mock(TaskDefinitionService.class),
                mock(DeviceAgentMessagingService.class));
        User operator = new User();
        operator.setId(4L);
        operator.setUsername("operator");
        operator.setRole("OPERATOR");

        Task result = service.manualAction(7L, "SWITCH_TO_BASELINE", operator);

        assertEquals(TaskStatus.PENDING_MANUAL, result.getStatus());
        verify(planning).switchToBaseline(7L);
        verify(planning, never()).advance(anyLong());
        verify(events).append(eq(7L), eq("TASK_MANUAL_ACTION_FAILED"), eq("SYSTEM"),
                eq("ERR_MANUAL_ACTION_FAILED"), eq("baseline validation failed"));
        verify(audit).record(4L, "operator", "OPERATOR", "TASK_MANUAL_ACTION",
                "TASK-7 -> SWITCH_TO_BASELINE", "FAILED", null);
    }
}
