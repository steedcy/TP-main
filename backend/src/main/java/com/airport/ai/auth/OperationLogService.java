package com.airport.ai.auth;

import com.airport.ai.common.CredentialMasker;
import com.airport.ai.common.PageResult;
import com.airport.ai.event.OperationLog;
import com.airport.ai.event.OperationLogMapper;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.github.pagehelper.PageHelper;
import com.github.pagehelper.PageInfo;
import org.springframework.stereotype.Service;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

import java.time.LocalDateTime;
import java.util.Map;

/**
 * 对应5.7.2操作记录：登录/登出/解锁等操作写入operation_logs。detail字段（变更前后关键
 * 字段摘要）写入前统一经CredentialMasker掩码，凭据类字段不落库原值（对应业务规则6）。
 */
@Service
public class OperationLogService {

    private static final ObjectMapper MAPPER = new ObjectMapper().findAndRegisterModules();

    private final OperationLogMapper operationLogMapper;

    public OperationLogService(OperationLogMapper operationLogMapper) {
        this.operationLogMapper = operationLogMapper;
    }

    public OperationLog getById(Long id) {
        if (id == null) return null;
        return operationLogMapper.findById(id);
    }

    /** 按账号、操作类型、操作结果、时间范围任意组合筛选，均为空时返回全量（对应5.7.2界面元素筛选项） */
    public PageResult<OperationLog> search(String username, String operationType, String operationResult,
                                            LocalDateTime startTime, LocalDateTime endTime, int page, int size) {
        PageHelper.startPage(page, size);
        return PageResult.of(new PageInfo<>(operationLogMapper.searchPaged(
                blankToNull(username), blankToNull(operationType), blankToNull(operationResult), startTime, endTime)));
    }

    private String blankToNull(String value) {
        return (value == null || value.isBlank()) ? null : value;
    }

    public void recordLogin(Long userId, String username, String role, String result, String sourceIp) {
        String safeUser = safeUsername(username);
        String safeResult = safeResult(result);
        OperationLog log = new OperationLog();
        log.setUserId(userId);
        log.setUsername(safeUser);
        log.setRole(safeCodeColumn(role, 64));
        log.setOperationType("LOGIN");
        log.setOperationTarget(com.airport.ai.task.SceneParamsPrivacyGuard.sanitizeGoal(safeUser));
        log.setOperationResult(safeResult);
        log.setSourceIp(safeCodeColumn(sourceIp == null ? currentRequestIp() : sourceIp, 128));
        java.util.Map<String, Object> detail = new java.util.LinkedHashMap<>();
        detail.put("action", "LOGIN");
        detail.put("target", safeUser);
        detail.put("result", safeResult);
        log.setDetail(toMaskedJson(detail));
        operationLogMapper.insert(log);
    }

    /** 连续密码错误触发锁定的独立审计记录，操作主体为被锁定账号（DEF-S3-056）；不含密码等凭据 */
    public void recordAccountLocked(User user, String sourceIp, int failedAttempts) {
        String safeUser = safeUsername(user == null ? null : user.getUsername());
        OperationLog log = new OperationLog();
        log.setUserId(user == null ? null : user.getId());
        log.setUsername(safeUser);
        log.setRole(safeCodeColumn(user == null ? null : user.getRole(), 64));
        log.setOperationType("ACCOUNT_LOCKED");
        log.setOperationTarget(safeUser);
        log.setOperationResult("SUCCESS");
        log.setSourceIp(safeCodeColumn(sourceIp == null ? currentRequestIp() : sourceIp, 128));
        java.util.Map<String, Object> detail = new java.util.LinkedHashMap<>();
        detail.put("action", "LOCK");
        detail.put("reason", "连续密码错误");
        detail.put("failedAttempts", failedAttempts);
        detail.put("before", Map.of("status", "ACTIVE", "failedLoginAttempts", Math.max(0, failedAttempts - 1)));
        detail.put("after", Map.of("status", "LOCKED", "failedLoginAttempts", failedAttempts));
        log.setDetail(toMaskedJson(detail));
        operationLogMapper.insert(log);
    }

    public void recordLogout(Long userId, String username, String role, String sourceIp) {
        String safeUser = safeUsername(username);
        OperationLog log = new OperationLog();
        log.setUserId(userId);
        log.setUsername(safeUser);
        log.setRole(safeCodeColumn(role, 64));
        log.setOperationType("LOGOUT");
        log.setOperationTarget(safeUser);
        log.setOperationResult("SUCCESS");
        log.setSourceIp(safeCodeColumn(sourceIp == null ? currentRequestIp() : sourceIp, 128));
        java.util.Map<String, Object> detail = new java.util.LinkedHashMap<>();
        detail.put("action", "LOGOUT");
        detail.put("target", safeUser);
        detail.put("result", "SUCCESS");
        log.setDetail(toMaskedJson(detail));
        operationLogMapper.insert(log);
    }

    public void recordUnlock(String targetUsername, User operator) {
        recordUnlock(targetUsername, operator, 0);
    }

