package com.airport.ai.task;

import com.airport.ai.auth.OperationLogService;
import com.airport.ai.auth.User;
import com.airport.ai.device.DeviceAgentMapper;
import com.airport.ai.device.DeviceAgentMessagingService;
import com.airport.ai.event.TaskEventService;
import com.airport.ai.planning.GoalUnderstandingResponse;
import com.airport.ai.planning.GoalUnderstandingRequest;
import com.airport.ai.planning.GoalUnderstandingService;
import com.airport.ai.task.dto.ClarifyTaskRequest;
import com.airport.ai.taskdef.TaskDefinitionService;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/** F025.R01/R02：服务端必要信息判定覆盖模型的错误完整度和错误追问。 */
class RequiredInfoF025OverrideTest {
    @Test
    void completeBusinessFieldsProceedEvenWhenModelAsksForIdentity() {
        Task task = task("SPECIAL_PASSENGER_SERVICE",
                "{\"assistanceType\":\"WHEELCHAIR\",\"origin\":\"F2_GATE_A\",\"destination\":\"F2_SERVICE_POINT\"}",
                "[\"旧问题\"]");
        TaskMapper tasks = mock(TaskMapper.class);
        when(tasks.findById(20L)).thenReturn(Optional.of(task));
        GoalUnderstandingService model = mock(GoalUnderstandingService.class);
        when(model.understand(any())).thenReturn(response(false, "F2_GATE_A", "F2_SERVICE_POINT",
                "请补充旅客姓名和证件号", "请指定机器人"));
        TaskPlanningOrchestrator planning = mock(TaskPlanningOrchestrator.class);
        TaskEventService events = mock(TaskEventService.class);
        TaskService service = service(tasks, model, events, planning);

        service.clarify(20L, answers(Map.of("旧问题",
                "F2_GATE_A; passengerName=FICTIONAL_F025_CANARY")), operator());

        verify(planning).advance(20L);
        assertNull(task.getMissingInfoQuestions());
        verify(events).append(eq(20L), eq("GOAL_CLARIFIED"), eq("SYSTEM"),
                eq("INFO_CHECK_OVERRIDE"), contains("忽略模型的追问"));
        assertFalse(task.getSceneParams().contains("FICTIONAL_F025_CANARY"));
        var request = org.mockito.ArgumentCaptor.forClass(GoalUnderstandingRequest.class);
        verify(model).understand(request.capture());
        assertFalse(request.getValue().getClarificationAnswers().toString().contains("FICTIONAL_F025_CANARY"));
        verify(events).append(eq(20L), eq("GOAL_CLARIFIED"), eq("OPERATOR"), isNull(),
                argThat(detail -> !detail.contains("FICTIONAL_F025_CANARY")));
    }

    @Test
    void missingDestinationStopsPlanningAndUsesOnlySystemQuestion() {
        Task task = task("SPECIAL_PASSENGER_SERVICE", "{\"assistanceType\":\"WHEELCHAIR\"}", "[\"旧问题\"]");
        TaskMapper tasks = mock(TaskMapper.class);
        when(tasks.findById(20L)).thenReturn(Optional.of(task));
        GoalUnderstandingService model = mock(GoalUnderstandingService.class);
        when(model.understand(any())).thenReturn(response(false, "F2_GATE_A", null,
                "请补充旅客姓名和证件号", "请指定机器人"));
        TaskPlanningOrchestrator planning = mock(TaskPlanningOrchestrator.class);
        TaskService service = service(tasks, model, mock(TaskEventService.class), planning);

        service.clarify(20L, answers(Map.of("旧问题", "已知")), operator());

        verify(planning, never()).advance(anyLong());
        assertEquals("[\"请补充服务目的地\"]", task.getMissingInfoQuestions());
    }

    @Test
    void identityTextInAnAnswerIsRedactedBeforePersistence() {
        Map<String, String> cleaned = SceneParamsPrivacyGuard.sanitizeFreeTextAnswers(
                Map.of("请补充服务起点", "F2_GATE_A; passengerName=FICTIONAL_CANARY"));

        assertFalse(cleaned.get("请补充服务起点").contains("FICTIONAL_CANARY"));
        assertTrue(cleaned.get("请补充服务起点").contains("PROTECTED_IDENTITY"));
    }

