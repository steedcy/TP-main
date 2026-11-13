package com.airport.ai.task;

import com.airport.ai.auth.OperationLogService;
import com.airport.ai.auth.User;
import com.airport.ai.device.DeviceAgent;
import com.airport.ai.device.DeviceAgentMapper;
import com.airport.ai.device.DeviceAgentMessagingService;
import com.airport.ai.event.TaskEventService;
import com.airport.ai.planning.GoalUnderstandingResponse;
import com.airport.ai.planning.GoalUnderstandingService;
import com.airport.ai.task.dto.SubmitTaskRequest;
import com.airport.ai.taskdef.TaskDefinitionService;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.*;

/** DEF-S3-130：目标理解失败必须持久化任务并进入安全降级闸门，不以 HTTP 503 结束提交。 */
class GoalUnderstandingFailureTaskServiceTest {

    @Test
    void failedUnderstandingIsRoutedToDowngradeWithoutThrowing503() {
        TaskMapper tasks = mock(TaskMapper.class);
        DeviceAgentMapper agents = mock(DeviceAgentMapper.class);
        GoalUnderstandingService model = mock(GoalUnderstandingService.class);
        TaskPlanningOrchestrator planning = mock(TaskPlanningOrchestrator.class);
        TaskEventService events = mock(TaskEventService.class);
        OperationLogService logs = mock(OperationLogService.class);
        TaskCodeGenerator codes = mock(TaskCodeGenerator.class);
        TaskDefinitionService definitions = mock(TaskDefinitionService.class);
        Task task = new Task();
        task.setId(130L);
        task.setTaskCode("TASK-NF015-130");
        task.setTaskGoal("synthetic navigation to F2_TEST_GATE");
        task.setCreatedBy("nf015_operator");
        task.setStatus(TaskStatus.PLANNING);

        DeviceAgent online = new DeviceAgent();
        online.setAgentStatus("ENABLED");
        online.setOnlineStatus("ONLINE");
        when(agents.findByAgentStatusAndOnlineStatus("ENABLED", "ONLINE")).thenReturn(List.of(online));
        when(codes.next()).thenReturn(task.getTaskCode());
        doAnswer(invocation -> {
            Task inserted = invocation.getArgument(0);
            inserted.setId(task.getId());
            return 1;
        }).when(tasks).insert(any(Task.class));
        when(tasks.findById(task.getId())).thenReturn(Optional.of(task));

        GoalUnderstandingResponse failed = new GoalUnderstandingResponse();
        failed.setResultCode("1003");
        failed.setErrorMessage("synthetic model unavailable");
        when(model.understand(any())).thenReturn(failed);

        TaskService service = new TaskService(tasks, mock(PlanVersionMapper.class),
                mock(ContextSnapshotMapper.class), agents, model, codes, events, logs,
                planning, mock(TaskStepAssignmentMapper.class), definitions,
                mock(DeviceAgentMessagingService.class));

        SubmitTaskRequest request = new SubmitTaskRequest();
        request.setTaskGoal(task.getTaskGoal());
        User operator = new User();
        operator.setId(15L);
        operator.setUsername("nf015_operator");
        operator.setRole("OPERATOR");

        Task result = assertDoesNotThrow(() -> service.submit(request, operator));

        // The submit call must complete normally and return the persisted task snapshot.
        org.junit.jupiter.api.Assertions.assertEquals(task.getId(), result.getId());
        verify(planning).downgradeAfterUnderstandingFailure(eq(task.getId()), contains("synthetic model unavailable"));
        verify(events).append(eq(task.getId()), eq("GOAL_UNDERSTANDING_FAILED"), eq("SYSTEM"),
                eq("ERR_GOAL_UNDERSTANDING_TIMEOUT"), contains("synthetic model unavailable"));
        verify(logs).record(isNull(), eq("nf015_operator"), eq("OPERATOR"),
                eq("GOAL_UNDERSTANDING_FAILURE"), eq(task.getTaskCode()), eq("FAILED"), isNull(), any());
    }
}
