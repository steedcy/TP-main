package com.airport.ai.planning;

import com.airport.ai.auth.OperationLogService;
import com.airport.ai.auth.User;
import com.airport.ai.common.BusinessException;
import com.airport.ai.common.CredentialMasker;
import com.airport.ai.common.ErrorCode;
import com.airport.ai.device.SystemSettingMapper;
import com.airport.ai.taskdef.TaskDefinitionMapper;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.annotation.PostConstruct;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import javax.crypto.Cipher;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.util.Base64;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Runtime management of primary (Kimi) and secondary (Anthropic Claude) planning model credentials
 * and failover toggle for SYSTEM_ADMIN. Keys are stored encrypted in {@code system_settings} and
 * only masked previews are returned to the UI.
 */
@Service
public class PlanningModelConfigService {
    private static final Logger LOG = LoggerFactory.getLogger(PlanningModelConfigService.class);

    static final String KEY_MOONSHOT_BASE_URL = "planning.moonshot.base_url";
    static final String KEY_MOONSHOT_MODEL = "planning.moonshot.model";
    static final String KEY_MOONSHOT_API_KEY = "planning.moonshot.api_key";
    static final String KEY_FALLBACK_ENABLED = "planning.fallback.enabled";
    static final String KEY_ACTIVE_MODE = "planning.active.mode";
    static final String KEY_CLAUDE_BASE_URL = "planning.claude.base_url";
    static final String KEY_CLAUDE_MODEL = "planning.claude.model";
    static final String KEY_CLAUDE_API_KEY = "planning.claude.api_key";
    private static final String ENC_PREFIX = "ENC:";
    private static final int GCM_TAG_BITS = 128;
    private static final int IV_BYTES = 12;

    private final SystemSettingMapper settings;
    private final OperationLogService operationLogService;
    private final MoonshotChatClient moonshotClient;
    private final FailoverChatClient failoverClient;
    private final MoonshotModelService liveModelService;
    @Autowired(required = false)
    private com.airport.ai.task.TerminalMapMapper terminalMapMapper;
    private final SecureRandom secureRandom = new SecureRandom();
    private final byte[] cipherKey;

    @Value("${app.planning-model.fallback.active-mode:SECONDARY_ONLY}")
    private String defaultActiveMode = FailoverChatClient.MODE_SECONDARY_ONLY;

    @Autowired
    public PlanningModelConfigService(SystemSettingMapper settings,
                                      OperationLogService operationLogService,
                                      TaskDefinitionMapper definitions,
                                      ObjectMapper mapper,
                                      @Autowired(required = false) MoonshotChatClient moonshotBean,
                                      @Autowired(required = false) FailoverChatClient failoverBean,
                                      @Autowired(required = false) MoonshotModelService modelServiceBean,
                                      @Value("${app.device.credential-encryption-key:}") String encryptionKey,
                                      @Value("${app.planning-model.moonshot.base-url:https://api.moonshot.cn/v1}") String moonshotBaseUrl,
                                      @Value("${app.planning-model.moonshot.api-key:}") String moonshotApiKey,
                                      @Value("${app.planning-model.moonshot.model:kimi-k2.6}") String moonshotModel,
                                      @Value("${app.planning-model.moonshot.max-tokens:4096}") int moonshotMaxTokens,
                                      @Value("${app.planning-model.fallback.enabled:false}") boolean fallbackEnabled,
                                      @Value("${app.planning-model.fallback.base-url:https://ai.axuremart.com/v1}") String claudeBaseUrl,
                                      @Value("${app.planning-model.fallback.api-key:}") String claudeApiKey,
                                      @Value("${app.planning-model.fallback.model:gpt-sonnet-6.1}") String claudeModel,
                                      @Value("${app.planning-model.fallback.max-tokens:4096}") int claudeMaxTokens,
                                      @Value("${app.planning-model.fallback.timeout-ms:30000}") long claudeTimeoutMs,
                                      @Value("${app.planning-model.fallback.primary-timeout-ms:30000}") long primaryTimeoutMs,
                                      @Value("${app.planning-model.timeout-ms:60000}") long totalTimeoutMs) {
        this.settings = settings;
        this.operationLogService = operationLogService;
        String keyMaterial = (encryptionKey == null || encryptionKey.isBlank())
                ? "tip-planning-model-local-key" : encryptionKey;
        this.cipherKey = sha256(keyMaterial);
        this.moonshotClient = moonshotBean != null ? moonshotBean
                : new MoonshotChatClient(mapper, moonshotBaseUrl, moonshotApiKey, moonshotModel,
                        moonshotMaxTokens, totalTimeoutMs);
        this.failoverClient = failoverBean != null ? failoverBean
                : new FailoverChatClient(this.moonshotClient, mapper, fallbackEnabled,
                        claudeBaseUrl, claudeApiKey, claudeModel, claudeMaxTokens,
                        claudeTimeoutMs, primaryTimeoutMs, totalTimeoutMs);
        if (failoverBean == null) {
            this.failoverClient.setActiveMode(FailoverChatClient.MODE_SECONDARY_ONLY);
        }
        this.liveModelService = modelServiceBean != null ? modelServiceBean
                : new MoonshotModelService(this.failoverClient, definitions, mapper);
    }

