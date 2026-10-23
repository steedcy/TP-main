package com.airport.ai.device;

import com.airport.ai.auth.CurrentUser;
import com.airport.ai.auth.OperationLogService;
import com.airport.ai.auth.User;
import com.airport.ai.common.BusinessException;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.Map;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class SimulatorManagementControllerTest {
    private final DeviceService deviceService = mock(DeviceService.class);
    private final DeviceAgentMapper agentMapper = mock(DeviceAgentMapper.class);
    private final DeviceEventService eventService = mock(DeviceEventService.class);
    private final DeviceCommandMapper commandMapper = mock(DeviceCommandMapper.class);
    private final DeviceAdapterClient adapterClient = mock(DeviceAdapterClient.class);
    private final CurrentUser currentUser = mock(CurrentUser.class);
    private final OperationLogService operationLogService = mock(OperationLogService.class);
    private SimulatorManagementController controller;
    private Device device;
    private DeviceAgent agent;

    @BeforeEach
    void setUp() {
        controller = new SimulatorManagementController(deviceService, agentMapper, eventService, commandMapper,
                adapterClient, currentUser, operationLogService, new ObjectMapper());
        device = new Device();
        device.setId(4L);
        device.setDeviceCode("SIM_TEST");
        device.setDeviceName("测试仿真器");
        device.setDeviceTypeCode("SIMULATOR");
        device.setIsSimulator(true);
        device.setSimulatedDeviceType("BAGGAGE_SCANNER");
        agent = new DeviceAgent();
        agent.setId(8L);
        agent.setAgentCode("AGENT_TEST");
        agent.setDeviceId(4L);
        when(deviceService.getByCode("SIM_TEST")).thenReturn(device);
        when(agentMapper.findByDeviceId(4L)).thenReturn(Optional.of(agent));
        User user = new User();
        user.setId(1L);
        user.setUsername("config-admin");
        user.setRole("CONFIG_ADMIN");
        when(currentUser.get()).thenReturn(user);
    }

    @Test
    void scenarioControlUsesDeviceAdapterAndWritesEventAndAudit() {
        var response = controller.scenario("SIM_TEST", Map.of("scenarioResult", "NO_OBJECT"));
        assertEquals("NO_OBJECT", response.getData().get("scenarioResult"));
        verify(adapterClient).setSimulatorScenario(device, "NO_OBJECT");
        verify(eventService).append(eq(8L), eq("SIMULATOR_SCENARIO_CHANGED"), eq("OPERATOR"), isNull(), contains("NO_OBJECT"));
        verify(operationLogService).record(eq(1L), eq("config-admin"), eq("CONFIG_ADMIN"),
                eq("SIMULATOR_SCENARIO_CHANGED"), eq("SIM_TEST"), eq("SUCCESS"), isNull(), anyMap());
    }

    @Test
    void scenarioControlRejectsOutcomeOutsideDeviceProfile() {
        assertThrows(BusinessException.class, () -> controller.scenario("SIM_TEST", Map.of("scenarioResult", "LOST_TARGET")));
        verifyNoInteractions(adapterClient);
    }

    @Test
    void onlineControlRoutesPauseAndResumeToSimulator() {
        controller.online("SIM_TEST", Map.of("onlineStatus", "OFFLINE"));
        controller.online("SIM_TEST", Map.of("onlineStatus", "ONLINE"));
        verify(adapterClient).setSimulatorOnline(device, false);
        verify(adapterClient).setSimulatorOnline(device, true);
    }
}
