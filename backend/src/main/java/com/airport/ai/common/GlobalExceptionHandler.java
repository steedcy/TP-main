package com.airport.ai.common;

import com.airport.ai.auth.OperationLogService;
import com.airport.ai.auth.User;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

@RestControllerAdvice
public class GlobalExceptionHandler {

    private static final Logger log = LoggerFactory.getLogger(GlobalExceptionHandler.class);

    private final OperationLogService operationLogService;

    public GlobalExceptionHandler(OperationLogService operationLogService) {
        this.operationLogService = operationLogService;
    }

    @ExceptionHandler(BusinessException.class)
    public ResponseEntity<ApiResponse<Void>> handleBusinessException(BusinessException ex, HttpServletRequest req) {
        ApiResponse<Void> resp = ApiResponse.error(ex.getErrorCode().getCode(), ex.getMessage());
        resp.setPath(req.getRequestURI());
        resp.setMethod(req.getMethod());
        return ResponseEntity.status(ex.getErrorCode().getHttpStatus()).body(resp);
    }

    /**
     * @PreAuthorize是方法级安全（AOP拦截），抛出的AccessDeniedException发生在DispatcherServlet
     * 调用栈内部，不会被SecurityConfig中配置的AccessDeniedHandlerImpl（Filter链层）捕获，
     * 必须在此单独处理，否则会被下方的Exception兜底处理器吞成1000系统错误（对应5.1.1业务规则5、TC_AUTH_008）。
     */
    @ExceptionHandler(AccessDeniedException.class)
    public ResponseEntity<ApiResponse<Void>> handleAccessDenied(AccessDeniedException ex, HttpServletRequest req) {
        Object principal = SecurityContextHolder.getContext().getAuthentication() != null
                ? SecurityContextHolder.getContext().getAuthentication().getPrincipal() : null;
        if (principal instanceof User user) {
            operationLogService.record(user.getId(), user.getUsername(), user.getRole(),
                    "ACCESS_DENIED", req.getRequestURI(), "FAILED", req.getRemoteAddr());
        }
        ApiResponse<Void> resp = ApiResponse.error(ErrorCode.FORBIDDEN.getCode(), ErrorCode.FORBIDDEN.getMessage());
        resp.setPath(req.getRequestURI());
        resp.setMethod(req.getMethod());
        return ResponseEntity.status(ErrorCode.FORBIDDEN.getHttpStatus()).body(resp);
    }

    @org.springframework.beans.factory.annotation.Autowired(required = false)
    private com.airport.ai.device.ReportRejectionRecorder rejectionRecorder;

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ApiResponse<Void>> handleValidationException(MethodArgumentNotValidException ex, HttpServletRequest req) {
        if (rejectionRecorder != null) {
            rejectionRecorder.record(com.airport.ai.device.ReportRejectionRecorder.agentCodeFromPath(req.getRequestURI()),
                    com.airport.ai.device.ReportRejectionRecorder.INVALID_FORMAT, "上报字段校验未通过");
        }
        String message = ex.getBindingResult().getFieldErrors().isEmpty()
                ? "请求参数校验失败"
                : ex.getBindingResult().getFieldErrors().get(0).getDefaultMessage();
        ApiResponse<Void> resp = ApiResponse.error(ErrorCode.PARAM_FORMAT_ERROR.getCode(), message);
        resp.setPath(req.getRequestURI());
        resp.setMethod(req.getMethod());
        return ResponseEntity.status(ErrorCode.PARAM_FORMAT_ERROR.getHttpStatus()).body(resp);
    }

    @ExceptionHandler(HttpMessageNotReadableException.class)
    public ResponseEntity<ApiResponse<Void>> handleUnreadableMessage(HttpMessageNotReadableException ex, HttpServletRequest req) {
        // 请求体包含未知字段或无法解析时返回400，避免被兜底成500系统错误
        log.warn("请求体无法解析: {} {} - {}", req.getMethod(), req.getRequestURI(), ex.getMessage());
        String message = ex.getCause() instanceof com.fasterxml.jackson.databind.exc.UnrecognizedPropertyException upe
                ? "请求参数不合法: " + upe.getPropertyName()
                : "请求参数格式错误";
        ApiResponse<Void> resp = ApiResponse.error(ErrorCode.PARAM_FORMAT_ERROR.getCode(), message);
        resp.setPath(req.getRequestURI());
        resp.setMethod(req.getMethod());
        return ResponseEntity.status(ErrorCode.PARAM_FORMAT_ERROR.getHttpStatus()).body(resp);
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<ApiResponse<Void>> handleUnexpectedException(Exception ex, HttpServletRequest req) {
        // 未预期异常必须打日志，否则根因被"系统繁忙"吞掉，后续排查无从下手
        log.error("未预期异常: {} {}", req.getMethod(), req.getRequestURI(), ex);
        ApiResponse<Void> resp = ApiResponse.error(ErrorCode.SYSTEM_ERROR.getCode(), "系统繁忙，请稍后重试");
        resp.setPath(req.getRequestURI());
        resp.setMethod(req.getMethod());
        return ResponseEntity.status(ErrorCode.SYSTEM_ERROR.getHttpStatus()).body(resp);
    }
}
