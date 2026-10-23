package com.airport.ai.device;

import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class DeviceCredentialServiceTest {

    @Test
    void rotatesStoresOnlyHashAndCiphertextAndAuthenticatesTheBoundDevice() {
        DeviceMapper devices = mock(DeviceMapper.class);
        DeviceAgentMapper agents = mock(DeviceAgentMapper.class);
        Device device = new Device();
        device.setId(41L);
        device.setDeviceCode("SIM-DISPLAY-01");
        when(devices.findByDeviceCode("SIM-DISPLAY-01")).thenReturn(Optional.of(device));
        when(devices.findById(41L)).thenReturn(Optional.of(device));
        DeviceAgent agent = new DeviceAgent();
        agent.setDeviceId(41L);
        when(agents.findByAgentCode("AGT-41")).thenReturn(Optional.of(agent));

        DeviceCredentialService service = new DeviceCredentialService(devices, agents,
                "test-only-key-with-at-least-32-characters");
        var issued = service.rotate("SIM-DISPLAY-01");

        ArgumentCaptor<String> hash = ArgumentCaptor.forClass(String.class);
        ArgumentCaptor<String> ciphertext = ArgumentCaptor.forClass(String.class);
        verify(devices).updateDeviceToken(eq(41L), hash.capture(), ciphertext.capture(), any());
        assertNotEquals(issued.token(), hash.getValue());
        assertNotEquals(issued.token(), ciphertext.getValue());
        assertFalse(ciphertext.getValue().contains(issued.token()));

        device.setDeviceTokenHash(hash.getValue());
        device.setDeviceTokenCiphertext(ciphertext.getValue());
        assertTrue(service.matchesDeviceCode("SIM-DISPLAY-01", issued.token()));
        assertTrue(service.matchesAgentCode("AGT-41", issued.token()));
        assertFalse(service.matchesAgentCode("AGT-41", "wrong-token"));
        assertEquals(issued.token(), service.tokenFor(device));
    }

    @Test
    void refusesToIssueTokenWithoutEncryptionKey() {
        DeviceMapper devices = mock(DeviceMapper.class);
        DeviceAgentMapper agents = mock(DeviceAgentMapper.class);
        Device device = new Device();
        device.setId(41L);
        when(devices.findByDeviceCode("SIM-DISPLAY-01")).thenReturn(Optional.of(device));
        DeviceCredentialService service = new DeviceCredentialService(devices, agents, "");

        var error = assertThrows(com.airport.ai.common.BusinessException.class,
                () -> service.rotate("SIM-DISPLAY-01"));
        assertEquals(4210, error.getErrorCode().getCode());
        verify(devices, never()).updateDeviceToken(anyLong(), anyString(), anyString(), any());
    }
}
