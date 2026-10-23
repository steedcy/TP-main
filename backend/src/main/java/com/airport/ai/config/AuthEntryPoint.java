package com.airport.ai.config;

import com.airport.ai.common.ApiResponse;
import com.airport.ai.common.ErrorCode;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.security.core.AuthenticationException;
import org.springframework.security.web.AuthenticationEntryPoint;
import org.springframework.stereotype.Component;

import java.io.IOException;

/**
 * 未认证访问的统一JSON响应，替代Spring Security默认的401页面。
 * 区分"未提供Token"（2000未授权访问）与"Token对应会话已过期/失效"（2001会话已过期，
 * 对应SRS_NF002会话空闲30分钟失效），标记由TokenAuthenticationFilter写入request attribute。
 */
@Component
public class AuthEntryPoint implements AuthenticationEntryPoint {

    private final ObjectMapper objectMapper;

    public AuthEntryPoint(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
    }

    @Override
    public void commence(HttpServletRequest request, HttpServletResponse response, AuthenticationException authException)
            throws IOException, ServletException {
        boolean sessionExpired = Boolean.TRUE.equals(request.getAttribute("sessionExpired"));
        ErrorCode errorCode = sessionExpired ? ErrorCode.SESSION_EXPIRED : ErrorCode.UNAUTHORIZED;

        ApiResponse<Void> body = ApiResponse.error(errorCode.getCode(), errorCode.getMessage());
        body.setPath(request.getRequestURI());
        body.setMethod(request.getMethod());

        response.setStatus(errorCode.getHttpStatus().value());
        response.setContentType("application/json;charset=UTF-8");
        response.getWriter().write(objectMapper.writeValueAsString(body));
    }
}
