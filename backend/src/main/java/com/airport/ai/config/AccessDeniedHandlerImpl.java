package com.airport.ai.config;

import com.airport.ai.auth.User;
import com.airport.ai.auth.OperationLogService;
import com.airport.ai.common.ApiResponse;
import com.airport.ai.common.ErrorCode;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.web.access.AccessDeniedHandler;
import org.springframework.stereotype.Component;

import java.io.IOException;

/**
 * 无权限访问的统一JSON响应（对应5.1.1业务规则5、附录B错误码2003、TC_AUTH_008）。
 * 越权调用同样写入操作记录，前端不展示越权入口，但服务端仍要留痕。
 */
@Component
public class AccessDeniedHandlerImpl implements AccessDeniedHandler {

    private final ObjectMapper objectMapper;
    private final OperationLogService operationLogService;

    public AccessDeniedHandlerImpl(ObjectMapper objectMapper, OperationLogService operationLogService) {
        this.objectMapper = objectMapper;
        this.operationLogService = operationLogService;
    }

    @Override
    public void handle(HttpServletRequest request, HttpServletResponse response, AccessDeniedException accessDeniedException)
            throws IOException, ServletException {
        Object principal = SecurityContextHolder.getContext().getAuthentication() != null
                ? SecurityContextHolder.getContext().getAuthentication().getPrincipal() : null;
        if (principal instanceof User user) {
            operationLogService.record(user.getId(), user.getUsername(), user.getRole(),
                    "ACCESS_DENIED", request.getRequestURI(), "FAILED", request.getRemoteAddr());
        }

        ApiResponse<Void> body = ApiResponse.error(ErrorCode.FORBIDDEN.getCode(), ErrorCode.FORBIDDEN.getMessage());
        body.setPath(request.getRequestURI());
        body.setMethod(request.getMethod());

        response.setStatus(ErrorCode.FORBIDDEN.getHttpStatus().value());
        response.setContentType("application/json;charset=UTF-8");
        response.getWriter().write(objectMapper.writeValueAsString(body));
    }
}
