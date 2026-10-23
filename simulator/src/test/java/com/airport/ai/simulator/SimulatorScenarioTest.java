package com.airport.ai.simulator;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.Map;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.TimeUnit;

import static org.junit.jupiter.api.Assertions.*;

class SimulatorScenarioTest {
    private static final BlockingQueue<Map<String, Object>> REPORTS = new LinkedBlockingQueue<>();
    private static final HttpServer REPORT_SERVER = startServer();

    @BeforeEach void clearReports() { clearReportQueue(); }
    @AfterAll static void stopServer() { REPORT_SERVER.stop(0); }

    @Test
    void failedScenarioReturnsTypedDeviceError() throws Exception {
        Map<String, Object> feedback = executeScenario("FAILED", "CMD-FAILED");
        assertEquals("FAILED", feedback.get("executionResult"));
        assertEquals("SIMULATED_DEVICE_ERROR", feedback.get("reasonCode"));
        Map<?, ?> output = (Map<?, ?>) feedback.get("outputParams");
        assertEquals("DEVICE_ERROR", output.get("displayStatus"));
        assertEquals(0, output.get("actualDuration"));
    }

    @Test
    void timeoutScenarioReturnsContractFields() throws Exception {
        Map<String, Object> feedback = executeScenario("TIMEOUT", "CMD-TIMEOUT");
        assertEquals("TIMEOUT", feedback.get("executionResult"));
        assertEquals("SIMULATED_TIMEOUT", feedback.get("reasonCode"));
        Map<?, ?> output = (Map<?, ?>) feedback.get("outputParams");
        assertEquals("TIMEOUT", output.get("displayStatus"));
        assertTrue(output.containsKey("actualDuration"));
        assertTrue(output.containsKey("errorMessage"));
    }

    @Test
    void baggageNoObjectAndRobotLostTargetHaveTypedOutcomes() throws Exception {
        Map<String, Object> noObject = executeScenario("NO_OBJECT", "BAGGAGE_SCANNER", "CAP_BAGGAGE_MEASURE",
                Map.of("measureMode", "AUTO", "timeout", 30), "CMD-NO-OBJECT");
        assertEquals("FAILED", noObject.get("executionResult"));
        assertEquals("NO_OBJECT", ((Map<?, ?>) noObject.get("outputParams")).get("measureStatus"));

        Map<String, Object> lostTarget = executeScenario("LOST_TARGET", "MOBILE_ROBOT", "CAP_ESCORT",
                Map.of("targetLocation", "GATE_A05", "escortMode", "LEAD", "maxDuration", 600), "CMD-LOST-TARGET");
        assertEquals("LOST_TARGET", ((Map<?, ?>) lostTarget.get("outputParams")).get("arrivalStatus"));

        Map<String, Object> unrelatedBaggageCapability = executeScenario("NO_OBJECT", "BAGGAGE_SCANNER", "CAP_OVERSIZE_ALERT",
                Map.of("baggageInfo", Map.of("length", 100, "width", 40, "height", 20, "weight", 10), "alertLevel", "ERROR"),
                "CMD-NO-OBJECT-ALERT");
        assertEquals("SUCCESS", unrelatedBaggageCapability.get("executionResult"),
                "NO_OBJECT只应影响行李测量，不应影响告警上报");

        Map<String, Object> unrelatedRobotCapability = executeScenario("LOST_TARGET", "MOBILE_ROBOT", "CAP_NAVIGATION",
                Map.of("targetLocation", "GATE_A05", "routePreference", "SHORTEST"), "CMD-LOST-TARGET-NAV");
        assertEquals("SUCCESS", unrelatedRobotCapability.get("executionResult"),
                "LOST_TARGET只应影响陪同，不应影响导航");
    }

