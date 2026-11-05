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
public class IndependentF017V161Test {
 @Test void productionComponentCanBeCreatedBySpring() {
  try(var c=new AnnotationConfigApplicationContext()) {
   c.registerBean(TaskStepAssignmentMapper.class,()->mock(TaskStepAssignmentMapper.class));
   c.registerBean(DeviceAgentMapper.class,()->mock(DeviceAgentMapper.class));
   c.registerBean(TaskEventService.class,()->mock(TaskEventService.class));
   c.registerBean(TaskExceptionService.class,()->mock(TaskExceptionService.class));
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
