package com.airport.ai.task;

import com.airport.ai.baseline.BaselineDryRunLifecycle;
import com.airport.ai.baseline.DryRunDeviceSelectionMapper;
import com.airport.ai.device.DeviceAgentMapper;
import com.airport.ai.device.DeviceAgentMessagingService;
import com.airport.ai.device.DeviceCapabilityMapper;
import com.airport.ai.device.DeviceMapper;
import com.airport.ai.device.DeviceAgent;
import com.airport.ai.device.Device;
import com.airport.ai.event.TaskEventService;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class FlightPartialChannelExecutionTest {
    private final TaskMapper tasks = mock(TaskMapper.class);
    private final PlanVersionMapper plans = mock(PlanVersionMapper.class);
    private final TaskStepAssignmentMapper assignments = mock(TaskStepAssignmentMapper.class);
    private final DeviceAgentMapper agents = mock(DeviceAgentMapper.class);
    private final DeviceMapper devices = mock(DeviceMapper.class);
    private final DeviceCapabilityMapper capabilities = mock(DeviceCapabilityMapper.class);
    private final StepParameterResolver resolver = mock(StepParameterResolver.class);
    private final DeviceAgentMessagingService messaging = mock(DeviceAgentMessagingService.class);
    private final TaskEventService events = mock(TaskEventService.class);
    private final List<TaskStepAssignment> saved = new ArrayList<>();
    private final Map<Integer, TaskStepAssignment> byStep = new HashMap<>();

    @Test
    void unavailableChannelsAreMarkedUncoveredAfterAPreviouslyCompletedPublication() throws Exception {
        Task task = taskAndPlan();
        executor().startExecution(1L, 2L, 2);

        assertEquals(TaskStatus.COMPLETED, task.getStatus());
        assertEquals("COMPLETED", byStep.get(1).getStepStatus());
        assertEquals("SKIPPED", byStep.get(2).getStepStatus());
        assertEquals("FLIGHT_CHANNEL_UNAVAILABLE", byStep.get(2).getReasonCode());
        assertTrue(byStep.get(2).getOutputParams().contains("UNCOVERED"));
        assertEquals("SKIPPED", byStep.get(3).getStepStatus());
        verifyNoInteractions(messaging);
        verify(events, times(2)).append(eq(1L), eq("FLIGHT_CHANNEL_UNCOVERED"), eq("SYSTEM"),
                eq("FLIGHT_CHANNEL_UNAVAILABLE"), anyString());
    }

    @Test
    void allUnavailableChannelsCannotCompleteWithoutAnyPublishedResult() throws Exception {
        Task task = taskAndPlan();
        executor().startExecution(1L, 2L);

        assertEquals(TaskStatus.PENDING_MANUAL, task.getStatus());
        assertTrue(task.getFailureReason().contains("无任何已完成的航班信息发布渠道"));
        assertTrue(saved.stream().allMatch(a -> "SKIPPED".equals(a.getStepStatus())));
        verifyNoInteractions(messaging);
    }

    @Test
    void unavailableFirstChannelDoesNotBlockARealDisplayAcceptanceRequest() throws Exception {
        Task task = taskAndPlan();
        DeviceAgent displayAgent = new DeviceAgent();
        displayAgent.setId(9L);
        displayAgent.setAgentCode("DISPLAY-9");
        displayAgent.setDeviceId(10L);
        displayAgent.setOnlineStatus("ONLINE");
        Device display = new Device();
        display.setId(10L);
        display.setDeviceTypeCode("SIMULATOR");
        display.setSimulatedDeviceType("SMART_DISPLAY");
        when(agents.findByAgentStatusAndOnlineStatus("ENABLED", "ONLINE")).thenReturn(List.of(displayAgent));
        when(devices.findByIds(List.of(10L))).thenReturn(List.of(display));
        when(capabilities.existsByDeviceIdAndCapabilityTypeAndCapabilityStatus(
                10L, "CAP_INFO_DISPLAY", "ENABLED")).thenReturn(true);
        when(resolver.resolve(eq(1L), eq(2L), anyMap())).thenReturn(Map.of());

        executor().startExecution(1L, 2L);

        assertEquals("SKIPPED", byStep.get(1).getStepStatus());
        assertEquals("PENDING_ASSIGNMENT", byStep.get(2).getStepStatus());
        assertEquals(9L, byStep.get(2).getDeviceAgentId());
        assertEquals(TaskStatus.PENDING_ASSIGNMENT, task.getStatus());
        verify(messaging).requestTaskAcceptance(eq("DISPLAY-9"), anyString(), eq(1L), eq(2),
                eq("CAP_INFO_DISPLAY"), eq(Map.of()));
        verify(messaging, never()).executeCapability(anyString(), anyString(), anyLong(), anyInt(),
                anyString(), anyInt(), any());
    }

    private Task taskAndPlan() throws Exception {
        Task task = new Task();
        task.setId(1L);
        task.setTaskFamily("FLIGHT_CHANGE_RESPONSE");
        task.setStatus(TaskStatus.PENDING_ASSIGNMENT);
        when(tasks.findById(1L)).thenReturn(Optional.of(task));
        PlanVersion plan = new PlanVersion();
        plan.setId(2L);
        plan.setTaskId(1L);
        plan.setPlanSteps(new ObjectMapper().writeValueAsString(List.of(
                Map.of("stepSeq", 1, "capabilityType", "CAP_FLIGHT_UPDATE"),
                Map.of("stepSeq", 2, "capabilityType", "CAP_INFO_DISPLAY"),
                Map.of("stepSeq", 3, "capabilityType", "CAP_NOTIFICATION"))));
        when(plans.findById(2L)).thenReturn(Optional.of(plan));
        when(assignments.insert(any())).thenAnswer(invocation -> {
            TaskStepAssignment assignment = invocation.getArgument(0);
            saved.add(assignment);
            byStep.put(assignment.getStepSeq(), assignment);
            return 1;
        });
        when(assignments.findByPlanVersionIdAndStepSeq(eq(2L), anyInt()))
                .thenAnswer(invocation -> Optional.ofNullable(byStep.get(invocation.getArgument(1))));
        when(assignments.findByPlanVersionIdOrderByStepSeqAsc(2L)).thenAnswer(invocation -> saved);
        when(agents.findByAgentStatusAndOnlineStatus("ENABLED", "ONLINE")).thenReturn(List.of());
        return task;
    }

    private TaskExecutionOrchestrator executor() {
        return new TaskExecutionOrchestrator(tasks, plans, assignments, agents, devices,
                capabilities, events, mock(TaskExceptionService.class), messaging,
                mock(BaselineDryRunLifecycle.class), mock(DryRunDeviceSelectionMapper.class),
                resolver);
    }
}
