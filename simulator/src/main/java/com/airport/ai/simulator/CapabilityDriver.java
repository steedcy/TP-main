package com.airport.ai.simulator;

import java.util.Map;
import java.util.Set;
import java.util.List;

public interface CapabilityDriver {
    String deviceType();
    Set<String> capabilities();
    Map<String, Object> execute(String capabilityType, Map<String, Object> input);
    default List<SimulatorProtocol.Location> routeLocations(String capabilityType, Map<String, Object> input,
                                                            SimulatorProtocol.Location current,
                                                            Map<String, Object> output) { return List.of(); }
}
