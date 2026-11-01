package com.airport.ai.task;

import com.airport.ai.device.*;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.Mockito.*;

/** DEF-S3-031 / SRS_F011.R01：上下文为每个代理给出可用时间；忙碌代理按进行中步骤的下发时刻+步骤超时预测。 */
class ContextAvailabilityF011Test {
    private final DeviceAgentMapper agents = mock(DeviceAgentMapper.class);
    private final DeviceMapper devices = mock(DeviceMapper.class);
    private final DeviceCapabilityMapper capabilities = mock(DeviceCapabilityMapper.class);
    private final TaskStepAssignmentMapper assignments = mock(TaskStepAssignmentMapper.class);
    private final PlanVersionMapper plans = mock(PlanVersionMapper.class);
    private final ContextSnapshotService service =
            new ContextSnapshotService(agents, devices, capabilities, mock(ContextSnapshotMapper.class));

    ContextAvailabilityF011Test() {
        ReflectionTestUtils.setField(service, "assignmentMapper", assignments);
        ReflectionTestUtils.setField(service, "planVersionMapper", plans);
        Device device = new Device();
        device.setId(1L);
        device.setDeviceStatus("ACTIVE");
        when(devices.findByIds(List.of(1L))).thenReturn(List.of(device));
        when(capabilities.findByDeviceIdAndCapabilityStatus(1L, "ENABLED")).thenReturn(List.of());
    }

    private JsonNode view(String workStatus) throws Exception {
        DeviceAgent agent = new DeviceAgent();
        agent.setId(5L);
        agent.setAgentCode("AGT-5");
        agent.setDeviceId(1L);
        agent.setOnlineStatus("ONLINE");
        agent.setWorkStatus(workStatus);
        when(agents.findByAgentStatusAndOnlineStatus("ENABLED", "ONLINE")).thenReturn(List.of(agent));
        return new ObjectMapper().readTree(service.buildSnapshot(1L, List.of()).getAgents()).get(0);
    }

    private TaskStepAssignment executing(LocalDateTime dispatchedAt, int stepSeq) {
        TaskStepAssignment a = new TaskStepAssignment();
        a.setPlanVersionId(9L);
        a.setStepSeq(stepSeq);
        a.setStepStatus("EXECUTING");
        a.setDispatchedAt(dispatchedAt);
        return a;
    }

    private void planWithTimeouts(String stepsJson) {
        PlanVersion plan = new PlanVersion();
        plan.setPlanSteps(stepsJson);
        when(plans.findById(9L)).thenReturn(Optional.of(plan));
    }

    @Test
    void idleAgentIsAvailableNow() throws Exception {
        LocalDateTime before = LocalDateTime.now();
        JsonNode v = view("IDLE");
        LocalDateTime at = LocalDateTime.parse(v.get("availableUntil").asText());
        assertFalse(at.isBefore(before.minusSeconds(1)));
        assertFalse(at.isAfter(LocalDateTime.now().plusSeconds(1)));
    }

    @Test
    void busyAgentIsAvailableAtDispatchPlusTheStepTimeout() throws Exception {
        LocalDateTime dispatched = LocalDateTime.now().minusSeconds(5);
        planWithTimeouts("[{\"stepSeq\":1,\"stepTimeout\":120}]");
        when(assignments.findActiveByAgentId(5L)).thenReturn(List.of(executing(dispatched, 1)));
        JsonNode v = view("BUSY");
        assertEquals("BUSY", v.get("workload").asText());
        assertEquals(dispatched.plusSeconds(120), LocalDateTime.parse(v.get("availableUntil").asText()));
    }

    @Test
    void stepWithoutAnExplicitTimeoutUsesTheDefault() throws Exception {
        LocalDateTime dispatched = LocalDateTime.now().minusSeconds(5);
        planWithTimeouts("[{\"stepSeq\":1}]");
        when(assignments.findActiveByAgentId(5L)).thenReturn(List.of(executing(dispatched, 1)));
        assertEquals(dispatched.plusSeconds(60), LocalDateTime.parse(view("BUSY").get("availableUntil").asText()));
    }

    @Test
    void overdueStepIsClampedToNowNotThePast() throws Exception {
        planWithTimeouts("[{\"stepSeq\":1,\"stepTimeout\":30}]");
        when(assignments.findActiveByAgentId(5L)).thenReturn(List.of(executing(LocalDateTime.now().minusMinutes(10), 1)));
        LocalDateTime before = LocalDateTime.now().minusSeconds(1);
        LocalDateTime at = LocalDateTime.parse(view("BUSY").get("availableUntil").asText());
        assertFalse(at.isBefore(before), "已超过预计时间时取当前时刻，不给出过去的时间");
    }

    @Test
    void latestOfSeveralActiveStepsWins() throws Exception {
        LocalDateTime now = LocalDateTime.now();
        planWithTimeouts("[{\"stepSeq\":1,\"stepTimeout\":30},{\"stepSeq\":2,\"stepTimeout\":200}]");
        when(assignments.findActiveByAgentId(5L)).thenReturn(List.of(
                executing(now.minusSeconds(5), 1), executing(now.minusSeconds(5), 2)));
        assertEquals(now.minusSeconds(5).plusSeconds(200), LocalDateTime.parse(view("BUSY").get("availableUntil").asText()));
    }

    @Test
    void busyAgentWithoutAnExecutingStepHasNoPredictionRatherThanAMadeUpOne() throws Exception {
        when(assignments.findActiveByAgentId(anyLong())).thenReturn(List.of());
        assertTrue(view("BUSY").get("availableUntil").isNull());
        TaskStepAssignment pending = executing(null, 1);
        pending.setStepStatus("PENDING_ASSIGNMENT");
        when(assignments.findActiveByAgentId(5L)).thenReturn(List.of(pending));
        assertTrue(view("BUSY").get("availableUntil").isNull());
    }

    @Test
    void unreadablePlanFallsBackToTheDefaultTimeout() throws Exception {
        LocalDateTime dispatched = LocalDateTime.now().minusSeconds(5);
        when(plans.findById(9L)).thenReturn(Optional.empty());
        when(assignments.findActiveByAgentId(5L)).thenReturn(List.of(executing(dispatched, 1)));
        assertEquals(dispatched.plusSeconds(60), LocalDateTime.parse(view("BUSY").get("availableUntil").asText()));
    }
}
