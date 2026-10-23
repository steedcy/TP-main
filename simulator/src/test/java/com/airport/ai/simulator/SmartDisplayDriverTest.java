package com.airport.ai.simulator;

import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

class SmartDisplayDriverTest {
    private final SmartDisplayDriver driver = new SmartDisplayDriver();

    @Test
    void supportsThreeDisplayCapabilitiesAndReturnsContractFields() {
        assertEquals(Map.of("displayStatus", "SUCCESS", "actualDuration", 30, "errorMessage", ""),
                driver.execute("CAP_INFO_DISPLAY", Map.of("contentType", "HTML", "contentData", "<p>Flight</p>", "displayDuration", 30)));
        var flight = driver.execute("CAP_FLIGHT_UPDATE", Map.of("flightNumber", "CA1234", "updateType", "DELAY",
                "updateContent", "延误30分钟", "displayDuration", 60));
        assertEquals("SUCCESS", flight.get("publishStatus"));
        assertTrue(flight.containsKey("publishTime"));
        var route = driver.execute("CAP_NAVIGATION", Map.of("targetLocation", "GATE_A05", "routePreference", "BARRIER_FREE"));
        assertEquals(true, route.get("routeGenerated"));
        assertTrue((Double) route.get("estimatedDistance") > 0);
        assertTrue((Integer) route.get("estimatedDuration") > 0);
        assertTrue((Integer) route.get("waypointCount") > 0);
    }

    @Test
    void rejectsUnsupportedTypesAndOutOfRangeDurations() {
        assertThrows(IllegalArgumentException.class, () -> driver.execute("CAP_INFO_DISPLAY",
                Map.of("contentType", "PDF", "contentData", "x", "displayDuration", 30)));
        assertThrows(IllegalArgumentException.class, () -> driver.execute("CAP_INFO_DISPLAY",
                Map.of("contentType", "TEXT", "contentData", "x", "displayDuration", 301)));
        assertThrows(IllegalArgumentException.class, () -> driver.execute("CAP_NAVIGATION",
                Map.of("targetLocation", "GATE_A05", "routePreference", "FASTEST")));
        assertThrows(IllegalArgumentException.class, () -> driver.execute("CAP_ESCORT", Map.of()));
    }
}
