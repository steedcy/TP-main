package com.airport.ai.simulator;

import org.junit.jupiter.api.Test;
import java.util.Map;
import static org.junit.jupiter.api.Assertions.*;

class BaggageThresholdTraceTest {
    @Test
    void returnsThresholdNumbersSourceAndInclusiveBoundary() {
        SimulatorProperties settings = new SimulatorProperties();
        settings.setBaggageLengthCm(80); settings.setBaggageWidthCm(55);
        settings.setBaggageHeightCm(23); settings.setBaggageWeightKg(32);
        BaggageScannerDriver scanner = new BaggageScannerDriver(settings);
        Map<String, Object> result = scanner.execute("CAP_BAGGAGE_MEASURE", Map.of("measureMode", "AUTO", "timeout", 30));
        assertEquals(false, result.get("isOversize"));
        assertEquals(158.0, result.get("totalDimensionCm"));
        assertEquals(158, result.get("dimensionThresholdCm"));
        assertEquals(32, result.get("weightThresholdKg"));
        assertTrue(result.get("thresholdSource").toString().contains("附录F"));
        settings.setBaggageWeightKg(35);
        assertEquals(true, scanner.execute("CAP_BAGGAGE_MEASURE", Map.of("measureMode", "AUTO", "timeout", 30)).get("isOversize"));
    }
}
