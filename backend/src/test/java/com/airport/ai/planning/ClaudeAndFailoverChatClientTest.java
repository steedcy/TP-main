package com.airport.ai.planning;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.net.http.HttpTimeoutException;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

class ClaudeAndFailoverChatClientTest {
    private final ObjectMapper mapper = new ObjectMapper();

    @SuppressWarnings("unchecked")
    private HttpResponse<String> response(int status, String body) {
        HttpResponse<String> response = mock(HttpResponse.class);
        when(response.statusCode()).thenReturn(status);
        when(response.body()).thenReturn(body);
        return response;
    }

    private String claudeEnvelope(String stopReason, String text) throws Exception {
        return mapper.writeValueAsString(Map.of(
                "stop_reason", stopReason,
                "content", List.of(Map.of("type", "text", "text", text)),
                "usage", Map.of("input_tokens", 12, "output_tokens", 8)));
    }

    private String kimiEnvelope(String finishReason, String content) throws Exception {
        return mapper.writeValueAsString(Map.of("choices", new Object[]{
                Map.of("finish_reason", finishReason, "message", Map.of("content", content))}));
    }

    @Test
    void secondaryClientUsesOpenAiCompatibleRelayForAxuremartGpt61Sol() throws Exception {
        HttpClient http = mock(HttpClient.class);
        when(http.send(any(), any(HttpResponse.BodyHandler.class))).thenAnswer(invocation -> {
            HttpRequest request = invocation.getArgument(0);
            assertEquals("https://ai.axuremart.com/v1/chat/completions", request.uri().toString());
            assertEquals("Bearer relay-test-key", request.headers().firstValue("Authorization").orElseThrow());
            assertEquals(30000, request.timeout().orElseThrow().toMillis());
            return response(200, kimiEnvelope("stop", "{\"resultCode\":\"0\",\"source\":\"gpt-6.1-sol\"}"));
        });
        ClaudeChatClient client = new ClaudeChatClient(http, mapper, "https://ai.axuremart.com/v1",
                "relay-test-key", "gpt-6.1-sol", 4096, 30000);
        JsonNode out = client.complete("Return JSON", Map.of(), "req-relay");
        assertEquals("0", out.path("resultCode").asText());
        assertEquals("gpt-6.1-sol", out.path("source").asText());
        verify(http, times(1)).send(any(), any(HttpResponse.BodyHandler.class));
    }

    @Test
    void claudeClientUsesAnthropicMessagesHeadersAndEndpoint() throws Exception {
        HttpClient http = mock(HttpClient.class);
        when(http.send(any(), any(HttpResponse.BodyHandler.class))).thenAnswer(invocation -> {
            HttpRequest request = invocation.getArgument(0);
            assertEquals("https://api.anthropic.com/v1/messages", request.uri().toString());
            assertEquals("test-claude-key", request.headers().firstValue("x-api-key").orElseThrow());
            assertEquals(ClaudeChatClient.ANTHROPIC_VERSION,
                    request.headers().firstValue("anthropic-version").orElseThrow());
            assertEquals(30000, request.timeout().orElseThrow().toMillis());
            return response(200, claudeEnvelope("end_turn", "{\"resultCode\":\"0\"}"));
        });
        ClaudeChatClient client = new ClaudeChatClient(http, mapper, "https://api.anthropic.com/",
                "test-claude-key", "claude-sonnet-5-5", 4096, 30000);
        assertEquals("0", client.complete("Return JSON", Map.of(), "req-1").path("resultCode").asText());
        verify(http, times(1)).send(any(), any(HttpResponse.BodyHandler.class));
    }

    @Test
    void claudeClientUnwrapsFencedJsonAndRejectsTruncatedOutput() throws Exception {
        HttpClient http = mock(HttpClient.class);
        HttpResponse<String> fenced = response(200, claudeEnvelope("end_turn", "```json\n{\"resultCode\":\"0\"}\n```"));
        HttpResponse<String> maxTokens = response(200, claudeEnvelope("max_tokens", "{\"resultCode\":\"0\"}"));
        when(http.send(any(), any(HttpResponse.BodyHandler.class))).thenReturn(fenced, maxTokens);
        ClaudeChatClient client = new ClaudeChatClient(http, mapper, "https://api.anthropic.com/v1",
                "test-claude-key", "claude-sonnet-5-5", 4096, 30000);
        assertEquals("0", client.complete("JSON", Map.of(), "req-1").path("resultCode").asText());
        MoonshotChatClient.CallFailure err = assertThrows(MoonshotChatClient.CallFailure.class,
                () -> client.complete("JSON", Map.of(), "req-2"));
        assertEquals("1002", err.code());
        assertFalse(err.providerUnavailable());
    }

