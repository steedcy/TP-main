package com.airport.ai.device;

import com.airport.ai.device.dto.SimulatorHealthResponse;
import org.junit.jupiter.api.Test;
import org.springframework.boot.web.client.RestTemplateBuilder;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpMethod;
import org.springframework.http.ResponseEntity;
import org.springframework.web.client.RestTemplate;

import java.math.BigDecimal;
import java.net.URI;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class DeviceAdapterClientTest {

    @Test
    void healthHandshakeUsesDeviceBearerTokenAndValidatesNonceAndSimulatorType() {
        RestTemplateBuilder builder = mock(RestTemplateBuilder.class);
        RestTemplate restTemplate = mock(RestTemplate.class);
        DeviceCredentialService credentials = mock(DeviceCredentialService.class);
        when(builder.setConnectTimeout(any(Duration.class))).thenReturn(builder);
        when(builder.setReadTimeout(any(Duration.class))).thenReturn(builder);
        when(builder.build()).thenReturn(restTemplate);
        when(credentials.tokenFor(any())).thenReturn("runtime-token");
        when(restTemplate.exchange(any(URI.class), eq(HttpMethod.GET), any(HttpEntity.class),
                eq(SimulatorHealthResponse.class))).thenAnswer(invocation -> {
            URI uri = invocation.getArgument(0);
            HttpEntity<?> request = invocation.getArgument(2);
            assertEquals("Bearer runtime-token", request.getHeaders().getFirst("Authorization"));
            assertEquals("/device-api/v1/health", uri.getPath());
            String nonce = URLDecoder.decode(uri.getRawQuery().substring("nonce=".length()), StandardCharsets.UTF_8);
            SimulatorHealthResponse response = new SimulatorHealthResponse();
            response.setProtocolVersion("1.0");
            response.setNonce(nonce);
            response.setDeviceCode("SIM-DISPLAY-01");
            response.setSimulatedDeviceType("SMART_DISPLAY");
            response.setOnlineStatus("ONLINE");
            response.setWorkStatus("IDLE");
            response.setCapabilities(List.of("CAP_INFO_DISPLAY"));
            SimulatorHealthResponse.Location location = new SimulatorHealthResponse.Location();
            location.setX(new BigDecimal("12.5"));
            location.setY(new BigDecimal("88.2"));
            response.setLocation(location);
            response.setReportedAt("2026-10-13T05:00:00+08:00");
            return ResponseEntity.ok(response);
        });
        DeviceAdapterClient client = new DeviceAdapterClient(builder, credentials, 2000, 3000,
                "http://platform.example");
        Device device = new Device();
        device.setDeviceCode("SIM-DISPLAY-01");
        device.setIsSimulator(true);
        device.setSimulatedDeviceType("SMART_DISPLAY");
        device.setAccessEndpoint("http://127.0.0.1:9001");

        SimulatorHealthResponse response = client.testConnection(device);

        assertEquals("SIM-DISPLAY-01", response.getDeviceCode());
        verify(restTemplate).exchange(any(URI.class), eq(HttpMethod.GET), any(HttpEntity.class),
                eq(SimulatorHealthResponse.class));
    }

    @Test
    void rejectsEndpointWithEmbeddedCredentials() {
        RestTemplateBuilder builder = mock(RestTemplateBuilder.class);
        when(builder.setConnectTimeout(any(Duration.class))).thenReturn(builder);
        when(builder.setReadTimeout(any(Duration.class))).thenReturn(builder);
        DeviceAdapterClient client = new DeviceAdapterClient(builder, mock(DeviceCredentialService.class),
                2000, 3000, "http://platform.example");
        Device device = new Device();
        device.setDeviceCode("SIM-DISPLAY-01");
        device.setAccessEndpoint("http://user:secret@127.0.0.1:9001");

        assertThrows(DeviceAdapterException.class, () -> client.testConnection(device));
    }
}
