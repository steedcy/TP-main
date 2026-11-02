package com.airport.ai.task;

import com.airport.ai.baseline.BaselineTemplate;
import com.airport.ai.baseline.BaselineTemplateService;
import com.airport.ai.event.TaskEventService;
import com.airport.ai.planning.PlanningModelService;
import com.airport.ai.risk.RiskAssessmentService;
import com.airport.ai.taskdef.TaskDefinitionService;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

import java.util.List;
import java.util.Map;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/** DEF-S3-085：人工切换基线时，解析出的目的地进入模板输入；显式场景参数优先；缺值留下记录。 */
class BaselineDowngradeBindingF008Test {
    private static final ObjectMapper JSON = new ObjectMapper();
    private static final String TEMPLATE_INPUTS = "[{\"name\":\"targetLocation\",\"type\":\"String\",\"required\":true,"
            + "\"defaultValue\":\"F2_TEST_GATE\"},{\"name\":\"repeatCount\",\"type\":\"Integer\",\"required\":true,\"defaultValue\":\"1\"}]";
    private static final String TEMPLATE_STEPS = "[{\"capabilityType\":\"CAP_NAVIGATION\",\"completionCondition\":\"routeGenerated=true\","
            + "\"paramMapping\":[{\"target\":\"targetLocation\",\"source\":\"TEMPLATE_INPUT.targetLocation\"}]}]";

    private final TaskMapper tasks = mock(TaskMapper.class);
    private final PlanVersionMapper plans = mock(PlanVersionMapper.class);
    private final ContextSnapshotService contexts = mock(ContextSnapshotService.class);
    private final PlanValidationService validation = mock(PlanValidationService.class);
    private final BaselineTemplateService templates = mock(BaselineTemplateService.class);
    private final TaskEventService events = mock(TaskEventService.class);
    private final TaskExecutionOrchestrator execution = mock(TaskExecutionOrchestrator.class);
    private final TaskPlanningOrchestrator orchestrator = new TaskPlanningOrchestrator(tasks, plans, contexts, validation,
            mock(PlanningModelService.class), mock(RiskAssessmentService.class), templates, events, execution,
            mock(TaskDefinitionService.class));

    BaselineDowngradeBindingF008Test() throws Exception {
        BaselineTemplate template = new BaselineTemplate();
        template.setId(1L);
        template.setTemplateName("SPECIAL");
        template.setInputParams(TEMPLATE_INPUTS);
        template.setSteps(TEMPLATE_STEPS);
        when(templates.matchForDowngrade("SPECIAL_PASSENGER_SERVICE")).thenReturn(Optional.of(template));
        ContextSnapshot snapshot = new ContextSnapshot();
        snapshot.setSnapshotCode("CTX-1");
        snapshot.setAgents("[]");
        when(contexts.buildSnapshot(anyLong(), anyList())).thenReturn(snapshot);
        when(contexts.parseAgents(any())).thenReturn(List.of());
        PlanValidationResult ok = new PlanValidationResult();
        when(validation.validate(anyList(), anyList(), any(), any())).thenReturn(ok);
        when(plans.countByTaskId(anyLong())).thenReturn(0L);
    }

