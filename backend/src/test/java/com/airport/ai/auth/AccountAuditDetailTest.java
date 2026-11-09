package com.airport.ai.auth;

import com.airport.ai.auth.dto.CreateUserRequest;
import com.airport.ai.event.OperationLog;
import com.airport.ai.event.OperationLogMapper;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.security.crypto.password.PasswordEncoder;

import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

/** DEF-S3-009 / SRS_F028.R03：账号创建、状态变更、重置密码、解锁的操作记录都带变更前后摘要，且不含任何凭据。 */
class AccountAuditDetailTest {
    private final UserMapper users = mock(UserMapper.class);
    private final PasswordEncoder encoder = mock(PasswordEncoder.class);
    private final OperationLogMapper logMapper = mock(OperationLogMapper.class);
    private final OperationLogService audit = new OperationLogService(logMapper);
    private final UserService userService = new UserService(users, encoder, audit);
    private final User admin = new User();

    AccountAuditDetailTest() {
        admin.setId(1L);
        admin.setUsername("sysadmin");
        admin.setRole("SYSTEM_ADMIN");
        when(encoder.encode(any())).thenReturn("HASHED-SECRET-VALUE");
    }

    private User target(String status) {
        User u = new User();
        u.setId(9L);
        u.setUsername("operator1");
        u.setRole("OPERATOR");
        u.setStatus(status);
        u.setContact("13800000000");
        u.setPasswordHash("OLD-HASH-VALUE");
        when(users.findById(9L)).thenReturn(Optional.of(u));
        return u;
    }

    private OperationLog lastLog() {
        ArgumentCaptor<OperationLog> c = ArgumentCaptor.forClass(OperationLog.class);
        verify(logMapper).insert(c.capture());
        return c.getValue();
    }

    @Test
    void statusChangeRecordsBeforeAndAfterAndTheTargetSummary() {
        target("ACTIVE");
        userService.updateStatus(9L, "INACTIVE", admin);
        OperationLog log = lastLog();
        assertEquals("USER_STATUS_CHANGE", log.getOperationType());
        assertNotNull(log.getDetail(), "详情不能为空");
        assertTrue(log.getDetail().contains("\"before\"") && log.getDetail().contains("ACTIVE"));
        assertTrue(log.getDetail().contains("\"after\"") && log.getDetail().contains("INACTIVE"));
        assertTrue(log.getDetail().contains("operator1"));
    }

    @Test
    void passwordResetRecordsTheFactButNeverThePasswordOrHashes() {
        target("ACTIVE");
        userService.resetPassword(9L, "NewSecret#123", admin);
        OperationLog log = lastLog();
        assertEquals("PASSWORD_RESET", log.getOperationType());
        assertTrue(log.getDetail().contains("passwordChanged"));
        for (String secret : new String[]{"NewSecret#123", "HASHED-SECRET-VALUE", "OLD-HASH-VALUE"}) {
            assertFalse(log.getDetail().contains(secret), "详情不得包含: " + secret);
        }
    }

    @Test
    void creationRecordsTheNewAccountSummaryWithoutPasswordOrContact() {
        when(users.existsByUsername(any())).thenReturn(false);
        CreateUserRequest req = new CreateUserRequest();
        req.setUsername("newop");
        req.setPassword("InitialSecret#1");
        req.setRealName("虚构姓名");
        req.setRole("OPERATOR");
        req.setContact("13900000000");
        userService.create(req, admin);
        OperationLog log = lastLog();
        assertEquals("USER_CREATE", log.getOperationType());
        assertTrue(log.getDetail().contains("newop") && log.getDetail().contains("OPERATOR"));
        for (String secret : new String[]{"InitialSecret#1", "HASHED-SECRET-VALUE", "13900000000", "虚构姓名"}) {
            assertFalse(log.getDetail().contains(secret), "详情不得包含: " + secret);
        }
    }

    @Test
    void unlockRecordsLockedToActiveAndTheFailedAttemptsBefore() {
        audit.recordUnlock("operator1", admin, 3);
        OperationLog log = lastLog();
        assertEquals("MANUAL_HANDLING", log.getOperationType());
        assertTrue(log.getDetail().contains("LOCKED") && log.getDetail().contains("ACTIVE"));
        assertTrue(log.getDetail().contains("\"failedLoginAttempts\":3"), log.getDetail());
        assertTrue(log.getDetail().startsWith("{"), "应为JSON而不是Map.toString()");
    }

    @Test
    void oldTwoArgumentUnlockStillWorks() {
        audit.recordUnlock("operator1", admin);
        assertNotNull(lastLog().getDetail());
    }
}
