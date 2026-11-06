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
