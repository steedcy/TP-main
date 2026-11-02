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

import java.util.List;
import java.util.Map;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/** DEF-S3-003/004/005 的端到端行为：模型说“信息不完整”时，系统按任务族核对，以核对结果为准。 */
class RequiredInfoOverrideTest {
    private final TaskMapper tasks = mock(TaskMapper.class);
    private final GoalUnderstandingService model = mock(GoalUnderstandingService.class);
    private final TaskEventService events = mock(TaskEventService.class);
    private final TaskPlanningOrchestrator planning = mock(TaskPlanningOrchestrator.class);
    private final TaskService service = new TaskService(tasks, mock(PlanVersionMapper.class), mock(ContextSnapshotMapper.class),
            mock(DeviceAgentMapper.class), model, mock(TaskCodeGenerator.class), events, mock(OperationLogService.class),
            planning, mock(TaskStepAssignmentMapper.class), mock(TaskDefinitionService.class), mock(DeviceAgentMessagingService.class));
    private final User operator = new User();

    RequiredInfoOverrideTest() { operator.setUsername("op"); }

    private Task task(String family, String sceneParams, String pending) {
        Task t = new Task();
        t.setId(20L);
        t.setStatus(TaskStatus.PLANNING);
        t.setTaskGoal("虚构目标");
        t.setTaskFamily(family);
        t.setSceneParams(sceneParams);
        t.setMissingInfoQuestions(pending);
        when(tasks.findById(20L)).thenReturn(Optional.of(t));
        return t;
    }

    private void modelSays(boolean complete, String origin, String destination, String... questions) {
        GoalUnderstandingResponse r = new GoalUnderstandingResponse();
        r.setResultCode("0");
        r.setInfoComplete(complete);
        r.setOrigin(origin);
        r.setDestination(destination);
        r.setMissingInfoQuestions(List.of(questions));
        when(model.understand(any())).thenReturn(r);
    }

    private ClarifyTaskRequest answers(Map<String, String> a) {
        ClarifyTaskRequest r = new ClarifyTaskRequest();
        r.setAnswers(a);
        return r;
    }

    @Test
    void oversizeBaggageWithSubmittedLocationProceedsEvenIfTheModelKeepsAskingForIt() {
        // 台账现象：任务带了 baggageLocation，模型三轮误报缺失
        Task t = task("OVERSIZE_BAGGAGE_HANDLING", "{\"baggageLocation\":\"F2_BAGGAGE_POINT\"}", "[\"缺少行李位置\"]");
        modelSays(false, null, null, "缺少行李位置");
        service.clarify(20L, answers(Map.of("缺少行李位置", "F2_BAGGAGE_POINT")), operator);
        assertEquals(TaskStatus.PLANNING, t.getStatus(), "不应转人工");
        verify(planning).advance(20L);
        assertNull(t.getMissingInfoQuestions());
        verify(events).append(eq(20L), eq("GOAL_CLARIFIED"), eq("SYSTEM"), eq("INFO_CHECK_OVERRIDE"), contains("忽略模型的追问"));
    }

    @Test
    void specialPassengerWithTypeOriginAndDestinationProceedsWithoutIdentityQuestions() {
        Task t = task("SPECIAL_PASSENGER_SERVICE", "{\"assistanceType\":\"WHEELCHAIR\"}", "[\"请补充服务编号\"]");
        modelSays(false, "F2_GATE_A", "F2_SERVICE_POINT", "请补充服务编号", "请提供备用联系人");
        service.clarify(20L, answers(Map.of("请补充服务编号", "已补充")), operator);
        verify(planning).advance(20L);
        assertNull(t.getMissingInfoQuestions());
        assertNotEquals(TaskStatus.PENDING_MANUAL, t.getStatus());
    }

    @Test
    void specialPassengerStillMissingDestinationGetsOnlyTheSystemQuestionNotTheModelOnes() {
        Task t = task("SPECIAL_PASSENGER_SERVICE", "{\"assistanceType\":\"WHEELCHAIR\"}", "[\"x\"]");
        modelSays(false, "F2_GATE_A", null, "请提供旅客姓名和证件号", "请指定机器人");
        service.clarify(20L, answers(Map.of("x", "y")), operator);
        verify(planning, never()).advance(anyLong());
        assertEquals("[\"请补充服务目的地\"]", t.getMissingInfoQuestions());
        assertFalse(t.getMissingInfoQuestions().contains("证件"));
        assertFalse(t.getMissingInfoQuestions().contains("机器人"));
    }

    @Test
    void flightChangeWithItsFactsProceedsAndNeverAsksForRobotIdOrRoute() {
        Task t = task("FLIGHT_CHANGE_RESPONSE",
                "{\"flightNumber\":\"CA1234\",\"changeType\":\"GATE_CHANGE\",\"changeDescription\":\"登机口变更\"}", "[\"请提供机器人ID\"]");
        modelSays(false, null, null, "请提供机器人ID", "请提供路线编码");
        service.clarify(20L, answers(Map.of("请提供机器人ID", "R1")), operator);
        verify(planning).advance(20L);
        assertNull(t.getMissingInfoQuestions());
    }

    @Test
    void whenTheModelSaysCompleteButRequiredInfoIsMissingTheSystemStillAsks() {
        Task t = task("OVERSIZE_BAGGAGE_HANDLING", "{}", "[\"x\"]");
        modelSays(true, null, null);
        service.clarify(20L, answers(Map.of("x", "y")), operator);
        verify(planning, never()).advance(anyLong());
        assertEquals("[\"请补充行李当前所在位置\"]", t.getMissingInfoQuestions());
        verify(events).append(eq(20L), eq("GOAL_CLARIFIED"), eq("SYSTEM"), eq("INFO_CHECK_OVERRIDE"), contains("仍缺"));
    }

    @Test
    void answeringTheSystemQuestionCompletesTheTaskInsteadOfLoopingThroughThreeRounds() {
        Task t = task("OVERSIZE_BAGGAGE_HANDLING", "{}", "[\"请补充行李当前所在位置\"]");
        modelSays(false, null, null, "模型换了个说法的追问");
        service.clarify(20L, answers(Map.of("请补充行李当前所在位置", "F2_BAGGAGE_POINT")), operator);
        verify(planning).advance(20L);
        assertEquals(TaskStatus.PLANNING, t.getStatus());
    }

    @Test
    void agreementBetweenModelAndSystemDoesNotWriteAnOverrideEvent() {
        task("OVERSIZE_BAGGAGE_HANDLING", "{\"baggageLocation\":\"F2_BAGGAGE_POINT\"}", "[\"x\"]");
        modelSays(true, null, null);
        service.clarify(20L, answers(Map.of("x", "y")), operator);
        verify(events, never()).append(eq(20L), eq("GOAL_CLARIFIED"), eq("SYSTEM"), eq("INFO_CHECK_OVERRIDE"), anyString());
        verify(planning).advance(20L);
    }
}
