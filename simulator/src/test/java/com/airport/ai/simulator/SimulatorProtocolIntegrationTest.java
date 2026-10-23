package com.airport.ai.simulator;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.http.*;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;

import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.Map;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.TimeUnit;

import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT,
        properties = {"simulator.token=integration-token", "simulator.execution-delay-milliseconds=5"})
class SimulatorProtocolIntegrationTest {
    private static final String TOKEN = "integration-token";
    private static final BlockingQueue<Map<String, Object>> REPORTS = new LinkedBlockingQueue<>();
    private static final HttpServer REPORT_SERVER = startReportServer();

    @Autowired private TestRestTemplate http;
    @Autowired private ObjectMapper objectMapper;

    @DynamicPropertySource
    static void properties(DynamicPropertyRegistry registry) {
        registry.add("simulator.token", () -> TOKEN);
        registry.add("simulator.device-code", () -> "SIM_DISPLAY_TEST");
        registry.add("simulator.device-type", () -> "SIMULATOR");
        registry.add("simulator.simulated-device-type", () -> "SMART_DISPLAY");
    }

    @AfterAll
    static void stopReportServer() { REPORT_SERVER.stop(0); }

    @Test
    void healthBindingAcceptanceAndTypedExecutionUsePlatformReportContract() throws Exception {
        HttpHeaders headers = authHeaders();
        var health = http.exchange("/device-api/v1/health?nonce=handshake", HttpMethod.GET,
                new HttpEntity<>(headers), Map.class);
        assertEquals(HttpStatus.OK, health.getStatusCode());
        assertEquals("handshake", health.getBody().get("nonce"));
        assertEquals("SIM_DISPLAY_TEST", health.getBody().get("deviceCode"));

        var binding = new SimulatorProtocol.BindingRequest("SIM_DISPLAY_TEST", "AGENT-DISPLAY-TEST",
                "http://localhost:" + REPORT_SERVER.getAddress().getPort() + "/device-api/v1/agents/AGENT-DISPLAY-TEST/report", 15, 30);
        var bound = http.exchange("/device-api/v1/agents/AGENT-DISPLAY-TEST/binding", HttpMethod.POST,
                new HttpEntity<>(binding, headers), Map.class);
        assertEquals(HttpStatus.OK, bound.getStatusCode());

        var acceptance = new SimulatorProtocol.Command("CMD-P2-1", "TASK_ACCEPT", 0, "TASK-P2-1", 1,
                "CAP_INFO_DISPLAY", Map.of(), null, null);
        http.postForEntity("/device-api/v1/agents/AGENT-DISPLAY-TEST/commands",
                new HttpEntity<>(acceptance, headers), Map.class);
        Map<String, Object> acceptedReport = awaitReport("TASK_RESPONSE");
        assertEquals(true, ((Map<?, ?>) acceptedReport.get("response")).get("accepted"));
        http.postForEntity("/device-api/v1/agents/AGENT-DISPLAY-TEST/commands",
                new HttpEntity<>(acceptance, headers), Map.class);
        assertEquals(acceptedReport, awaitReport("TASK_RESPONSE"), "重复承接必须重放同一份幂等报告");

        var execution = new SimulatorProtocol.Command("CMD-P2-1", "EXECUTE_CAPABILITY", 0, "TASK-P2-1", 1,
                "CAP_INFO_DISPLAY", Map.of("contentType", "TEXT", "contentData", "Gate A05", "displayDuration", 20), null, null);
        http.postForEntity("/device-api/v1/agents/AGENT-DISPLAY-TEST/commands",
                new HttpEntity<>(execution, headers), Map.class);
        Map<String, Object> feedback = awaitReport("EXECUTION_FEEDBACK");
        Map<?, ?> payload = (Map<?, ?>) feedback.get("feedback");
        assertEquals("SUCCESS", payload.get("executionResult"));
        assertEquals("SUCCESS", ((Map<?, ?>) payload.get("outputParams")).get("displayStatus"));
        assertEquals(20, ((Map<?, ?>) payload.get("outputParams")).get("actualDuration"));
        http.postForEntity("/device-api/v1/agents/AGENT-DISPLAY-TEST/commands",
                new HttpEntity<>(execution, headers), Map.class);
        assertEquals(feedback, awaitReport("EXECUTION_FEEDBACK"), "重复执行命令必须重放原结果而不重做动作");

        http.postForEntity("/device-api/v1/control/online?value=false", new HttpEntity<>(headers), Map.class);
        var stopped = http.exchange("/device-api/v1/health?nonce=stopped", HttpMethod.GET,
                new HttpEntity<>(headers), Map.class);
        assertEquals("OFFLINE", stopped.getBody().get("onlineStatus"));
        assertEquals("OFFLINE", awaitStatus("OFFLINE").get("onlineStatus"));
        var stoppedCommand = new SimulatorProtocol.Command("CMD-STOPPED", "TASK_ACCEPT", 0, "TASK-STOPPED", 1,
                "CAP_INFO_DISPLAY", Map.of(), null, null);
        var rejectedWhileStopped = http.exchange("/device-api/v1/agents/AGENT-DISPLAY-TEST/commands",
                HttpMethod.POST, new HttpEntity<>(stoppedCommand, headers), Map.class);
        assertEquals(HttpStatus.CONFLICT, rejectedWhileStopped.getStatusCode());
        http.postForEntity("/device-api/v1/control/online?value=true", new HttpEntity<>(headers), Map.class);
        var resumed = http.exchange("/device-api/v1/health?nonce=resumed", HttpMethod.GET,
                new HttpEntity<>(headers), Map.class);
        assertEquals("ONLINE", resumed.getBody().get("onlineStatus"));
        assertEquals("ONLINE", awaitStatus("ONLINE").get("onlineStatus"));

        http.postForEntity("/device-api/v1/control/scenario", new HttpEntity<>(Map.of("scenarioResult", "FAILED"), headers), Map.class);
        assertEquals("FAILED", awaitScenario("FAILED").get("scenarioResult"));
        http.postForEntity("/device-api/v1/control/scenario", new HttpEntity<>(Map.of("scenarioResult", "SUCCESS"), headers), Map.class);
        assertEquals("SUCCESS", awaitScenario("SUCCESS").get("scenarioResult"));
    }

