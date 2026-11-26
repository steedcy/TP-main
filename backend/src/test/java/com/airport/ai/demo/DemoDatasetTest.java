package com.airport.ai.demo;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class DemoDatasetTest {
    @Test
    void loadsV15StandardDemoDatasetWithExpectedCountsAndDigest() {
        DemoDataset dataset = new DemoDataset(new ObjectMapper());
        assertEquals("V1.5-DEMO-20261126", DemoDataset.VERSION);
        assertEquals(20, dataset.devices().size());
        assertEquals(18, dataset.mapRegions().size());
        assertEquals(68, dataset.mapPois().size());
        assertEquals(3, dataset.baselines().size());
        assertEquals(4, dataset.scenarios().size());
        assertEquals(3, dataset.riskRules().size());
        assertTrue(dataset.validationRules().path("fixedDeviceStrictZone").asBoolean());
        assertEquals(650, dataset.validationRules().path("fixedMaxServiceDistance").asInt());
        assertEquals(1600, dataset.validationRules().path("robotMaxServiceDistance").asInt());
        assertNotNull(dataset.sourceDigest());
        assertEquals(64, dataset.sourceDigest().length());
        assertTrue(dataset.deviceCodes().contains("SIM_ROBOT_C1"));
        assertTrue(dataset.deviceCodes().contains("SIM_DISPLAY_H2"));
    }
}