    @PostConstruct
    public void loadStoredSettings() {
        if (this.terminalMapMapper != null && this.liveModelService != null) {
            this.liveModelService.setTerminalMapMapper(this.terminalMapMapper);
        }
        try {
            String mUrl = findOrNull(KEY_MOONSHOT_BASE_URL);
            String mModel = findOrNull(KEY_MOONSHOT_MODEL);
            String mKey = decryptIfPresent(findOrNull(KEY_MOONSHOT_API_KEY));
            if (mUrl != null || mModel != null || mKey != null) {
                moonshotClient.reconfigure(
                        mUrl != null ? mUrl : moonshotClient.baseUrl(),
                        mKey != null ? mKey : moonshotClient.apiKey(),
                        mModel != null ? mModel : moonshotClient.model());
            }
            ClaudeChatClient claude = failoverClient.claudeSecondary();
            String cUrl = findOrNull(KEY_CLAUDE_BASE_URL);
            String cModel = findOrNull(KEY_CLAUDE_MODEL);
            String cKey = decryptIfPresent(findOrNull(KEY_CLAUDE_API_KEY));
            if (claude != null && (cUrl != null || cModel != null || cKey != null)) {
                claude.reconfigure(
                        cUrl != null ? cUrl : claude.baseUrl(),
                        cKey != null ? cKey : claude.apiKey(),
                        cModel != null ? cModel : claude.model());
            }
            String fb = findOrNull(KEY_FALLBACK_ENABLED);
            if (fb != null) {
                failoverClient.setFallbackEnabled(Boolean.parseBoolean(fb));
            }
            String mode = findOrNull(KEY_ACTIVE_MODE);
            if (mode != null && !mode.isBlank()) {
                failoverClient.setActiveMode(mode);
            } else if (defaultActiveMode != null && !defaultActiveMode.isBlank()) {
                failoverClient.setActiveMode(defaultActiveMode);
            }
        } catch (Exception ex) {
            LOG.warn("Skipped loading persisted planning model settings: {}", ex.getMessage());
        }
    }

    public Map<String, Object> currentView() {
        ClaudeChatClient claude = failoverClient.claudeSecondary();
        String kimiKey = moonshotClient.apiKey();
        String claudeKey = claude != null ? claude.apiKey() : "";
        Map<String, Object> view = new LinkedHashMap<>();
        view.put("moonshotBaseUrl", moonshotClient.baseUrl());
        view.put("moonshotModel", moonshotClient.model());
        view.put("moonshotKeyConfigured", !kimiKey.isBlank());
        view.put("moonshotApiKeyMasked", kimiKey.isBlank() ? "" : CredentialMasker.mask(kimiKey));
        view.put("fallbackEnabled", failoverClient.isFallbackEnabled());
        view.put("activeMode", failoverClient.activeMode());
        view.put("claudeBaseUrl", claude != null ? claude.baseUrl() : ClaudeChatClient.DEFAULT_BASE_URL);
        view.put("claudeModel", claude != null && !claude.model().isBlank() ? claude.model() : ClaudeChatClient.DEFAULT_MODEL);
        view.put("claudeKeyConfigured", !claudeKey.isBlank());
        view.put("claudeApiKeyMasked", claudeKey.isBlank() ? "" : CredentialMasker.mask(claudeKey));
        view.put("lastUsedSlot", failoverClient.lastUsedSlot());
        view.put("lastUsedModel", failoverClient.lastUsedModel());
        view.put("lastCallStatus", failoverClient.lastCallStatus());
        view.put("lastCallAt", failoverClient.lastCallAt());
        return view;
    }

