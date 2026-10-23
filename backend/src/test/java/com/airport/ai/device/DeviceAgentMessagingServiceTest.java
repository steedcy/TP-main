package com.airport.ai.device;

import com.airport.ai.common.BusinessException;
import com.airport.ai.task.Task;
import com.airport.ai.task.TaskMapper;
import com.airport.ai.devicetype.DeviceTypeCapabilityService;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.HashMap;
import java.util.Map;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class DeviceAgentMessagingServiceTest {
    private DeviceAgentMapper agents;
    private DeviceMapper devices;
    private DeviceCommandMapper commands;
    private DeviceCapabilityMapper capabilities;
    private TaskMapper tasks;
    private DeviceAdapterClient adapter;
    private DeviceTypeCapabilityService typeCapabilities;
    private DeviceAgentMessagingService service;
    private final Map<String, DeviceCommandRecord> records = new HashMap<>();

    @BeforeEach
    void setUp() {
        agents = mock(DeviceAgentMapper.class);
        devices = mock(DeviceMapper.class);
        commands = mock(DeviceCommandMapper.class);
        capabilities = mock(DeviceCapabilityMapper.class);
        tasks = mock(TaskMapper.class);
        adapter = mock(DeviceAdapterClient.class);
        typeCapabilities = mock(DeviceTypeCapabilityService.class);

        DeviceAgent agent = new DeviceAgent();
        agent.setAgentCode("AGT-41");
        agent.setDeviceId(41L);
        agent.setAgentStatus("ENABLED");
        agent.setOnlineStatus("ONLINE");
        when(agents.findByAgentCode("AGT-41")).thenReturn(Optional.of(agent));

        Device device = new Device();
        device.setId(41L);
        device.setDeviceCode("SIM-DISPLAY-01");
        device.setDeviceTypeCode("SIMULATOR");
        device.setSimulatedDeviceType("SMART_DISPLAY");
        when(devices.findById(41L)).thenReturn(Optional.of(device));
        when(capabilities.existsByDeviceIdAndCapabilityTypeAndCapabilityStatus(41L, "CAP_INFO_DISPLAY", "ENABLED"))
                .thenReturn(true);
        DeviceCapability configured = new DeviceCapability();
        configured.setCapabilityType("CAP_INFO_DISPLAY");
        configured.setInputParams("[{\"name\":\"contentType\",\"type\":\"String\",\"required\":true},{\"name\":\"contentData\",\"type\":\"String\",\"required\":true}]");
        when(capabilities.findByDeviceIdAndCapabilityStatus(41L,"ENABLED")).thenReturn(java.util.List.of(configured));
        when(typeCapabilities.isCapabilityTypeSupported("SIMULATOR", "SMART_DISPLAY", "CAP_INFO_DISPLAY"))
                .thenReturn(true);

        Task task = new Task();
        task.setId(900L);
        task.setTaskCode("TASK-900");
        when(tasks.findById(900L)).thenReturn(Optional.of(task));

        when(commands.insertIfAbsent(any())).thenAnswer(invocation -> {
            DeviceCommandRecord record = invocation.getArgument(0);
            String key = key(record.getAgentCode(), record.getCommandId(), record.getCommandType(), record.getAttemptNo());
            if (records.containsKey(key)) return 0;
            records.put(key, record);
            return 1;
        });
        when(commands.findByKey(anyString(), anyString(), anyString(), anyInt())).thenAnswer(invocation ->
                Optional.ofNullable(records.get(key(invocation.getArgument(0), invocation.getArgument(1),
                        invocation.getArgument(2), invocation.getArgument(3)))));
        when(commands.updateStatus(anyString(), anyString(), anyString(), anyInt(), anyString(), any()))
                .thenAnswer(invocation -> {
                    DeviceCommandRecord record = records.get(key(invocation.getArgument(0), invocation.getArgument(1),
                            invocation.getArgument(2), invocation.getArgument(3)));
                    if (record != null) record.setCommandStatus(invocation.getArgument(4));
                    return record == null ? 0 : 1;
                });

        service = new DeviceAgentMessagingService(agents, devices, commands, capabilities, tasks, adapter, 60,
                new ObjectMapper().findAndRegisterModules(), typeCapabilities);
    }

    @Test
    void persistsAndSendsCommandOnceWhenSameCommandIsReplayed() {
        service.requestTaskAcceptance("AGT-41", "CMD-41", 900L, 1, "CAP_INFO_DISPLAY",
                Map.of("contentType", "TEXT", "contentData", "Gate A05"));
        DeviceAgent occupiedAgent = agents.findByAgentCode("AGT-41").orElseThrow();
        occupiedAgent.setWorkStatus("BUSY");
        occupiedAgent.setCurrentTaskId(900L);
        service.requestTaskAcceptance("AGT-41", "CMD-41", 900L, 1, "CAP_INFO_DISPLAY",
                Map.of("contentType", "TEXT", "contentData", "Gate A05"));

        verify(adapter, times(1)).sendCommand(argThat(device -> "SIM-DISPLAY-01".equals(device.getDeviceCode())),
                eq("AGT-41"), argThat(command ->
                "CMD-41".equals(command.getCommandId()) && "TASK_ACCEPT".equals(command.getCommandType())
                        && "TASK-900".equals(command.getTaskId())));
        assertEquals("SENT", records.get(key("AGT-41", "CMD-41", "TASK_ACCEPT", 0)).getCommandStatus());
    }

    @Test
    void refusesCommandIdReuseWithDifferentBusinessPayload() {
        service.requestTaskAcceptance("AGT-41", "CMD-42", 900L, 1, "CAP_INFO_DISPLAY",
                Map.of("contentType", "TEXT", "contentData", "Gate A05"));

        assertThrows(BusinessException.class, () -> service.requestTaskAcceptance("AGT-41", "CMD-42", 900L,
                1, "CAP_INFO_DISPLAY", Map.of("contentType", "TEXT", "contentData", "Gate B02")));
        verify(adapter, times(1)).sendCommand(any(), anyString(), any());
    }

    @Test
    void blocksMotionSafetyFieldsBeforePersistenceOrDownlink() {
        BusinessException error = assertThrows(BusinessException.class, () -> service.requestTaskAcceptance("AGT-41",
                "CMD-43", 900L, 1, "CAP_INFO_DISPLAY", Map.of("speedLimit", 2)));

        assertEquals(4106, error.getErrorCode().getCode());
        verify(commands, never()).insertIfAbsent(any());
        verify(adapter, never()).sendCommand(any(), anyString(), any());
    }

    private static String key(String agent, String command, String type, Integer attempt) {
        return agent + "/" + command + "/" + type + "/" + attempt;
    }

}
