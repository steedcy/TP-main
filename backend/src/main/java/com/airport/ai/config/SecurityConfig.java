package com.airport.ai.config;

import com.airport.ai.auth.OperationLogService;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
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

    @Autowired(required = false)
    private CorsOriginSecurityFilter corsOriginSecurityFilter;

    @Autowired(required = false)
    private ObjectMapper objectMapper;

    @Autowired(required = false)
    private OperationLogService operationLogService;

    @Value("${app.cors.allowed-origins:http://localhost:5173,http://127.0.0.1:5173,http://localhost:8080,http://127.0.0.1:8080}")
    private String allowedOriginsConfig = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8080,http://127.0.0.1:8080";

    @Value("${app.cors.allow-localhost-patterns:true}")
    private boolean allowLocalhostPatterns = true;

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
        CorsOriginSecurityFilter effectiveCorsFilter = corsOriginSecurityFilter != null
                ? corsOriginSecurityFilter
                : new CorsOriginSecurityFilter(objectMapper, operationLogService, allowedOriginsConfig, allowLocalhostPatterns);
        http
            .csrf(csrf -> csrf.disable())
            .cors(cors -> cors.disable())
            .sessionManagement(sm -> sm.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .exceptionHandling(eh -> eh
                .authenticationEntryPoint(authEntryPoint)
                .accessDeniedHandler(accessDeniedHandler)
            )
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/api/v1/auth/login").permitAll()
                .requestMatchers("/actuator/**").permitAll()
                .requestMatchers("/ws/**").permitAll()
                .requestMatchers("/device-api/v1/agents/*/report").hasRole("DEVICE_AGENT")
                .requestMatchers("/api/v1/device-agents/report/*").hasRole("DEVICE_AGENT")
                .requestMatchers("/api/v1/device-agents/*/task-response").hasRole("DEVICE_AGENT")
                .requestMatchers("/api/v1/device-agents/*/execution-feedback").hasRole("DEVICE_AGENT")
                .requestMatchers("/internal/v1/device-agent/messages").hasRole("SYSTEM_ADMIN")
                // 账号管理仅系统管理员：在过滤器链先校验角色，避免无权限请求先经请求体校验返回400（DEF-S3-001、TC-003.S2）
                .requestMatchers("/api/v1/users", "/api/v1/users/**").hasRole("SYSTEM_ADMIN")
                .anyRequest().authenticated()
            )
            .addFilterBefore(tokenAuthenticationFilter, UsernamePasswordAuthenticationFilter.class)
            .addFilterBefore(deviceTokenAuthenticationFilter, TokenAuthenticationFilter.class)
            .addFilterAfter(effectiveCorsFilter, TokenAuthenticationFilter.class);
        return http.build();
    }
}