    /** 解锁记录带变更前后摘要：LOCKED -> ACTIVE，失败次数清零（DEF-S3-009）。 */
    public void recordUnlock(String targetUsername, User operator, int failedAttemptsBefore) {
        OperationLog log = new OperationLog();
        log.setDetail(toMaskedJson(java.util.Map.of("action", "UNLOCK",
                "target", targetUsername == null ? "" : targetUsername,
                "before", java.util.Map.of("status", "LOCKED", "failedLoginAttempts", failedAttemptsBefore),
                "after", java.util.Map.of("status", "ACTIVE", "failedLoginAttempts", 0))));
        log.setUserId(operator == null ? null : operator.getId());
        log.setUsername(safeUsername(operator == null ? "SYSTEM" : operator.getUsername()));
        log.setRole(safeCodeColumn(operator == null ? "SYSTEM_ADMIN" : operator.getRole(), 64));
        log.setOperationType("MANUAL_HANDLING");
        log.setOperationTarget(targetUsername);
        log.setOperationResult("SUCCESS");
        log.setSourceIp(safeCodeColumn(currentRequestIp(), 128));
        operationLogMapper.insert(log);
    }

    /**
     * sourceIp为null时自动从当前请求上下文取（对应5.7.2业务规则3"每条记录须包含来源IP"）；
     * 部分调用点（如仿真体/后台任务）没有请求上下文，此时保持null，属于该场景下的合理值。
     */
    public void record(Long userId, String username, String role, String operationType,
                        String target, String result, String sourceIp) {
        record(userId, username, role, operationType, target, result, sourceIp, null);
    }

    /**
     * detail为变更前后关键字段摘要（对应5.7.2界面元素"详情"），写入前对其中的凭据类字段
     * （accessCredentialRef/password等，见CredentialMasker.SENSITIVE_KEYS）做掩码，
     * 不落库原值（对应业务规则6）。
     */
    public void record(Long userId, String username, String role, String operationType,
                        String target, String result, String sourceIp, Map<String, Object> detail) {
        String safeUser = safeUsername(username);
        String safeType = safeCodeColumn(operationType == null || operationType.isBlank() ? "UNKNOWN" : operationType, 64);
        String safeResult = safeResult(result);
        String sanitizedTarget = com.airport.ai.task.SceneParamsPrivacyGuard.sanitizeGoal(target);
        OperationLog log = new OperationLog();
        log.setUserId(userId);
        log.setUsername(safeUser);
        log.setRole(safeCodeColumn(role, 64));
        log.setOperationType(safeType);
        log.setOperationTarget(sanitizedTarget);
        log.setOperationResult(safeResult);
        log.setSourceIp(safeCodeColumn(sourceIp == null ? currentRequestIp() : sourceIp, 128));
        Map<String, Object> effectiveDetail = detail;
        if (effectiveDetail == null) {
            effectiveDetail = new java.util.LinkedHashMap<>();
            effectiveDetail.put("operationType", safeType);
            effectiveDetail.put("target", sanitizedTarget == null ? "" : sanitizedTarget);
            effectiveDetail.put("result", safeResult);
        }
        log.setDetail(toMaskedJson(effectiveDetail));
        operationLogMapper.insert(log);
    }

    private String safeUsername(String username) {
        if (username == null || username.isBlank()) return "UNKNOWN";
        return safeCodeColumn(username.trim(), 256);
    }

    private String safeResult(String result) {
        if (result == null || result.isBlank()) return "SUCCESS";
        String upper = result.trim().toUpperCase();
        if ("SUCCESS".equals(upper) || "FAILED".equals(upper)
                || "CANCELLED".equals(upper) || "INTERCEPTED".equals(upper)) {
            return upper;
        }
        return "FAILED";
    }

    /** 按 Unicode 代码点安全截断编码类短列，避免切碎 UTF-16 代理对导致乱码（SRS_NF016.R01） */
    private String safeCodeColumn(String input, int maxCodePoints) {
        if (input == null) return null;
        if (input.length() <= maxCodePoints) return input;
        int count = input.codePointCount(0, input.length());
        if (count <= maxCodePoints) return input;
        int endIndex = input.offsetByCodePoints(0, maxCodePoints);
        return input.substring(0, endIndex);
    }

    private String currentRequestIp() {
        ServletRequestAttributes attrs = (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
        return attrs == null ? null : attrs.getRequest().getRemoteAddr();
    }

    private String toMaskedJson(Map<String, Object> detail) {
        if (detail == null) return null;
        try {
            Map<String, Object> maskedCredentials = CredentialMasker.maskSensitiveFields(detail);
            Map<String, Object> sanitized = com.airport.ai.task.SceneParamsPrivacyGuard.sanitize(maskedCredentials);
            return MAPPER.writeValueAsString(sanitized);
        } catch (Exception e) {
            try {
                Map<String, Object> fallback = new java.util.LinkedHashMap<>();
                for (Map.Entry<String, Object> entry : detail.entrySet()) {
                    String k = entry.getKey() == null ? "null" : entry.getKey();
                    if (com.airport.ai.task.SceneParamsPrivacyGuard.isIdentityKey(k)) continue;
                    String v = entry.getValue() == null ? null : String.valueOf(entry.getValue());
                    if (v != null && CredentialMasker.isSensitiveKey(k)) {
                        v = CredentialMasker.mask(v);
                    } else if (v != null) {
                        v = com.airport.ai.task.SceneParamsPrivacyGuard.sanitizeGoal(v);
                    }
                    fallback.put(k, v);
                }
                return MAPPER.writeValueAsString(fallback);
            } catch (Exception ignored) {
                return "{}";
            }
        }
    }
}
