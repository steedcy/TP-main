package com.airport.ai.task;

import com.airport.ai.baseline.BaselineTemplateService;
import com.airport.ai.event.TaskEventService;
import com.airport.ai.planning.PlanningModelService;
import com.airport.ai.planning.PlanningRequest;
import com.airport.ai.planning.PlanningResponse;
import com.airport.ai.risk.RiskAssessmentResult;
import com.airport.ai.risk.RiskAssessmentService;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.*;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class IndependentF012QuotaTest {
    private Map<String,Object> step(int n) {
        Map<String,Object> s=new LinkedHashMap<>();
        s.put("stepSeq",n);s.put("stepGoal","go "+n);s.put("capabilityType","CAP_NAVIGATION");
        s.put("inputParams",Map.of("targetLocation","F2_TEST_GATE"));s.put("precondition","device online");
        s.put("completionCondition","routeGenerated=true");s.put("failureHandling","manual");
        return s;
    }
    @Test void fiveCompletedActionsHaveZeroQuotaAndDoNotCallModel() {
        TaskMapper tasks=mock(TaskMapper.class);PlanVersionMapper plans=mock(PlanVersionMapper.class);
        TaskStepAssignmentMapper assignments=mock(TaskStepAssignmentMapper.class);PlanningModelService model=mock(PlanningModelService.class);
        TaskEventService events=mock(TaskEventService.class);
        Task t=new Task();t.setId(9011L);t.setCurrentPlanVersionId(9012L);when(tasks.findById(9011L)).thenReturn(Optional.of(t));
        List<TaskStepAssignment> done=new ArrayList<>();for(int n=1;n<=5;n++){TaskStepAssignment a=new TaskStepAssignment();a.setStepSeq(n);a.setStepStatus("COMPLETED");done.add(a);}
        when(assignments.findByPlanVersionIdOrderByStepSeqAsc(9012L)).thenReturn(done);
        new ReplanningService(tasks,plans,assignments,mock(ContextSnapshotService.class),mock(PlanValidationService.class),
            model,mock(RiskAssessmentService.class),mock(TaskExecutionOrchestrator.class),events,mock(BaselineTemplateService.class))
            .replan(9011L,6,"STEP_FAILED");
        assertEquals(TaskStatus.PENDING_MANUAL,t.getStatus());verifyNoInteractions(model);
        verify(events).append(eq(9011L),eq("REPLAN_FAILED"),eq("SYSTEM"),eq("ERR_STEP_QUOTA_EXHAUSTED"),anyString());
    }
    @Test void twoCompletedPlusThreeReplacementActionsFreezeFiveActionVersion() throws Exception {
        TaskMapper tasks=mock(TaskMapper.class);PlanVersionMapper plans=mock(PlanVersionMapper.class);
        TaskStepAssignmentMapper assignments=mock(TaskStepAssignmentMapper.class);
        ContextSnapshotService context=mock(ContextSnapshotService.class);PlanningModelService model=mock(PlanningModelService.class);
        PlanValidationService validator=mock(PlanValidationService.class);RiskAssessmentService risk=mock(RiskAssessmentService.class);
        TaskExecutionOrchestrator execution=mock(TaskExecutionOrchestrator.class);TaskEventService events=mock(TaskEventService.class);
        Task t=new Task();t.setId(9001L);t.setCurrentPlanVersionId(9002L);t.setTaskGoal("F012 synthetic goal");
        when(tasks.findById(9001L)).thenReturn(Optional.of(t));when(tasks.claimReplan(eq(9001L),anyString())).thenReturn(1);
        PlanVersion old=new PlanVersion();old.setId(9002L);
        old.setPlanSteps("[{\"stepSeq\":1,\"capabilityType\":\"CAP_NAVIGATION\"},{\"stepSeq\":2,\"capabilityType\":\"CAP_NAVIGATION\"},{\"stepSeq\":3,\"capabilityType\":\"CAP_NAVIGATION\"},{\"stepSeq\":4,\"capabilityType\":\"CAP_NAVIGATION\"},{\"stepSeq\":5,\"capabilityType\":\"CAP_NAVIGATION\"}]");
        when(plans.findById(9002L)).thenReturn(Optional.of(old));
        TaskStepAssignment a1=new TaskStepAssignment();a1.setStepSeq(1);a1.setStepStatus("COMPLETED");a1.setExecutionResult("SUCCESS");
        TaskStepAssignment a2=new TaskStepAssignment();a2.setStepSeq(2);a2.setStepStatus("COMPLETED");a2.setExecutionResult("SUCCESS");
        TaskStepAssignment a3=new TaskStepAssignment();a3.setStepSeq(3);a3.setStepStatus("FAILED");
        when(assignments.findByPlanVersionIdOrderByStepSeqAsc(9002L)).thenReturn(List.of(a1,a2,a3));
        ContextSnapshot snap=new ContextSnapshot();snap.setSnapshotCode("CTX-IND-F012");snap.setGeneratedAt(LocalDateTime.now());
        when(context.buildSnapshot(eq(9001L),anyList())).thenReturn(snap);
        PlanningResponse response=new PlanningResponse();response.setResultCode("0");response.setConfidence(new BigDecimal("0.99"));
        response.setPlanSteps(List.of(step(1),step(2),step(3)));when(model.generatePlan(any())).thenReturn(response);
        when(validator.validate(anyList(),any(),any(),any(),eq(2))).thenReturn(new PlanValidationResult());
        when(risk.assess(any(),any(),any(),anyBoolean(),anyInt())).thenReturn(new RiskAssessmentResult("LOW","RULE_LOW_RISK","test",new BigDecimal("0.99"),"AUTO_EXECUTE","V1.0"));
        new ReplanningService(tasks,plans,assignments,context,validator,model,risk,execution,events,mock(BaselineTemplateService.class)).replan(9001L,3,"STEP_FAILED");
        ArgumentCaptor<PlanningRequest> req=ArgumentCaptor.forClass(PlanningRequest.class);verify(model).generatePlan(req.capture());
        assertEquals(3,req.getValue().getRemainingStepQuota());assertEquals(2,req.getValue().getCompletedSteps().size());
        ArgumentCaptor<PlanVersion> inserted=ArgumentCaptor.forClass(PlanVersion.class);verify(plans).insert(inserted.capture());
        PlanVersion v=inserted.getValue();
        assertNotNull(v.getFrozenAt());
        assertEquals(5,new com.fasterxml.jackson.databind.ObjectMapper().readTree(v.getPlanSteps()).size());
        verify(execution).startExecution(eq(9001L),any(),eq(3));
    }
}