    private Map<String, Object> awaitReport(String reportType) throws InterruptedException {
        long end = System.nanoTime() + TimeUnit.SECONDS.toNanos(5);
        while (System.nanoTime() < end) {
            Map<String, Object> report = REPORTS.poll(100, TimeUnit.MILLISECONDS);
            if (report != null && reportType.equals(report.get("reportType"))) return report;
        }
        fail("未收到设备报告: " + reportType);
        return Map.of();
    }

    private Map<?, ?> awaitStatus(String onlineStatus) throws InterruptedException {
        long end = System.nanoTime() + TimeUnit.SECONDS.toNanos(5);
        while (System.nanoTime() < end) {
            Map<String, Object> report = REPORTS.poll(100, TimeUnit.MILLISECONDS);
            if (report == null || !"STATUS".equals(report.get("reportType"))) continue;
            Map<?, ?> status = (Map<?, ?>) report.get("status");
            if (onlineStatus.equals(status.get("onlineStatus"))) return status;
        }
        fail("未收到指定状态上报: " + onlineStatus);
        return Map.of();
    }

    private Map<?, ?> awaitScenario(String scenarioResult) throws InterruptedException {
        long end = System.nanoTime() + TimeUnit.SECONDS.toNanos(5);
        while (System.nanoTime() < end) {
            Map<String, Object> report = REPORTS.poll(100, TimeUnit.MILLISECONDS);
            if (report == null || !"STATUS".equals(report.get("reportType"))) continue;
            Map<?, ?> businessStatus = (Map<?, ?>) ((Map<?, ?>) report.get("status")).get("businessStatus");
            if (scenarioResult.equals(businessStatus.get("scenarioResult"))) return businessStatus;
        }
        fail("未收到场景配置状态: " + scenarioResult);
        return Map.of();
    }

    private HttpHeaders authHeaders() {
        HttpHeaders headers = new HttpHeaders();
        headers.setBearerAuth(TOKEN);
        headers.setContentType(MediaType.APPLICATION_JSON);
        return headers;
    }

    private static HttpServer startReportServer() {
        try {
            HttpServer server = HttpServer.create(new InetSocketAddress("localhost", 0), 0);
            server.createContext("/device-api/v1/agents/AGENT-DISPLAY-TEST/report", exchange -> {
                try {
                    byte[] body = exchange.getRequestBody().readAllBytes();
                    REPORTS.add(new ObjectMapper().readValue(body, Map.class));
                    byte[] response = "{\"code\":200,\"message\":\"success\",\"data\":null}".getBytes(StandardCharsets.UTF_8);
                    exchange.getResponseHeaders().set("Content-Type", "application/json");
                    exchange.sendResponseHeaders(200, response.length);
                    exchange.getResponseBody().write(response);
                } finally { exchange.close(); }
            });
            server.start();
            return server;
        } catch (Exception ex) { throw new ExceptionInInitializerError(ex); }
    }
}
