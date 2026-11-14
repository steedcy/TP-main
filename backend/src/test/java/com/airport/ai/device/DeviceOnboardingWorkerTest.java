package com.airport.ai.device;

import com.airport.ai.auth.User;
import org.junit.jupiter.api.Test;

import java.time.LocalDateTime;
import java.util.Optional;

import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class DeviceOnboardingWorkerTest {
    final DeviceService devices = mock(DeviceService.class);
    final DeviceMapper mapper = mock(DeviceMapper.class);
    final DeviceAgentMapper agents = mock(DeviceAgentMapper.class);
    final DeviceCredentialService credentials = mock(DeviceCredentialService.class);
    final ManagedSimulatorService simulators = mock(ManagedSimulatorService.class);
    final DeviceOnboardingWorker worker = new DeviceOnboardingWorker(devices, mapper, agents, credentials, simulators);
    final User user = new User();

    Device prepare() {
        Device d = new Device(); d.setId(1L); d.setDeviceCode("AUTO"); d.setIsSimulator(true);
        d.setConnectionTestStatus("PASSED");
        when(devices.getByCode("AUTO")).thenReturn(d);
        when(devices.testConnectionByCode("AUTO", user)).thenReturn(d);
        when(credentials.tokenFor(d)).thenReturn("test-token");
        when(simulators.isAlive("AUTO")).thenReturn(true);
        return d;
    }

    @Test void onlyMarksReadyAfterHandshakeBindingAndNewHeartbeat() {
        Device d = prepare();
        DeviceAgent agent = new DeviceAgent(); agent.setId(5L);
        when(devices.createAgentByCode("AUTO", user)).thenReturn(agent);
        when(agents.findById(5L)).thenAnswer(call -> {
            agent.setOnlineStatus("ONLINE"); agent.setLastReportedAt(LocalDateTime.now()); return Optional.of(agent);
        });
        worker.onboard(new DeviceOnboardingRequestedEvent("AUTO", user));
        var order = inOrder(simulators, devices, mapper);
        order.verify(simulators).restart(d, "test-token");
        order.verify(devices).checkConnectionReadiness(d);
        order.verify(devices).testConnectionByCode("AUTO", user);
        order.verify(devices).createAgentByCode("AUTO", user);
        order.verify(mapper).updateOnboarding(eq(1L), eq("READY"), anyString());
    }

    @Test void startupFailureIsSavedAndNeverCreatesAnAgent() {
        prepare();
        doThrow(new IllegalStateException("port occupied")).when(simulators).restart(any(), anyString());
        worker.onboard(new DeviceOnboardingRequestedEvent("AUTO", user));
        verify(mapper).updateOnboarding(1L, "FAILED", "port occupied");
        verify(devices, never()).createAgentByCode(any(), any());
    }

    @Test void failedFinalConnectionTestNeverCreatesAnAgent() {
        Device d = prepare(); d.setConnectionTestStatus("FAILED"); d.setConnectionTestResult("identity mismatch");
        worker.onboard(new DeviceOnboardingRequestedEvent("AUTO", user));
        verify(mapper).updateOnboarding(1L, "FAILED", "identity mismatch");
        verify(devices, never()).createAgentByCode(any(), any());
    }
}
