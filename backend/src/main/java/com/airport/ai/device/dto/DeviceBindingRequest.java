package com.airport.ai.device.dto;

public record DeviceBindingRequest(String deviceCode, String agentCode, String reportUrl,
                                   Integer heartbeatIntervalSeconds, Integer heartbeatTimeoutSeconds) {}
