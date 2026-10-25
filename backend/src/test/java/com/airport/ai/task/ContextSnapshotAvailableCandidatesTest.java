package com.airport.ai.task;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class ContextSnapshotAvailableCandidatesTest {
    @Test
    void spareResourceCountExcludesBusyAndWrongPhysicalChannels() {
        ContextSnapshot snapshot = new ContextSnapshot();
        snapshot.setAgents("""
                [
                  {"capabilities":["CAP_NOTIFICATION"],"workload":"IDLE","deviceTypeCode":"SIMULATOR","simulatedDeviceType":"MOBILE_ROBOT"},
                  {"capabilities":["CAP_NOTIFICATION"],"workload":"BUSY","deviceTypeCode":"SIMULATOR","simulatedDeviceType":"MOBILE_ROBOT"},
                  {"capabilities":["CAP_NOTIFICATION"],"workload":"IDLE","deviceTypeCode":"SIMULATOR","simulatedDeviceType":"SMART_DISPLAY"}
                ]
                """);
        ContextSnapshotService service = new ContextSnapshotService(null, null, null, null);
        assertEquals(1, service.countAvailableCandidates(snapshot, "CAP_NOTIFICATION", "FLIGHT_CHANGE_RESPONSE"));
    }
}
