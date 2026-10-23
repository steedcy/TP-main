package com.airport.ai.simulator;

import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

class AdditionalSimulatorDriversTest {
    @Test
    void baggageMeasurementUsesExclusiveAppendixFThresholdsAndValidatesInputs() {
        SimulatorProperties properties = new SimulatorProperties();
        BaggageScannerDriver driver = new BaggageScannerDriver(properties);
        var standard = driver.execute("CAP_BAGGAGE_MEASURE", Map.of("measureMode", "AUTO", "timeout", 30));
        assertEquals(false, standard.get("isOversize"));
        assertEquals("SUCCESS", standard.get("measureStatus"));
        properties.setBaggageLengthCm(100);
        properties.setBaggageWidthCm(40);
        properties.setBaggageHeightCm(20);
        assertEquals(true, driver.execute("CAP_BAGGAGE_MEASURE", Map.of("measureMode", "MANUAL", "timeout", 10)).get("isOversize"));
        properties.setBaggageLengthCm(55);
        properties.setBaggageWidthCm(40);
        properties.setBaggageHeightCm(20);
        properties.setBaggageWeightKg(32);
        assertEquals(false, driver.execute("CAP_BAGGAGE_MEASURE", Map.of("measureMode", "AUTO", "timeout", 60)).get("isOversize"));
        assertThrows(IllegalArgumentException.class, () -> driver.execute("CAP_BAGGAGE_MEASURE", Map.of("measureMode", "AUTO", "timeout", 9)));
        var alert = driver.execute("CAP_OVERSIZE_ALERT", Map.of("baggageInfo", Map.of(
                "length", 100, "width", 40, "height", 20, "weight", 10), "alertLevel", "ERROR"));
        assertEquals("SUCCESS", alert.get("reportStatus"));
        assertTrue(alert.get("alertId").toString().startsWith("ALERT-"));
        assertThrows(IllegalArgumentException.class, () -> driver.execute("CAP_OVERSIZE_ALERT",
                Map.of("baggageInfo", Map.of("length", 100), "alertLevel", "ERROR")));
    }

    @Test
    void flightDelayBoardSupportsOnlyItsTwoDisplayCapabilities() {
        FlightDelayBoardDriver driver = new FlightDelayBoardDriver();
        var update = driver.execute("CAP_FLIGHT_UPDATE", Map.of("flightNumber", "CA1234", "updateType", "GATE_CHANGE",
                "updateContent", "改至A05", "displayDuration", 60));
        assertEquals("SUCCESS", update.get("publishStatus"));
        assertTrue(update.containsKey("publishTime"));
        var display = driver.execute("CAP_INFO_DISPLAY", Map.of("contentType", "TEXT", "contentData", "航班信息", "displayDuration", 5));
        assertEquals(5, display.get("actualDuration"));
        assertThrows(IllegalArgumentException.class, () -> driver.execute("CAP_NAVIGATION", Map.of()));
    }

    @Test
    void mobileRobotValidatesBusinessInputsAndProducesProgressLocations() {
        MobileRobotDriver driver = new MobileRobotDriver();
        var escort = driver.execute("CAP_ESCORT", Map.of("targetLocation", "GATE_A05", "escortMode", "LEAD", "maxDuration", 600));
        assertEquals("ARRIVED", escort.get("arrivalStatus"));
        var navigation = driver.execute("CAP_NAVIGATION", Map.of("targetLocation", "GATE_A05", "routePreference", "SHORTEST"));
        assertEquals(true, navigation.get("routeGenerated"));
        assertTrue(navigation.containsKey("estimatedDistance"));
        assertTrue(navigation.containsKey("estimatedDuration"));
        assertTrue(navigation.containsKey("waypointCount"));
        var notify = driver.execute("CAP_NOTIFICATION", Map.of("notificationType", "BOTH", "notificationContent", "请前往A05", "repeatCount", 2));
        assertEquals(2, notify.get("actualRepeatCount"));
        var display = driver.execute("CAP_INFO_DISPLAY", Map.of("contentType", "TEXT", "contentData", "欢迎", "displayDuration", 15));
        assertEquals("SUCCESS", display.get("displayStatus"));
        var route = driver.routeLocations("CAP_ESCORT", Map.of("targetLocation", "GATE_A05"),
                new SimulatorProtocol.Location(BigDecimal.ZERO, BigDecimal.ZERO, "T2"), escort);
        assertEquals(4, route.size());
        assertNotEquals(BigDecimal.ZERO, route.get(3).x());
        assertThrows(IllegalArgumentException.class, () -> driver.execute("CAP_ESCORT",
                Map.of("targetLocation", "GATE_A05", "escortMode", "DRIVE", "maxDuration", 600)));
    }

    @Test
    void mobileRobotRuntimeReportsEachTrajectoryStep() throws Exception {
        SimulatorScenarioTest.clearReportQueue();
        SimulatorProperties properties = new SimulatorProperties();
        properties.setToken("test-token");
        properties.setSimulatedDeviceType("MOBILE_ROBOT");
        properties.setExecutionDelayMilliseconds(80);
        SimulatorRuntime runtime = new SimulatorRuntime(properties, java.util.List.of(
                new SmartDisplayDriver(), new BaggageScannerDriver(properties),
                new FlightDelayBoardDriver(), new MobileRobotDriver()));
        String agent = "AGENT-ROBOT-TRAJECTORY";
        runtime.bind(agent, new SimulatorProtocol.BindingRequest(properties.getDeviceCode(), agent,
                "http://localhost:" + SimulatorScenarioTest.reportPort() + "/report", 15, 30));
        runtime.accept(new SimulatorProtocol.Command("CMD-ROBOT-TRAJECTORY", "TASK_ACCEPT", 0, "TASK-1", 1,
                "CAP_NAVIGATION", Map.of(), null, null));
        SimulatorScenarioTest.awaitReport("TASK_RESPONSE");
        runtime.accept(new SimulatorProtocol.Command("CMD-ROBOT-TRAJECTORY", "EXECUTE_CAPABILITY", 0, "TASK-1", 1,
                "CAP_NAVIGATION", Map.of("targetLocation", "GATE_A05", "routePreference", "SHORTEST"), null, null));

        java.util.Set<String> locations = new java.util.HashSet<>();
        long deadline = System.nanoTime() + java.util.concurrent.TimeUnit.SECONDS.toNanos(3);
        boolean completed = false;
        while (System.nanoTime() < deadline && !completed) {
            Map<String, Object> report = SimulatorScenarioTest.awaitNextReport(500);
            if (report == null) continue;
            if ("STATUS".equals(report.get("reportType"))) {
                Object status = report.get("status");
                if (status instanceof Map<?, ?> map && map.get("location") instanceof Map<?, ?> location) {
                    locations.add(location.get("x") + "," + location.get("y"));
                }
            } else if ("EXECUTION_FEEDBACK".equals(report.get("reportType"))) {
                completed = true;
            }
        }
        assertTrue(completed, "机器人导航应返回执行反馈");
        assertTrue(locations.size() >= 4, "运行时应逐段上报至少四个不同位置");
    }
}
