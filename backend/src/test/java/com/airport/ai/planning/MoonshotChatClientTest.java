package com.airport.ai.planning;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.net.http.HttpTimeoutException;
import java.util.Map;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class MoonshotChatClientTest {
    private final ObjectMapper mapper = new ObjectMapper();

    @SuppressWarnings("unchecked")
    private HttpResponse<String> response(int status, String body) {
        HttpResponse<String> response = mock(HttpResponse.class);
        when(response.statusCode()).thenReturn(status);
        when(response.body()).thenReturn(body);
        return response;
    }

    private MoonshotChatClient client(HttpClient http) {
        return new MoonshotChatClient(http, mapper, "https://api.moonshot.cn/v1/",
                "test-only-token", "kimi-k2.6", 4096, 60000);
    }

    private String envelope(String finishReason, String content) throws Exception {
        return mapper.writeValueAsString(Map.of("choices", new Object[]{Map.of("finish_reason", finishReason,
                "message", Map.of("content", content))}));
    }

    @Test
    void usesOfficialEndpointBearerAndSixtySecondRequestDeadline() throws Exception {
        HttpClient http = mock(HttpClient.class);
        when(http.send(any(), any(HttpResponse.BodyHandler.class))).thenAnswer(invocation -> {
            HttpRequest request = invocation.getArgument(0);
            assertEquals("https://api.moonshot.cn/v1/chat/completions", request.uri().toString());
            assertEquals("Bearer test-only-token", request.headers().firstValue("Authorization").orElseThrow());
            assertEquals(60000, request.timeout().orElseThrow().toMillis());
            assertEquals("probe-1", request.headers().firstValue("X-Request-ID").orElseThrow());
            return response(200, envelope("stop", "{\"resultCode\":\"0\"}"));
        });
        assertEquals("0", client(http).complete("Return JSON", Map.of(), "probe-1").path("resultCode").asText());
        verify(http, times(1)).send(any(), any(HttpResponse.BodyHandler.class));
    }

    @Test
    void rejectsTruncatedAndNonObjectModelResults() throws Exception {
        for (String body : new String[]{envelope("length", "{}"), envelope("stop", "[]"),
                envelope("stop", "```json\n{}\n```"), envelope("stop", "{} {}")}) {
            HttpClient http = mock(HttpClient.class);
            HttpResponse<String> stubResponse = response(200, body);
            when(http.send(any(), any(HttpResponse.BodyHandler.class))).thenReturn(stubResponse);
            assertEquals("1002", assertThrows(MoonshotChatClient.CallFailure.class,
                    () -> client(http).complete("JSON", Map.of(), "probe")).code());
        }
    }

    @Test
    void upstreamErrorDoesNotExposeRawBodyOrRetry() throws Exception {
        HttpClient http = mock(HttpClient.class);
        HttpResponse<String> stubResponse = response(429, "sensitive upstream diagnostic test-only-token");
        when(http.send(any(), any(HttpResponse.BodyHandler.class)))
                .thenReturn(stubResponse);
        MoonshotChatClient.CallFailure error = assertThrows(MoonshotChatClient.CallFailure.class,
                () -> client(http).complete("JSON", Map.of(), "probe"));
        assertEquals("1003", error.code());
        assertFalse(error.getMessage().contains("test-only-token"));
        assertTrue(error.getMessage().contains("429"));
        verify(http, times(1)).send(any(), any(HttpResponse.BodyHandler.class));
    }

    @Test
    void missingKeyFailsBeforeNetworkAndTimeoutIsClassified() throws Exception {
        HttpClient http = mock(HttpClient.class);
        MoonshotChatClient missing = new MoonshotChatClient(http, mapper, "https://api.moonshot.cn/v1",
                "", "kimi-k2.6", 4096, 60000);
        assertEquals("1004", assertThrows(MoonshotChatClient.CallFailure.class,
                () -> missing.complete("JSON", Map.of(), "probe")).code());
        verifyNoInteractions(http);
        when(http.send(any(), any(HttpResponse.BodyHandler.class))).thenThrow(new HttpTimeoutException("internal detail"));
        assertEquals("1003", assertThrows(MoonshotChatClient.CallFailure.class,
                () -> client(http).complete("JSON", Map.of(), "probe")).code());
    }
}