    private Task task(String sceneParams, String goalParsingResult) {
        Task t = new Task();
        t.setId(70L);
        t.setStatus(TaskStatus.PLANNING);
        t.setTaskFamily("SPECIAL_PASSENGER_SERVICE");
        t.setSceneParams(sceneParams);
        t.setGoalParsingResult(goalParsingResult);
        when(tasks.findById(70L)).thenReturn(Optional.of(t));
        return t;
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> scene(Task t) throws Exception {
        return JSON.readValue(t.getSceneParams(), Map.class);
    }

    @Test
    void parsedDestinationIsUsedInsteadOfTheTemplateDefaultWhenSceneParamsAreEmpty() throws Exception {
        Task t = task("{}", "{\"originalGoal\":\"去F2_SERVICE_POINT\",\"destination\":\"F2_SERVICE_POINT\",\"origin\":null}");
        orchestrator.switchToBaseline(70L);
        assertEquals("F2_SERVICE_POINT", scene(t).get("targetLocation"));
        assertEquals(TaskStatus.DOWNGRADING, t.getStatus());
        verify(events).append(eq(70L), eq("BASELINE_INPUT_BOUND"), eq("SYSTEM"), isNull(), contains("targetLocation"));
        verify(events, never()).append(eq(70L), eq("BASELINE_INPUT_DEFAULTED"), any(), any(), any());
    }

    @Test
    void explicitSceneParameterWinsOverTheParsedDestination() throws Exception {
        Task t = task("{\"targetLocation\":\"GATE_B7\"}", "{\"destination\":\"F2_SERVICE_POINT\"}");
        orchestrator.switchToBaseline(70L);
        assertEquals("GATE_B7", scene(t).get("targetLocation"));
        verify(events, never()).append(eq(70L), eq("BASELINE_INPUT_BOUND"), any(), any(), any());
    }

    @Test
    void nothingToBindFallsBackToTheDefaultButRecordsIt() throws Exception {
        Task t = task("{}", "{\"destination\":null}");
        orchestrator.switchToBaseline(70L);
        assertEquals("F2_TEST_GATE", scene(t).get("targetLocation"));
        verify(events).append(eq(70L), eq("BASELINE_INPUT_DEFAULTED"), eq("SYSTEM"), eq("WARN_LOCATION_DEFAULTED"),
                contains("targetLocation"));
    }

    @Test
    void missingGoalParsingResultBehavesLikeNoParsedValue() throws Exception {
        Task t = task("{\"note\":\"keep\"}", null);
        orchestrator.switchToBaseline(70L);
        assertEquals("F2_TEST_GATE", scene(t).get("targetLocation"));
        assertEquals("keep", scene(t).get("note"), "原有场景参数保留");
    }

    @Test
    void sceneParamsRecordedForTheStepsCarryTheBoundValueIntoDeviceCommands() throws Exception {
        Task t = task("{}", "{\"destination\":\"F2_SERVICE_POINT\"}");
        orchestrator.switchToBaseline(70L);
        ArgumentCaptor<Task> saved = ArgumentCaptor.forClass(Task.class);
        verify(tasks, atLeastOnce()).update(saved.capture());
        assertTrue(saved.getAllValues().stream().anyMatch(x -> x.getSceneParams() != null
                && x.getSceneParams().contains("F2_SERVICE_POINT") && !x.getSceneParams().contains("F2_TEST_GATE")),
                "任务落库的场景参数里不应再有被默认值替换的地点");
    }

    @Test
    void goalRequiresSpecificLocationButDestinationIsNullRoutesToPendingManualWithoutDispatchingDefault() throws Exception {
        Task t = task("{}", "{\"originalGoal\":\"Guide virtual passenger to F2_SERVICE_POINT G131\",\"destination\":null,\"origin\":\"F2_TEST_GATE\"}");
        t.setTaskGoal("Guide virtual passenger to F2_SERVICE_POINT G131");
        orchestrator.switchToBaseline(70L);
        assertEquals(TaskStatus.PENDING_MANUAL, t.getStatus());
        assertFalse(scene(t).containsKey("targetLocation"), "不得将模板默认地点 F2_TEST_GATE 写入任务场景参数");
        verify(events).append(eq(70L), eq("BASELINE_INPUT_DEFAULTED"), eq("SYSTEM"), eq("ERR_LOCATION_UNRESOLVED"),
                contains("targetLocation"));
        verify(events).append(eq(70L), eq("TASK_PENDING_MANUAL"), eq("SYSTEM"), eq("ERR_PLANNING_FAILED"),
                contains("targetLocation"));
        verifyNoInteractions(execution);
    }

    @Test
    void taskActuallyNotRequiringLocationStillDowngradesWhenTemplateHasNoLocationInput() throws Exception {
        BaselineTemplate broadcastTemplate = new BaselineTemplate();
        broadcastTemplate.setId(2L);
        broadcastTemplate.setTemplateName("BROADCAST_ONLY");
        broadcastTemplate.setInputParams("[{\"name\":\"repeatCount\",\"type\":\"Integer\",\"required\":true,\"defaultValue\":\"1\"}]");
        broadcastTemplate.setSteps("[{\"capabilityType\":\"CAP_NOTIFICATION\",\"completionCondition\":\"notificationStatus=SUCCESS\","
                + "\"paramMapping\":[{\"target\":\"repeatCount\",\"source\":\"TEMPLATE_INPUT.repeatCount\"}]}]");
        when(templates.matchForDowngrade("BROADCAST_FAMILY")).thenReturn(Optional.of(broadcastTemplate));

        Task t = task("{}", "{\"originalGoal\":\"Broadcast notice\",\"destination\":null}");
        t.setTaskFamily("BROADCAST_FAMILY");
        t.setTaskGoal("Broadcast notice");
        orchestrator.switchToBaseline(70L);
        assertEquals(TaskStatus.DOWNGRADING, t.getStatus());
        assertEquals(1, scene(t).get("repeatCount"));
        verify(execution).startExecution(eq(70L), any());
    }
}
