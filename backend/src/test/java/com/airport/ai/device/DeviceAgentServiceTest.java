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
    @Test
    void terminatedTaskReleasesAgentOnlyAfterIdleReport() {
        DeviceAgentMapper agents = mock(DeviceAgentMapper.class);
        DeviceMapper devices = mock(DeviceMapper.class);
        DeviceCommandMapper commands = mock(DeviceCommandMapper.class);
        com.airport.ai.task.TaskMapper tasks = mock(com.airport.ai.task.TaskMapper.class);
        TaskEventService taskEvents = mock(TaskEventService.class);
        DeviceAgent agent = new DeviceAgent();
        agent.setId(5L);
        agent.setAgentCode("AGT-5");
        agent.setDeviceId(5L);
        agent.setAgentStatus("ENABLED");
        agent.setOnlineStatus("ONLINE");
        agent.setWorkStatus("BUSY");
        agent.setCurrentTaskId(7L);
        agent.setCurrentStepSeq(1);
        Device device = new Device();
        device.setId(5L);
        when(agents.findByAgentCode("AGT-5")).thenReturn(Optional.of(agent));
        when(devices.findById(5L)).thenReturn(Optional.of(device));
        com.airport.ai.task.Task terminated = new com.airport.ai.task.Task();
        terminated.setStatus(com.airport.ai.task.TaskStatus.MANUAL_TERMINATED);
        when(tasks.findById(7L)).thenReturn(Optional.of(terminated));
        DeviceCommandRecord cancel = new DeviceCommandRecord();
        cancel.setCommandType("TASK_CANCEL");
        cancel.setCommandId("CMD-7");
        cancel.setTaskId(7L);
        cancel.setCommandStatus("SENT");
        when(commands.findRecentByAgentCode("AGT-5", 20)).thenReturn(java.util.List.of(cancel));
        when(commands.updateStatus("AGT-5", "CMD-7", "TASK_CANCEL", 0, "CONFIRMED_IDLE", null)).thenReturn(1);
        DeviceAgentService service = new DeviceAgentService(agents, devices, mock(OperationLogService.class),
                taskEvents, mock(DeviceEventService.class), mock(TaskExceptionService.class));
        org.springframework.test.util.ReflectionTestUtils.setField(service, "taskMapper", tasks);
        org.springframework.test.util.ReflectionTestUtils.setField(service, "commandMapper", commands);

        service.reportStatus("AGT-5", "ONLINE", "IDLE", null, null);

        assertEquals("IDLE", agent.getWorkStatus());
        assertNull(agent.getCurrentTaskId());
        assertNull(agent.getCurrentStepSeq());
        verify(commands).updateStatus("AGT-5", "CMD-7", "TASK_CANCEL", 0, "CONFIRMED_IDLE", null);
        verify(taskEvents).append(eq(7L), eq("TASK_CANCEL_CONFIRMED_IDLE"), eq("DEVICE"),
                isNull(), contains("AGT-5"));
    }
    @Test
    void unconfirmedCancelDoesNotReleaseAgentOnUnrelatedIdleReport() {
        DeviceAgentMapper agents = mock(DeviceAgentMapper.class);
        DeviceMapper devices = mock(DeviceMapper.class);
        DeviceCommandMapper commands = mock(DeviceCommandMapper.class);
        com.airport.ai.task.TaskMapper tasks = mock(com.airport.ai.task.TaskMapper.class);
        DeviceAgent agent = new DeviceAgent();
        agent.setId(5L);
        agent.setAgentCode("AGT-5");
        agent.setDeviceId(5L);
        agent.setAgentStatus("ENABLED");
        agent.setOnlineStatus("ONLINE");
        agent.setWorkStatus("BUSY");
        agent.setCurrentTaskId(7L);
        Device device = new Device();
        device.setId(5L);
        when(agents.findByAgentCode("AGT-5")).thenReturn(Optional.of(agent));
        when(devices.findById(5L)).thenReturn(Optional.of(device));
        com.airport.ai.task.Task terminated = new com.airport.ai.task.Task();
        terminated.setStatus(com.airport.ai.task.TaskStatus.MANUAL_TERMINATED);
        when(tasks.findById(7L)).thenReturn(Optional.of(terminated));
        when(commands.findRecentByAgentCode("AGT-5", 20)).thenReturn(java.util.List.of());

        DeviceAgentService service = new DeviceAgentService(agents, devices, mock(OperationLogService.class),
                mock(TaskEventService.class), mock(DeviceEventService.class), mock(TaskExceptionService.class));
        org.springframework.test.util.ReflectionTestUtils.setField(service, "taskMapper", tasks);
        org.springframework.test.util.ReflectionTestUtils.setField(service, "commandMapper", commands);
        service.reportStatus("AGT-5", "ONLINE", "IDLE", null, null);

        assertEquals("BUSY", agent.getWorkStatus());
        assertEquals(7L, agent.getCurrentTaskId());
    }}
