package com.airport.ai.config;

import com.airport.ai.auth.SessionService;
import com.airport.ai.auth.User;
import com.airport.ai.auth.UserMapper;
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

/**
 * 从Authorization: Bearer {token}中解析会话，加载用户角色注入SecurityContext。
 * 会话不存在或已过期时不设置Authentication；携带了Token但会话已失效的场景通过
 * request属性sessionExpired标记，供AuthEntryPoint区分返回2000（未授权）还是2001（会话已过期，
 * 对应SRS_NF002会话空闲30分钟失效）。
 */
@Component
public class TokenAuthenticationFilter extends OncePerRequestFilter {

    private final SessionService sessionService;
    private final UserMapper userMapper;

    public TokenAuthenticationFilter(SessionService sessionService, UserMapper userMapper) {
        this.sessionService = sessionService;
        this.userMapper = userMapper;
    }

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        String path = request.getServletPath();
        return (path.startsWith("/device-api/v1/agents/") && path.endsWith("/report"))
                || path.startsWith("/api/v1/device-agents/report/")
                || path.matches("/api/v1/device-agents/[^/]+/(task-response|execution-feedback)");
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain filterChain)
            throws ServletException, IOException {
        String header = request.getHeader("Authorization");
        if (header != null && header.startsWith("Bearer ")) {
            String token = header.substring(7);
            Long userId = sessionService.touchAndGetUserId(token);
            if (userId != null) {
                userMapper.findById(userId).ifPresentOrElse(user -> {
                    UsernamePasswordAuthenticationToken authToken = new UsernamePasswordAuthenticationToken(
                            user, null, List.of(new SimpleGrantedAuthority("ROLE_" + user.getRole())));
                    SecurityContextHolder.getContext().setAuthentication(authToken);
                    request.setAttribute("currentUser", user);
                }, () -> request.setAttribute("sessionExpired", true));
            } else {
                // 携带了Bearer Token但Redis中找不到对应会话：已过期或已被登出
                request.setAttribute("sessionExpired", true);
            }
        }
        filterChain.doFilter(request, response);
    }
}
