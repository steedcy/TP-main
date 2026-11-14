package com.airport.ai.device;

import com.airport.ai.auth.User;

public record DeviceOnboardingRequestedEvent(String deviceCode, User operator) { }
