package com.airport.ai.common;

import com.airport.ai.auth.OperationLogService;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.web.HttpRequestMethodNotSupportedException;
import org.springframework.web.servlet.resource.NoResourceFoundException;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.mock;

/** DEF-S3-058/061：不支持的方法/路径返回明确 405/404，而不是被兜底成 500“系统繁忙”；真正的未知异常仍是 500。 */
class GlobalExceptionHandlerStatusTest {
    private final GlobalExceptionHandler handler = new GlobalExceptionHandler(mock(OperationLogService.class));

    private MockHttpServletRequest request(String method, String uri) {
        return new MockHttpServletRequest(method, uri);
    }

    @Test
    void putDeleteAndPatchOnAnImmutableRecordPathReturn405WithAllowHeader() {
        for (String method : new String[]{"PUT", "DELETE", "PATCH"}) {
            var ex = new HttpRequestMethodNotSupportedException(method, java.util.List.of("GET"));
            ResponseEntity<ApiResponse<Void>> r = handler.handleMethodNotSupported(ex, request(method, "/api/v1/tasks/19/events/5"));
            assertEquals(HttpStatus.METHOD_NOT_ALLOWED, r.getStatusCode(), method);
            assertEquals(ErrorCode.METHOD_NOT_ALLOWED.getCode(), r.getBody().getCode());
            assertTrue(r.getBody().getMessage().contains(method));
            assertNotEquals("系统繁忙，请稍后重试", r.getBody().getMessage());
            assertTrue(r.getHeaders().getAllow().contains(HttpMethod.GET), "应告知允许的方法");
            assertEquals("/api/v1/tasks/19/events/5", r.getBody().getPath());
        }
    }

    @Test
    void methodNotSupportedWithoutAnAllowListStillReturns405() {
        var ex = new HttpRequestMethodNotSupportedException("DELETE");
        ResponseEntity<ApiResponse<Void>> r = handler.handleMethodNotSupported(ex, request("DELETE", "/api/v1/operation-logs/976"));
        assertEquals(HttpStatus.METHOD_NOT_ALLOWED, r.getStatusCode());
    }

    @Test
    void unknownPathReturns404NotAServerError() {
        var ex = new NoResourceFoundException(HttpMethod.PUT, "api/v1/operation-logs/976");
        ResponseEntity<ApiResponse<Void>> r = handler.handleNoResource(ex, request("PUT", "/api/v1/operation-logs/976"));
        assertEquals(HttpStatus.NOT_FOUND, r.getStatusCode());
        assertEquals(ErrorCode.RESOURCE_NOT_FOUND.getCode(), r.getBody().getCode());
    }

    @Test
    void connectionPoolTimeoutReturns503WithGracefulPrompt() {
        var ex1 = new org.springframework.jdbc.CannotGetJdbcConnectionException("Failed to obtain JDBC Connection",
                new java.sql.SQLTransientConnectionException("Connection is not available, request timed out after 30000ms."));
        ResponseEntity<ApiResponse<Void>> r1 = handler.handleConnectionPoolTimeout(ex1, request("POST", "/api/v1/tasks"));
        assertEquals(HttpStatus.SERVICE_UNAVAILABLE, r1.getStatusCode());
        assertEquals(ErrorCode.DATABASE_POOL_BUSY.getCode(), r1.getBody().getCode());
        assertEquals("数据库连接繁忙，正在排队重试，请稍后刷新", r1.getBody().getMessage());
        assertEquals("/api/v1/tasks", r1.getBody().getPath());

        var ex2 = new java.sql.SQLTransientConnectionException("HikariPool-1 - Connection is not available");
        ResponseEntity<ApiResponse<Void>> r2 = handler.handleConnectionPoolTimeout(ex2, request("POST", "/api/v1/devices"));
        assertEquals(HttpStatus.SERVICE_UNAVAILABLE, r2.getStatusCode());
        assertEquals(ErrorCode.DATABASE_POOL_BUSY.getCode(), r2.getBody().getCode());
    }

    @Test
    void concurrencyLockExceptionReturns409Conflict() {
        var ex = new org.springframework.dao.CannotAcquireLockException("deadlock detected");
        ResponseEntity<ApiResponse<Void>> r = handler.handleConcurrencyLockException(ex, request("PUT", "/api/v1/devices/1"));
        assertEquals(HttpStatus.CONFLICT, r.getStatusCode());
        assertEquals(ErrorCode.DATA_CONCURRENCY_CONFLICT.getCode(), r.getBody().getCode());
        assertEquals("数据库操作并发竞争冲突，系统已自动防护，请稍后重试", r.getBody().getMessage());
    }

    @Test
    void dataIntegrityViolationReturns409Conflict() {
        var ex = new org.springframework.dao.DuplicateKeyException("duplicate key value violates unique constraint");
        ResponseEntity<ApiResponse<Void>> r = handler.handleDataIntegrityViolation(ex, request("POST", "/api/v1/devices"));
        assertEquals(HttpStatus.CONFLICT, r.getStatusCode());
        assertEquals(ErrorCode.DUPLICATE_KEY_CONFLICT.getCode(), r.getBody().getCode());
        assertEquals("数据并发冲突或唯一标识已存在，请勿重复提交", r.getBody().getMessage());
    }

    @Test
    void genuinelyUnexpectedExceptionsAreStillReportedAs500() {
        ResponseEntity<ApiResponse<Void>> r = handler.handleUnexpectedException(new IllegalStateException("boom"), request("GET", "/x"));
        assertEquals(HttpStatus.INTERNAL_SERVER_ERROR, r.getStatusCode());
        assertEquals("系统繁忙，请稍后重试", r.getBody().getMessage());
    }

    @Test
    void errorCodesStayUnique() {
        long distinct = java.util.Arrays.stream(ErrorCode.values()).map(ErrorCode::getCode).distinct().count();
        assertEquals(ErrorCode.values().length, distinct, "错误码必须唯一");
    }
}
