package com.airport.ai.task;

import com.airport.ai.auth.OperationLogService;
import com.airport.ai.auth.User;
import com.airport.ai.common.BusinessException;
import com.airport.ai.device.DeviceAgentMapper;
import com.airport.ai.device.DeviceAgentMessagingService;
import com.airport.ai.event.TaskEventService;
import com.airport.ai.planning.GoalUnderstandingRequest;
import com.airport.ai.planning.GoalUnderstandingResponse;
import com.airport.ai.planning.GoalUnderstandingService;
import com.airport.ai.task.dto.ClarifyTaskRequest;
import com.airport.ai.taskdef.TaskDefinitionService;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

class GoalClarificationRoundsTest {
    @Test void keepsAllAnswersAndStopsAfterThreeIncompleteRounds() {
        Task task = new Task();
        task.setId(8L);
        task.setStatus(TaskStatus.PLANNING);
        task.setTaskGoal("虚构协助目标");
        task.setTaskFamily("SPECIAL_PASSENGER_SERVICE");
        task.setSceneParams("{}");
        task.setMissingInfoQuestions("[\"请提供地点\"]");
        TaskMapper tasks = mock(TaskMapper.class);
        when(tasks.findById(8L)).thenReturn(Optional.of(task));
        GoalUnderstandingService model = mock(GoalUnderstandingService.class);
        GoalUnderstandingResponse incomplete = new GoalUnderstandingResponse();
        incomplete.setResultCode("0");
        incomplete.setInfoComplete(false);
        incomplete.setMissingInfoQuestions(List.of("请提供地点"));
        incomplete.setInferredTaskFamily("SPECIAL_PASSENGER_SERVICE");
        when(model.understand(any())).thenReturn(incomplete);
        TaskPlanningOrchestrator planning = mock(TaskPlanningOrchestrator.class);
        TaskService service = new TaskService(tasks, mock(PlanVersionMapper.class),
                mock(ContextSnapshotMapper.class), mock(DeviceAgentMapper.class), model,
                mock(TaskCodeGenerator.class), mock(TaskEventService.class), mock(OperationLogService.class),
                planning, mock(TaskStepAssignmentMapper.class), mock(TaskDefinitionService.class),
                mock(DeviceAgentMessagingService.class));
        User operator = new User();
        operator.setUsername("operator");

        ClarifyTaskRequest missing = new ClarifyTaskRequest();
        missing.setAnswers(Map.of("wrong question", "answer"));
        assertThrows(BusinessException.class, () -> service.clarify(8L, missing, operator));
        verifyNoInteractions(model);

        for (int round = 1; round <= 3; round++) {
            ClarifyTaskRequest answer = new ClarifyTaskRequest();
            answer.setAnswers(Map.of("请提供地点", "虚构位置" + round));
            service.clarify(8L, answer, operator);
            assertEquals(round == 3 ? TaskStatus.PENDING_MANUAL : TaskStatus.PLANNING, task.getStatus());
        }
        var request = org.mockito.ArgumentCaptor.forClass(GoalUnderstandingRequest.class);
        verify(model, times(3)).understand(request.capture());
        assertEquals(3, request.getValue().getClarificationAnswers().size());
        assertTrue(task.getSceneParams().contains("虚构位置1"));
        assertTrue(task.getSceneParams().contains("虚构位置3"));
        verifyNoInteractions(planning);
    }
}
