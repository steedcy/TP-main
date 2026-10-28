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

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private final OperationLogMapper operationLogMapper;

    public OperationLogService(OperationLogMapper operationLogMapper) {
        this.operationLogMapper = operationLogMapper;
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
        OperationLog log = new OperationLog();
        log.setUserId(userId);
        log.setUsername(username);
        log.setRole(role);
        log.setOperationType("LOGIN");
        log.setOperationResult(result);
        log.setSourceIp(sourceIp);
        operationLogMapper.insert(log);
    }

    /** 连续密码错误触发锁定的独立审计记录，操作主体为被锁定账号（DEF-S3-056）；不含密码等凭据 */
    public void recordAccountLocked(User user, String sourceIp, int failedAttempts) {
        OperationLog log = new OperationLog();
        log.setUserId(user.getId());
        log.setUsername(user.getUsername());
        log.setRole(user.getRole());
        log.setOperationType("ACCOUNT_LOCKED");
        log.setOperationTarget(user.getUsername());
        log.setOperationResult("SUCCESS");
        log.setSourceIp(sourceIp);
        log.setDetail(toMaskedJson(Map.of("reason", "连续密码错误", "failedAttempts", failedAttempts)));
        operationLogMapper.insert(log);
    }

    public void recordLogout(Long userId, String username, String role, String sourceIp) {
        OperationLog log = new OperationLog();
        log.setUserId(userId);
        log.setUsername(username);
        log.setRole(role);
        log.setOperationType("LOGOUT");
        log.setOperationResult("SUCCESS");
        log.setSourceIp(sourceIp);
        operationLogMapper.insert(log);
    }

    public void recordUnlock(String targetUsername, User operator) {
        OperationLog log = new OperationLog();
        log.setUserId(operator.getId());
        log.setUsername(operator.getUsername());
        log.setRole(operator.getRole());
        log.setOperationType("MANUAL_HANDLING");
        log.setOperationTarget(targetUsername);
        log.setOperationResult("SUCCESS");
        log.setSourceIp(currentRequestIp());
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
        OperationLog log = new OperationLog();
        log.setUserId(userId);
        log.setUsername(username);
        log.setRole(role);
        log.setOperationType(operationType);
        log.setOperationTarget(target);
        log.setOperationResult(result);
        log.setSourceIp(sourceIp == null ? currentRequestIp() : sourceIp);
        log.setDetail(toMaskedJson(detail));
        operationLogMapper.insert(log);
    }

    private String currentRequestIp() {
        ServletRequestAttributes attrs = (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
        return attrs == null ? null : attrs.getRequest().getRemoteAddr();
    }

    private String toMaskedJson(Map<String, Object> detail) {
        if (detail == null) return null;
        try {
            return MAPPER.writeValueAsString(CredentialMasker.maskSensitiveFields(detail));
        } catch (Exception e) {
            return null;
        }
    }
}
