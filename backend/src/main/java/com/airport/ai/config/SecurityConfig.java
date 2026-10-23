package com.airport.ai.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.method.configuration.EnableMethodSecurity;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;

/**
 * 权限模型：RBAC，权限由服务端逐接口校验，不依赖前端菜单隐藏（对应SRS_NF004）。
 * 会话认证通过TokenAuthenticationFilter基于Redis会话完成，不使用Spring Security默认的表单登录/JWT体系。
 */
@Configuration
@EnableWebSecurity
@EnableMethodSecurity
public class SecurityConfig {

    private final TokenAuthenticationFilter tokenAuthenticationFilter;
    private final DeviceTokenAuthenticationFilter deviceTokenAuthenticationFilter;
    private final AuthEntryPoint authEntryPoint;
    private final AccessDeniedHandlerImpl accessDeniedHandler;

    public SecurityConfig(TokenAuthenticationFilter tokenAuthenticationFilter,
                           DeviceTokenAuthenticationFilter deviceTokenAuthenticationFilter,
                           AuthEntryPoint authEntryPoint,
                           AccessDeniedHandlerImpl accessDeniedHandler) {
        this.tokenAuthenticationFilter = tokenAuthenticationFilter;
        this.deviceTokenAuthenticationFilter = deviceTokenAuthenticationFilter;
        this.authEntryPoint = authEntryPoint;
        this.accessDeniedHandler = accessDeniedHandler;
    }

    @Bean
    public PasswordEncoder passwordEncoder() {
        // 不可逆摘要（加盐）存储，对应SRS_NF001
        return new BCryptPasswordEncoder();
    }

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http
            .csrf(csrf -> csrf.disable())
            .sessionManagement(sm -> sm.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .exceptionHandling(eh -> eh
                .authenticationEntryPoint(authEntryPoint)
                .accessDeniedHandler(accessDeniedHandler)
            )
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/api/v1/auth/login").permitAll()
                .requestMatchers("/actuator/health").permitAll()
                .requestMatchers("/ws/**").permitAll()
                .requestMatchers("/device-api/v1/agents/*/report").hasRole("DEVICE_AGENT")
                .requestMatchers("/api/v1/device-agents/report/*").hasRole("DEVICE_AGENT")
                .requestMatchers("/api/v1/device-agents/*/task-response").hasRole("DEVICE_AGENT")
                .requestMatchers("/api/v1/device-agents/*/execution-feedback").hasRole("DEVICE_AGENT")
                .requestMatchers("/internal/v1/device-agent/messages").hasRole("SYSTEM_ADMIN")
                .anyRequest().authenticated()
            )
            .addFilterBefore(tokenAuthenticationFilter, UsernamePasswordAuthenticationFilter.class)
            .addFilterBefore(deviceTokenAuthenticationFilter, TokenAuthenticationFilter.class);
        return http.build();
    }
}
