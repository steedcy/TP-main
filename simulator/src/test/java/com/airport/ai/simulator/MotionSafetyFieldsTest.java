package com.airport.ai.simulator;

import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

/** DEF-S3-052：适配器拒绝全部八类运动安全字段及其常见写法，正常业务意图仍可通过。 */
class MotionSafetyFieldsTest {

    private SimulatorRuntime runtime() {
        SimulatorProperties properties = new SimulatorProperties();
        properties.setToken("t");
        properties.setScenarioResult("SUCCESS");
        properties.setExecutionDelayMilliseconds(0);
        return new SimulatorRuntime(properties, List.of(new SmartDisplayDriver()));
    }

    private Map<String, Object> run(Map<String, Object> input) {
        return runtime().testCapability(Map.of("commandId", "T-1", "capabilityType", "CAP_INFO_DISPLAY", "inputParams", input));
    }

    @Test
    void everySafetyFieldAndItsCommonSpellingsIsRejected() {
        for (String key : List.of("speed", "velocity", "acceleration", "attitude", "orientation", "pathPoints", "path_points",
                "waypoints", "obstacleAvoidance", "emergencyStop", "emergency-stop", "speedLimit", "speed_limit",
                "lostConnectionParking", "lost_connection_parking", "safeStopOnDisconnect",
                "速度", "加速度", "姿态", "路径点", "避障", "急停", "限速", "失联停靠")) {
            SimulatorRuntime rt = runtime();
            Map<String, Object> res = rt.testCapability(Map.of("commandId", "T-" + key,
                    "capabilityType", "CAP_INFO_DISPLAY",
                    "inputParams", Map.of("contentType", "TEXT", "contentData", "x", "displayDuration", 5, key, 1)));
            assertEquals("FAILED", res.get("result"), key + " 应被适配器拒绝");
            assertEquals("BLOCKED_MOTION_SAFETY", rt.commandStates().get("T-" + key + ":blocked"),
                    key + " 应记录运动安全拦截状态");
        }
    }

    @Test
    void ordinaryBusinessInputStillSucceeds() {
        assertEquals("SUCCESS", run(Map.of("contentType", "TEXT", "contentData", "CA1234 延误", "displayDuration", 30)).get("result"));
    }
}
