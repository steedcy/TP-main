package com.airport.ai.task;

import com.airport.ai.baseline.BaselineTemplateService;
import com.airport.ai.event.TaskEventService;
import com.airport.ai.planning.PlanningModelService;
import com.airport.ai.planning.PlanningResponse;
import com.airport.ai.risk.RiskAssessmentService;
import com.airport.ai.taskdef.TaskDefinitionService;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;
import java.time.LocalDateTime;
import java.util.concurrent.CompletionException;
import java.util.concurrent.TimeoutException;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;
import static org.mockito.ArgumentMatchers.*;

/** Actual judgeAndRoute error handling with a timed-out component, no shared service disruption. */
public class IndependentF014TimeoutV151Test {
 @Test void timedOutSupervisionGoesManualWithoutBaselineOrExecution() {
  TaskMapper tasks=mock(TaskMapper.class);PlanVersionMapper plans=mock(PlanVersionMapper.class);
  ContextSnapshotService contexts=mock(ContextSnapshotService.class);RiskAssessmentService risks=mock(RiskAssessmentService.class);
  BaselineTemplateService baselines=mock(BaselineTemplateService.class);TaskEventService events=mock(TaskEventService.class);
  TaskExecutionOrchestrator execution=mock(TaskExecutionOrchestrator.class);
  TaskPlanningOrchestrator orchestrator=new TaskPlanningOrchestrator(tasks,plans,contexts,mock(PlanValidationService.class),mock(PlanningModelService.class),risks,baselines,events,execution,mock(TaskDefinitionService.class));
  Task task=new Task();task.setId(715101L);task.setTaskFamily("GENERAL_GUIDANCE");task.setStatus(TaskStatus.SUPERVISING);
  PlanVersion plan=new PlanVersion();plan.setId(715102L);plan.setPlanSteps("[{\"stepSeq\":1,\"capabilityType\":\"CAP_NAVIGATION\"}]");
  plan.setStructureCheckResult("PASS");plan.setCapabilityCheckResult("PASS");plan.setConstraintCheckResult("PASS");
  ContextSnapshot snapshot=new ContextSnapshot();snapshot.setGeneratedAt(LocalDateTime.now());PlanningResponse response=new PlanningResponse();response.setCandidateDiverse(false);
  when(contexts.countAvailableCandidates(any(),eq("CAP_NAVIGATION"),eq("GENERAL_GUIDANCE"))).thenReturn(3);
  when(risks.assess(eq(plan),eq("GENERAL_GUIDANCE"),any(),eq(false),eq(3))).thenThrow(new CompletionException(new TimeoutException("synthetic supervision deadline")));
  ReflectionTestUtils.invokeMethod(orchestrator,"judgeAndRoute",task,plan,snapshot,response);
  assertEquals(TaskStatus.PENDING_MANUAL,task.getStatus());verify(tasks).update(task);
  verify(events).append(eq(task.getId()),eq("SUPERVISION_JUDGED"),eq("SYSTEM"),eq("ERR_SUPERVISION_UNAVAILABLE"),contains("synthetic supervision deadline"));
  verifyNoInteractions(execution,baselines,plans);
 }
}
