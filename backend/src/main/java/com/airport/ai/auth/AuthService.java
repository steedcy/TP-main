package com.airport.ai.auth;

import com.airport.ai.common.BusinessException;
import com.airport.ai.common.ErrorCode;
import com.airport.ai.auth.dto.LoginRequest;
import com.airport.ai.auth.dto.LoginResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;

/**
 * 对应5.1.1用户登录与预置角色权限 + 用户登录密码锁定功能补充
 * 统一提示"账号或密码错误"，不区分账号不存在/密码错误/账号停用/账号锁定（5.1.1业务规则、附录B 6.1.1节）
 */
@Service
public class AuthService {

    private final UserMapper userMapper;
    private final PasswordEncoder passwordEncoder;
    private final SessionService sessionService;
    private final OperationLogService operationLogService;
    private final int maxFailedAttempts;

    public AuthService(UserMapper userMapper,
                        PasswordEncoder passwordEncoder,
                        SessionService sessionService,
                        OperationLogService operationLogService,
                        @Value("${app.auth.max-failed-attempts:3}") int maxFailedAttempts) {
        this.userMapper = userMapper;
        this.passwordEncoder = passwordEncoder;
        this.sessionService = sessionService;
        this.operationLogService = operationLogService;
        this.maxFailedAttempts = maxFailedAttempts;
    }

    /**
     * noRollbackFor是关键：登录失败/账号锁定/停用场景下方法体会抛出BusinessException，
     * 若不排除该异常的默认回滚，failed_login_attempts递增、锁定状态写入、失败操作记录
     * 都会随异常一起被整体回滚，导致连续3次锁定（TC_AUTH_004）和登录失败留痕（5.1.1业务规则6）失效。
     */
    @Transactional(noRollbackFor = BusinessException.class)
    public LoginResponse login(LoginRequest request, String clientIp) {
        User user = userMapper.findByUsername(request.getUsername()).orElse(null);

        if (user == null) {
            // 账号不存在：不落库计数（无主体），但仍按统一提示拒绝，写操作记录
            operationLogService.recordLogin(null, request.getUsername(), null, "FAILED", clientIp);
            throw new BusinessException(ErrorCode.LOGIN_FAILED);
        }

        if ("LOCKED".equals(user.getStatus())) {
            operationLogService.recordLogin(user.getId(), user.getUsername(), user.getRole(), "FAILED", clientIp);
            throw new BusinessException(ErrorCode.ACCOUNT_LOCKED);
        }
        if ("INACTIVE".equals(user.getStatus())) {
            operationLogService.recordLogin(user.getId(), user.getUsername(), user.getRole(), "FAILED", clientIp);
            throw new BusinessException(ErrorCode.ACCOUNT_INACTIVE);
        }

        if (!passwordEncoder.matches(request.getPassword(), user.getPasswordHash())) {
            handleFailedLogin(user);
            operationLogService.recordLogin(user.getId(), user.getUsername(), user.getRole(), "FAILED", clientIp);
            if ("LOCKED".equals(user.getStatus())) {
                throw new BusinessException(ErrorCode.ACCOUNT_JUST_LOCKED);
            }
            throw new BusinessException(ErrorCode.LOGIN_FAILED);
        }

        // 登录成功：失败计数清零
        user.setFailedLoginAttempts(0);
        user.setLastLoginAt(LocalDateTime.now());
        userMapper.update(user);

        String token = sessionService.createSession(user.getId());
        operationLogService.recordLogin(user.getId(), user.getUsername(), user.getRole(), "SUCCESS", clientIp);

        return new LoginResponse(token, sessionService.getIdleTimeoutSeconds(),
                new LoginResponse.UserView(user.getId(), user.getUsername(), user.getRealName(), user.getRole()));
    }

    /** 连续失败达到阈值即锁定账号，对应TC_AUTH_004 */
    private void handleFailedLogin(User user) {
        int attempts = user.getFailedLoginAttempts() == null ? 0 : user.getFailedLoginAttempts();
        attempts += 1;
        user.setFailedLoginAttempts(attempts);
        user.setLastFailedLoginAt(LocalDateTime.now());
        if (attempts >= maxFailedAttempts) {
            user.setStatus("LOCKED");
            user.setLockedAt(LocalDateTime.now());
            user.setLockedReason("连续" + maxFailedAttempts + "次密码输入错误");
        }
        userMapper.update(user);
    }

    /** 退出登录同样写入操作记录（对应5.1.1业务规则6） */
    public void logout(String token, String clientIp) {
        Long userId = sessionService.touchAndGetUserId(token);
        if (userId != null) {
            userMapper.findById(userId).ifPresent(user ->
                    operationLogService.recordLogout(user.getId(), user.getUsername(), user.getRole(), clientIp));
        }
        sessionService.invalidate(token);
    }

    @Transactional
    public void unlock(Long targetUserId, User operator) {
        User user = userMapper.findById(targetUserId)
                .orElseThrow(() -> new BusinessException(ErrorCode.USER_NOT_FOUND));
        if (!"LOCKED".equals(user.getStatus())) {
            throw new BusinessException(ErrorCode.USER_NOT_LOCKED);
        }
        user.setStatus("ACTIVE");
        user.setFailedLoginAttempts(0);
        userMapper.update(user);
        operationLogService.recordUnlock(user.getUsername(), operator);
    }
}
