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

    /**
     * 路径存在但不支持该方法（如对事件、操作记录发 PUT/DELETE）：这是客户端用法问题，不是服务内部故障，
     * 返回明确的 405 并带 Allow，不被兜底成 500“系统繁忙”（DEF-S3-058、061）。请求没进入业务，数据不会被改动。
     */
    @ExceptionHandler(org.springframework.web.HttpRequestMethodNotSupportedException.class)
    public ResponseEntity<ApiResponse<Void>> handleMethodNotSupported(
            org.springframework.web.HttpRequestMethodNotSupportedException ex, HttpServletRequest req) {
        ApiResponse<Void> resp = ApiResponse.error(ErrorCode.METHOD_NOT_ALLOWED.getCode(),
                "该资源不支持" + req.getMethod() + "方法（记录不可修改或删除）");
        resp.setPath(req.getRequestURI());
        resp.setMethod(req.getMethod());
        ResponseEntity.BodyBuilder builder = ResponseEntity.status(ErrorCode.METHOD_NOT_ALLOWED.getHttpStatus());
        if (ex.getSupportedHttpMethods() != null && !ex.getSupportedHttpMethods().isEmpty()) {
            builder.allow(ex.getSupportedHttpMethods().toArray(new org.springframework.http.HttpMethod[0]));
        }
        return builder.body(resp);
    }

    /** 路径不存在：明确的 404，不当作系统故障。 */
    @ExceptionHandler({org.springframework.web.servlet.resource.NoResourceFoundException.class,
            org.springframework.web.servlet.NoHandlerFoundException.class})
    public ResponseEntity<ApiResponse<Void>> handleNoResource(Exception ex, HttpServletRequest req) {
        ApiResponse<Void> resp = ApiResponse.error(ErrorCode.RESOURCE_NOT_FOUND.getCode(), "请求的资源不存在");
        resp.setPath(req.getRequestURI());
        resp.setMethod(req.getMethod());
        return ResponseEntity.status(ErrorCode.RESOURCE_NOT_FOUND.getHttpStatus()).body(resp);
    }

    /**
     * SRS_NF010 / NT-S3-011: 数据库连接池耗尽、排队等待超时或连接获取失败。
     * 保证瞬时高频并发访问时连接排队超时能够返回友好的服务不可用(503)提示，而非未捕获的500崩溃。
     */
    @ExceptionHandler({
            org.springframework.jdbc.CannotGetJdbcConnectionException.class,
            java.sql.SQLTransientConnectionException.class
    })
    public ResponseEntity<ApiResponse<Void>> handleConnectionPoolTimeout(Exception ex, HttpServletRequest req) {
        log.error("数据库连接池排队超时或连接不可用: {} {} - {}", req.getMethod(), req.getRequestURI(), ex.getMessage());
        ApiResponse<Void> resp = ApiResponse.error(ErrorCode.DATABASE_POOL_BUSY.getCode(),
                "数据库连接繁忙，正在排队重试，请稍后刷新");
        resp.setPath(req.getRequestURI());
        resp.setMethod(req.getMethod());
        return ResponseEntity.status(ErrorCode.DATABASE_POOL_BUSY.getHttpStatus()).body(resp);
    }

    /**
     * SRS_NF010 / NT-S3-011: 数据库并发事务死锁、悲观锁/行锁竞争超时。
     * 杜绝数据库连接死锁导致服务挂死，通过409 Conflict向客户端提供友好的重试提示。
     */
    @ExceptionHandler({
            org.springframework.dao.CannotAcquireLockException.class,
            org.springframework.dao.PessimisticLockingFailureException.class,
            org.springframework.dao.DeadlockLoserDataAccessException.class,
            org.springframework.dao.ConcurrencyFailureException.class
    })
    public ResponseEntity<ApiResponse<Void>> handleConcurrencyLockException(Exception ex, HttpServletRequest req) {
        log.warn("数据库操作并发竞争冲突或锁超时: {} {} - {}", req.getMethod(), req.getRequestURI(), ex.getMessage());
        ApiResponse<Void> resp = ApiResponse.error(ErrorCode.DATA_CONCURRENCY_CONFLICT.getCode(),
                "数据库操作并发竞争冲突，系统已自动防护，请稍后重试");
        resp.setPath(req.getRequestURI());
        resp.setMethod(req.getMethod());
        return ResponseEntity.status(ErrorCode.DATA_CONCURRENCY_CONFLICT.getHttpStatus()).body(resp);
    }

    /**
     * SRS_NF010 / NT-S3-011: 双浏览器/多客户端并发提交导致唯一键冲突或数据完整性约束异常。
     * 返回明确的409 Conflict防竞争提示，避免抛出500未预期异常。
     */
    @ExceptionHandler({
            org.springframework.dao.DuplicateKeyException.class,
            org.springframework.dao.DataIntegrityViolationException.class
    })
    public ResponseEntity<ApiResponse<Void>> handleDataIntegrityViolation(Exception ex, HttpServletRequest req) {
        log.warn("并发操作唯一键冲突或数据完整性约束异常: {} {} - {}", req.getMethod(), req.getRequestURI(), ex.getMessage());
        ApiResponse<Void> resp = ApiResponse.error(ErrorCode.DUPLICATE_KEY_CONFLICT.getCode(),
                "数据并发冲突或唯一标识已存在，请勿重复提交");
        resp.setPath(req.getRequestURI());
        resp.setMethod(req.getMethod());
        return ResponseEntity.status(ErrorCode.DUPLICATE_KEY_CONFLICT.getHttpStatus()).body(resp);
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
