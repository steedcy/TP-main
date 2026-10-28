package com.airport.ai.config;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.context.ApplicationContext;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.security.authorization.AuthorizationDecision;
import org.springframework.security.authorization.method.PreAuthorizeAuthorizationManager;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.access.expression.method.DefaultMethodSecurityExpressionHandler;
import org.springframework.stereotype.Component;
import org.springframework.web.method.HandlerMethod;
import org.springframework.web.servlet.HandlerInterceptor;
import org.aopalliance.intercept.MethodInvocation;

import java.lang.reflect.Method;

/**
 * 在参数绑定与@Valid校验之前先执行控制器上的@PreAuthorize（方法级优先于类级），
 * 使无权限请求不论请求体是否合法都先得到403并由GlobalExceptionHandler留痕（DEF-S3-001、DEF-S3-072、TC-003.S2）。
 * 方法级@PreAuthorize在业务方法调用时仍会再校验一次，注解保持为唯一的权限来源。
 */
@Component
public class PreAuthorizeInterceptor implements HandlerInterceptor {

    private final PreAuthorizeAuthorizationManager manager = new PreAuthorizeAuthorizationManager();

    public PreAuthorizeInterceptor(ApplicationContext context) {
        DefaultMethodSecurityExpressionHandler handler = new DefaultMethodSecurityExpressionHandler();
        handler.setApplicationContext(context);
        manager.setExpressionHandler(handler);
    }

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) {
        if (!(handler instanceof HandlerMethod hm)) {
            return true;
        }
        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        if (auth == null) {
            return true; // 未认证请求已由过滤器链以401处理
        }
        AuthorizationDecision decision = manager.check(() -> auth, new HandlerInvocation(hm));
        if (decision != null && !decision.isGranted()) {
            throw new AccessDeniedException("Access Denied");
        }
        return true;
    }

    private record HandlerInvocation(HandlerMethod hm) implements MethodInvocation {
        @Override public Method getMethod() { return hm.getMethod(); }
        @Override public Object[] getArguments() { return new Object[hm.getMethod().getParameterCount()]; }
        @Override public Object proceed() { throw new UnsupportedOperationException(); }
        @Override public Object getThis() { return hm.getBean(); }
        @Override public java.lang.reflect.AccessibleObject getStaticPart() { return hm.getMethod(); }
    }
}
