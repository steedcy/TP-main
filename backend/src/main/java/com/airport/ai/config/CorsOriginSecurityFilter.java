package com.airport.ai.config;

import com.airport.ai.auth.OperationLogService;
import com.airport.ai.auth.User;
import com.airport.ai.common.ApiResponse;
import com.airport.ai.common.ErrorCode;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import java.util.LinkedHashSet;
import java.util.Locale;
import java.util.Set;
import java.util.stream.Collectors;

/**
 * 跨域源白名单校验与拦截过滤器（对应SRS_NF004、TC-003、TC-085）。
 * 严格限制可信 Origin 白名单，拦截未知外部源发起的跨域预检与跨域读写请求，防止 CSRF/CORS 跨域越权调用。
 */
@Component
public class CorsOriginSecurityFilter extends OncePerRequestFilter {

    private static final String ALLOWED_METHODS = "GET, POST, PUT, PATCH, DELETE, OPTIONS";
    private static final String ALLOWED_HEADERS = "Authorization, Content-Type, X-Device-Token, X-Requested-With, Accept, Origin";
    private static final String MAX_AGE_SECONDS = "3600";

    private final ObjectMapper objectMapper;
    private final OperationLogService operationLogService;
    private final Set<String> allowedOrigins;
    private final boolean allowLocalhostPatterns;

    @Autowired
    public CorsOriginSecurityFilter(
            ObjectMapper objectMapper,
            @Autowired(required = false) OperationLogService operationLogService,
            @Value("${app.cors.allowed-origins:http://localhost:5173,http://127.0.0.1:5173,http://localhost:8080,http://127.0.0.1:8080}") String allowedOriginsConfig,
            @Value("${app.cors.allow-localhost-patterns:true}") boolean allowLocalhostPatterns) {
        this.objectMapper = objectMapper != null ? objectMapper : new ObjectMapper();
        this.operationLogService = operationLogService;
        this.allowedOrigins = parseAllowedOrigins(allowedOriginsConfig);
        this.allowLocalhostPatterns = allowLocalhostPatterns;
    }

    public CorsOriginSecurityFilter(ObjectMapper objectMapper, OperationLogService operationLogService) {
        this(objectMapper, operationLogService,
                "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8080,http://127.0.0.1:8080",
                true);
    }

    private static Set<String> parseAllowedOrigins(String raw) {
        if (raw == null || raw.isBlank()) {
            return Set.of();
        }
        return Arrays.stream(raw.split(","))
                .map(String::trim)
                .filter(s -> !s.isEmpty())
                .map(CorsOriginSecurityFilter::normalizeOriginString)
                .collect(Collectors.toCollection(LinkedHashSet::new));
    }

    private static String normalizeOriginString(String origin) {
        String trimmed = origin.trim();
        while (trimmed.endsWith("/")) {
            trimmed = trimmed.substring(0, trimmed.length() - 1);
        }
        return trimmed.toLowerCase(Locale.ROOT);
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                    HttpServletResponse response,
                                    FilterChain filterChain) throws ServletException, IOException {
        String origin = request.getHeader(HttpHeaders.ORIGIN);
        if (origin == null || origin.isBlank()) {
            filterChain.doFilter(request, response);
            return;
        }

        if (!isAllowedOrigin(origin, request)) {
            recordDeniedOriginIfPossible(request);
            response.setStatus(HttpServletResponse.SC_FORBIDDEN);
            response.setCharacterEncoding(StandardCharsets.UTF_8.name());
            response.setContentType(MediaType.APPLICATION_JSON_VALUE);
            ApiResponse<Void> body = ApiResponse.error(
                    ErrorCode.FORBIDDEN.getCode(),
                    "跨域请求源未授权：" + origin.trim()
            );
            body.setPath(request.getRequestURI());
            body.setMethod(request.getMethod());
            response.getWriter().write(objectMapper.writeValueAsString(body));
            return;
        }

        String cleanOrigin = origin.trim();
        response.setHeader(HttpHeaders.ACCESS_CONTROL_ALLOW_ORIGIN, cleanOrigin);
        response.setHeader(HttpHeaders.ACCESS_CONTROL_ALLOW_CREDENTIALS, "true");
        response.addHeader(HttpHeaders.VARY, HttpHeaders.ORIGIN);

        if (HttpMethod.OPTIONS.matches(request.getMethod())) {
            response.setHeader(HttpHeaders.ACCESS_CONTROL_ALLOW_METHODS, ALLOWED_METHODS);
            response.setHeader(HttpHeaders.ACCESS_CONTROL_ALLOW_HEADERS, ALLOWED_HEADERS);
            response.setHeader(HttpHeaders.ACCESS_CONTROL_MAX_AGE, MAX_AGE_SECONDS);
            response.setStatus(HttpServletResponse.SC_OK);
            return;
        }

        filterChain.doFilter(request, response);
    }

