package com.airport.ai.task;

import com.airport.ai.device.*;
import com.airport.ai.event.TaskEventService;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.springframework.context.annotation.AnnotationConfigApplicationContext;
import java.time.LocalDateTime;
import java.util.*;
import java.util.concurrent.*;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;
import static org.mockito.ArgumentMatchers.*;

/** Independent component observations. No HTTP, persistence, real device or UI claim. */
public class IndependentF017V162Test {
 static class Dispatch {
  TaskMapper tasks=mock(TaskMapper.class);PlanVersionMapper plans=mock(PlanVersionMapper.class);TaskStepAssignmentMapper rows=mock(TaskStepAssignmentMapper.class);DeviceAgentMapper agents=mock(DeviceAgentMapper.class);DeviceAgentMessagingService gateway=mock(DeviceAgentMessagingService.class);TaskEventService events=mock(TaskEventService.class);TaskExceptionService exceptions=mock(TaskExceptionService.class);StepParameterResolver resolver=mock(StepParameterResolver.class);
  TaskStepAssignment a=new TaskStepAssignment();DeviceAgent agent=new DeviceAgent();Task task=new Task();PlanVersion plan=new PlanVersion();TaskExecutionOrchestrator service;
  Dispatch(Map<String,Object> input,String intent) throws Exception {
   task.setId(161101L);task.setStatus(TaskStatus.PENDING_ASSIGNMENT);task.setIsDryRun(false);plan.setId(161102L);plan.setPlanSteps(new com.fasterxml.jackson.databind.ObjectMapper().writeValueAsString(List.of(Map.of("stepSeq",1,"stepGoal",intent,"capabilityType","CAP_NAVIGATION","inputParams",input,"completionCondition","routeGenerated=true"))));
   a.setTaskId(task.getId());a.setPlanVersionId(plan.getId());a.setStepSeq(1);a.setStepStatus("PENDING_ASSIGNMENT");a.setCommandId("ACCEPT-GPT161");a.setDeviceAgentId(161103L);a.setRetryCount(0);
   agent.setId(a.getDeviceAgentId());agent.setAgentCode("GPT161");agent.setWorkStatus("IDLE");agent.setOnlineStatus("ONLINE");agent.setAgentStatus("ENABLED");
   when(tasks.findById(task.getId())).thenReturn(Optional.of(task));when(plans.findById(plan.getId())).thenReturn(Optional.of(plan));when(rows.findByCommandId(a.getCommandId())).thenReturn(Optional.of(a));when(rows.findByExecuteCommandId(anyString())).thenReturn(Optional.of(a));when(agents.findByIdForUpdate(agent.getId())).thenReturn(Optional.of(agent));when(agents.findById(agent.getId())).thenReturn(Optional.of(agent));when(agents.findByAgentCode(agent.getAgentCode())).thenReturn(Optional.of(agent));when(agents.claimAgent(agent.getId(),task.getId(),1)).thenReturn(1);when(resolver.resolve(anyLong(),anyLong(),anyMap())).thenReturn(input);
   service=new TaskExecutionOrchestrator(tasks,plans,rows,agents,mock(DeviceMapper.class),mock(DeviceCapabilityMapper.class),events,exceptions,gateway,mock(com.airport.ai.baseline.BaselineDryRunLifecycle.class),mock(com.airport.ai.baseline.DryRunDeviceSelectionMapper.class),resolver);
  }
  void accept(){service.onTaskResponse(agent.getAgentCode(),a.getCommandId(),true,null);}
 }
 @ParameterizedTest @ValueSource(strings={"速度","加速度","姿态","路径点","避障","急停","限速","失联停靠"})
 void dispatchBoundaryBlocksEachForbiddenCategoryAndRecordsFailure(String key) throws Exception {
  var d=new Dispatch(Map.of(key,1),"前往区域");d.accept();assertEquals("FAILED",d.a.getStepStatus());assertEquals("ERR_MOTION_SAFETY_FIELD",d.a.getReasonCode());assertEquals("IDLE",d.agent.getWorkStatus());assertNull(d.agent.getCurrentTaskId());verifyNoInteractions(d.gateway);verify(d.events).append(eq(d.task.getId()),eq("COMMAND_DISPATCH_BLOCKED"),eq("SYSTEM"),eq("ERR_MOTION_SAFETY_FIELD"),anyString());verify(d.exceptions).handleException(eq(d.task.getId()),eq(1),eq("STEP_FAILED"),anyString());
 }
 @ParameterizedTest @ValueSource(strings={"前往区域","会合","陪同","空间引导","现场通知"})
 void legalIntentReachesUnifiedMessagingBoundary(String intent) throws Exception {
  var d=new Dispatch(Map.of("targetLocation","F2_TEST_GATE"),intent);d.accept();assertEquals("EXECUTING",d.a.getStepStatus());verify(d.gateway).executeCapability(eq("GPT161"),eq(d.a.getExecuteCommandId()),eq(d.task.getId()),eq(1),eq("CAP_NAVIGATION"),eq(0),anyMap());
 }
 @Test void secondFailureStopsRetryAndEntersImpactJudgment() throws Exception {
  var d=new Dispatch(Map.of("targetLocation","F2_TEST_GATE"),"前往区域");d.accept();String id=d.a.getExecuteCommandId();d.service.onExecutionFeedback("GPT161",id,0,"FAILED","SYNTHETIC_FAILURE",Map.of());assertEquals(1,d.a.getRetryCount());assertEquals(id,d.a.getExecuteCommandId());d.service.onExecutionFeedback("GPT161",id,1,"FAILED","SYNTHETIC_FAILURE",Map.of());assertEquals("FAILED",d.a.getStepStatus());assertEquals(1,d.a.getRetryCount());verify(d.gateway,times(2)).executeCapability(eq("GPT161"),eq(id),eq(d.task.getId()),eq(1),eq("CAP_NAVIGATION"),anyInt(),anyMap());verify(d.exceptions).handleException(eq(d.task.getId()),eq(1),eq("STEP_FAILED"),anyString());verify(d.events).append(eq(d.task.getId()),eq("STEP_RETRY_DISPATCHED"),eq("SYSTEM"),eq("SYNTHETIC_FAILURE"),anyString());assertNull(d.agent.getCurrentTaskId());
 }
 @Test void productionComponentCanBeCreatedBySpring() {
  try(var c=new AnnotationConfigApplicationContext()) {
   // Prebuilt boundary mocks are singletons, so Spring does not inject real fields into them.
   c.getBeanFactory().registerSingleton("assignments",mock(TaskStepAssignmentMapper.class));
   c.getBeanFactory().registerSingleton("agents",mock(DeviceAgentMapper.class));
   c.getBeanFactory().registerSingleton("events",mock(TaskEventService.class));
   c.getBeanFactory().registerSingleton("exceptions",mock(TaskExceptionService.class));
   c.registerBean(StepTimeoutMonitorTask.class);c.refresh();
   assertNotNull(c.getBean(StepTimeoutMonitorTask.class));
  }
 }
 @Test void concurrentIdsAreUniqueAndMatchPublishedFormat() throws Exception {
  Set<String> ids=ConcurrentHashMap.newKeySet();var pool=Executors.newFixedThreadPool(8);
  try {var jobs=new ArrayList<Future<?>>();for(int t=0;t<8;t++)jobs.add(pool.submit(()->{for(int i=0;i<10000;i++){String id=CommandIds.next();assertTrue(id.matches("CMD-\\d{14}-[0-9A-F]{8}"));assertTrue(ids.add(id),"duplicate "+id);}}));for(var f:jobs)f.get();assertEquals(80000,ids.size());}finally{pool.shutdownNow();}
 }
 @ParameterizedTest @ValueSource(strings={"speed","acceleration","attitude","waypoints","obstacleAvoidance","emergencyStop","speedLimit","失联停靠"})
 void prohibitedFieldsAreDetected(String key){assertFalse(MotionSafetyGuard.detect(Map.of("inputParams",Map.of(key,1))).isEmpty(),key);}
 @ParameterizedTest @ValueSource(strings={"前往区域","会合","陪同","空间引导","现场通知"})
 void legalBusinessIntentPassesGuard(String intent){assertTrue(MotionSafetyGuard.detect(Map.of("stepGoal",intent,"inputParams",Map.of("targetLocation","F2_TEST_GATE"))).isEmpty());}
 @Test void originalFalsePredicateCounterexampleAndLegalControl(){var step=Map.<String,Object>of("capabilityType","CAP_NAVIGATION","completionCondition","routeGenerated=false");assertFalse(CompletionConditionEvaluator.satisfied(step,Map.of("routeGenerated",true)));assertTrue(CompletionConditionEvaluator.satisfied(step,Map.of("routeGenerated",false)));}
 @Test void receiptDoesNotMeetBusinessCondition(){var step=Map.<String,Object>of("capabilityType","CAP_NAVIGATION","completionCondition","routeGenerated=true");assertFalse(CompletionConditionEvaluator.satisfied(step,Map.of("received",true)));assertTrue(CompletionConditionEvaluator.satisfied(step,Map.of("routeGenerated",true)));}
 @Test void conjunctionNeedsAllPredicates(){var step=Map.<String,Object>of("completionCondition","routeGenerated=true and displayStatus=SUCCESS");assertFalse(CompletionConditionEvaluator.satisfied(step,Map.of("routeGenerated",true,"displayStatus","FAILED")));assertTrue(CompletionConditionEvaluator.satisfied(step,Map.of("routeGenerated",true,"displayStatus","SUCCESS")));}
 @ParameterizedTest @ValueSource(ints={20,40})
 void planThirtySecondTimeoutHasBeforeAndAfterBoundary(int age) {
  var rows=mock(TaskStepAssignmentMapper.class);var agents=mock(DeviceAgentMapper.class);var events=mock(TaskEventService.class);var exceptions=mock(TaskExceptionService.class);var plans=mock(PlanVersionMapper.class);var commands=mock(DeviceCommandMapper.class);
  var a=new TaskStepAssignment();a.setId(161001L);a.setTaskId(161002L);a.setPlanVersionId(161003L);a.setDeviceAgentId(161004L);a.setStepSeq(1);a.setRetryCount(0);a.setExecuteCommandId("CMD-SYNTHETIC-161");a.setStepStatus("EXECUTING");a.setDispatchedAt(LocalDateTime.now().minusSeconds(age));
  var agent=new DeviceAgent();agent.setId(a.getDeviceAgentId());agent.setAgentCode("GPT-161");agent.setWorkStatus("BUSY");agent.setCurrentTaskId(a.getTaskId());agent.setCurrentStepSeq(1);
  var plan=new PlanVersion();plan.setPlanSteps("[{\"stepSeq\":1,\"stepTimeout\":30}]");when(plans.findById(a.getPlanVersionId())).thenReturn(Optional.of(plan));when(rows.findByStepStatusAndDispatchedAtBefore(eq("EXECUTING"),any())).thenReturn(List.of(a));when(agents.findById(agent.getId())).thenReturn(Optional.of(agent));
  new StepTimeoutMonitorTask(rows,agents,events,exceptions,60,plans,commands).checkStepTimeout();
  if(age<30){assertEquals("EXECUTING",a.getStepStatus());assertEquals("BUSY",agent.getWorkStatus());verifyNoInteractions(exceptions,commands);}
  else{assertEquals("FAILED",a.getStepStatus());assertEquals("TIMEOUT",a.getExecutionResult());assertEquals("ERR_EXECUTION_TIMEOUT",a.getReasonCode());assertNull(agent.getCurrentTaskId());assertEquals("IDLE",agent.getWorkStatus());verify(commands).updateStatus(eq("GPT-161"),eq(a.getExecuteCommandId()),eq("EXECUTE_CAPABILITY"),eq(0),eq("TIMED_OUT"),anyString());verify(exceptions).handleException(eq(a.getTaskId()),eq(1),eq("EXECUTION_TIMEOUT"),anyString());}
 }
}
