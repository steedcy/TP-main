package com.airport.ai.planning;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

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
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Secondary planning-model transport supporting both OpenAI-compatible relay endpoints
 * (e.g. {@code https://ai.axuremart.com/v1/chat/completions} for {@code gpt-6.1-sol})
 * and Anthropic native Messages endpoints ({@code https://api.anthropic.com/v1/messages} for {@code claude-*}).
 * Same safety rules as the Kimi transport: HTTPS only, no redirects, no automatic retries,
 * privacy-sanitised input and no credential or raw upstream body in errors/logs.
 */
public class ClaudeChatClient implements PlanningChatClient {
    private static final Logger LOG = LoggerFactory.getLogger(ClaudeChatClient.class);
    static final String ANTHROPIC_VERSION = "2023-06-01";
    static final String DEFAULT_BASE_URL = "https://ai.axuremart.com/v1";
    static final String DEFAULT_MODEL = "gpt-6.1-sol";
    static final String JSON_ONLY_SUFFIX = "\n\n输出要求：只输出一个 JSON 对象本身，不要输出 Markdown 代码块、解释或任何其他文字。";
    private static final Pattern FENCED = Pattern.compile("^```(?:json)?\\s*\\n(.*)\\n```$", Pattern.DOTALL);

    private final HttpClient httpClient;
    private final ObjectMapper mapper;
    private volatile String configuredBaseUrl;
    private volatile URI endpoint;
    private volatile boolean anthropicProtocol;
    private volatile String apiKey;
    private volatile String model;
    private final int maxTokens;
    private final Duration timeout;

    public ClaudeChatClient(ObjectMapper mapper, String baseUrl, String apiKey, String model,
                            int maxTokens, long timeoutMs) {
        this(HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(10))
                .followRedirects(HttpClient.Redirect.NEVER).build(), mapper,
                baseUrl, apiKey, model, maxTokens, timeoutMs);
    }

    ClaudeChatClient(HttpClient httpClient, ObjectMapper mapper, String baseUrl, String apiKey,
                     String model, int maxTokens, long timeoutMs) {
        this.httpClient = httpClient;
        this.mapper = mapper;
        if (maxTokens < 1 || maxTokens > 64000 || timeoutMs < 1 || timeoutMs > 60000) {
            throw new IllegalArgumentException("Invalid secondary model token limit or timeout (maximum 60000 ms)");
        }
        this.maxTokens = maxTokens;
        this.timeout = Duration.ofMillis(timeoutMs);
        reconfigure(baseUrl, apiKey, model);
    }

    public synchronized void reconfigure(String baseUrl, String apiKey, String model) {
        String base = (baseUrl == null || baseUrl.isBlank() ? DEFAULT_BASE_URL : baseUrl.trim())
                .replaceAll("/+$", "");
        boolean useAnthropic = isAnthropicNative(base);
        String suffix = useAnthropic ? "/messages" : "/chat/completions";
        URI nextEndpoint = URI.create(base.endsWith("/v1") ? base + suffix : base + "/v1" + suffix);
        if (!"https".equals(nextEndpoint.getScheme()) || nextEndpoint.getUserInfo() != null
                || nextEndpoint.getQuery() != null || nextEndpoint.getFragment() != null) {
            throw new IllegalArgumentException("Secondary model base URL must be HTTPS without credentials or query parameters");
        }
        this.configuredBaseUrl = base;
        this.endpoint = nextEndpoint;
        this.anthropicProtocol = useAnthropic;
        this.apiKey = apiKey == null ? "" : apiKey.trim();
        this.model = model == null ? "" : model.trim();
    }

    private static boolean isAnthropicNative(String base) {
        return base.contains("anthropic.com");
    }

    public String baseUrl() { return configuredBaseUrl; }
    public String apiKey() { return apiKey; }
    public String model() { return model; }

    URI endpoint() { return endpoint; }
    Duration timeout() { return timeout; }

    @Override
    public JsonNode complete(String instruction, Object input, String requestId) {
        return complete(instruction, input, requestId, timeout);
    }

    @Override
    public JsonNode complete(String instruction, Object input, String requestId, Duration timeout) {
        URI currentEndpoint = this.endpoint;
        boolean useAnthropic = this.anthropicProtocol;
        String currentApiKey = this.apiKey;
        String currentModel = this.model;
        if (currentApiKey.isBlank() || currentModel.isBlank()) {
            throw MoonshotChatClient.CallFailure.unavailable("1004", "第二模型密钥或模型名称未配置");
        }
        long started = System.nanoTime();
        try {
            String userContent = mapper.writeValueAsString(input);
            userContent = com.airport.ai.task.SceneParamsPrivacyGuard.sanitizeText(userContent);
            Map<String, Object> body = new LinkedHashMap<>();
            body.put("model", currentModel);
            body.put("max_tokens", maxTokens);
            body.put("stream", false);

            HttpRequest.Builder reqBuilder = HttpRequest.newBuilder(currentEndpoint).timeout(timeout)
                    .header("Content-Type", "application/json")
                    .header("X-Request-ID", requestId != null && requestId.matches("[A-Za-z0-9_-]{1,128}")
                            ? requestId : UUID.randomUUID().toString());

            if (useAnthropic) {
                body.put("system", instruction + JSON_ONLY_SUFFIX);
                body.put("messages", List.of(Map.of("role", "user", "content", userContent)));
                reqBuilder.header("x-api-key", currentApiKey)
                        .header("anthropic-version", ANTHROPIC_VERSION);
            } else {
                body.put("messages", List.of(
                        Map.of("role", "system", "content", instruction + JSON_ONLY_SUFFIX),
                        Map.of("role", "user", "content", userContent)));
                body.put("response_format", Map.of("type", "json_object"));
                reqBuilder.header("Authorization", "Bearer " + currentApiKey);
            }

            HttpRequest request = reqBuilder
                    .POST(HttpRequest.BodyPublishers.ofString(mapper.writeValueAsString(body), StandardCharsets.UTF_8))
                    .build();
            HttpResponse<String> response = httpClient.send(request,
                    HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));
            if (response.statusCode() != 200) {
                throw MoonshotChatClient.CallFailure.unavailable("1003", "第二模型调用失败，HTTP " + response.statusCode());
            }
            JsonNode envelope = readObject(response.body());
            String content = useAnthropic ? extractAnthropicText(envelope) : extractOpenAiText(envelope);
            Matcher fenced = FENCED.matcher(content);
            if (fenced.matches()) content = fenced.group(1).trim();
            JsonNode result = readObject(content);
            JsonNode usage = envelope.path("usage");
            int inTokens = usage.path("prompt_tokens").asInt(usage.path("input_tokens").asInt(0));
            int outTokens = usage.path("completion_tokens").asInt(usage.path("output_tokens").asInt(0));
            LOG.info("SecondaryModel model={} elapsedMs={} inputTokens={} outputTokens={}", currentModel,
                    (System.nanoTime() - started) / 1_000_000, inTokens, outTokens);
            return result;
        } catch (MoonshotChatClient.CallFailure ex) {
            throw ex;
        } catch (InterruptedException ex) {
            Thread.currentThread().interrupt();
            throw new MoonshotChatClient.CallFailure("1003", "第二模型调用已中断");
        } catch (java.net.http.HttpTimeoutException ex) {
            throw MoonshotChatClient.CallFailure.unavailable("1003", "第二模型调用超时");
        } catch (JsonProcessingException ex) {
            throw new MoonshotChatClient.CallFailure("1002", "第二模型返回内容不是有效 JSON");
        } catch (IOException ex) {
            throw MoonshotChatClient.CallFailure.unavailable("1003", "第二模型网络连接异常");
        }
    }

    private String extractOpenAiText(JsonNode envelope) {
        JsonNode choices = envelope.path("choices");
        if (!choices.isArray() || choices.isEmpty()) {
            throw new MoonshotChatClient.CallFailure("1002", "第二模型响应为空、被截断或未正常完成");
        }
        JsonNode first = choices.get(0);
        String finishReason = first.path("finish_reason").asText("");
        if (!finishReason.isEmpty() && !"stop".equals(finishReason)) {
            throw new MoonshotChatClient.CallFailure("1002", "第二模型响应为空、被截断或未正常完成");
        }
        JsonNode content = first.path("message").path("content");
        if (!content.isTextual() || content.asText().isBlank()) {
            throw new MoonshotChatClient.CallFailure("1002", "第二模型未返回 JSON 内容");
        }
        return content.asText().trim();
    }

    private String extractAnthropicText(JsonNode envelope) {
        if (!"end_turn".equals(envelope.path("stop_reason").asText())) {
            throw new MoonshotChatClient.CallFailure("1002", "第二模型响应为空、被截断或未正常完成");
        }
        StringBuilder text = new StringBuilder();
        for (JsonNode block : envelope.path("content")) {
            if ("text".equals(block.path("type").asText()) && block.path("text").isTextual()) {
                text.append(block.path("text").asText());
            }
        }
        String content = text.toString().trim();
        if (content.isEmpty()) {
            throw new MoonshotChatClient.CallFailure("1002", "第二模型未返回 JSON 内容");
        }
        return content;
    }

    private JsonNode readObject(String text) throws IOException {
        JsonNode node = mapper.reader().with(DeserializationFeature.FAIL_ON_TRAILING_TOKENS).readTree(text);
        if (node == null || !node.isObject()) {
            throw new MoonshotChatClient.CallFailure("1002", "第二模型返回内容必须为 JSON 对象");
        }
        return node;
    }
}
