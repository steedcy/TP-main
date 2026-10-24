package com.airport.ai.situation;

import com.airport.ai.common.PageResult;
import com.airport.ai.device.Device;
import com.airport.ai.device.DeviceAgent;
import com.airport.ai.device.DeviceAgentService;
import com.airport.ai.device.DeviceCapability;
import com.airport.ai.device.DeviceCapabilityMapper;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class SituationControllerTest {
    @Test
    void snapshotIncludesLatestDeviceLocationAndAgentState() {
        DeviceAgentService service = mock(DeviceAgentService.class);
        DeviceAgent agent = new DeviceAgent();
        agent.setAgentCode("AGENT-1");
        agent.setAgentStatus("ENABLED");
        agent.setOnlineStatus("ONLINE");
        agent.setWorkStatus("BUSY");
        agent.setCurrentTaskId(22L);
        Device device = new Device();
        device.setId(3L);
        device.setDeviceCode("SIM-1");
        device.setDeviceName("航显仿真器");
        device.setDeviceTypeCode("SIMULATOR");
        device.setIsSimulator(true);
        device.setSimulatedDeviceType("SMART_DISPLAY");
        device.setPositionX(new BigDecimal("120.5"));
        device.setPositionY(new BigDecimal("88.2"));
        device.setAreaCode("T2-B");
        when(service.list("ENABLED", null, 1, 100)).thenReturn(new PageResult<>(List.of(agent), 1, 1, 100));
        when(service.getDeviceOf(agent)).thenReturn(device);
        DeviceCapabilityMapper capabilities = mock(DeviceCapabilityMapper.class);
        DeviceCapability display = new DeviceCapability();
        display.setCapabilityType("CAP_INFO_DISPLAY");
        when(capabilities.findByDeviceIdAndCapabilityStatus(3L, "ENABLED")).thenReturn(List.of(display));

        var response = new SituationController(service, capabilities).snapshot();
        var marker = response.getData().agents().get(0);
        assertEquals("SIM-1", marker.deviceCode());
        assertEquals("SMART_DISPLAY", marker.simulatedDeviceType());
        assertEquals("ONLINE", marker.onlineStatus());
        assertEquals(new BigDecimal("120.5"), marker.location().x());
        assertEquals(22L, marker.currentTaskId());
        assertEquals(List.of("CAP_INFO_DISPLAY"), marker.capabilityTypes());
        verify(service).list("ENABLED", null, 1, 100);
    }
}
