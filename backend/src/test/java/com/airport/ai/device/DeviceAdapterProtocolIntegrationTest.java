package com.airport.ai.device;

import com.airport.ai.device.dto.DeviceCommandRequest;
import com.airport.ai.device.dto.SimulatorHealthResponse;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.boot.web.client.RestTemplateBuilder;

import java.io.IOException;
import java.math.BigDecimal;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

/** Wire-level smoke test against a tiny local fake runtime; the production simulator arrives in P2. */
class DeviceAdapterProtocolIntegrationTest {
    private final ObjectMapper objectMapper = new ObjectMapper().findAndRegisterModules();
    private final List<String> requests = new ArrayList<>();
    private HttpServer server;
    private Device device;
    private DeviceAdapterClient client;

    @BeforeEach
    void startFakeRuntime() throws IOException {
        server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/device-api/v1", exchange -> {
            try {
                String path = exchange.getRequestURI().getPath();
                String auth = exchange.getRequestHeaders().getFirst("Authorization");
                requests.add(exchange.getRequestMethod() + " " + path + " " + auth);
                if (path.equals("/device-api/v1/health")) {
                    String nonce = exchange.getRequestURI().getRawQuery().substring("nonce=".length());
                    String body = "{\"protocolVersion\":\"1.0\",\"nonce\":\"" + nonce
                            + "\",\"deviceCode\":\"SIM-DISPLAY-01\",\"simulatedDeviceType\":\"SMART_DISPLAY\","
                            + "\"onlineStatus\":\"ONLINE\",\"workStatus\":\"IDLE\","
                            + "\"location\":{\"x\":12.5,\"y\":88.2,\"zone\":\"T2\"},"
                            + "\"capabilities\":[\"CAP_INFO_DISPLAY\"],"
                            + "\"reportedAt\":\"2026-10-13T05:00:00+08:00\"}";
                    write(exchange, 200, body);
                } else {
                    write(exchange, 202, "");
                }
            } catch (Exception ex) {
                try { write(exchange, 500, "{}"); } catch (IOException ignored) { }
            }
        });
        server.start();

        DeviceCredentialService credentials = mock(DeviceCredentialService.class);
        when(credentials.tokenFor(any())).thenReturn("fake-runtime-token");
        client = new DeviceAdapterClient(new RestTemplateBuilder(), credentials, 2000, 3000,
                "http://127.0.0.1:8080");
        device = new Device();
        device.setId(41L);
        device.setDeviceCode("SIM-DISPLAY-01");
        device.setIsSimulator(true);
        device.setSimulatedDeviceType("SMART_DISPLAY");
        device.setStatusReportInterval(15);
        device.setAccessEndpoint("http://127.0.0.1:" + server.getAddress().getPort());
    }

    @AfterEach
    void stopFakeRuntime() {
        if (server != null) server.stop(0);
    }

    @Test
    void handshakeBindingAndCommandUseTheSameDeviceProtocolAndCredential() throws Exception {
        SimulatorHealthResponse health = client.testConnection(device);
        assertEquals("SIM-DISPLAY-01", health.getDeviceCode());
        assertEquals(new BigDecimal("12.5"), health.getLocation().getX());

        DeviceAgent agent = new DeviceAgent();
        agent.setAgentCode("AGT-41");
        client.bind(device, agent, 30);

        DeviceCommandRequest command = new DeviceCommandRequest();
        command.setCommandId("CMD-41");
        command.setCommandType("EXECUTE_CAPABILITY");
        command.setAttemptNo(0);
        command.setTaskId("TASK-900");
        command.setStepSeq(1);
        command.setCapabilityType("CAP_INFO_DISPLAY");
        command.setInputParams(java.util.Map.of("contentType", "TEXT", "contentData", "Gate A05"));
        command.setIssuedAt(OffsetDateTime.now());
        command.setDeadline(command.getIssuedAt().plusSeconds(60));
        client.sendCommand(device, "AGT-41", command);

        assertEquals(3, requests.size());
        assertTrue(requests.get(0).startsWith("GET /device-api/v1/health Bearer fake-runtime-token"));
        assertTrue(requests.get(1).startsWith("POST /device-api/v1/agents/AGT-41/binding Bearer fake-runtime-token"));
        assertTrue(requests.get(2).startsWith("POST /device-api/v1/agents/AGT-41/commands Bearer fake-runtime-token"));
    }

    private void write(com.sun.net.httpserver.HttpExchange exchange, int code, String body) throws IOException {
        byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
        if (!body.isEmpty()) exchange.getResponseHeaders().set("Content-Type", "application/json");
        exchange.sendResponseHeaders(code, body.isEmpty() ? -1 : bytes.length);
        try (var output = exchange.getResponseBody()) {
            if (bytes.length > 0) output.write(bytes);
        }
    }
}
