package com.airport.ai.task;

import com.airport.ai.baseline.BaselineTemplate;
import com.airport.ai.baseline.BaselineTemplateService;
import com.airport.ai.event.TaskEventService;
import com.airport.ai.planning.PlanningModelService;
import com.airport.ai.planning.PlanningResponse;
import com.airport.ai.risk.RiskAssessmentResult;
import com.airport.ai.risk.RiskAssessmentService;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.atomic.AtomicLong;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class ReplanningHighRiskDowngradeTest {
    private final TaskMapper tasks = mock(TaskMapper.class);
    private final PlanVersionMapper plans = mock(PlanVersionMapper.class);
    private final TaskStepAssignmentMapper assignments = mock(TaskStepAssignmentMapper.class);
    private final ContextSnapshotService context = mock(ContextSnapshotService.class);
    private final PlanValidationService validation = mock(PlanValidationService.class);
    private final PlanningModelService model = mock(PlanningModelService.class);
    private final RiskAssessmentService risk = mock(RiskAssessmentService.class);
    private final TaskExecutionOrchestrator execution = mock(TaskExecutionOrchestrator.class);
    private final TaskEventService events = mock(TaskEventService.class);
    private final BaselineTemplateService baselines = mock(BaselineTemplateService.class);

    private Task task;
    private BaselineTemplate template;
    private ReplanningService service;

    private void arrange(String baselineFirstCapability) {
        task = new Task();
        task.setId(1L);
        task.setCurrentPlanVersionId(2L);
        task.setTaskFamily("TEST_FAMILY");
        task.setTaskGoal("原始目标");
        task.setSceneParams("{}");
        when(tasks.findById(1L)).thenReturn(Optional.of(task));
        when(tasks.claimReplan(1L, "DEVICE_OFFLINE")).thenReturn(1);

        PlanVersion original = new PlanVersion();
        original.setPlanSteps("[{\"stepSeq\":1,\"capabilityType\":\"CAP_DONE\",\"completionCondition\":\"done=true\"},"
                + "{\"stepSeq\":2,\"capabilityType\":\"CAP_NEW\",\"completionCondition\":\"new=true\"}]");
        when(plans.findById(2L)).thenReturn(Optional.of(original));
        TaskStepAssignment completed = new TaskStepAssignment();
        completed.setStepSeq(1);
        completed.setStepStatus("COMPLETED");
        completed.setExecutionResult("SUCCESS");
        completed.setOutputParams("{\"done\":true}");
        when(assignments.findByPlanVersionIdOrderByStepSeqAsc(2L)).thenReturn(List.of(completed));

        ContextSnapshot snapshot = new ContextSnapshot();
        snapshot.setSnapshotCode("CTX-TEST");
        snapshot.setAgents("[]");
        when(context.buildSnapshot(eq(1L), anyList())).thenReturn(snapshot);
        when(context.parseAgents("[]")).thenReturn(List.of());
        when(context.capabilityContext(eq(snapshot), anyList())).thenReturn(List.of());
        when(context.countOnlineCandidates(eq(snapshot), anyString())).thenReturn(1);
        when(validation.validate(anyList(), anyList(), isNull(), eq("TEST_FAMILY")))
                .thenAnswer(invocation -> new PlanValidationResult());
        PlanningResponse response = new PlanningResponse();
        response.setResultCode("0");
        response.setPlanSteps(List.of(Map.of("capabilityType", "CAP_NEW", "completionCondition", "new=true")));
        response.setCandidateDiverse(false);
        when(model.generatePlan(any())).thenReturn(response);
        when(risk.assess(any(), eq("TEST_FAMILY"), any(), eq(false), eq(1)))
                .thenReturn(new RiskAssessmentResult("HIGH", "RULE_TEST", "受控高风险", BigDecimal.ONE,
                        "BASELINE_DOWNGRADE", "V1.0"));
        when(plans.countByTaskId(1L)).thenReturn(1L, 2L);
        AtomicLong nextId = new AtomicLong(10);
        doAnswer(invocation -> {
            ((PlanVersion) invocation.getArgument(0)).setId(nextId.getAndIncrement());
            return 1;
        }).when(plans).insert(any());

        template = new BaselineTemplate();
        template.setId(9L);
        template.setTemplateName("受控基线");
        template.setInputParams("[]");
        template.setSteps("[{\"capabilityType\":\"" + baselineFirstCapability
                + "\",\"completionCondition\":\"done=true\"},"
                + "{\"capabilityType\":\"CAP_NEW\",\"completionCondition\":\"new=true\"}]");
        when(baselines.matchForDowngrade("TEST_FAMILY")).thenReturn(Optional.of(template));
        service = new ReplanningService(tasks, plans, assignments, context, validation, model, risk,
                execution, events, baselines);
    }

    @Test void highRiskUsesValidatedBaselineTailWithoutRepeatingCompletedAction() throws Exception {
        arrange("CAP_DONE");
        service.replan(1L, 2, "DEVICE_OFFLINE");

        assertEquals(TaskStatus.DOWNGRADING, task.getStatus());
        assertEquals(11L, task.getCurrentPlanVersionId());
        assertTrue(task.getReplanUsed());
        verify(execution).startExecution(1L, 11L, 2);
        var versions = org.mockito.ArgumentCaptor.forClass(PlanVersion.class);
        verify(plans, times(2)).insert(versions.capture());
        PlanVersion baseline = versions.getAllValues().get(1);
        assertEquals("BASELINE_TEMPLATE", baseline.getSource());
        assertEquals(9L, baseline.getBaselineTemplateId());
        assertNotNull(baseline.getFrozenAt());
        var steps = new ObjectMapper().readTree(baseline.getPlanSteps());
        assertEquals(2, steps.size());
        assertEquals("SUCCESS", steps.get(0).get("executionResult").asText());
        assertEquals(2, steps.get(1).get("stepSeq").asInt());
    }

    @Test void incompatibleBaselinePrefixStopsBeforeDispatch() {
        arrange("CAP_UNRELATED");
        service.replan(1L, 2, "DEVICE_OFFLINE");

        assertEquals(TaskStatus.PENDING_MANUAL, task.getStatus());
        assertTrue(task.getFailureReason().contains("前缀与已完成步骤不一致"));
        verify(plans, times(1)).insert(any());
        verifyNoInteractions(execution);
    }

    @Test void baselineTailBeyondRemainingQuotaStopsBeforeDispatch() throws Exception {
        arrange("CAP_DONE");
        var steps = new java.util.ArrayList<Map<String, Object>>();
        steps.add(Map.of("capabilityType", "CAP_DONE", "completionCondition", "done=true"));
        for (int i = 0; i < 5; i++) {
            steps.add(Map.of("capabilityType", "CAP_NEW", "completionCondition", "new=true"));
        }
        template.setSteps(new ObjectMapper().writeValueAsString(steps));

        service.replan(1L, 2, "DEVICE_OFFLINE");

        assertEquals(TaskStatus.PENDING_MANUAL, task.getStatus());
        assertTrue(task.getFailureReason().contains("超过五步路径额度"));
        verify(plans, times(1)).insert(any());
        verifyNoInteractions(execution);
    }
}
