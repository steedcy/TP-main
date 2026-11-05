package com.airport.ai.task;

import com.airport.ai.device.*;
import com.airport.ai.event.TaskEventService;
import org.junit.jupiter.api.Test;
import java.time.LocalDateTime;
import java.util.*;
import static org.mockito.Mockito.*;
import static org.mockito.ArgumentMatchers.*;
import static org.junit.jupiter.api.Assertions.*;

/** Real timeout monitor, controlled expired assignment/storage; no scheduler wait.
 * Explicit service-level ownership guard and own-occupation positive control.
 */
public class IndependentF016TimeoutOwnershipV160Test {
 void exercise(boolean otherOwner) {
  TaskStepAssignmentMapper rows=mock(TaskStepAssignmentMapper.class);DeviceAgentMapper agents=mock(DeviceAgentMapper.class);
  TaskEventService events=mock(TaskEventService.class);TaskExceptionService exceptions=mock(TaskExceptionService.class);
  StepTimeoutMonitorTask monitor=new StepTimeoutMonitorTask(rows,agents,events,exceptions,60);
  TaskStepAssignment a=new TaskStepAssignment();a.setId(159001L);a.setTaskId(159002L);a.setPlanVersionId(159003L);a.setDeviceAgentId(159004L);a.setStepSeq(1);a.setStepStatus("EXECUTING");a.setExecuteCommandId("EXE-G160");a.setDispatchedAt(LocalDateTime.now().minusSeconds(120));
  DeviceAgent agent=new DeviceAgent();agent.setId(159004L);agent.setWorkStatus("BUSY");agent.setCurrentTaskId(otherOwner?159005L:a.getTaskId());agent.setCurrentStepSeq(1);
  when(rows.findByStepStatusAndDispatchedAtBefore(eq("EXECUTING"),any())).thenReturn(List.of(a));when(agents.findById(agent.getId())).thenReturn(Optional.of(agent));
  monitor.checkStepTimeout();assertEquals("FAILED",a.getStepStatus());assertEquals("TIMEOUT",a.getExecutionResult());
  verify(exceptions).handleException(eq(a.getTaskId()),eq(1),eq("EXECUTION_TIMEOUT"),anyString());
  if(otherOwner){assertEquals("BUSY",agent.getWorkStatus());assertEquals(159005L,agent.getCurrentTaskId());assertEquals(1,agent.getCurrentStepSeq());verify(agents,never()).update(any());}
  else{assertEquals("IDLE",agent.getWorkStatus());assertNull(agent.getCurrentTaskId());assertNull(agent.getCurrentStepSeq());verify(agents).update(agent);}
 }
 @Test void expiredOtherTaskDoesNotClearCurrentOwner(){exercise(true);}
 @Test void expiredOwnTaskReleasesItsOccupation(){exercise(false);}
}