    @Test
    void failoverCallsClaudeWhenKimiIsUnavailable() throws Exception {
        HttpClient kimiHttp = mock(HttpClient.class);
        HttpClient claudeHttp = mock(HttpClient.class);
        HttpResponse<String> kimi503 = response(503, "upstream unavailable");
        HttpResponse<String> claudeOk = response(200, claudeEnvelope("end_turn", "{\"resultCode\":\"0\",\"source\":\"claude\"}"));
        when(kimiHttp.send(any(), any(HttpResponse.BodyHandler.class))).thenReturn(kimi503);
        when(claudeHttp.send(any(), any(HttpResponse.BodyHandler.class))).thenReturn(claudeOk);

        MoonshotChatClient primary = new MoonshotChatClient(kimiHttp, mapper, "https://api.moonshot.cn/v1",
                "kimi-key", "kimi-k2.6", 4096, 60000);
        ClaudeChatClient secondary = new ClaudeChatClient(claudeHttp, mapper, "https://api.anthropic.com",
                "claude-key", "claude-sonnet-5-5", 4096, 30000);
        FailoverChatClient failover = new FailoverChatClient(primary, secondary, 30000, 30000, 60000);

        JsonNode result = failover.complete("JSON", Map.of(), "req-failover");
        assertEquals("claude", result.path("source").asText());
        verify(kimiHttp, times(1)).send(any(), any(HttpResponse.BodyHandler.class));
        verify(claudeHttp, times(1)).send(any(), any(HttpResponse.BodyHandler.class));
    }

    @Test
    void failoverAlsoSwitchesOnKimiTimeoutOrMissingKey() throws Exception {
        HttpClient kimiHttp = mock(HttpClient.class);
        HttpClient claudeHttp = mock(HttpClient.class);
        HttpResponse<String> claudeOk = response(200, claudeEnvelope("end_turn", "{\"resultCode\":\"0\"}"));
        when(kimiHttp.send(any(), any(HttpResponse.BodyHandler.class)))
                .thenThrow(new HttpTimeoutException("timed out"));
        when(claudeHttp.send(any(), any(HttpResponse.BodyHandler.class))).thenReturn(claudeOk);

        MoonshotChatClient primary = new MoonshotChatClient(kimiHttp, mapper, "https://api.moonshot.cn/v1",
                "kimi-key", "kimi-k2.6", 4096, 60000);
        ClaudeChatClient secondary = new ClaudeChatClient(claudeHttp, mapper, "https://api.anthropic.com",
                "claude-key", "claude-sonnet-5-5", 4096, 30000);
        FailoverChatClient failover = new FailoverChatClient(primary, secondary, 30000, 30000, 60000);

        assertEquals("0", failover.complete("JSON", Map.of(), "req-timeout").path("resultCode").asText());
        verify(claudeHttp, times(1)).send(any(), any(HttpResponse.BodyHandler.class));
    }

    @Test
    void failoverDoesNotSwitchOnContentError1002() throws Exception {
        HttpClient kimiHttp = mock(HttpClient.class);
        HttpClient claudeHttp = mock(HttpClient.class);
        HttpResponse<String> kimiBadJson = response(200, kimiEnvelope("stop", "not valid json"));
        when(kimiHttp.send(any(), any(HttpResponse.BodyHandler.class))).thenReturn(kimiBadJson);

        MoonshotChatClient primary = new MoonshotChatClient(kimiHttp, mapper, "https://api.moonshot.cn/v1",
                "kimi-key", "kimi-k2.6", 4096, 60000);
        ClaudeChatClient secondary = new ClaudeChatClient(claudeHttp, mapper, "https://api.anthropic.com",
                "claude-key", "claude-sonnet-5-5", 4096, 30000);
        FailoverChatClient failover = new FailoverChatClient(primary, secondary, 30000, 30000, 60000);

        MoonshotChatClient.CallFailure err = assertThrows(MoonshotChatClient.CallFailure.class,
                () -> failover.complete("JSON", Map.of(), "req-1002"));
        assertEquals("1002", err.code());
        verify(kimiHttp, times(1)).send(any(), any(HttpResponse.BodyHandler.class));
        verifyNoInteractions(claudeHttp);
    }

