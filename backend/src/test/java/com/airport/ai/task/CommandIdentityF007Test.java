package com.airport.ai.task;

import com.airport.ai.baseline.BaselineDryRunLifecycle;
import com.airport.ai.baseline.DryRunDeviceSelectionMapper;
import com.airport.ai.common.BusinessException;
import com.airport.ai.device.CommandIds;
import com.airport.ai.device.Device;
import com.airport.ai.device.DeviceAgent;
import com.airport.ai.device.DeviceAgentMapper;
import com.airport.ai.device.DeviceAgentMessagingService;
import com.airport.ai.device.DeviceCapabilityMapper;
import com.airport.ai.device.DeviceMapper;
import com.airport.ai.event.TaskEventService;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * SRS_F007.R02（BL-003 方案B）：承接、执行、取消各为独立逻辑消息，各用独立指令编号；
 * 同一执行消息的重试沿用同一编号并递增尝试序号；反馈按执行编号关联。
 */
class CommandIdentityF007Test {
    private final TaskMapper tasks = mock(TaskMapper.class);
    private final PlanVersionMapper plans = mock(PlanVersionMapper.class);
    private final TaskStepAssignmentMapper assignments = mock(TaskStepAssignmentMapper.class);
    private final DeviceAgentMapper agents = mock(DeviceAgentMapper.class);
    private final DeviceMapper devices = mock(DeviceMapper.class);
    private final DeviceCapabilityMapper capabilities = mock(DeviceCapabilityMapper.class);
    private final StepParameterResolver resolver = mock(StepParameterResolver.class);
    private final DeviceAgentMessagingService messaging = mock(DeviceAgentMessagingService.class);
    private final TaskEventService events = mock(TaskEventService.class);
    private final TaskExceptionService exceptions = mock(TaskExceptionService.class);
    private final TaskStepAssignment assignment = new TaskStepAssignment();
    private final DeviceAgent agent = new DeviceAgent();

    private TaskExecutionOrchestrator orchestrator() throws Exception {
        Task task = new Task();
        task.setId(1L);
        task.setTaskFamily("CUSTOM");
        task.setStatus(TaskStatus.PENDING_ASSIGNMENT);
        when(tasks.findById(1L)).thenReturn(Optional.of(task));
        PlanVersion plan = new PlanVersion();
        plan.setId(2L);
        plan.setTaskId(1L);
        plan.setPlanSteps(new ObjectMapper().writeValueAsString(List.of(
                Map.of("stepSeq", 1, "capabilityType", "CAP_INFO_DISPLAY", "stepGoal", "展示"))));
        when(plans.findById(2L)).thenReturn(Optional.of(plan));
        assignment.setTaskId(1L);
        assignment.setPlanVersionId(2L);
        assignment.setStepSeq(1);
        assignment.setStepStatus("PENDING_ASSIGNMENT");
        assignment.setRetryCount(0);
        when(assignments.findByPlanVersionIdAndStepSeq(2L, 1)).thenReturn(Optional.of(assignment));
        agent.setId(9L);
        agent.setAgentCode("AGT-9");
        agent.setDeviceId(10L);
        agent.setOnlineStatus("ONLINE");
        agent.setWorkStatus("IDLE");
        when(agents.findByAgentCode("AGT-9")).thenReturn(Optional.of(agent));
        when(agents.findById(9L)).thenReturn(Optional.of(agent));
        when(agents.findByAgentStatusAndOnlineStatus("ENABLED", "ONLINE")).thenReturn(List.of(agent));
        Device device = new Device();
        device.setId(10L);
        device.setDeviceStatus("ACTIVE");
        device.setDeviceTypeCode("SMART_DISPLAY");
        when(devices.findByIds(List.of(10L))).thenReturn(List.of(device));
        when(capabilities.existsByDeviceIdAndCapabilityTypeAndCapabilityStatus(10L, "CAP_INFO_DISPLAY", "ENABLED")).thenReturn(true);
        when(resolver.resolve(eq(1L), eq(2L), anyMap())).thenReturn(Map.of());
        // 反馈/响应关联：按各自编号查
        when(assignments.findByCommandId(anyString())).thenAnswer(i ->
                i.getArgument(0).equals(assignment.getCommandId()) ? Optional.of(assignment) : Optional.empty());
        when(assignments.findByExecuteCommandId(anyString())).thenAnswer(i ->
                i.getArgument(0).equals(assignment.getExecuteCommandId()) ? Optional.of(assignment) : Optional.empty());
        return new TaskExecutionOrchestrator(tasks, plans, assignments, agents, devices, capabilities, events, exceptions,
                messaging, mock(BaselineDryRunLifecycle.class), mock(DryRunDeviceSelectionMapper.class), resolver);
    }

