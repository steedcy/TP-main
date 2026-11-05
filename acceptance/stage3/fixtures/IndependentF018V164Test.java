package com.airport.ai.task;
import com.airport.ai.baseline.BaselineTemplateService;
import com.airport.ai.event.TaskEventService;
import com.airport.ai.planning.*;
import com.airport.ai.risk.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import java.util.*;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;
import static org.mockito.ArgumentMatchers.*;
/** Independent quota/state boundary observations; service with synthetic storage/model only. */
public class IndependentF018V164Test {
 static class F {
  TaskMapper tm=mock(TaskMapper.class);PlanVersionMapper pm=mock(PlanVersionMapper.class);TaskStepAssignmentMapper am=mock(TaskStepAssignmentMapper.class);ContextSnapshotService cs=mock(ContextSnapshotService.class);PlanningModelService model=mock(PlanningModelService.class);PlanValidationService validator=mock(PlanValidationService.class);TaskEventService ev=mock(TaskEventService.class);TaskExceptionMapper em=mock(TaskExceptionMapper.class);Task task=new Task();ReplanningService svc;
  F(int completed,boolean used) throws Exception {
   task.setId(163001L);task.setStatus(TaskStatus.EXECUTING);task.setCurrentPlanVersionId(163002L);task.setReplanUsed(used);task.setTaskGoal("Synthetic F018 quota");task.setSceneParams("{}");task.setGoalParsingResult("{}");task.setTaskFamily("EXT_SYNTHETIC");
   when(tm.findById(task.getId())).thenReturn(Optional.of(task));when(tm.claimReplan(anyLong(),anyString())).thenReturn(1);
   List<TaskStepAssignment> rows=new ArrayList<>();List<Map<String,Object>> steps=new ArrayList<>();
   for(int i=1;i<=completed+1;i++){var a=new TaskStepAssignment();a.setStepSeq(i);a.setStepStatus(i<=completed?"COMPLETED":"FAILED");a.setExecutionResult(i<=completed?"SUCCESS":"FAILED");a.setOutputParams("{\"routeGenerated\":true}");a.setCommandId("ORIGINAL-"+i);rows.add(a);steps.add(Map.of("stepSeq",i,"stepGoal","Synthetic navigation","capabilityType","CAP_NAVIGATION","inputParams",Map.of("targetLocation","F2_TEST_GATE"),"precondition","online","completionCondition","routeGenerated=true","failureHandling","manual"));}
   when(am.findByPlanVersionIdOrderByStepSeqAsc(163002L)).thenReturn(rows);PlanVersion old=new PlanVersion();old.setId(163002L);old.setPlanSteps(new ObjectMapper().writeValueAsString(steps));when(pm.findById(163002L)).thenReturn(Optional.of(old));
   ContextSnapshot ctx=new ContextSnapshot();ctx.setSnapshotCode("CTX-SYNTHETIC");ctx.setAgents("[]");when(cs.buildSnapshot(anyLong(),anyList())).thenReturn(ctx);when(cs.parseAgents(any())).thenReturn(List.of());
   PlanningResponse bad=new PlanningResponse();bad.setResultCode("ERROR");when(model.generatePlan(any())).thenReturn(bad);
   svc=new ReplanningService(tm,pm,am,cs,validator,model,mock(RiskAssessmentService.class),mock(TaskExecutionOrchestrator.class),ev,mock(BaselineTemplateService.class));
   var field=ReplanningService.class.getDeclaredField("taskExceptionMapper");field.setAccessible(true);field.set(svc,em);
  }
 }
 @ParameterizedTest @ValueSource(ints={0,4}) void quotaBoundaryReachesModelWithExactPreservedPrefix(int completed) throws Exception {
  F f=new F(completed,false);f.svc.replan(f.task.getId(),completed+1,"SYNTHETIC");var cap=org.mockito.ArgumentCaptor.forClass(PlanningRequest.class);verify(f.model).generatePlan(cap.capture());assertEquals(5-completed,cap.getValue().getRemainingStepQuota());assertEquals(completed,cap.getValue().getCompletedSteps().size());assertTrue(f.task.getReplanUsed());assertEquals(TaskStatus.PENDING_MANUAL,f.task.getStatus());verify(f.em).insert(argThat(e->"REPLAN_FAILED".equals(e.getExceptionType())&&"RESOLVED".equals(e.getExceptionStatus())&&"FAILED".equals(e.getRecoveryResult())));
 }
 @Test void exhaustedFiveStepBudgetConsumesOpportunityAndSkipsModel() throws Exception {F f=new F(5,false);f.svc.replan(f.task.getId(),6,"SYNTHETIC");verifyNoInteractions(f.model);assertTrue(f.task.getReplanUsed());assertEquals(TaskStatus.PENDING_MANUAL,f.task.getStatus());verify(f.ev).append(eq(f.task.getId()),eq("REPLAN_FAILED"),eq("SYSTEM"),eq("ERR_STEP_QUOTA_EXHAUSTED"),anyString());verify(f.em).insert(argThat(e->"ERR_STEP_QUOTA_EXHAUSTED".equals(e.getReasonCode())));}
 @Test void usedOpportunityNeverRequestsAnotherModel() throws Exception {F f=new F(0,true);f.svc.replan(f.task.getId(),1,"SYNTHETIC");verifyNoInteractions(f.model,f.cs);assertEquals(TaskStatus.PENDING_MANUAL,f.task.getStatus());verify(f.em).insert(argThat(e->"ERR_REPLAN_LIMIT_EXCEEDED".equals(e.getReasonCode())));}
}
