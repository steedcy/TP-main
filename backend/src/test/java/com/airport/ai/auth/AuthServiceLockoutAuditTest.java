package com.airport.ai.auth;

import com.airport.ai.auth.dto.LoginRequest;
import com.airport.ai.common.BusinessException;
import com.airport.ai.common.ErrorCode;
import com.airport.ai.event.OperationLog;
import com.airport.ai.event.OperationLogMapper;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.security.crypto.password.PasswordEncoder;

import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

/** DEF-S3-056 / TC-002.S3：第3次错密触发锁定时，除LOGIN/FAILED外写入独立可识别的ACCOUNT_LOCKED审计。 */
class AuthServiceLockoutAuditTest {

    private final UserMapper userMapper = mock(UserMapper.class);
    private final PasswordEncoder encoder = mock(PasswordEncoder.class);
    private final OperationLogMapper logMapper = mock(OperationLogMapper.class);
    private final AuthService service = new AuthService(userMapper, encoder, mock(SessionService.class),
            new OperationLogService(logMapper), 3);

    private LoginRequest request() {
        LoginRequest r = new LoginRequest();
        r.setUsername("alice");
        r.setPassword("wrong-password-secret");
        return r;
    }

    private User alice(int attempts) {
        User u = new User();
        u.setId(9L);
        u.setUsername("alice");
        u.setRole("OPERATOR");
        u.setStatus("ACTIVE");
        u.setPasswordHash("hash");
        u.setFailedLoginAttempts(attempts);
        return u;
    }

    @Test
    void thirdFailureWritesFailedLoginAndAccountLockedRecords() {
        User u = alice(2);
        when(userMapper.findByUsername("alice")).thenReturn(Optional.of(u));
        when(encoder.matches(any(), any())).thenReturn(false);

        BusinessException ex = assertThrows(BusinessException.class, () -> service.login(request(), "192.0.2.9"));
        assertEquals(ErrorCode.ACCOUNT_JUST_LOCKED, ex.getErrorCode());
        assertEquals("LOCKED", u.getStatus());

        ArgumentCaptor<OperationLog> logs = ArgumentCaptor.forClass(OperationLog.class);
        verify(logMapper, times(2)).insert(logs.capture());
        OperationLog failed = logs.getAllValues().get(0);
        OperationLog locked = logs.getAllValues().get(1);
        assertEquals("LOGIN", failed.getOperationType());
        assertEquals("FAILED", failed.getOperationResult());
        assertEquals("ACCOUNT_LOCKED", locked.getOperationType());
        assertEquals("alice", locked.getOperationTarget());
        assertEquals("192.0.2.9", locked.getSourceIp());
        assertFalse(String.valueOf(locked.getDetail()).contains("wrong-password-secret"));
    }

    @Test
    void failureBelowThresholdDoesNotWriteLockRecord() {
        User u = alice(0);
        when(userMapper.findByUsername("alice")).thenReturn(Optional.of(u));
        when(encoder.matches(any(), any())).thenReturn(false);

        assertThrows(BusinessException.class, () -> service.login(request(), "192.0.2.9"));

        ArgumentCaptor<OperationLog> logs = ArgumentCaptor.forClass(OperationLog.class);
        verify(logMapper, times(1)).insert(logs.capture());
        assertEquals("LOGIN", logs.getValue().getOperationType());
    }
}
