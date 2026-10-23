package com.airport.ai.common;

import com.airport.ai.auth.OperationLogService;
import com.airport.ai.auth.User;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class GlobalExceptionHandlerTest {
    private final OperationLogService operationLogService = mock(OperationLogService.class);
    private final GlobalExceptionHandler handler = new GlobalExceptionHandler(operationLogService);

    @AfterEach
    void clearSecurityContext() {
        SecurityContextHolder.clearContext();
    }

    @Test
    void methodSecurityDenialReturnsForbiddenAndAuditsActor() {
        User actor = new User();
        actor.setId(7L);
        actor.setUsername("operator-1");
        actor.setRole("OPERATOR");
        SecurityContextHolder.getContext().setAuthentication(
                new UsernamePasswordAuthenticationToken(actor, "session", List.of()));
        MockHttpServletRequest request = new MockHttpServletRequest("POST", "/api/v1/users/4/unlock");

        var response = handler.handleAccessDenied(new org.springframework.security.access.AccessDeniedException("denied"), request);

        assertEquals(HttpStatus.FORBIDDEN, response.getStatusCode());
        assertNotNull(response.getBody());
        assertEquals(ErrorCode.FORBIDDEN.getCode(), response.getBody().getCode());
        assertEquals(request.getRequestURI(), response.getBody().getPath());
        verify(operationLogService).record(7L, "operator-1", "OPERATOR", "ACCESS_DENIED",
                request.getRequestURI(), "FAILED", "127.0.0.1");
    }

    @Test
    void unexpectedFailureHidesInternalMessageFromClient() {
        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/api/v1/devices");

        var response = handler.handleUnexpectedException(new IllegalStateException("sensitive database detail"), request);

        assertEquals(HttpStatus.INTERNAL_SERVER_ERROR, response.getStatusCode());
        assertNotNull(response.getBody());
        assertFalse(response.getBody().getMessage().contains("sensitive database detail"));
        assertEquals("系统繁忙，请稍后重试", response.getBody().getMessage());
    }
}