    @Test
    void failedAndTimeoutScenariosKeepTypedOutputsForEveryP3Capability() throws Exception {
        record CapabilityCase(String deviceType, String capability, Map<String, Object> input, String outputField) {}
        var cases = java.util.List.of(
                new CapabilityCase("BAGGAGE_SCANNER", "CAP_BAGGAGE_MEASURE", Map.of("measureMode", "AUTO", "timeout", 30), "measureStatus"),
                new CapabilityCase("BAGGAGE_SCANNER", "CAP_OVERSIZE_ALERT", Map.of("baggageInfo", Map.of("length", 100, "width", 40, "height", 20, "weight", 10), "alertLevel", "ERROR"), "reportStatus"),
                new CapabilityCase("FLIGHT_DELAY_BOARD", "CAP_FLIGHT_UPDATE", Map.of("flightNumber", "CA1234", "updateType", "DELAY", "updateContent", "延误", "displayDuration", 60), "publishStatus"),
                new CapabilityCase("FLIGHT_DELAY_BOARD", "CAP_INFO_DISPLAY", Map.of("contentType", "TEXT", "contentData", "通知", "displayDuration", 30), "displayStatus"),
                new CapabilityCase("MOBILE_ROBOT", "CAP_NAVIGATION", Map.of("targetLocation", "GATE_A05", "routePreference", "SHORTEST"), "routeGenerated"),
                new CapabilityCase("MOBILE_ROBOT", "CAP_ESCORT", Map.of("targetLocation", "GATE_A05", "escortMode", "LEAD", "maxDuration", 600), "arrivalStatus"),
                new CapabilityCase("MOBILE_ROBOT", "CAP_NOTIFICATION", Map.of("notificationType", "TEXT", "notificationContent", "请前往登机口", "repeatCount", 1), "notificationStatus"),
                new CapabilityCase("MOBILE_ROBOT", "CAP_INFO_DISPLAY", Map.of("contentType", "TEXT", "contentData", "通知", "displayDuration", 30), "displayStatus"));

        int index = 0;
        for (CapabilityCase capability : cases) {
            for (String scenario : java.util.List.of("FAILED", "TIMEOUT")) {
                Map<String, Object> feedback = executeScenario(scenario, capability.deviceType(), capability.capability(),
                        capability.input(), "CMD-TYPED-" + index++);
                assertEquals(scenario, feedback.get("executionResult"));
                assertTrue(((Map<?, ?>) feedback.get("outputParams")).containsKey(capability.outputField()),
                        capability.deviceType() + "/" + capability.capability() + " must keep its typed output field");
            }
        }
    }

    private Map<String, Object> executeScenario(String result, String commandId) throws Exception {
        return executeScenario(result, "SMART_DISPLAY", "CAP_INFO_DISPLAY",
                Map.of("contentType", "TEXT", "contentData", "Gate A05", "displayDuration", 20), commandId);
    }

    private Map<String, Object> executeScenario(String result, String deviceType, String capabilityType,
                                               Map<String, Object> input, String commandId) throws Exception {
        SimulatorProperties properties = new SimulatorProperties();
        properties.setToken("test-token");
        properties.setScenarioResult(result);
        properties.setExecutionDelayMilliseconds(1);
        properties.setSimulatedDeviceType(deviceType);
        SimulatorRuntime runtime = new SimulatorRuntime(properties, java.util.List.of(new SmartDisplayDriver(), new BaggageScannerDriver(properties), new FlightDelayBoardDriver(), new MobileRobotDriver()));
        String agent = "AGENT-" + result;
        runtime.bind(agent, new SimulatorProtocol.BindingRequest(properties.getDeviceCode(), agent,
                "http://localhost:" + REPORT_SERVER.getAddress().getPort() + "/report", 15, 30));
        runtime.accept(new SimulatorProtocol.Command(commandId, "TASK_ACCEPT", 0, "TASK-1", 1,
                "CAP_INFO_DISPLAY", Map.of(), null, null));
        REPORTS.poll(3, TimeUnit.SECONDS); // accept response
        runtime.accept(new SimulatorProtocol.Command(commandId, "EXECUTE_CAPABILITY", 0, "TASK-1", 1,
                capabilityType, input, null, null));
        long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(3);
        while (System.nanoTime() < deadline) {
            Map<String, Object> report = REPORTS.poll(100, TimeUnit.MILLISECONDS);
            if (report != null && "EXECUTION_FEEDBACK".equals(report.get("reportType"))) {
                return (Map<String, Object>) report.get("feedback");
            }
        }
        fail("未收到仿真执行反馈");
        return Map.of();
    }

    private static HttpServer startServer() {
        try {
            HttpServer server = HttpServer.create(new InetSocketAddress("localhost", 0), 0);
            server.createContext("/report", exchange -> {
                try {
                    REPORTS.add(new ObjectMapper().readValue(exchange.getRequestBody().readAllBytes(), Map.class));
                    byte[] body = "{}".getBytes(StandardCharsets.UTF_8);
                    exchange.sendResponseHeaders(200, body.length);
                    exchange.getResponseBody().write(body);
                } finally { exchange.close(); }
            });
            server.start();
            return server;
        } catch (Exception ex) { throw new ExceptionInInitializerError(ex); }
    }

    static int reportPort() { return REPORT_SERVER.getAddress().getPort(); }

    static void clearReportQueue() { REPORTS.clear(); }

    static Map<String, Object> awaitReport(String reportType) throws InterruptedException {
        long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(3);
        while (System.nanoTime() < deadline) {
            Map<String, Object> report = REPORTS.poll(100, TimeUnit.MILLISECONDS);
            if (report != null && reportType.equals(report.get("reportType"))) return report;
        }
        fail("未收到仿真报告: " + reportType);
        return Map.of();
    }

    static Map<String, Object> awaitNextReport(long timeoutMillis) throws InterruptedException {
        return REPORTS.poll(timeoutMillis, TimeUnit.MILLISECONDS);
    }
}
