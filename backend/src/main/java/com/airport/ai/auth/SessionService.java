package com.airport.ai.auth;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.util.Set;
import java.util.UUID;

/**
 * 会话管理：Redis存储，空闲30分钟失效（对应SRS_NF002），不采用固定有效期Token方案。
 * 支持单Token注销及按用户维度全量会话注销（密码重置、账号状态停用/锁定触发）。
 */
@Service
public class SessionService {

    private static final String SESSION_KEY_PREFIX = "session:";
    private static final String USER_SESSIONS_PREFIX = "user_sessions:";

    private final StringRedisTemplate redisTemplate;
    private final long idleTimeoutMinutes;

    public SessionService(StringRedisTemplate redisTemplate,
                           @Value("${app.session.idle-timeout-minutes:30}") long idleTimeoutMinutes) {
        this.redisTemplate = redisTemplate;
        this.idleTimeoutMinutes = idleTimeoutMinutes;
    }

    public String createSession(Long userId) {
        String token = UUID.randomUUID().toString().replace("-", "");
        redisTemplate.opsForValue().set(SESSION_KEY_PREFIX + token, String.valueOf(userId),
                Duration.ofMinutes(idleTimeoutMinutes));
        if (userId != null) {
            String userKey = USER_SESSIONS_PREFIX + userId;
            redisTemplate.opsForSet().add(userKey, token);
            redisTemplate.expire(userKey, Duration.ofMinutes(idleTimeoutMinutes));
        }
        return token;
    }

    /** 校验会话并滑动延续过期时间；返回用户ID，会话不存在或已过期返回null */
    public Long touchAndGetUserId(String token) {
        if (token == null || token.isBlank()) {
            return null;
        }
        String key = SESSION_KEY_PREFIX + token;
        String userId = redisTemplate.opsForValue().get(key);
        if (userId == null) {
            return null;
        }
        redisTemplate.expire(key, Duration.ofMinutes(idleTimeoutMinutes));
        String userKey = USER_SESSIONS_PREFIX + userId;
        redisTemplate.expire(userKey, Duration.ofMinutes(idleTimeoutMinutes));
        return Long.valueOf(userId);
    }

    public void invalidate(String token) {
        if (token == null || token.isBlank()) {
            return;
        }
        String key = SESSION_KEY_PREFIX + token;
        String userId = redisTemplate.opsForValue().get(key);
        redisTemplate.delete(key);
        if (userId != null) {
            redisTemplate.opsForSet().remove(USER_SESSIONS_PREFIX + userId, token);
        }
    }

    /**
     * 注销指定用户的所有活动会话（密码重置、账号锁定/停用时调用，对应SRS_NF001会话防劫持要求）
     */
    public void invalidateUserSessions(Long userId) {
        if (userId == null) {
            return;
        }
        String userKey = USER_SESSIONS_PREFIX + userId;
        Set<String> tokens = redisTemplate.opsForSet().members(userKey);
        if (tokens != null && !tokens.isEmpty()) {
            for (String t : tokens) {
                redisTemplate.delete(SESSION_KEY_PREFIX + t);
            }
        }
        redisTemplate.delete(userKey);
    }

    public long getIdleTimeoutSeconds() {
        return idleTimeoutMinutes * 60;
    }
}
