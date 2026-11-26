package com.airport.ai.planning;

import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.core.JsonProcessingException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/** Kimi transport only: no device commands, automatic retries, or credential logging. */
@Component
@ConditionalOnProperty(name = "app.planning-model.provider", havingValue = "moonshot")
public class MoonshotChatClient implements PlanningChatClient {
    private static final Logger LOG = LoggerFactory.getLogger(MoonshotChatClient.class);
    private final HttpClient httpClient;
    private final ObjectMapper mapper;
    private volatile URI endpoint;
    private volatile String apiKey;
    private volatile String model;
    private final int maxTokens;
    private final Duration timeout;

    @Autowired
    public MoonshotChatClient(ObjectMapper mapper,
            @Value("${app.planning-model.moonshot.base-url:https://api.moonshot.cn/v1}") String baseUrl,
            @Value("${app.planning-model.moonshot.api-key:}") String apiKey,
            @Value("${app.planning-model.moonshot.model:kimi-k2.6}") String model,
            @Value("${app.planning-model.moonshot.max-tokens:4096}") int maxTokens,
            @Value("${app.planning-model.timeout-ms:60000}") long timeoutMs) {
        this(HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(10))
                .followRedirects(HttpClient.Redirect.NEVER).build(), mapper,
                baseUrl, apiKey, model, maxTokens, timeoutMs);
    }

    MoonshotChatClient(HttpClient httpClient, ObjectMapper mapper, String baseUrl,
                       String apiKey, String model, int maxTokens, long timeoutMs) {
        this.httpClient = httpClient;
        this.mapper = mapper;
        if (maxTokens < 1 || maxTokens > 32768 || timeoutMs < 1 || timeoutMs > 60000) {
            throw new IllegalArgumentException("Invalid Moonshot token limit or timeout (maximum 60000 ms)");
        }
        this.maxTokens = maxTokens;
        this.timeout = Duration.ofMillis(timeoutMs);
        reconfigure(baseUrl, apiKey, model);
    }

    public synchronized void reconfigure(String baseUrl, String apiKey, String model) {
        String base = (baseUrl == null || baseUrl.isBlank() ? "https://api.moonshot.cn/v1" : baseUrl.trim())
                .replaceAll("/+$", "");
        URI nextEndpoint = URI.create(base + "/chat/completions");
        if (!"https".equals(nextEndpoint.getScheme()) || nextEndpoint.getUserInfo() != null
                || nextEndpoint.getQuery() != null || nextEndpoint.getFragment() != null) {
            throw new IllegalArgumentException("Moonshot base URL must be HTTPS without credentials or query parameters");
        }
        this.endpoint = nextEndpoint;
        this.apiKey = apiKey == null ? "" : apiKey.trim();
        this.model = model;
    }

    public String baseUrl() {
        String raw = endpoint.toString();
        return raw.endsWith("/chat/completions") ? raw.substring(0, raw.length() - "/chat/completions".length()) : raw;
    }

    public String apiKey() { return apiKey; }
    public String model() { return model; }

    @Override
    public JsonNode complete(String instruction, Object input, String requestId) {
        return complete(instruction, input, requestId, timeout);
    }

    @Override
    public JsonNode complete(String instruction, Object input, String requestId, Duration timeout) {
        URI currentEndpoint = this.endpoint;
        String currentApiKey = this.apiKey;
        String currentModel = this.model;
        if (currentApiKey.isBlank() || currentModel == null || currentModel.isBlank()) {
            throw CallFailure.unavailable("1004", "Kimi 密钥或模型名称未配置");
        }
        long started = System.nanoTime();
        try {
            Map<String, Object> body = new LinkedHashMap<>();
            body.put("model", currentModel);
            String userContent = mapper.writeValueAsString(input);
            userContent = com.airport.ai.task.SceneParamsPrivacyGuard.sanitizeText(userContent);
            body.put("messages", List.of(Map.of("role", "system", "content", instruction),
                    Map.of("role", "user", "content", userContent)));
            body.put("response_format", Map.of("type", "json_object"));
            body.put("max_tokens", maxTokens);
            body.put("stream", false);
            if ("kimi-k2.6".equals(currentModel)) body.put("thinking", Map.of("type", "disabled"));
            if ("kimi-k3".equals(currentModel)) body.put("reasoning_effort", "low");
            HttpRequest request = HttpRequest.newBuilder(currentEndpoint).timeout(timeout)
                    .header("Content-Type", "application/json")
                    .header("Authorization", "Bearer " + currentApiKey)
                    .header("X-Request-ID", requestId != null && requestId.matches("[A-Za-z0-9_-]{1,128}")
                            ? requestId : UUID.randomUUID().toString())
                    .POST(HttpRequest.BodyPublishers.ofString(mapper.writeValueAsString(body), StandardCharsets.UTF_8))
                    .build();
            HttpResponse<String> response = httpClient.send(request,
                    HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));
            if (response.statusCode() != 200) {
                // Do not pass raw upstream bodies or exception text into user-facing task events.
                throw CallFailure.unavailable("1003", "Kimi 调用失败，HTTP " + response.statusCode());
            }
            JsonNode envelope = readObject(response.body());
            JsonNode choices = envelope.path("choices");
            if (!choices.isArray() || choices.size() != 1
                    || !"stop".equals(choices.get(0).path("finish_reason").asText())) {
                throw new CallFailure("1002", "Kimi 响应为空、被截断或未正常完成");
            }
            JsonNode content = choices.get(0).path("message").path("content");
            if (!content.isTextual() || content.asText().isBlank()) {
                throw new CallFailure("1002", "Kimi 未返回 JSON 内容");
            }
            JsonNode result = readObject(content.asText());
            LOG.info("Kimi model={} elapsedMs={} inputTokens={} outputTokens={}", currentModel,
                    (System.nanoTime() - started) / 1_000_000,
                    envelope.path("usage").path("prompt_tokens").asInt(),
                    envelope.path("usage").path("completion_tokens").asInt());
            return result;
        } catch (CallFailure ex) {
            throw ex;
        } catch (InterruptedException ex) {
            Thread.currentThread().interrupt();
            throw new CallFailure("1003", "Kimi 调用已中断");
        } catch (java.net.http.HttpTimeoutException ex) {
            throw CallFailure.unavailable("1003", "Kimi 调用超时");
        } catch (JsonProcessingException ex) {
            throw new CallFailure("1002", "Kimi 返回内容不是有效 JSON");
        } catch (IOException ex) {
            throw CallFailure.unavailable("1003", "Kimi 网络连接异常");
        }
    }

    private JsonNode readObject(String text) throws IOException {
        JsonNode node = mapper.reader().with(DeserializationFeature.FAIL_ON_TRAILING_TOKENS).readTree(text);
        if (node == null || !node.isObject()) throw new CallFailure("1002", "Kimi 返回内容必须为 JSON 对象");
        return node;
    }

    /**
     * Model call failure. {@code providerUnavailable} is true only when the provider itself could not
     * serve the call (unconfigured, timeout, network error, non-200 HTTP); content/protocol errors (1002)
     * are never marked unavailable and therefore never trigger failover to the secondary model.
     */
    public static class CallFailure extends RuntimeException {
        private final String code;
        private final boolean providerUnavailable;
        public CallFailure(String code, String message) { this(code, message, false); }
        public CallFailure(String code, String message, boolean providerUnavailable) {
            super(message);
            this.code = code;
            this.providerUnavailable = providerUnavailable;
        }
        public static CallFailure unavailable(String code, String message) {
            return new CallFailure(code, message, true);
        }
        public String code() { return code; }
        public boolean providerUnavailable() { return providerUnavailable; }
    }
}
