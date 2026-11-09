package com.airport.ai.task;

import com.airport.ai.auth.OperationLogService;
import com.airport.ai.auth.User;
import com.airport.ai.device.DeviceAgentMapper;
import com.airport.ai.device.DeviceAgentMessagingService;
import com.airport.ai.event.TaskEventService;
import com.airport.ai.planning.GoalUnderstandingResponse;
import com.airport.ai.planning.GoalUnderstandingService;
import com.airport.ai.task.dto.ClarifyTaskRequest;
import com.airport.ai.taskdef.TaskDefinitionService;
import org.junit.jupiter.api.Test;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class FlightChangeRequiredInfoOverrideTest {
    private final TaskMapper tasks = mock(TaskMapper.class);
    private final GoalUnderstandingService model = mock(GoalUnderstandingService.class);
    private final TaskEventService events = mock(TaskEventService.class);
    private final TaskPlanningOrchestrator planning = mock(TaskPlanningOrchestrator.class);
    private final TaskService service = new TaskService(tasks, mock(PlanVersionMapper.class), mock(ContextSnapshotMapper.class),
            mock(DeviceAgentMapper.class), model, mock(TaskCodeGenerator.class), events, mock(OperationLogService.class),
            planning, mock(TaskStepAssignmentMapper.class), mock(TaskDefinitionService.class), mock(DeviceAgentMessagingService.class));
    private final User operator = new User();

    FlightChangeRequiredInfoOverrideTest() { operator.setUsername("synthetic-operator"); }

    private Task task(String sceneParams) {
        Task task = new Task();
        task.setId(260L);
        task.setStatus(TaskStatus.PLANNING);
        task.setTaskFamily("FLIGHT_CHANGE_RESPONSE");
        task.setTaskGoal("虚构航班变更目标");
        task.setSceneParams(sceneParams);
        task.setMissingInfoQuestions("[\"operator note\"]");
        when(tasks.findById(260L)).thenReturn(Optional.of(task));
        return task;
    }

    private void modelSays(boolean complete, String... questions) {
        GoalUnderstandingResponse response = new GoalUnderstandingResponse();
        response.setResultCode("0");
        response.setInfoComplete(complete);
        response.setMissingInfoQuestions(List.of(questions));
        when(model.understand(any())).thenReturn(response);
    }

    private void clarify() {
        ClarifyTaskRequest request = new ClarifyTaskRequest();
        request.setAnswers(Map.of("operator note", "synthetic answer"));
        service.clarify(260L, request, operator);
    }

    @Test
    void completeFlightFactsProceedWhenTheModelStillAsksForRobotAndRoute() {
        Task task = task("{\"flightNumber\":\"CA1234\",\"changeType\":\"GATE_CHANGE\","
                + "\"originalTime\":\"2026-11-09T12:00:00\",\"newGate\":\"F2_TEST_GATE\","
                + "\"changeDescription\":\"虚构登机口变更\"}");
        modelSays(false, "请补充机器人ID", "请补充路线编码");

        clarify();

        verify(planning).advance(260L);
        assertNull(task.getMissingInfoQuestions());
        verify(events).append(eq(260L), eq("GOAL_CLARIFIED"), eq("SYSTEM"), eq("INFO_CHECK_OVERRIDE"),
                contains("忽略模型追问"));
    }

    @Test
    void missingConditionalFlightTimeOverridesModelCompletionAndOnlyAsksForThatTime() {
        Task task = task("{\"flightNumber\":\"CA1234\",\"changeType\":\"DELAY\","
                + "\"originalTime\":\"2026-11-09T12:00:00\",\"changeDescription\":\"虚构延误\"}");
        modelSays(true, "please choose a robot");

        clarify();

        verify(planning, never()).advance(anyLong());
        assertEquals("[\"请补充变更后的航班时间\"]", task.getMissingInfoQuestions());
        assertFalse(task.getMissingInfoQuestions().contains("机器人"));
    }
}