    @Test
    void staleIdentityQuestionIsRejectedBeforeItsAnswerIsPersistedOrSent() {
        Task task = task("SPECIAL_PASSENGER_SERVICE", "{}", "[\"请补充旅客姓名和证件号\"]");
        TaskMapper tasks = mock(TaskMapper.class);
        when(tasks.findById(20L)).thenReturn(Optional.of(task));
        GoalUnderstandingService model = mock(GoalUnderstandingService.class);
        TaskEventService events = mock(TaskEventService.class);
        TaskService service = service(tasks, model, events, mock(TaskPlanningOrchestrator.class));

        assertThrows(com.airport.ai.common.BusinessException.class,
                () -> service.clarify(20L, answers(Map.of("请补充旅客姓名和证件号", "FICTIONAL_F025_CANARY")), operator()));

        verifyNoInteractions(model, events);
        verify(tasks, never()).update(any());
        assertFalse(task.getSceneParams().contains("FICTIONAL_F025_CANARY"));
    }

    @Test
    void priorClarificationHistoryIsSanitizedBeforePersistenceAndModelCall() {
        String prior = "{\"assistanceType\":\"WHEELCHAIR\",\"origin\":\"F2_GATE_A\","
                + "\"destination\":\"F2_SERVICE_POINT\",\"clarificationAnswers\":[{"
                + "\"questions\":[\"请补充服务起点\",\"请提供旅客姓名\"],"
                + "\"answers\":{\"请补充服务起点\":\"passengerName=OLD_F025_CANARY\","
                + "\"请提供旅客姓名\":\"OLD_F025_CANARY\"}}]}";
        Task task = task("SPECIAL_PASSENGER_SERVICE", prior, "[\"旧问题\"]");
        TaskMapper tasks = mock(TaskMapper.class);
        when(tasks.findById(20L)).thenReturn(Optional.of(task));
        GoalUnderstandingService model = mock(GoalUnderstandingService.class);
        when(model.understand(any())).thenReturn(response(true, "F2_GATE_A", "F2_SERVICE_POINT"));
        TaskService service = service(tasks, model, mock(TaskEventService.class),
                mock(TaskPlanningOrchestrator.class));

        service.clarify(20L, answers(Map.of("旧问题", "安全补充")), operator());

        var request = org.mockito.ArgumentCaptor.forClass(GoalUnderstandingRequest.class);
        verify(model).understand(request.capture());
        assertFalse(request.getValue().getClarificationAnswers().toString().contains("OLD_F025_CANARY"));
        assertFalse(task.getSceneParams().contains("OLD_F025_CANARY"));
        assertFalse(request.getValue().getClarificationAnswers().toString().contains("请提供旅客姓名"));
    }

    private static Task task(String family, String scene, String questions) {
        Task task = new Task();
        task.setId(20L);
        task.setStatus(TaskStatus.PLANNING);
        task.setTaskGoal("虚构特殊旅客目标");
        task.setTaskFamily(family);
        task.setSceneParams(scene);
        task.setMissingInfoQuestions(questions);
        return task;
    }

    private static GoalUnderstandingResponse response(boolean complete, String origin,
                                                       String destination, String... questions) {
        GoalUnderstandingResponse response = new GoalUnderstandingResponse();
        response.setResultCode("0");
        response.setInfoComplete(complete);
        response.setOrigin(origin);
        response.setDestination(destination);
        response.setMissingInfoQuestions(List.of(questions));
        return response;
    }

    private static ClarifyTaskRequest answers(Map<String, String> answers) {
        ClarifyTaskRequest request = new ClarifyTaskRequest();
        request.setAnswers(answers);
        return request;
    }

    private static User operator() {
        User user = new User();
        user.setUsername("operator");
        return user;
    }

    private static TaskService service(TaskMapper tasks, GoalUnderstandingService model,
                                       TaskEventService events, TaskPlanningOrchestrator planning) {
        return new TaskService(tasks, mock(PlanVersionMapper.class), mock(ContextSnapshotMapper.class),
                mock(DeviceAgentMapper.class), model, mock(TaskCodeGenerator.class), events,
                mock(OperationLogService.class), planning, mock(TaskStepAssignmentMapper.class),
                mock(TaskDefinitionService.class), mock(DeviceAgentMessagingService.class));
    }
}