    @Test
    void acceptAndExecuteUseDifferentIdsAndFeedbackIsCorrelatedByTheExecuteId() throws Exception {
        TaskExecutionOrchestrator o = orchestrator();
        o.assignStep(1L, 2L, 1);
        ArgumentCaptor<String> acceptId = ArgumentCaptor.forClass(String.class);
        verify(messaging).requestTaskAcceptance(eq("AGT-9"), acceptId.capture(), eq(1L), eq(1), eq("CAP_INFO_DISPLAY"), anyMap());

        o.onTaskResponse("AGT-9", acceptId.getValue(), true, null);
        ArgumentCaptor<String> executeId = ArgumentCaptor.forClass(String.class);
        verify(messaging).executeCapability(eq("AGT-9"), executeId.capture(), eq(1L), eq(1), eq("CAP_INFO_DISPLAY"), eq(0), anyMap());

        assertNotEquals(acceptId.getValue(), executeId.getValue(), "承接与执行是不同逻辑消息，须各用独立指令编号");
        assertEquals(acceptId.getValue(), assignment.getCommandId());
        assertEquals(executeId.getValue(), assignment.getExecuteCommandId());
        assertTrue(executeId.getValue().length() <= 32, "须适配列宽32");
    }

    @Test
    void feedbackCarryingTheAcceptIdIsNotAcceptedAsExecutionFeedback() throws Exception {
        TaskExecutionOrchestrator o = orchestrator();
        o.assignStep(1L, 2L, 1);
        o.onTaskResponse("AGT-9", assignment.getCommandId(), true, null);
        assertThrows(BusinessException.class,
                () -> o.onExecutionFeedback("AGT-9", assignment.getCommandId(), 0, "SUCCESS", null, Map.of()));
    }

    @Test
    void retryKeepsTheExecuteIdAndBumpsTheAttemptNumber() throws Exception {
        TaskExecutionOrchestrator o = orchestrator();
        o.assignStep(1L, 2L, 1);
        o.onTaskResponse("AGT-9", assignment.getCommandId(), true, null);
        String executeId = assignment.getExecuteCommandId();

        o.onExecutionFeedback("AGT-9", executeId, 0, "FAILED", "DEVICE_ERROR", Map.of());

        assertEquals(1, assignment.getRetryCount());
        assertEquals(executeId, assignment.getExecuteCommandId(), "同一逻辑消息重试保持编号");
        verify(messaging).executeCapability(eq("AGT-9"), eq(executeId), eq(1L), eq(1), eq("CAP_INFO_DISPLAY"), eq(1), anyMap());
    }

    @Test
    void reassignmentAfterARejectionStartsNewLogicalMessages() throws Exception {
        TaskExecutionOrchestrator o = orchestrator();
        o.assignStep(1L, 2L, 1);
        String firstAccept = assignment.getCommandId();
        o.onTaskResponse("AGT-9", firstAccept, false, "DEVICE_BUSY");
        assertNull(assignment.getCommandId());
        assertNull(assignment.getExecuteCommandId());
    }

    @Test
    void legacyRowsWithoutAnExecuteIdAreStillCorrelatedByTheOldId() throws Exception {
        TaskExecutionOrchestrator o = orchestrator();
        assignment.setStepStatus("EXECUTING");
        assignment.setDeviceAgentId(9L);
        assignment.setCommandId("CMD-OLD");
        assignment.setExecuteCommandId(null);
        o.onExecutionFeedback("AGT-9", "CMD-OLD", 0, "FAILED", "X", Map.of());
        verify(events).append(eq(1L), eq("EXECUTION_FEEDBACK_RECEIVED"), any(), any(), anyString());
    }

    @Test
    void generatedIdsAreUniqueAndFitTheColumn() {
        Set<String> seen = new HashSet<>();
        for (int i = 0; i < 2000; i++) {
            String id = CommandIds.next();
            assertTrue(id.length() <= 32);
            assertTrue(seen.add(id), "指令编号重复: " + id);
        }
    }
}
