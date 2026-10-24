package com.airport.ai.auth;

import com.airport.ai.event.OperationLog;
import com.airport.ai.event.OperationLogMapper;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class OperationLogServiceTest {
    @AfterEach void clear() { RequestContextHolder.resetRequestAttributes(); }

    @Test void loginAndUnlockRecordActorRoleAndRequestIp() {
        OperationLogMapper mapper = mock(OperationLogMapper.class);
        OperationLogService service = new OperationLogService(mapper);
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.setRemoteAddr("192.0.2.15");
        RequestContextHolder.setRequestAttributes(new ServletRequestAttributes(request));
        User admin = new User();
        admin.setId(3L);
        admin.setUsername("system-admin");
        admin.setRole("SYSTEM_ADMIN");

        service.recordLogin(3L, "system-admin", "SYSTEM_ADMIN", "SUCCESS", request.getRemoteAddr());
        service.recordUnlock("locked-user", admin);

        ArgumentCaptor<OperationLog> captured = ArgumentCaptor.forClass(OperationLog.class);
        verify(mapper, times(2)).insert(captured.capture());
        for (OperationLog log : captured.getAllValues()) {
            assertEquals(3L, log.getUserId());
            assertEquals("system-admin", log.getUsername());
            assertEquals("SYSTEM_ADMIN", log.getRole());
            assertEquals("192.0.2.15", log.getSourceIp());
        }
        assertEquals("locked-user", captured.getAllValues().get(1).getOperationTarget());
    }
}