    public Map<String, Object> update(UpdateRequest req, User operator) {
        if (req == null) {
            throw new BusinessException(ErrorCode.PARAM_MISSING, "配置参数不能为空");
        }
        ClaudeChatClient claude = failoverClient.claudeSecondary();
        String nextKimiUrl = blankOr(req.moonshotBaseUrl(), moonshotClient.baseUrl());
        String nextKimiModel = blankOr(req.moonshotModel(),
                moonshotClient.model() == null || moonshotClient.model().isBlank() ? "kimi-k2.6" : moonshotClient.model());
        String nextKimiKey = Boolean.TRUE.equals(req.clearMoonshotApiKey()) ? ""
                : (req.moonshotApiKey() != null && !req.moonshotApiKey().isBlank()
                        ? req.moonshotApiKey().trim() : moonshotClient.apiKey());

        String currentClaudeUrl = claude != null ? claude.baseUrl() : ClaudeChatClient.DEFAULT_BASE_URL;
        String currentClaudeModel = claude != null && !claude.model().isBlank() ? claude.model() : ClaudeChatClient.DEFAULT_MODEL;
        String currentClaudeKey = claude != null ? claude.apiKey() : "";
        String nextClaudeUrl = blankOr(req.claudeBaseUrl(), currentClaudeUrl);
        String nextClaudeModel = blankOr(req.claudeModel(), currentClaudeModel);
        String nextClaudeKey = Boolean.TRUE.equals(req.clearClaudeApiKey()) ? ""
                : (req.claudeApiKey() != null && !req.claudeApiKey().isBlank()
                        ? req.claudeApiKey().trim() : currentClaudeKey);
        boolean nextFallback = req.fallbackEnabled() != null
                ? req.fallbackEnabled()
                : (!nextClaudeKey.isBlank() || failoverClient.isFallbackEnabled());
        String nextMode = req.activeMode();
        if (nextMode == null || nextMode.isBlank()) {
            nextMode = nextFallback ? FailoverChatClient.MODE_AUTO_FAILOVER : FailoverChatClient.MODE_PRIMARY_ONLY;
        } else if (FailoverChatClient.MODE_PRIMARY_ONLY.equalsIgnoreCase(nextMode)) {
            nextFallback = false;
        } else if (FailoverChatClient.MODE_AUTO_FAILOVER.equalsIgnoreCase(nextMode)) {
            nextFallback = true;
        }

        try {
            moonshotClient.reconfigure(nextKimiUrl, nextKimiKey, nextKimiModel);
            if (claude != null) {
                claude.reconfigure(nextClaudeUrl, nextClaudeKey, nextClaudeModel);
            }
            failoverClient.setFallbackEnabled(nextFallback);
            failoverClient.setActiveMode(nextMode);
        } catch (IllegalArgumentException ex) {
            throw new BusinessException(ErrorCode.PARAM_FORMAT_ERROR, ex.getMessage());
        }

        String actor = operator != null ? operator.getUsername() : "system";
        settings.upsert(KEY_MOONSHOT_BASE_URL, moonshotClient.baseUrl(), actor);
        settings.upsert(KEY_MOONSHOT_MODEL, moonshotClient.model(), actor);
        settings.upsert(KEY_MOONSHOT_API_KEY, nextKimiKey.isBlank() ? "" : encrypt(nextKimiKey), actor);
        settings.upsert(KEY_FALLBACK_ENABLED, String.valueOf(failoverClient.isFallbackEnabled()), actor);
        settings.upsert(KEY_ACTIVE_MODE, failoverClient.activeMode(), actor);
        settings.upsert(KEY_CLAUDE_BASE_URL, claude != null ? claude.baseUrl() : nextClaudeUrl, actor);
        settings.upsert(KEY_CLAUDE_MODEL, claude != null ? claude.model() : nextClaudeModel, actor);
        settings.upsert(KEY_CLAUDE_API_KEY, nextClaudeKey.isBlank() ? "" : encrypt(nextClaudeKey), actor);

        if (operator != null && operationLogService != null) {
            String summary = "mode=" + failoverClient.activeMode()
                    + ", primary=" + moonshotClient.model()
                    + "(key=" + (nextKimiKey.isBlank() ? "UNSET" : CredentialMasker.mask(nextKimiKey)) + ")"
                    + ", fallbackEnabled=" + failoverClient.isFallbackEnabled()
                    + ", secondary=" + nextClaudeModel
                    + "(key=" + (nextClaudeKey.isBlank() ? "UNSET" : CredentialMasker.mask(nextClaudeKey)) + ")";
            operationLogService.record(operator.getId(), operator.getUsername(), operator.getRole(),
                    "PLANNING_MODEL_CONFIG_UPDATE", summary, "SUCCESS", null);
        }
        return currentView();
    }

