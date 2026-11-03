package com.airport.ai.task;

import com.airport.ai.baseline.BaselineTemplateService;
import com.airport.ai.device.DeviceCapabilityMapper;
import com.airport.ai.event.TaskEventService;
import com.airport.ai.planning.PlanningModelService;
import com.airport.ai.planning.PlanningResponse;
import com.airport.ai.risk.RiskAssessmentResult;
import com.airport.ai.risk.RiskAssessmentService;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.*;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/** Real validator and ReplanningService; only storage/context/model/risk boundaries are synthetic. */
class IndependentF013OwnedReplanV144Test {
    static final long TASK_ID=714401L, OLD_ID=714402L;
    Map<String,Object> step() {
        return new LinkedHashMap<>(Map.of("stepSeq",1,"stepGoal","Synthetic navigation", "capabilityType","CAP_NAVIGATION",
            "inputParams",Map.of("targetLocation","F2_TEST_GATE"),"precondition","device online",
            "completionCondition","routeGenerated=true","failureHandling","manual"));
    }
    List<Map<String,Object>> agents(long owner) {
        return List.of(Map.of("agentId","AGT-SYNTHETIC-OWNED","capabilities",List.of("CAP_NAVIGATION"),
            "onlineStatus","ONLINE","workload","BUSY","currentTaskId",owner,"currentStepSeq",1,
            "deviceTypeCode","SIMULATOR","simulatedDeviceType","MOBILE_ROBOT"));
    }
    PlanValidationService validator() {
        DeviceCapabilityMapper caps=mock(DeviceCapabilityMapper.class);
        when(caps.existsByCapabilityTypeAndCapabilityStatus(eq("CAP_NAVIGATION"),eq("ENABLED"))).thenReturn(true);
        return new PlanValidationService(caps);
    }
    @Test void sixArgumentValidatorCorrectlyAllowsSameOwner() {
        assertTrue(validator().validate(List.of(step()),agents(TASK_ID),null,"EXT_2AD8B934",0,TASK_ID).isAllPassed());
    }
    PlanVersion throughProductionReplan(long owner) throws Exception {
        TaskMapper tasks=mock(TaskMapper.class);PlanVersionMapper plans=mock(PlanVersionMapper.class);
        TaskStepAssignmentMapper assignments=mock(TaskStepAssignmentMapper.class);
        ContextSnapshotService context=mock(ContextSnapshotService.class);PlanningModelService model=mock(PlanningModelService.class);
        RiskAssessmentService risk=mock(RiskAssessmentService.class);TaskExecutionOrchestrator exec=mock(TaskExecutionOrchestrator.class);
        TaskEventService events=mock(TaskEventService.class);
        Task task=new Task();task.setId(TASK_ID);task.setTaskFamily("EXT_2AD8B934");task.setTaskGoal("Synthetic owned-resource replanning");
        task.setCurrentPlanVersionId(OLD_ID);task.setSceneParams("{}");task.setGoalParsingResult("{}");task.setStatus(TaskStatus.EXECUTING);
        when(tasks.findById(TASK_ID)).thenReturn(Optional.of(task));when(tasks.claimReplan(eq(TASK_ID),anyString())).thenReturn(1);
        PlanVersion old=new PlanVersion();old.setId(OLD_ID);old.setVersionNo(1);old.setFrozenAt(LocalDateTime.now().minusMinutes(1));
        old.setPlanSteps(new ObjectMapper().writeValueAsString(List.of(step())));String oldSteps=old.getPlanSteps();
        when(plans.findById(OLD_ID)).thenReturn(Optional.of(old));when(plans.countByTaskId(TASK_ID)).thenReturn(1L);
        TaskStepAssignment failed=new TaskStepAssignment();failed.setStepSeq(1);failed.setStepStatus("FAILED");
        when(assignments.findByPlanVersionIdOrderByStepSeqAsc(OLD_ID)).thenReturn(List.of(failed));
        ContextSnapshot snapshot=new ContextSnapshot();snapshot.setSnapshotCode("CTX-SYNTHETIC-OWNED");snapshot.setTaskId(TASK_ID);
        snapshot.setAgents(new ObjectMapper().writeValueAsString(agents(owner)));
        when(context.buildSnapshot(eq(TASK_ID),anyList())).thenReturn(snapshot);
        when(context.parseAgents(any())).thenReturn(agents(owner));when(context.countAvailableCandidates(any(),anyString(),anyString())).thenReturn(1);
        PlanningResponse response=new PlanningResponse();response.setResultCode("0");response.setPlanSteps(List.of(step()));response.setConfidence(new BigDecimal("0.99"));
        when(model.generatePlan(any())).thenReturn(response);
        when(risk.assess(any(),any(),any(),anyBoolean(),anyInt())).thenReturn(new RiskAssessmentResult("LOW","RULE_LOW_RISK","synthetic",new BigDecimal("0.99"),"AUTO_EXECUTE","V1.0"));
        new ReplanningService(tasks,plans,assignments,context,validator(),model,risk,exec,events,mock(BaselineTemplateService.class))
            .replan(TASK_ID,1,"STEP_TIMEOUT");
        ArgumentCaptor<PlanVersion> captured=ArgumentCaptor.forClass(PlanVersion.class);verify(plans).insert(captured.capture());
        assertEquals(oldSteps,old.getPlanSteps());assertEquals(2,captured.getValue().getVersionNo());
        return captured.getValue();
    }
    @Test void productionReplanMustPreserveSameOwnerException() throws Exception {
        PlanVersion actual=throughProductionReplan(TASK_ID);
        assertEquals("PASS",actual.getConstraintCheckResult(),()->"Same task ownership must not be external conflict: "+actual.getValidationErrors());
        assertNotNull(actual.getFrozenAt());
    }
    @Test void productionReplanStillRejectsDifferentOwner() throws Exception {
        PlanVersion actual=throughProductionReplan(TASK_ID+1);
        assertEquals("FAIL",actual.getConstraintCheckResult());assertNull(actual.getFrozenAt());
        assertTrue(actual.getValidationErrors().contains("ERR_RESOURCE_CONFLICT"));
    }
}
