package com.airport.ai.auth;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.util.UUID;

/**
 * 会话管理：Redis存储，空闲30分钟失效（对应SRS_NF002），不采用固定有效期Token方案
 */
@Service
public class SessionService {

    private static final String SESSION_KEY_PREFIX = "session:";

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
        return token;
    }

    /** 校验会话并滑动延续过期时间；返回用户ID，会话不存在或已过期返回null */
    public Long touchAndGetUserId(String token) {
        String key = SESSION_KEY_PREFIX + token;
        String userId = redisTemplate.opsForValue().get(key);
        if (userId == null) {
            return null;
        }
        redisTemplate.expire(key, Duration.ofMinutes(idleTimeoutMinutes));
        return Long.valueOf(userId);
    }

    public void invalidate(String token) {
        redisTemplate.delete(SESSION_KEY_PREFIX + token);
    }

    public long getIdleTimeoutSeconds() {
        return idleTimeoutMinutes * 60;
    }
}