    public boolean hasLiveModelKey() {
        ClaudeChatClient claude = failoverClient.claudeSecondary();
        String mode = failoverClient.activeMode();
        if (FailoverChatClient.MODE_SECONDARY_ONLY.equals(mode)) {
            return claude != null && !claude.apiKey().isBlank();
        }
        return !moonshotClient.apiKey().isBlank()
                || (failoverClient.isFallbackEnabled() && claude != null && !claude.apiKey().isBlank());
    }

    public GoalUnderstandingResponse delegateUnderstand(GoalUnderstandingRequest request) {
        return liveModelService.understand(request);
    }

    public PlanningResponse delegateGeneratePlan(PlanningRequest request) {
        return liveModelService.generatePlan(request);
    }

    private String findOrNull(String key) {
        return settings == null ? null : settings.findValue(key);
    }

    private static String blankOr(String candidate, String fallback) {
        return candidate == null || candidate.isBlank() ? fallback : candidate.trim();
    }

    private String encrypt(String plaintext) {
        try {
            byte[] iv = new byte[IV_BYTES];
            secureRandom.nextBytes(iv);
            Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
            cipher.init(Cipher.ENCRYPT_MODE, new SecretKeySpec(cipherKey, "AES"), new GCMParameterSpec(GCM_TAG_BITS, iv));
            byte[] encrypted = cipher.doFinal(plaintext.getBytes(StandardCharsets.UTF_8));
            byte[] packed = new byte[iv.length + encrypted.length];
            System.arraycopy(iv, 0, packed, 0, iv.length);
            System.arraycopy(encrypted, 0, packed, iv.length, encrypted.length);
            return ENC_PREFIX + Base64.getEncoder().encodeToString(packed);
        } catch (Exception ex) {
            throw new IllegalStateException("无法加密模型密钥", ex);
        }
    }

    private String decryptIfPresent(String stored) {
        if (stored == null) return null;
        if (stored.isBlank()) return "";
        if (!stored.startsWith(ENC_PREFIX)) return stored.trim();
        try {
            byte[] packed = Base64.getDecoder().decode(stored.substring(ENC_PREFIX.length()));
            byte[] iv = new byte[IV_BYTES];
            byte[] encrypted = new byte[packed.length - IV_BYTES];
            System.arraycopy(packed, 0, iv, 0, IV_BYTES);
            System.arraycopy(packed, IV_BYTES, encrypted, 0, encrypted.length);
            Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
            cipher.init(Cipher.DECRYPT_MODE, new SecretKeySpec(cipherKey, "AES"), new GCMParameterSpec(GCM_TAG_BITS, iv));
            return new String(cipher.doFinal(encrypted), StandardCharsets.UTF_8);
        } catch (Exception ex) {
            LOG.warn("Unable to decrypt stored planning model key: {}", ex.getMessage());
            return null;
        }
    }

    private static byte[] sha256(String value) {
        try {
            return MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.UTF_8));
        } catch (Exception ex) {
            throw new IllegalStateException("SHA-256 unavailable", ex);
        }
    }

    public record UpdateRequest(
            String moonshotBaseUrl,
            String moonshotModel,
            String moonshotApiKey,
            Boolean clearMoonshotApiKey,
            Boolean fallbackEnabled,
            String activeMode,
            String claudeBaseUrl,
            String claudeModel,
            String claudeApiKey,
            Boolean clearClaudeApiKey) {
        public UpdateRequest(
                String moonshotBaseUrl,
                String moonshotModel,
                String moonshotApiKey,
                Boolean clearMoonshotApiKey,
                Boolean fallbackEnabled,
                String claudeBaseUrl,
                String claudeModel,
                String claudeApiKey,
                Boolean clearClaudeApiKey) {
            this(moonshotBaseUrl, moonshotModel, moonshotApiKey, clearMoonshotApiKey,
                    fallbackEnabled, null, claudeBaseUrl, claudeModel, claudeApiKey, clearClaudeApiKey);
        }
    }
}
