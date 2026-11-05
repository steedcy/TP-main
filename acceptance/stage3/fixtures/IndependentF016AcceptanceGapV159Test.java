package com.airport.ai.task;

import com.airport.ai.device.*;
import com.airport.ai.devicetype.DeviceTypeCapabilityService;
import com.airport.ai.baseline.*;
import com.airport.ai.event.TaskEventService;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import java.util.*;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;
import static org.mockito.ArgumentMatchers.*;

/** Exact accepted->dispatch gap, real orchestrator and real messaging gateway.
 * Storage and offline transition are controlled. This is service-level evidence,
 * not an HTTP timing or physical-device observation.
 */
public class IndependentF016AcceptanceGapV159Test {
 @Test void offlineAfterAcceptedWriteBeforeDispatchNeverReachesAdapterAndReleasesOccupation() {
  TaskMapper tasks=mock(TaskMapper.class);PlanVersionMapper plans=mock(PlanVersionMapper.class);
  TaskStepAssignmentMapper assignments=mock(TaskStepAssignmentMapper.class);
  DeviceAgentMapper agents=mock(DeviceAgentMapper.class);DeviceMapper devices=mock(DeviceMapper.class);
  DeviceCapabilityMapper caps=mock(DeviceCapabilityMapper.class);DeviceCommandMapper commands=mock(DeviceCommandMapper.class);
  DeviceAdapterClient adapter=mock(DeviceAdapterClient.class);TaskEventService events=mock(TaskEventService.class);
  TaskExceptionService exceptions=mock(TaskExceptionService.class);StepParameterResolver params=mock(StepParameterResolver.class);
  DeviceAgentMessagingService gateway=new DeviceAgentMessagingService(agents,devices,commands,caps,tasks,adapter,60,new ObjectMapper(),mock(DeviceTypeCapabilityService.class));
  TaskExecutionOrchestrator orchestrator=new TaskExecutionOrchestrator(tasks,plans,assignments,agents,devices,caps,events,exceptions,gateway,mock(BaselineDryRunLifecycle.class),mock(DryRunDeviceSelectionMapper.class),params);
  Task task=new Task();task.setId(157001L);task.setStatus(TaskStatus.PENDING_ASSIGNMENT);task.setIsDryRun(false);
  PlanVersion plan=new PlanVersion();plan.setId(157002L);plan.setPlanSteps("[{\"stepSeq\":1,\"stepGoal\":\"synthetic navigation\",\"capabilityType\":\"CAP_NAVIGATION\",\"inputParams\":{},\"completionCondition\":\"routeGenerated=true\"}]");
  TaskStepAssignment a=new TaskStepAssignment();a.setTaskId(task.getId());a.setPlanVersionId(plan.getId());a.setStepSeq(1);a.setStepStatus("PENDING_ASSIGNMENT");a.setCommandId("ACCEPT-157");a.setDeviceAgentId(157003L);a.setRetryCount(0);
  DeviceAgent agent=new DeviceAgent();agent.setId(157003L);agent.setAgentCode("AGT-G159-GAP");agent.setAgentStatus("ENABLED");agent.setOnlineStatus("ONLINE");agent.setWorkStatus("IDLE");
  when(tasks.findById(task.getId())).thenReturn(Optional.of(task));when(plans.findById(plan.getId())).thenReturn(Optional.of(plan));
  when(assignments.findByCommandId(a.getCommandId())).thenReturn(Optional.of(a));when(assignments.findByExecuteCommandId(anyString())).thenReturn(Optional.of(a));
  when(agents.findByIdForUpdate(agent.getId())).thenReturn(Optional.of(agent));when(agents.claimAgent(agent.getId(),task.getId(),1)).thenReturn(1);when(agents.findByAgentCode(agent.getAgentCode())).thenReturn(Optional.of(agent));when(agents.findById(agent.getId())).thenReturn(Optional.of(agent));
  when(params.resolve(anyLong(),anyLong(),anyMap())).thenReturn(Map.of());
  doAnswer(inv->{ if("BUSY".equals(agent.getWorkStatus()))agent.setOnlineStatus("OFFLINE");return 1; }).when(agents).update(agent);
  orchestrator.onTaskResponse(agent.getAgentCode(),a.getCommandId(),true,null);
  verify(events).append(eq(task.getId()),eq("AGENT_ASSIGNED"),eq("SYSTEM"),isNull(),anyString());
  verifyNoInteractions(adapter);verify(commands,never()).insertIfAbsent(any());
  assertEquals("OFFLINE",agent.getOnlineStatus());assertEquals("IDLE",agent.getWorkStatus());assertNull(agent.getCurrentTaskId());assertNull(agent.getCurrentStepSeq());
  assertEquals("FAILED",a.getStepStatus());verify(exceptions).handleException(eq(task.getId()),eq(1),eq("STEP_FAILED"),anyString());
 }
}
