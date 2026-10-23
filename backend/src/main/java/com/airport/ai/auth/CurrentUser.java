package com.airport.ai.auth;

import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;

/**
 * 从SecurityContext中取出TokenAuthenticationFilter注入的当前登录用户
 */
@Component
public class CurrentUser {

    public User get() {
        Object principal = SecurityContextHolder.getContext().getAuthentication().getPrincipal();
        return (User) principal;
    }
}