    public boolean isAllowedOrigin(String origin, HttpServletRequest request) {
        if (origin == null) {
            return false;
        }
        String trimmed = origin.trim();
        if (trimmed.isEmpty() || "null".equalsIgnoreCase(trimmed) || "*".equals(trimmed)) {
            return false;
        }

        URI uri;
        try {
            uri = URI.create(trimmed);
        } catch (IllegalArgumentException ex) {
            return false;
        }

        String scheme = uri.getScheme();
        String host = uri.getHost();
        if (scheme == null || host == null) {
            return false;
        }
        String lowerScheme = scheme.toLowerCase(Locale.ROOT);
        if (!"http".equals(lowerScheme) && !"https".equals(lowerScheme)) {
            return false;
        }
        if (uri.getUserInfo() != null || uri.getRawQuery() != null || uri.getRawFragment() != null) {
            return false;
        }
        String rawPath = uri.getRawPath();
        if (rawPath != null && !rawPath.isEmpty() && !"/".equals(rawPath)) {
            return false;
        }

        int port = uri.getPort();
        if (port < -1 || port == 0 || port > 65535) {
            return false;
        }

        String normalized = normalizeOriginString(trimmed);
        if (allowedOrigins.contains(normalized)) {
            return true;
        }

        String lowerHost = host.toLowerCase(Locale.ROOT);
        if (allowLocalhostPatterns && isLoopbackHost(lowerHost)) {
            return true;
        }

        return isSameOrigin(lowerScheme, lowerHost, port, request);
    }

    private static boolean isLoopbackHost(String lowerHost) {
        return "localhost".equals(lowerHost)
                || "127.0.0.1".equals(lowerHost)
                || "[::1]".equals(lowerHost)
                || "::1".equals(lowerHost);
    }

    private static boolean isSameOrigin(String originScheme, String originHost, int originPort, HttpServletRequest request) {
        if (request == null || request.getScheme() == null || request.getServerName() == null) {
            return false;
        }
        String reqScheme = request.getScheme().toLowerCase(Locale.ROOT);
        String reqHost = request.getServerName().toLowerCase(Locale.ROOT);
        int reqPort = effectivePort(reqScheme, request.getServerPort());
        int effOriginPort = effectivePort(originScheme, originPort);
        return reqScheme.equals(originScheme) && reqHost.equals(originHost) && reqPort == effOriginPort;
    }

    private static int effectivePort(String scheme, int port) {
        if (port > 0) {
            return port;
        }
        return "https".equals(scheme) ? 443 : 80;
    }

    private void recordDeniedOriginIfPossible(HttpServletRequest request) {
        if (operationLogService == null) {
            return;
        }
        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        if (auth != null && auth.getPrincipal() instanceof User user) {
            operationLogService.record(
                    user.getId(),
                    user.getUsername(),
                    user.getRole(),
                    "ACCESS_DENIED",
                    request.getRequestURI(),
                    "FAILED",
                    request.getRemoteAddr()
            );
        }
    }
}
