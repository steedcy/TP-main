package com.airport.ai.device;

import com.airport.ai.auth.OperationLogService;
import com.airport.ai.auth.User;
import com.airport.ai.common.BusinessException;
import com.airport.ai.device.dto.CreateDeviceRequest;
import com.airport.ai.device.dto.DeviceView;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.springframework.context.ApplicationEventPublisher;

import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class DeviceRegistrationServiceTest {
    final DeviceService devices = mock(DeviceService.class);
    final DeviceMapper mapper = mock(DeviceMapper.class);
    final DeviceAgentMapper agents = mock(DeviceAgentMapper.class);
    final DeviceCredentialService credentials = mock(DeviceCredentialService.class);
    final ManagedSimulatorService simulators = mock(ManagedSimulatorService.class);
    final ApplicationEventPublisher events = mock(ApplicationEventPublisher.class);
    final DeviceRegistrationService service = new DeviceRegistrationService(devices, mapper, agents, credentials,
            simulators, events, mock(OperationLogService.class));
    final User operator = new User();

    Device device(boolean simulator) {
        Device d = new Device(); d.setId(1L); d.setDeviceCode("AUTO_1"); d.setIsSimulator(simulator);
        when(devices.getByCode("AUTO_1")).thenReturn(d);
        when(mapper.findByDeviceCodeForUpdate("AUTO_1")).thenReturn(Optional.of(d));
        return d;
    }

    @Test void createsTokenAndSchedulesSimulatorAfterRegistrationWithoutPlaintextInView() throws Exception {
        Device d = device(true);
        d.setDeviceTokenHash("hash"); d.setDeviceTokenCiphertext("encrypted");
        when(devices.create(any(), any())).thenReturn(d);
        when(simulators.allocateEndpoint("AUTO_1")).thenReturn("http://127.0.0.1:18100");
        CreateDeviceRequest request = new CreateDeviceRequest(); request.setDeviceCode("AUTO_1"); request.setIsSimulator(true);
        Device saved = service.create(request, operator);
        assertEquals("http://127.0.0.1:18100", request.getAccessEndpoint());
        assertEquals("device-token:AUTO_1", request.getAccessCredentialRef());
        verify(credentials).rotate("AUTO_1");
        verify(events).publishEvent(any(DeviceOnboardingRequestedEvent.class));
        assertEquals("PENDING", saved.getOnboardingStatus());
        String json = new ObjectMapper().findAndRegisterModules().writeValueAsString(DeviceView.from(saved));
        assertFalse(json.contains("encrypted")); assertFalse(json.contains("\"hash\""));
        assertTrue(json.contains("\"deviceTokenConfigured\":true"));
    }

    @Test void physicalDeviceGetsTokenWithoutStartingSimulator() {
        Device d = device(false); when(devices.create(any(), any())).thenReturn(d);
        CreateDeviceRequest request = new CreateDeviceRequest(); request.setIsSimulator(false);
        service.create(request, operator);
        verify(credentials).rotate("AUTO_1"); verifyNoInteractions(events, simulators);
    }

    @Test void busyDeviceRejectsRotationAndRestartWithoutChangingToken() {
        Device d = device(true);
        DeviceAgent agent = new DeviceAgent(); agent.setCurrentTaskId(99L);
        when(agents.findByDeviceId(d.getId())).thenReturn(Optional.of(agent));
        assertThrows(BusinessException.class, () -> service.rotate("AUTO_1", operator));
        assertThrows(BusinessException.class, () -> service.retry("AUTO_1", operator));
        verifyNoInteractions(credentials, events, simulators);
    }

    @Test void activeAssignmentAlsoRejectsRestartEvenIfAgentLooksIdle() {
        Device d = device(true);
        DeviceAgent agent = new DeviceAgent(); agent.setId(8L);
        when(agents.findByDeviceId(d.getId())).thenReturn(Optional.of(agent));
        when(agents.countActiveTaskAssignments(8L)).thenReturn(1L);
        assertThrows(BusinessException.class, () -> service.retry("AUTO_1", operator));
        verifyNoInteractions(credentials, events);
    }

    @Test void retryReusesTokenAndTakesExistingAgentOutOfSchedulingBeforeRestart() {
        Device d = device(true); d.setDeviceTokenCiphertext("encrypted");
        DeviceAgent agent = new DeviceAgent(); agent.setId(8L); agent.setOnlineStatus("ONLINE");
        when(agents.findByDeviceId(d.getId())).thenReturn(Optional.of(agent));
        when(agents.findByIdForUpdate(8L)).thenReturn(Optional.of(agent));
        service.retry("AUTO_1", operator);
        verify(credentials, never()).rotate(any());
        assertEquals("DISABLED", agent.getAgentStatus()); assertEquals("OFFLINE", agent.getOnlineStatus());
        verify(events).publishEvent(any(DeviceOnboardingRequestedEvent.class));
    }

    @Test void concurrentOnboardingAndArchivedAgentAreRejected() {
        Device d = device(true); d.setOnboardingStatus("CONNECTING");
        assertThrows(BusinessException.class, () -> service.retry("AUTO_1", operator));
        d.setOnboardingStatus("FAILED");
        DeviceAgent agent = new DeviceAgent(); agent.setAgentStatus("ARCHIVED");
        when(agents.findByDeviceId(d.getId())).thenReturn(Optional.of(agent));
        assertThrows(BusinessException.class, () -> service.retry("AUTO_1", operator));
        verifyNoInteractions(credentials, events);
    }
}
