package com.airport.ai.situation;

import com.airport.ai.common.PageResult;
import com.airport.ai.device.Device;
import com.airport.ai.device.DeviceAgent;
import com.airport.ai.device.DeviceAgentService;
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
        device.setDeviceCode("SIM-1");
        device.setDeviceName("航显仿真器");
        device.setDeviceTypeCode("SIMULATOR");
        device.setIsSimulator(true);
        device.setSimulatedDeviceType("SMART_DISPLAY");
        device.setPositionX(new BigDecimal("120.5"));
        device.setPositionY(new BigDecimal("88.2"));
        device.setAreaCode("T2-B");
        when(service.list(null, null, 1, 100)).thenReturn(new PageResult<>(List.of(agent), 1, 1, 100));
        when(service.getDeviceOf(agent)).thenReturn(device);

        var response = new SituationController(service).snapshot();
        var marker = response.getData().agents().get(0);
        assertEquals("SIM-1", marker.deviceCode());
        assertEquals("SMART_DISPLAY", marker.simulatedDeviceType());
        assertEquals("ONLINE", marker.onlineStatus());
        assertEquals(new BigDecimal("120.5"), marker.location().x());
        assertEquals(22L, marker.currentTaskId());
    }
}