    @Test
    void configServicePersistsEncryptedKeysMasksViewAndHotReloadsRuntime() {
        Map<String, String> store = new java.util.HashMap<>();
        com.airport.ai.device.SystemSettingMapper settings = mock(com.airport.ai.device.SystemSettingMapper.class);
        when(settings.findValue(anyString())).thenAnswer(inv -> store.get(inv.getArgument(0)));
        when(settings.upsert(anyString(), anyString(), anyString())).thenAnswer(inv -> {
            store.put(inv.getArgument(0), inv.getArgument(1));
            return 1;
        });
        com.airport.ai.auth.OperationLogService audit = mock(com.airport.ai.auth.OperationLogService.class);
        com.airport.ai.taskdef.TaskDefinitionMapper defs = mock(com.airport.ai.taskdef.TaskDefinitionMapper.class);

        PlanningModelConfigService svc = new PlanningModelConfigService(
                settings, audit, defs, mapper, null, null, null,
                "unit-test-encryption-secret-32chars",
                "https://api.moonshot.cn/v1", "", "kimi-k2.6", 4096,
                false, "https://ai.axuremart.com/v1", "", "gpt-6.1-sol", 4096,
                30000, 30000, 60000);

        com.airport.ai.auth.User admin = new com.airport.ai.auth.User();
        admin.setId(1L);
        admin.setUsername("sysadmin");
        admin.setRole("SYSTEM_ADMIN");

        Map<String, Object> view = svc.update(new PlanningModelConfigService.UpdateRequest(
                "https://api.moonshot.cn/v1", "kimi-k2.6", "sk-kimi-secret-1234", false,
                true, "https://ai.axuremart.com/v1", "gpt-6.1-sol", "sk-relay-secret-5678", false), admin);

        assertEquals(true, view.get("moonshotKeyConfigured"));
        assertEquals("sk****34", view.get("moonshotApiKeyMasked"));
        assertEquals(true, view.get("claudeKeyConfigured"));
        assertEquals("sk****78", view.get("claudeApiKeyMasked"));
        assertEquals("https://ai.axuremart.com/v1", view.get("claudeBaseUrl"));
        assertEquals("gpt-6.1-sol", view.get("claudeModel"));
        assertEquals(true, view.get("fallbackEnabled"));
        assertTrue(store.get(PlanningModelConfigService.KEY_MOONSHOT_API_KEY).startsWith("ENC:"));
        assertFalse(store.get(PlanningModelConfigService.KEY_MOONSHOT_API_KEY).contains("sk-kimi-secret-1234"));
        assertTrue(store.get(PlanningModelConfigService.KEY_CLAUDE_API_KEY).startsWith("ENC:"));
        assertFalse(store.get(PlanningModelConfigService.KEY_CLAUDE_API_KEY).contains("sk-relay-secret-5678"));
        assertTrue(svc.hasLiveModelKey());

        // Blank key on subsequent save preserves existing key
        Map<String, Object> view2 = svc.update(new PlanningModelConfigService.UpdateRequest(
                null, "kimi-k2.6", "", false,
                true, "SECONDARY_ONLY", null, "gpt-6.1-sol", "", false), admin);
        assertEquals("sk****34", view2.get("moonshotApiKeyMasked"));
        assertEquals("sk****78", view2.get("claudeApiKeyMasked"));
        assertEquals("SECONDARY_ONLY", view2.get("activeMode"));
    }

    @Test
    void manualSecondaryOnlyModeBypassesPrimaryAndRecordsLastUsedModel() throws Exception {
        HttpClient kimiHttp = mock(HttpClient.class);
        HttpClient relayHttp = mock(HttpClient.class);
        HttpResponse<String> relayOk = response(200, kimiEnvelope("stop", "{\"resultCode\":\"0\",\"source\":\"manual-second\"}"));
        when(relayHttp.send(any(), any(HttpResponse.BodyHandler.class))).thenReturn(relayOk);

        MoonshotChatClient primary = new MoonshotChatClient(kimiHttp, mapper, "https://api.moonshot.cn/v1",
                "kimi-key", "kimi-k2.6", 4096, 60000);
        ClaudeChatClient secondary = new ClaudeChatClient(relayHttp, mapper, "https://ai.axuremart.com/v1",
                "relay-key", "gpt-6.1-sol", 4096, 30000);
        FailoverChatClient failover = new FailoverChatClient(primary, secondary, 30000, 30000, 60000);
        failover.setActiveMode(FailoverChatClient.MODE_SECONDARY_ONLY);

        JsonNode result = failover.complete("JSON", Map.of(), "req-manual");
        assertEquals("manual-second", result.path("source").asText());
        assertEquals("SECONDARY", failover.lastUsedSlot());
        assertEquals("gpt-6.1-sol", failover.lastUsedModel());
        verifyNoInteractions(kimiHttp);
        verify(relayHttp, times(1)).send(any(), any(HttpResponse.BodyHandler.class));
    }
}
