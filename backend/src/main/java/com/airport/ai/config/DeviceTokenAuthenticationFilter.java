package com.airport.ai.config;

import com.airport.ai.device.DeviceCredentialService;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.List;

/** Authenticates device reports with a per-device bearer token, separate from operator sessions. */
@Component
public class DeviceTokenAuthenticationFilter extends OncePerRequestFilter {
    private final DeviceCredentialService credentialService;

    public DeviceTokenAuthenticationFilter(DeviceCredentialService credentialService) {
        this.credentialService = credentialService;
    }

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        String path = request.getServletPath();
        return !isReportPath(path);
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws ServletException, IOException {
        String path = request.getServletPath();
        String header = request.getHeader("Authorization");
        if (header != null && header.startsWith("Bearer ")) {
            String token = header.substring(7).trim();
            String[] segments = path.split("/");
            boolean authenticated = false;
            if (path.startsWith("/device-api/v1/agents/") && path.endsWith("/report") && segments.length >= 6) {
                authenticated = credentialService.matchesAgentCode(segments[4], token);
            } else if (path.startsWith("/api/v1/device-agents/report/") && segments.length >= 6) {
                authenticated = credentialService.matchesDeviceCode(segments[5], token);
            } else if (path.startsWith("/api/v1/device-agents/") && segments.length >= 5) {
                authenticated = credentialService.matchesAgentCode(segments[4], token);
            }
            if (authenticated) {
                var authentication = new UsernamePasswordAuthenticationToken(
                        path, null, List.of(new SimpleGrantedAuthority("ROLE_DEVICE_AGENT")));
                SecurityContextHolder.getContext().setAuthentication(authentication);
            }
        }
        chain.doFilter(request, response);
    }

    private boolean isReportPath(String path) {
        return (path.startsWith("/device-api/v1/agents/") && path.endsWith("/report"))
                || path.startsWith("/api/v1/device-agents/report/")
                || path.matches("/api/v1/device-agents/[^/]+/(task-response|execution-feedback)");
    }
}
