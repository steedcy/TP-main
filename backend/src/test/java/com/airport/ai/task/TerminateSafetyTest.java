package com.airport.ai.task;

import com.airport.ai.auth.*;
import com.airport.ai.device.*;
import com.airport.ai.event.TaskEventService;
import com.airport.ai.planning.GoalUnderstandingService;
import com.airport.ai.taskdef.TaskDefinitionService;
import org.junit.jupiter.api.Test;
import java.util.List;
import java.util.Optional;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class TerminateSafetyTest {
    @Test void queuedCancelKeepsAgentOccupiedUntilDeviceReportsIdle() {
        TaskMapper tasks = mock(TaskMapper.class);
        DeviceAgentMapper agents = mock(DeviceAgentMapper.class);
        DeviceAgentMessagingService messaging = mock(DeviceAgentMessagingService.class);
        Task task = new Task();
        task.setId(7L);
        task.setTaskCode("TASK-7");
        task.setStatus(TaskStatus.EXECUTING);
        when(tasks.findById(7L)).thenReturn(Optional.of(task));
        DeviceAgent agent = new DeviceAgent();
        agent.setId(3L);
        agent.setAgentCode("AGT-3");
        agent.setWorkStatus("BUSY");
        agent.setCurrentTaskId(7L);
        when(agents.findByCurrentTaskId(7L)).thenReturn(List.of(agent));
        TaskService service = new TaskService(tasks, mock(PlanVersionMapper.class),
                mock(ContextSnapshotMapper.class), agents, mock(GoalUnderstandingService.class),
                mock(TaskCodeGenerator.class), mock(TaskEventService.class), mock(OperationLogService.class),
                mock(TaskPlanningOrchestrator.class), mock(TaskStepAssignmentMapper.class),
                mock(TaskDefinitionService.class), messaging);
        User operator = new User();
        operator.setUsername("operator");
        operator.setRole("OPERATOR");

        Task result = service.terminate(7L, "stop", operator);

        assertEquals(TaskStatus.MANUAL_TERMINATED, result.getStatus());
        assertEquals("BUSY", agent.getWorkStatus());
        assertEquals(7L, agent.getCurrentTaskId());
        verify(messaging).cancelTask(eq("AGT-3"), anyString(), eq(7L), isNull());
        verify(agents).update(agent);
    }
}
