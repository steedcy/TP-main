package com.airport.ai.device.dto;

import java.time.LocalDateTime;

/** Token is returned once from the explicit rotation endpoint and is never included in DeviceView. */
public record DeviceTokenRotationView(String deviceCode, String accessToken, LocalDateTime issuedAt) {}
