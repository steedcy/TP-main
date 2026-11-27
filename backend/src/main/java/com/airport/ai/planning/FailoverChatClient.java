package com.airport.ai.planning;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Primary;
import org.springframework.stereotype.Component;

import java.time.Duration;
import java.time.Instant;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;

/**
 * Primary (Kimi) / Secondary (gpt-6.1-sol or Claude) routing and automatic failover.
 * Supports three routing modes:
 * <ul>
 *   <li>{@code AUTO_FAILOVER}: calls primary first; switches to secondary only when primary is unavailable
 *       (1003/1004). Content/protocol errors (1002) never fail over.</li>
 *   <li>{@code PRIMARY_ONLY}: always calls primary model only.</li>
 *   <li>{@code SECONDARY_ONLY}: manually switched to always call secondary model directly.</li>
 * </ul>
 */
@Component
@Primary
@ConditionalOnProperty(name = "app.planning-model.provider", havingValue = "moonshot")
public class FailoverChatClient implements PlanningChatClient {
    private static final Logger LOG = LoggerFactory.getLogger(FailoverChatClient.class);
    static final long MIN_SECONDARY_BUDGET_MS = 3000;
    private static final DateTimeFormatter TS_FMT =
            DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss").withZone(ZoneId.of("Asia/Shanghai"));

    public static final String MODE_AUTO_FAILOVER = "AUTO_FAILOVER";
    public static final String MODE_PRIMARY_ONLY = "PRIMARY_ONLY";
    public static final String MODE_SECONDARY_ONLY = "SECONDARY_ONLY";

    private final PlanningChatClient primary;
    private final PlanningChatClient secondary;
    private final MoonshotChatClient moonshotPrimary;
    private final ClaudeChatClient claudeSecondary;
    private volatile boolean fallbackEnabled;
    private volatile String activeMode;
    private final Duration primaryTimeout;
    private final Duration secondaryTimeout;
    private final Duration totalBudget;

    private volatile String lastUsedSlot = "NONE";
    private volatile String lastUsedModel = "";
    private volatile String lastCallStatus = "尚未发生模型调用";
    private volatile String lastCallAt = "";

    @Autowired
    public FailoverChatClient(MoonshotChatClient primary, ObjectMapper mapper,
            @Value("${app.planning-model.fallback.enabled:false}") boolean fallbackEnabled,
            @Value("${app.planning-model.fallback.base-url:https://ai.axuremart.com/v1}") String baseUrl,
            @Value("${app.planning-model.fallback.api-key:}") String apiKey,
            @Value("${app.planning-model.fallback.model:gpt-6.1-sol}") String model,
            @Value("${app.planning-model.fallback.max-tokens:4096}") int maxTokens,
            @Value("${app.planning-model.fallback.timeout-ms:30000}") long secondaryTimeoutMs,
            @Value("${app.planning-model.fallback.primary-timeout-ms:30000}") long primaryTimeoutMs,
            @Value("${app.planning-model.timeout-ms:60000}") long totalBudgetMs) {
        this(primary, new ClaudeChatClient(mapper, baseUrl, apiKey, model, maxTokens, secondaryTimeoutMs),
                fallbackEnabled, primaryTimeoutMs, secondaryTimeoutMs, totalBudgetMs);
        setActiveMode(MODE_SECONDARY_ONLY);
    }

    FailoverChatClient(PlanningChatClient primary, PlanningChatClient secondary,
                       long primaryTimeoutMs, long secondaryTimeoutMs, long totalBudgetMs) {
        this(primary, secondary, true, primaryTimeoutMs, secondaryTimeoutMs, totalBudgetMs);
    }

    FailoverChatClient(PlanningChatClient primary, PlanningChatClient secondary, boolean fallbackEnabled,
                       long primaryTimeoutMs, long secondaryTimeoutMs, long totalBudgetMs) {
        if (totalBudgetMs < 1 || totalBudgetMs > 60000 || primaryTimeoutMs < 1 || secondaryTimeoutMs < 1
                || primaryTimeoutMs >= totalBudgetMs) {
            throw new IllegalArgumentException("Invalid failover timeouts: primary must be shorter than the "
                    + "overall budget (maximum 60000 ms)");
        }
        this.primary = primary;
        this.secondary = secondary;
        this.moonshotPrimary = primary instanceof MoonshotChatClient m ? m : null;
        this.claudeSecondary = secondary instanceof ClaudeChatClient c ? c : null;
        this.fallbackEnabled = fallbackEnabled;
        this.activeMode = fallbackEnabled ? MODE_AUTO_FAILOVER : MODE_PRIMARY_ONLY;
        this.primaryTimeout = Duration.ofMillis(primaryTimeoutMs);
        this.secondaryTimeout = Duration.ofMillis(secondaryTimeoutMs);
        this.totalBudget = Duration.ofMillis(totalBudgetMs);
    }

    public boolean isFallbackEnabled() { return fallbackEnabled; }

    public void setFallbackEnabled(boolean fallbackEnabled) {
        this.fallbackEnabled = fallbackEnabled;
        if (!MODE_SECONDARY_ONLY.equals(this.activeMode)) {
            this.activeMode = fallbackEnabled ? MODE_AUTO_FAILOVER : MODE_PRIMARY_ONLY;
        }
    }

    public String activeMode() { return activeMode; }

