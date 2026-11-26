package com.airport.ai.planning;

import com.fasterxml.jackson.databind.JsonNode;

import java.time.Duration;

/** Transport for planning-model chat calls that must return exactly one JSON object. */
public interface PlanningChatClient {

    /** Calls the model with the client's configured request deadline. */
    JsonNode complete(String instruction, Object input, String requestId);

    /** Calls the model with an explicit request deadline (used to share one overall budget). */
    JsonNode complete(String instruction, Object input, String requestId, Duration timeout);
}
