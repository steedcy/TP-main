package com.airport.ai.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.InterceptorRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

@Configuration
public class WebMvcAuthorizationConfig implements WebMvcConfigurer {

    private final PreAuthorizeInterceptor preAuthorizeInterceptor;

    public WebMvcAuthorizationConfig(PreAuthorizeInterceptor preAuthorizeInterceptor) {
        this.preAuthorizeInterceptor = preAuthorizeInterceptor;
    }

    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        registry.addInterceptor(preAuthorizeInterceptor).addPathPatterns("/api/**", "/internal/**");
    }
}
