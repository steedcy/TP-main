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
        when(agents.findByIdForUpdate(3L)).thenReturn(Optional.of(agent));
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

    @Test
    void terminatingPendingTaskPreservesOtherExecutingTaskOccupation_DEF_S3_103() {
        TaskMapper tasks = mock(TaskMapper.class);
        DeviceAgentMapper agents = mock(DeviceAgentMapper.class);
        TaskStepAssignmentMapper assignments = mock(TaskStepAssignmentMapper.class);
        DeviceAgentMessagingService messaging = mock(DeviceAgentMessagingService.class);

        // 任务 A: 处于待分配阶段，预选了代理 AGT-5
        Task taskA = new Task();
        taskA.setId(101L);
        taskA.setTaskCode("TASK-101");
        taskA.setStatus(TaskStatus.PENDING_ASSIGNMENT);
        taskA.setCurrentPlanVersionId(201L);
        when(tasks.findById(101L)).thenReturn(Optional.of(taskA));

        TaskStepAssignment assignA = new TaskStepAssignment();
        assignA.setId(301L);
        assignA.setTaskId(101L);
        assignA.setPlanVersionId(201L);
        assignA.setStepSeq(1);
        assignA.setStepStatus("PENDING_ASSIGNMENT");
        assignA.setDeviceAgentId(5L);
        when(assignments.findByPlanVersionIdOrderByStepSeqAsc(201L)).thenReturn(List.of(assignA));

        // 代理 AGT-5 当前已经被任务 B (102L) 占有并正在执行
        DeviceAgent agent = new DeviceAgent();
        agent.setId(5L);
        agent.setAgentCode("AGT-5");
        agent.setWorkStatus("BUSY");
        agent.setCurrentTaskId(102L);
        agent.setCurrentStepSeq(1);

        when(agents.findByCurrentTaskId(101L)).thenReturn(List.of());
        when(agents.findById(5L)).thenReturn(Optional.of(agent));
        when(agents.findByIdForUpdate(5L)).thenReturn(Optional.of(agent));

        TaskService service = new TaskService(tasks, mock(PlanVersionMapper.class),
                mock(ContextSnapshotMapper.class), agents, mock(GoalUnderstandingService.class),
                mock(TaskCodeGenerator.class), mock(TaskEventService.class), mock(OperationLogService.class),
                mock(TaskPlanningOrchestrator.class), assignments,
                mock(TaskDefinitionService.class), messaging);

        User operator = new User();
        operator.setUsername("operator");
        operator.setRole("OPERATOR");

        // 仅终止任务 A
        Task result = service.terminate(101L, "Cancel only pending task, preserve executing task", operator);

        // 验证任务 A 终止，步骤被冻结
        assertEquals(TaskStatus.MANUAL_TERMINATED, result.getStatus());
        assertEquals("FROZEN", assignA.getStepStatus());
        verify(assignments).update(assignA);

        // 验证 DEF-S3-103: 严禁向该代理发送任务 A 的取消指令
        verify(messaging, never()).cancelTask(eq("AGT-5"), anyString(), anyLong(), any());

        // 验证 DEF-S3-103: 代理保持归属于任务 B 的 BUSY 占用，严禁被清为 IDLE 或清空 currentTaskId
        assertEquals("BUSY", agent.getWorkStatus());
        assertEquals(102L, agent.getCurrentTaskId());
        assertEquals(1, agent.getCurrentStepSeq());
        verify(agents, never()).update(agent);
    }
}
