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

    @Test void partialAgentQueryFailureRecordsFailedAgentCodeAndBuildsWithSuccessfulAgents() throws Exception {
        DeviceAgentMapper agents = mock(DeviceAgentMapper.class);
        DeviceMapper devices = mock(DeviceMapper.class);
        DeviceCapabilityMapper capabilities = mock(DeviceCapabilityMapper.class);
        ContextSnapshotMapper snapshots = mock(ContextSnapshotMapper.class);

        DeviceAgent successAgent = new DeviceAgent();
        successAgent.setDeviceId(10L);
        successAgent.setAgentCode("AGT-SUCCESS");

        DeviceAgent failedAgent = new DeviceAgent();
        failedAgent.setDeviceId(999L);
        failedAgent.setAgentCode("AGT-FAIL");

        when(agents.findByAgentStatusAndOnlineStatus("ENABLED", "ONLINE"))
                .thenReturn(List.of(successAgent, failedAgent));

        Device successDevice = new Device();
        successDevice.setId(10L);
        successDevice.setDeviceCode("DEV-SUCCESS");
        successDevice.setDeviceStatus("ACTIVE");
        when(devices.findByIds(List.of(10L, 999L))).thenReturn(List.of(successDevice));

        DeviceCapability cap = new DeviceCapability();
        cap.setCapabilityType("CAP_SUCCESS");
        when(capabilities.findByDeviceIdAndCapabilityStatus(10L, "ENABLED")).thenReturn(List.of(cap));

        ContextSnapshotService service = new ContextSnapshotService(agents, devices, capabilities, snapshots);
        ContextSnapshot snapshot = service.buildSnapshot(100L, List.of("CAP_SUCCESS", "CAP_OTHER"));

        ObjectMapper mapper = new ObjectMapper();
        var agentViews = mapper.readTree(snapshot.getAgents());
        assertEquals(1, agentViews.size(), "快照仅由查询成功的代理构建");
        assertEquals("AGT-SUCCESS", agentViews.get(0).get("agentId").asText());

        var failedList = mapper.readTree(snapshot.getFailedAgentCodes());
        assertEquals(1, failedList.size(), "快照标注状态查询失败的代理清单");
        assertEquals("AGT-FAIL", failedList.get(0).asText());

        var coverage = mapper.readTree(snapshot.getCapabilityCoverage());
        assertEquals("[\"CAP_SUCCESS\"]", coverage.get("available").toString());
        assertEquals("[\"CAP_OTHER\"]", coverage.get("missing").toString());
    }

    @Test void faultInjectedAgentQueryFailureRecordsFailedCodeAndMaintainsConsistency() throws Exception {
        DeviceAgentMapper agents = mock(DeviceAgentMapper.class);
        DeviceMapper devices = mock(DeviceMapper.class);
        DeviceCapabilityMapper capabilities = mock(DeviceCapabilityMapper.class);
        ContextSnapshotMapper snapshots = mock(ContextSnapshotMapper.class);

        DeviceAgent agentA = new DeviceAgent();
        agentA.setDeviceId(1L);
        agentA.setAgentCode("AGT-A");

        DeviceAgent agentB = new DeviceAgent();
        agentB.setDeviceId(2L);
        agentB.setAgentCode("AGT-B");

        when(agents.findByAgentStatusAndOnlineStatus("ENABLED", "ONLINE"))
                .thenReturn(List.of(agentA, agentB));

        Device devA = new Device();
        devA.setId(1L);
        devA.setDeviceCode("DEV-A");
        devA.setDeviceStatus("ACTIVE");

        Device devB = new Device();
        devB.setId(2L);
        devB.setDeviceCode("DEV-B");
        devB.setDeviceStatus("ACTIVE");

        when(devices.findByIds(List.of(1L, 2L))).thenReturn(List.of(devA, devB));

        DeviceCapability capA = new DeviceCapability();
        capA.setCapabilityType("CAP_A");
        DeviceCapability capB = new DeviceCapability();
        capB.setCapabilityType("CAP_B");

        when(capabilities.findByDeviceIdAndCapabilityStatus(1L, "ENABLED")).thenReturn(List.of(capA));
        when(capabilities.findByDeviceIdAndCapabilityStatus(2L, "ENABLED")).thenReturn(List.of(capB));

        ContextSnapshotService service = new ContextSnapshotService(agents, devices, capabilities, snapshots);
        service.setFaultInjectedFailedAgentCodes("AGT-B");

        ContextSnapshot snapshot = service.buildSnapshot(200L, List.of("CAP_A", "CAP_B"));

        ObjectMapper mapper = new ObjectMapper();
        var agentViews = mapper.readTree(snapshot.getAgents());
        assertEquals(1, agentViews.size());
        assertEquals("AGT-A", agentViews.get(0).get("agentId").asText());

        var failedList = mapper.readTree(snapshot.getFailedAgentCodes());
        assertEquals(1, failedList.size());
        assertEquals("AGT-B", failedList.get(0).asText());

        var coverage = mapper.readTree(snapshot.getCapabilityCoverage());
        assertEquals("[\"CAP_A\"]", coverage.get("available").toString());
        assertEquals("[\"CAP_B\"]", coverage.get("missing").toString());
    }
}
