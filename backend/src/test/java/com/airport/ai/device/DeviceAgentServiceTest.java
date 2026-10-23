package com.airport.ai.device;

import com.airport.ai.auth.OperationLogService;
import com.airport.ai.event.TaskEventService;
import com.airport.ai.task.TaskExceptionService;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class DeviceAgentServiceTest {

    @Test
    void statusReportStoresSnapshotAndRoutesOfflineRecovery() {
        DeviceAgentMapper agents = mock(DeviceAgentMapper.class);
        DeviceMapper devices = mock(DeviceMapper.class);
        DeviceEventService deviceEvents = mock(DeviceEventService.class);
        TaskEventService taskEvents = mock(TaskEventService.class);
        TaskExceptionService taskExceptions = mock(TaskExceptionService.class);
        DeviceAgent agent = new DeviceAgent();
        agent.setId(41L);
        agent.setAgentCode("AGT-41");
        agent.setDeviceId(41L);
        agent.setAgentStatus("ENABLED");
        agent.setOnlineStatus("OFFLINE");
        when(agents.findByAgentCode("AGT-41")).thenReturn(Optional.of(agent));
        Device device = new Device();
        device.setId(41L);
        device.setDeviceCode("SIM-DISPLAY-01");
        when(devices.findById(41L)).thenReturn(Optional.of(device));

        DeviceAgentService service = new DeviceAgentService(agents, devices, mock(OperationLogService.class),
                taskEvents, deviceEvents, taskExceptions);
        service.reportStatus("AGT-41", "ONLINE", "IDLE", new BigDecimal("12.5"), new BigDecimal("88.2"),
                "{\"displayStatus\":\"IDLE\"}");

        assertEquals("ONLINE", agent.getOnlineStatus());
        assertEquals("{\"displayStatus\":\"IDLE\"}", agent.getBusinessStatus());
        assertEquals(new BigDecimal("12.5"), device.getPositionX());
        assertEquals(new BigDecimal("88.2"), device.getPositionY());
        verify(deviceEvents).append(eq(41L), eq("AGENT_ONLINE_RECOVERED"), eq("SYSTEM"), isNull(), anyString());

        agent.setCurrentTaskId(900L);
        agent.setCurrentStepSeq(2);
        service.reportStatus("AGT-41", "OFFLINE", "BUSY", null, null, null);

        assertEquals("OFFLINE", agent.getOnlineStatus());
        verify(deviceEvents).append(eq(41L),eq("AGENT_OFFLINE_REPORTED"),eq("SYSTEM"),eq("DEVICE_REPORTED_OFFLINE"),anyString());
        verify(taskExceptions).handleAgentOffline(agent);
        verify(agents, times(2)).update(agent);
    }
}
