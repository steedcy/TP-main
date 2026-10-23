package com.airport.ai.simulator;

import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

class SimulatorRuntimeTest {
    @Test
    void cancelReleasesAnEqualCommandIdReceivedInAnotherRequest() throws Exception {
        var properties=new SimulatorProperties(); properties.setExecutionDelayMilliseconds(0); properties.setScenarioResult("NO_FEEDBACK");
        var runtime=new SimulatorRuntime(properties,java.util.List.of(new SmartDisplayDriver()));
        runtime.accept(new SimulatorProtocol.Command(new String("CMD-CANCEL"),"TASK_ACCEPT",0,"TASK-1",1,"CAP_INFO_DISPLAY",Map.of(),null,null));
        runtime.accept(new SimulatorProtocol.Command(new String("CMD-CANCEL"),"EXECUTE_CAPABILITY",0,"TASK-1",1,"CAP_INFO_DISPLAY",Map.of(),null,null));
        Thread.sleep(100);
        assertEquals("BUSY",runtime.health("before").workStatus());
        runtime.accept(new SimulatorProtocol.Command(new String("CMD-CANCEL"),"TASK_CANCEL",0,"TASK-1",1,null,Map.of(),null,null));
        assertEquals("IDLE",runtime.health("after").workStatus());
    }
    @Test
    void healthAndBindingExposeP0IdentityAndState() {
        SimulatorProperties properties = new SimulatorProperties();
        properties.setToken("test-token");
        SimulatorRuntime runtime = new SimulatorRuntime(properties, java.util.List.of(new SmartDisplayDriver(), new BaggageScannerDriver(properties), new FlightDelayBoardDriver(), new MobileRobotDriver()));
        var before = runtime.health("nonce-1");
        assertEquals("1.0", before.protocolVersion());
        assertEquals("nonce-1", before.nonce());
        assertEquals("SIMULATOR", before.deviceTypeCode());
        assertEquals("SMART_DISPLAY", before.simulatedDeviceType());
        assertTrue(before.capabilities().containsAll(java.util.List.of("CAP_INFO_DISPLAY", "CAP_FLIGHT_UPDATE", "CAP_NAVIGATION")));
        assertEquals(new BigDecimal("120.5"), before.location().x());
        runtime.bind("AGENT-1", new SimulatorProtocol.BindingRequest("SIM_DISPLAY_001", "AGENT-1",
                "http://localhost:8080/device-api/v1/agents/AGENT-1/report", 15, 30));
        assertEquals("AGENT-1", runtime.agentCode());
        assertThrows(IllegalArgumentException.class, () -> runtime.bind("AGENT-2",
                new SimulatorProtocol.BindingRequest("SIM_DISPLAY_001", "AGENT-2", "http://localhost/report", 15, 30)));
    }

    @Test
    void commandSafetyBoundaryRejectsMotionControlFields() {
        SimulatorProperties properties = new SimulatorProperties();
        SimulatorRuntime runtime = new SimulatorRuntime(properties, java.util.List.of(new SmartDisplayDriver(), new BaggageScannerDriver(properties), new FlightDelayBoardDriver(), new MobileRobotDriver()));
        var command = new SimulatorProtocol.Command("CMD-1", "TASK_ACCEPT", 0, "TASK-1", 1,
                "CAP_NAVIGATION", Map.of("targetLocation", "GATE_A05", "nested", Map.of("speed", 1)), null, null);
        assertThrows(IllegalArgumentException.class, () -> runtime.accept(command));
    }

    @Test
    void offlineRuntimeDoesNotClaimOnline() {
        SimulatorProperties properties = new SimulatorProperties();
        SimulatorRuntime runtime = new SimulatorRuntime(properties, java.util.List.of(new SmartDisplayDriver(), new BaggageScannerDriver(properties), new FlightDelayBoardDriver(), new MobileRobotDriver()));
        runtime.setOnline(false);
        assertEquals("OFFLINE", runtime.health("nonce").onlineStatus());
    }

    @Test
    void startupRejectsScenarioThatDoesNotMatchSimulatedDeviceType() {
        SimulatorProperties properties = new SimulatorProperties();
        properties.setScenarioResult("NO_OBJECT");
        assertThrows(IllegalStateException.class, () -> new SimulatorRuntime(properties,
                java.util.List.of(new SmartDisplayDriver(), new BaggageScannerDriver(properties),
                        new FlightDelayBoardDriver(), new MobileRobotDriver())));
    }
}