    public void setActiveMode(String mode) {
        if (MODE_SECONDARY_ONLY.equalsIgnoreCase(mode)) {
            this.activeMode = MODE_SECONDARY_ONLY;
        } else if (MODE_PRIMARY_ONLY.equalsIgnoreCase(mode)) {
            this.activeMode = MODE_PRIMARY_ONLY;
            this.fallbackEnabled = false;
        } else {
            this.activeMode = MODE_AUTO_FAILOVER;
            this.fallbackEnabled = true;
        }
    }

    public ClaudeChatClient claudeSecondary() { return claudeSecondary; }
    public String lastUsedSlot() { return lastUsedSlot; }
    public String lastUsedModel() { return lastUsedModel; }
    public String lastCallStatus() { return lastCallStatus; }
    public String lastCallAt() { return lastCallAt; }

    private String primaryModelName() {
        return moonshotPrimary != null && moonshotPrimary.model() != null ? moonshotPrimary.model() : "kimi-k2.6";
    }

    private String secondaryModelName() {
        return claudeSecondary != null && claudeSecondary.model() != null && !claudeSecondary.model().isBlank()
                ? claudeSecondary.model() : ClaudeChatClient.DEFAULT_MODEL;
    }

    private void recordCall(String slot, String modelName, String status) {
        this.lastUsedSlot = slot;
        this.lastUsedModel = modelName;
        this.lastCallStatus = status;
        this.lastCallAt = TS_FMT.format(Instant.now());
    }

    @Override
    public JsonNode complete(String instruction, Object input, String requestId) {
        return complete(instruction, input, requestId, totalBudget);
    }

    @Override
    public JsonNode complete(String instruction, Object input, String requestId, Duration budget) {
        Duration overall = budget.compareTo(totalBudget) < 0 ? budget : totalBudget;
        String mode = this.activeMode;

        if (MODE_SECONDARY_ONLY.equals(mode)) {
            try {
                JsonNode res = secondary.complete(instruction, input, requestId, overall);
                recordCall("SECONDARY", secondaryModelName(), "成功（手动指定第二模型直连）");
                return res;
            } catch (MoonshotChatClient.CallFailure ex) {
                recordCall("SECONDARY", secondaryModelName(), "失败：" + ex.getMessage());
                throw ex;
            }
        }

        if (!fallbackEnabled || MODE_PRIMARY_ONLY.equals(mode)) {
            try {
                JsonNode res = primary.complete(instruction, input, requestId, overall);
                recordCall("PRIMARY", primaryModelName(), "成功（第一模型直连）");
                return res;
            } catch (MoonshotChatClient.CallFailure ex) {
                recordCall("PRIMARY", primaryModelName(), "失败：" + ex.getMessage());
                throw ex;
            }
        }

        long started = System.nanoTime();
        Duration firstDeadline = primaryTimeout.compareTo(overall) < 0 ? primaryTimeout : overall;
        try {
            JsonNode res = primary.complete(instruction, input, requestId, firstDeadline);
            recordCall("PRIMARY", primaryModelName(), "成功（主备模式：第一模型命中）");
            return res;
        } catch (MoonshotChatClient.CallFailure primaryFailure) {
            if (!primaryFailure.providerUnavailable()) {
                recordCall("PRIMARY", primaryModelName(), "协议/内容不合规（1002，按规则不切换）：" + primaryFailure.getMessage());
                throw primaryFailure;
            }
            long remainingMs = overall.toMillis() - (System.nanoTime() - started) / 1_000_000;
            if (remainingMs < MIN_SECONDARY_BUDGET_MS) {
                LOG.warn("Planning model failover skipped: primary=kimi code={} reason={} remainingMs={}",
                        primaryFailure.code(), primaryFailure.getMessage(), remainingMs);
                recordCall("PRIMARY", primaryModelName(), "失败且剩余预算不足以切换：" + primaryFailure.getMessage());
                throw primaryFailure;
            }
            Duration secondDeadline = Duration.ofMillis(Math.min(remainingMs, secondaryTimeout.toMillis()));
            LOG.warn("Planning model failover: primary=kimi code={} reason={} -> secondary=claude timeoutMs={}",
                    primaryFailure.code(), primaryFailure.getMessage(), secondDeadline.toMillis());
            try {
                JsonNode result = secondary.complete(instruction, input, requestId, secondDeadline);
                LOG.info("Planning model served by secondary=claude after primary=kimi failure code={}",
                        primaryFailure.code());
                recordCall("SECONDARY", secondaryModelName(),
                        "成功（第一模型不可用 [" + primaryFailure.getMessage() + "] 后自动切换第二模型命中）");
                return result;
            } catch (MoonshotChatClient.CallFailure secondaryFailure) {
                LOG.warn("Planning model secondary also failed code={} reason={}",
                        secondaryFailure.code(), secondaryFailure.getMessage());
                recordCall("SECONDARY", secondaryModelName(),
                        "主备均失败：主 [" + primaryFailure.getMessage() + "]，备 [" + secondaryFailure.getMessage() + "]");
                throw new MoonshotChatClient.CallFailure(secondaryFailure.code(),
                        primaryFailure.getMessage() + "；已切换第二备用模型，" + secondaryFailure.getMessage(),
                        secondaryFailure.providerUnavailable());
            }
        }
    }
}
