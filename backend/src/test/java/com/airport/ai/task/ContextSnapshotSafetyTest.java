package com.airport.ai.task;

import com.airport.ai.device.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import java.util.List;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class ContextSnapshotSafetyTest {
    @Test void excludesDisabledDeviceAndRetainsAgentWithUnknownCoordinates() throws Exception {
        DeviceAgentMapper agents = mock(DeviceAgentMapper.class);
        DeviceMapper devices = mock(DeviceMapper.class);
        DeviceCapabilityMapper capabilities = mock(DeviceCapabilityMapper.class);
        ContextSnapshotMapper snapshots = mock(ContextSnapshotMapper.class);
        DeviceAgent disabledAgent = new DeviceAgent();
        disabledAgent.setDeviceId(1L);
        disabledAgent.setAgentCode("disabled");
        DeviceAgent activeAgent = new DeviceAgent();
        activeAgent.setDeviceId(2L);
        activeAgent.setAgentCode("active");
        when(agents.findByAgentStatusAndOnlineStatus("ENABLED", "ONLINE"))
                .thenReturn(List.of(disabledAgent, activeAgent));
        Device disabled = new Device();
        disabled.setId(1L);
        disabled.setDeviceStatus("INACTIVE");
        Device active = new Device();
        active.setId(2L);
        active.setDeviceStatus("ACTIVE");
        when(devices.findByIds(List.of(1L, 2L))).thenReturn(List.of(disabled, active));
        when(capabilities.findByDeviceIdAndCapabilityStatus(2L, "ENABLED")).thenReturn(List.of());
        ContextSnapshotService service = new ContextSnapshotService(agents, devices, capabilities, snapshots);

        ContextSnapshot snapshot = service.buildSnapshot(11L, List.of());
        var agentViews = new ObjectMapper().readTree(snapshot.getAgents());
        assertEquals(1, agentViews.size());
        assertEquals("active", agentViews.get(0).get("agentId").asText());
        assertTrue(agentViews.get(0).get("location").get("x").isNull());
        verify(capabilities, never()).findByDeviceIdAndCapabilityStatus(1L, "ENABLED");
    }

    @Test void emptyPlanCannotPassValidationAndFreeze() {
        PlanValidationResult result = new PlanValidationService(mock(DeviceCapabilityMapper.class))
                .validate(List.of(), List.of());
        assertFalse(result.isAllPassed());
        assertEquals("FAIL", result.getStructureCheckResult());
    }
}
