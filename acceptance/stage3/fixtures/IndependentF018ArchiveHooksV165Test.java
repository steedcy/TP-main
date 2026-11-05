package com.airport.ai.task;
import com.airport.ai.device.*;
import com.airport.ai.event.TaskEventService;
import org.junit.jupiter.api.Test;
import java.util.*;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;
import static org.mockito.ArgumentMatchers.*;
/** Service-only regression for three completion exits and archive preservation. No HTTP/hardware claim. */
public class IndependentF018ArchiveHooksV165Test {
 static class F {
  TaskMapper tasks=mock(TaskMapper.class);PlanVersionMapper plans=mock(PlanVersionMapper.class);TaskStepAssignmentMapper rows=mock(TaskStepAssignmentMapper.class);TaskExceptionService errors=mock(TaskExceptionService.class);TaskEventService events=mock(TaskEventService.class);Task task=new Task();TaskExecutionOrchestrator exec;
  F(String family) {
   task.setId(165901L);task.setTaskFamily(family);task.setIsDryRun(false);task.setStatus(TaskStatus.EXECUTING);task.setCurrentPlanVersionId(165902L);when(tasks.findById(task.getId())).thenReturn(Optional.of(task));
   exec=new TaskExecutionOrchestrator(tasks,plans,rows,mock(DeviceAgentMapper.class),mock(DeviceMapper.class),mock(DeviceCapabilityMapper.class),events,errors,mock(DeviceAgentMessagingService.class),mock(com.airport.ai.baseline.BaselineDryRunLifecycle.class),mock(com.airport.ai.baseline.DryRunDeviceSelectionMapper.class),mock(StepParameterResolver.class));
  }
  TaskStepAssignment row(int seq,String status){var a=new TaskStepAssignment();a.setTaskId(task.getId());a.setPlanVersionId(165902L);a.setStepSeq(seq);a.setStepStatus(status);return a;}
  void complete(List<TaskStepAssignment> all) throws Exception {var method=TaskExecutionOrchestrator.class.getDeclaredMethod("completeAvailableChannels",Long.class,Long.class,List.class);method.setAccessible(true);method.invoke(exec,task.getId(),165902L,all);assertEquals(TaskStatus.COMPLETED,task.getStatus());verify(errors).archiveAllUnresolvedOnTaskComplete(task.getId());}
 }
 @Test void ordinaryCompletionArchives() throws Exception {F f=new F("EXT_SYNTHETIC");f.complete(List.of(f.row(1,"COMPLETED")));}
 @Test void flightPublicationCompletionArchives() throws Exception {F f=new F("FLIGHT_CHANGE_RESPONSE");PlanVersion p=new PlanVersion();p.setId(165902L);p.setPlanSteps("[{\"stepSeq\":1,\"capabilityType\":\"CAP_FLIGHT_UPDATE\"}]");when(f.plans.findById(165902L)).thenReturn(Optional.of(p));f.complete(List.of(f.row(1,"COMPLETED")));}
 @Test void normalBaggageSkipCompletionArchives() throws Exception {F f=new F("OVERSIZE_BAGGAGE_HANDLING");var first=f.row(1,"COMPLETED");var next=f.row(2,"PENDING_ASSIGNMENT");when(f.rows.findByPlanVersionIdOrderByStepSeqAsc(165902L)).thenReturn(List.of(first,next));var method=TaskExecutionOrchestrator.class.getDeclaredMethod("completeNormalBaggageBranch",Task.class,Long.class,Integer.class,Map.class);method.setAccessible(true);method.invoke(f.exec,f.task,165902L,1,Map.of("isOversize",false));assertEquals(TaskStatus.COMPLETED,f.task.getStatus());assertEquals("SKIPPED",next.getStepStatus());verify(f.errors).archiveAllUnresolvedOnTaskComplete(f.task.getId());}
 @Test void archiveClosesOutstandingOnlyAndPreservesIgnoredAndResolved() {
  TaskExceptionMapper em=mock(TaskExceptionMapper.class);var processing=new TaskException();processing.setTaskId(165901L);processing.setExceptionStatus("PROCESSING");processing.setRecoveryAction("指令重试");var resolved=new TaskException();resolved.setExceptionStatus("RESOLVED");resolved.setRecoveryResult("SUCCESS");var ignored=new TaskException();ignored.setExceptionStatus("IGNORED");when(em.findByTaskIdOrderByOccurredAtDesc(165901L)).thenReturn(List.of(processing,resolved,ignored));var service=new TaskExceptionService(mock(TaskMapper.class),mock(TaskStepAssignmentMapper.class),em,mock(DeviceAgentMapper.class),mock(TaskEventService.class),mock(TaskExecutionOrchestrator.class),mock(ReplanningService.class),mock(PlanVersionMapper.class));service.archiveAllUnresolvedOnTaskComplete(165901L);assertEquals("RESOLVED",processing.getExceptionStatus());assertEquals("FAILED",processing.getRecoveryResult());assertNotNull(processing.getResolvedAt());assertEquals("指令重试",processing.getRecoveryAction());assertEquals("IGNORED",ignored.getExceptionStatus());assertEquals("SUCCESS",resolved.getRecoveryResult());verify(em).update(processing);verify(em,never()).update(resolved);verify(em,never()).update(ignored);
 }
}
