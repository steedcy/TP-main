package com.airport.ai.task;

import com.airport.ai.auth.OperationLogService;
import com.airport.ai.auth.User;
import com.airport.ai.device.DeviceAgent;
import com.airport.ai.device.DeviceAgentMapper;
import com.airport.ai.device.DeviceAgentMessagingService;
import com.airport.ai.event.TaskEventService;
import com.airport.ai.planning.GoalUnderstandingService;
import com.airport.ai.taskdef.TaskDefinitionService;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/** SRS_F007.R02：任务取消是独立逻辑消息，不得复用该步骤承接/执行的指令编号。 */
class TerminateCancelIdF007Test {

    @Test
    void cancelUsesItsOwnCommandIdDistinctFromAcceptAndExecuteIds() {
        TaskMapper tasks = mock(TaskMapper.class);
        TaskStepAssignmentMapper assignments = mock(TaskStepAssignmentMapper.class);
        DeviceAgentMapper agents = mock(DeviceAgentMapper.class);
        DeviceAgentMessagingService messaging = mock(DeviceAgentMessagingService.class);
        Task task = new Task();
        task.setId(7L);
        task.setTaskCode("TASK-7");
        task.setStatus(TaskStatus.EXECUTING);
        task.setCurrentPlanVersionId(70L);
        when(tasks.findById(7L)).thenReturn(Optional.of(task));
        TaskStepAssignment a = new TaskStepAssignment();
        a.setTaskId(7L);
        a.setPlanVersionId(70L);
        a.setStepSeq(1);
        a.setStepStatus("EXECUTING");
        a.setDeviceAgentId(9L);
        a.setCommandId("CMD-ACCEPT");
        a.setExecuteCommandId("CMD-EXECUTE");
        when(assignments.findByPlanVersionIdOrderByStepSeqAsc(70L)).thenReturn(List.of(a));
        DeviceAgent agent = new DeviceAgent();
        agent.setId(9L);
        agent.setAgentCode("AGT-9");
        agent.setCurrentTaskId(7L);
        when(agents.findByCurrentTaskId(7L)).thenReturn(List.of(agent));
        TaskService service = new TaskService(tasks, mock(PlanVersionMapper.class),
                mock(ContextSnapshotMapper.class), agents, mock(GoalUnderstandingService.class),
                mock(TaskCodeGenerator.class), mock(TaskEventService.class), mock(OperationLogService.class),
                mock(TaskPlanningOrchestrator.class), assignments, mock(TaskDefinitionService.class), messaging);
        User operator = new User();
        operator.setId(4L);
        operator.setUsername("op");
        operator.setRole("OPERATOR");

        service.terminate(7L, "人工终止", operator);

        ArgumentCaptor<String> cancelId = ArgumentCaptor.forClass(String.class);
        verify(messaging).cancelTask(eq("AGT-9"), cancelId.capture(), eq(7L), eq(1));
        assertNotEquals("CMD-ACCEPT", cancelId.getValue());
        assertNotEquals("CMD-EXECUTE", cancelId.getValue());
        assertTrue(cancelId.getValue().startsWith("CMD-"));
    }
}
