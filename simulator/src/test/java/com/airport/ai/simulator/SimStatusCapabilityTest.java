package com.airport.ai.simulator;

import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

/** DEF-S3-079：CAP_SIM_STATUS 是仿真体自身能力，不论所模拟设备类型，均应通过能力测试并返回状态快照。 */
class SimStatusCapabilityTest {

    private SimulatorRuntime runtime(String scenario) {
        SimulatorProperties properties = new SimulatorProperties();
        properties.setToken("t");
        properties.setScenarioResult(scenario);
        return new SimulatorRuntime(properties, List.of(new SmartDisplayDriver(), new BaggageScannerDriver(properties),
                new FlightDelayBoardDriver(), new MobileRobotDriver()));
    }

    @SuppressWarnings("unchecked")
    @Test
    void simStatusPassesCapabilityTestWithStatusSnapshot() {
        Map<String, Object> r = runtime("SUCCESS").testCapability(
                Map.of("commandId", "TEST-1", "capabilityType", "CAP_SIM_STATUS", "inputParams", Map.of()));
        assertEquals("SUCCESS", r.get("result"));
        Map<String, Object> out = (Map<String, Object>) r.get("outputParams");
        assertEquals("ONLINE", out.get("onlineStatus"));
        assertEquals("IDLE", out.get("workStatus"));
        assertNotNull(out.get("simulatedDeviceType"));
        assertNotNull(out.get("location"));
    }

    @Test
    void businessCapabilityStillGoesThroughDriver() {
        Map<String, Object> r = runtime("SUCCESS").testCapability(
                Map.of("commandId", "TEST-2", "capabilityType", "CAP_ESCORT", "inputParams", Map.of()));
        // 智慧航显驱动不支持陪同能力：仍应失败，证明业务能力未被一并放行
        assertEquals("FAILED", r.get("result"));
    }

    @Test
    void failureScenarioStillFailsSimStatusTest() {
        Map<String, Object> r = runtime("FAILED").testCapability(
                Map.of("commandId", "TEST-3", "capabilityType", "CAP_SIM_STATUS", "inputParams", Map.of()));
        assertEquals("FAILED", r.get("result"));
    }
}
