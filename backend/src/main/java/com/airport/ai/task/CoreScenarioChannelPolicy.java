package com.airport.ai.task;

import com.airport.ai.device.Device;
import java.util.Map;
import java.util.Set;

/** Physical channel required by the three preset passenger-service scenarios. */
public final class CoreScenarioChannelPolicy {
    private static final Set<String> FLIGHT_CHANNELS = Set.of(
            "CAP_FLIGHT_UPDATE", "CAP_INFO_DISPLAY", "CAP_NOTIFICATION", "CAP_NAVIGATION");
    private static final Set<String> FLIGHT_PUBLICATION_CHANNELS = Set.of(
            "CAP_FLIGHT_UPDATE", "CAP_INFO_DISPLAY", "CAP_NOTIFICATION");
    private CoreScenarioChannelPolicy() {}

    public static boolean isFlightChannel(String taskFamily, String capabilityType) {
        return "FLIGHT_CHANGE_RESPONSE".equals(taskFamily) && FLIGHT_CHANNELS.contains(capabilityType);
    }

    public static boolean isFlightPublication(String capabilityType) {
        return FLIGHT_PUBLICATION_CHANNELS.contains(capabilityType);
    }

    public static String requiredType(String taskFamily, String capabilityType) {
        if (taskFamily == null || capabilityType == null) return null;
        return switch (taskFamily) {
            case "FLIGHT_CHANGE_RESPONSE" -> Map.of(
                    "CAP_FLIGHT_UPDATE", "FLIGHT_DELAY_BOARD",
                    "CAP_INFO_DISPLAY", "SMART_DISPLAY",
                    "CAP_NOTIFICATION", "MOBILE_ROBOT",
                    "CAP_NAVIGATION", "MOBILE_ROBOT").get(capabilityType);
            case "OVERSIZE_BAGGAGE_HANDLING" -> Map.of(
                    "CAP_BAGGAGE_MEASURE", "BAGGAGE_SCANNER",
                    "CAP_OVERSIZE_ALERT", "BAGGAGE_SCANNER",
                    "CAP_INFO_DISPLAY", "SMART_DISPLAY",
                    "CAP_NAVIGATION", "MOBILE_ROBOT").get(capabilityType);
            case "SPECIAL_PASSENGER_SERVICE" -> Map.of(
                    "CAP_INFO_DISPLAY", "SMART_DISPLAY",
                    "CAP_NOTIFICATION", "MOBILE_ROBOT",
                    "CAP_ESCORT", "MOBILE_ROBOT",
                    "CAP_NAVIGATION", "MOBILE_ROBOT").get(capabilityType);
            default -> null;
        };
    }

    public static boolean matches(String taskFamily, String capabilityType, String deviceType,
                                  String simulatedDeviceType) {
        String required = requiredType(taskFamily, capabilityType);
        if (required == null) return true;
        String actual = "SIMULATOR".equals(deviceType) ? simulatedDeviceType : deviceType;
        return required.equals(actual);
    }

    public static boolean matches(String taskFamily, String capabilityType, Device device) {
        return matches(taskFamily, capabilityType, device.getDeviceTypeCode(), device.getSimulatedDeviceType());
    }
}
