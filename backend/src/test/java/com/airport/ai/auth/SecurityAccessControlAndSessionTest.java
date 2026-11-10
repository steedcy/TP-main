package com.airport.ai.auth;

import com.airport.ai.auth.dto.CreateUserRequest;
import com.airport.ai.auth.dto.ResetPasswordRequest;
import com.airport.ai.common.GlobalExceptionHandler;
import com.airport.ai.config.AccessDeniedHandlerImpl;
import com.airport.ai.config.AuthEntryPoint;
import com.airport.ai.config.DeviceTokenAuthenticationFilter;
import com.airport.ai.config.PreAuthorizeInterceptor;
import com.airport.ai.config.SecurityConfig;
import com.airport.ai.config.TokenAuthenticationFilter;
import com.airport.ai.config.WebMvcAuthorizationConfig;
import com.airport.ai.device.DeviceController;
import com.airport.ai.device.DeviceCredentialService;
import com.airport.ai.device.DeviceService;
import com.airport.ai.event.TaskEventService;
import com.airport.ai.task.TaskController;
import com.airport.ai.task.TaskService;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.Import;
import org.springframework.data.redis.core.SetOperations;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.ValueOperations;
import org.springframework.http.MediaType;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.test.web.servlet.MockMvc;

import java.util.Optional;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.assertNull;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * 对应 SRS_NF001 系统安全性（认证与权限）：
 * 1. 越权访问防护与会话安全：跨权限调用统一返回 403 Forbidden 并记录 ACCESS_DENIED 审计日志；
 * 2. 会话时效与防劫持机制：验证非法/过期 Token、伪造 JWT 签名的请求被快速拦截（401 Unauthorized）；
 * 3. 会话注销或重置后旧 Token 立即失效。
 */
@WebMvcTest({UserController.class, DeviceController.class, TaskController.class})
@Import({SecurityConfig.class, AccessDeniedHandlerImpl.class, AuthEntryPoint.class,
        TokenAuthenticationFilter.class, DeviceTokenAuthenticationFilter.class, GlobalExceptionHandler.class,
        PreAuthorizeInterceptor.class, WebMvcAuthorizationConfig.class})
class SecurityAccessControlAndSessionTest {

    @Autowired MockMvc mvc;

    @MockBean UserService userService;
    @MockBean AuthService authService;
    @MockBean CurrentUser currentUser;
    @MockBean DeviceService deviceService;
    @MockBean DeviceCredentialService deviceCredentialService;
    @MockBean TaskService taskService;
    @MockBean TaskEventService taskEventService;
    @MockBean SessionService sessionService;
    @MockBean UserMapper userMapper;
    @MockBean OperationLogService operationLogService;

    private User mockActiveLogin(String token, long userId, String role) {
        User u = new User();
        u.setId(userId);
        u.setUsername(role.toLowerCase() + "-" + userId);
        u.setRole(role);
        u.setStatus("ACTIVE");
        when(sessionService.touchAndGetUserId(token)).thenReturn(userId);
        when(userMapper.findById(userId)).thenReturn(Optional.of(u));
        return u;
    }

    private User mockLoginWithStatus(String token, long userId, String role, String status) {
        User u = new User();
        u.setId(userId);
        u.setUsername(role.toLowerCase() + "-" + userId);
        u.setRole(role);
        u.setStatus(status);
        when(sessionService.touchAndGetUserId(token)).thenReturn(userId);
        when(userMapper.findById(userId)).thenReturn(Optional.of(u));
        return u;
    }

    @Nested
    @DisplayName("1. 越权访问防护与审计留痕")
    class AuthorizationAndPrivilegeEscalationProtection {

        @Test
        @DisplayName("系统操作员越权调用用户列表接口被拦截为 403 并留痕")
        void operatorAccessUserListIsForbidden() throws Exception {
            mockActiveLogin("op-token-1", 101L, "OPERATOR");

            mvc.perform(get("/api/v1/users").header("Authorization", "Bearer op-token-1"))
                    .andExpect(status().isForbidden())
                    .andExpect(jsonPath("$.code").value(2003));

            verify(operationLogService).record(eq(101L), eq("operator-101"), eq("OPERATOR"), eq("ACCESS_DENIED"),
                    eq("/api/v1/users"), eq("FAILED"), any());
            verifyNoInteractions(userService);
        }

        @Test
        @DisplayName("配置管理员越权重置用户密码被拦截为 403 并留痕")
        void configAdminResetPasswordIsForbidden() throws Exception {
            mockActiveLogin("ca-token-1", 102L, "CONFIG_ADMIN");

            mvc.perform(post("/api/v1/users/5/reset-password")
                            .header("Authorization", "Bearer ca-token-1")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content("{\"newPassword\":\"NewPass1234!\"}"))
                    .andExpect(status().isForbidden())
                    .andExpect(jsonPath("$.code").value(2003));

            verify(operationLogService).record(eq(102L), eq("config_admin-102"), eq("CONFIG_ADMIN"), eq("ACCESS_DENIED"),
                    eq("/api/v1/users/5/reset-password"), eq("FAILED"), any());
            verifyNoInteractions(userService);
        }

        @Test
        @DisplayName("系统操作员越权创建设备接口被拦截为 403 并留痕")
        void operatorCreateDeviceIsForbidden() throws Exception {
            mockActiveLogin("op-token-2", 103L, "OPERATOR");

            mvc.perform(post("/api/v1/devices")
                            .header("Authorization", "Bearer op-token-2")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content("{\"deviceCode\":\"DEV_01\",\"deviceName\":\"Robot\"}"))
                    .andExpect(status().isForbidden())
                    .andExpect(jsonPath("$.code").value(2003));

            verify(operationLogService).record(eq(103L), eq("operator-103"), eq("OPERATOR"), eq("ACCESS_DENIED"),
                    eq("/api/v1/devices"), eq("FAILED"), any());
            verifyNoInteractions(deviceService);
        }

        @Test
        @DisplayName("系统管理员越权提交业务任务接口被拦截为 403 并留痕")
        void systemAdminSubmitTaskIsForbidden() throws Exception {
            mockActiveLogin("sa-token-1", 104L, "SYSTEM_ADMIN");

            mvc.perform(post("/api/v1/tasks")
                            .header("Authorization", "Bearer sa-token-1")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content("{\"goal\":\"Clean floor\",\"taskType\":\"CLEAN\"}"))
                    .andExpect(status().isForbidden())
                    .andExpect(jsonPath("$.code").value(2003));

            verify(operationLogService).record(eq(104L), eq("system_admin-104"), eq("SYSTEM_ADMIN"), eq("ACCESS_DENIED"),
                    eq("/api/v1/tasks"), eq("FAILED"), any());
            verifyNoInteractions(taskService);
        }

        @Test
        @DisplayName("配置管理员越权人工终止任务接口被拦截为 403 并留痕")
        void configAdminTerminateTaskIsForbidden() throws Exception {
            mockActiveLogin("ca-token-2", 105L, "CONFIG_ADMIN");

            mvc.perform(post("/api/v1/tasks/888/terminate")
                            .header("Authorization", "Bearer ca-token-2")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content("{\"reason\":\"Config admin unauthorized terminate\"}"))
                    .andExpect(status().isForbidden())
                    .andExpect(jsonPath("$.code").value(2003));

            verify(operationLogService).record(eq(105L), eq("config_admin-105"), eq("CONFIG_ADMIN"), eq("ACCESS_DENIED"),
                    eq("/api/v1/tasks/888/terminate"), eq("FAILED"), any());
            verifyNoInteractions(taskService);
        }
    }

    @Nested
    @DisplayName("2. 会话时效与防劫持机制")
    class SessionTimelinessAndAntiHijacking {

        @Test
        @DisplayName("未携带 Authorization Header 快速拦截返回 401 (UNAUTHORIZED 2000)")
        void requestWithoutTokenReturns401() throws Exception {
            mvc.perform(get("/api/v1/users"))
                    .andExpect(status().isUnauthorized())
                    .andExpect(jsonPath("$.code").value(2000));
        }

        @Test
        @DisplayName("携带空白 Bearer Token 快速拦截返回 401")
        void requestWithBlankTokenReturns401() throws Exception {
            mvc.perform(get("/api/v1/users").header("Authorization", "Bearer   "))
                    .andExpect(status().isUnauthorized())
                    .andExpect(jsonPath("$.code").value(2001));
        }

        @Test
        @DisplayName("携带过期或已删除 Token 快速拦截返回 401 (SESSION_EXPIRED 2001)")
        void requestWithExpiredTokenReturns401() throws Exception {
            when(sessionService.touchAndGetUserId("expired-token-999")).thenReturn(null);

            mvc.perform(get("/api/v1/users").header("Authorization", "Bearer expired-token-999"))
                    .andExpect(status().isUnauthorized())
                    .andExpect(jsonPath("$.code").value(2001));
        }

        @Test
        @DisplayName("携带伪造 JWT 签名 Token 快速拦截返回 401")
        void requestWithForgedJwtTokenReturns401() throws Exception {
            String fakeJwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsInJvbGUiOiJTWVNURU1fQURNSU4ifQ.invalid_signature_xxx";
            when(sessionService.touchAndGetUserId(fakeJwt)).thenReturn(null);

            mvc.perform(get("/api/v1/users").header("Authorization", "Bearer " + fakeJwt))
                    .andExpect(status().isUnauthorized())
                    .andExpect(jsonPath("$.code").value(2001));
        }

        @Test
        @DisplayName("账号被停用（INACTIVE）后即便携带合法Token也被拦截为 401")
        void inactiveUserWithTokenReturns401() throws Exception {
            mockLoginWithStatus("token-inactive", 201L, "OPERATOR", "INACTIVE");

            mvc.perform(post("/api/v1/tasks")
                            .header("Authorization", "Bearer token-inactive")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content("{\"goal\":\"test\"}"))
                    .andExpect(status().isUnauthorized())
                    .andExpect(jsonPath("$.code").value(2001));
        }

        @Test
        @DisplayName("账号被锁定（LOCKED）后即便携带合法Token也被拦截为 401")
        void lockedUserWithTokenReturns401() throws Exception {
            mockLoginWithStatus("token-locked", 202L, "OPERATOR", "LOCKED");

            mvc.perform(post("/api/v1/tasks")
                            .header("Authorization", "Bearer token-locked")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content("{\"goal\":\"test\"}"))
                    .andExpect(status().isUnauthorized())
                    .andExpect(jsonPath("$.code").value(2001));
        }
    }

    @Nested
    @DisplayName("3. 会话注销与密码重置联动失效")
    class SessionInvalidationOnResetAndLogout {

        @Test
        @DisplayName("管理员重置密码时联动注销该用户所有活跃会话")
        void passwordResetInvalidatesUserSessions() {
            UserMapper mockUserMapper = mock(UserMapper.class);
            PasswordEncoder mockEncoder = mock(PasswordEncoder.class);
            OperationLogService mockAudit = mock(OperationLogService.class);
            SessionService mockSessionService = mock(SessionService.class);

            UserService service = new UserService(mockUserMapper, mockEncoder, mockAudit, mockSessionService);

            User target = new User();
            target.setId(301L);
            target.setUsername("target_op");
            target.setRole("OPERATOR");
            target.setStatus("ACTIVE");
            when(mockUserMapper.findById(301L)).thenReturn(Optional.of(target));
            when(mockEncoder.encode("NewSecretPassword123!")).thenReturn("$2a$10$new-hash");

            User admin = new User();
            admin.setId(1L);
            admin.setUsername("admin");
            admin.setRole("SYSTEM_ADMIN");

            service.resetPassword(301L, "NewSecretPassword123!", admin);

            verify(mockUserMapper).update(target);
            verify(mockSessionService).invalidateUserSessions(301L);
        }

        @Test
        @DisplayName("停用或锁定账号时联动注销该用户所有活跃会话")
        void deactivatingUserInvalidatesUserSessions() {
            UserMapper mockUserMapper = mock(UserMapper.class);
            PasswordEncoder mockEncoder = mock(PasswordEncoder.class);
            OperationLogService mockAudit = mock(OperationLogService.class);
            SessionService mockSessionService = mock(SessionService.class);

            UserService service = new UserService(mockUserMapper, mockEncoder, mockAudit, mockSessionService);

            User target = new User();
            target.setId(302L);
            target.setUsername("target_ca");
            target.setRole("CONFIG_ADMIN");
            target.setStatus("ACTIVE");
            when(mockUserMapper.findById(302L)).thenReturn(Optional.of(target));

            User admin = new User();
            admin.setId(1L);
            admin.setUsername("admin");
            admin.setRole("SYSTEM_ADMIN");

            service.updateStatus(302L, "INACTIVE", admin);

            verify(mockUserMapper).update(target);
            verify(mockSessionService).invalidateUserSessions(302L);
        }

        @Test
        @DisplayName("SessionService 正确管理单 Token 注销与用户全量 Token 注销")
        @SuppressWarnings("unchecked")
        void sessionServiceLifecycleVerification() {
            StringRedisTemplate redisTemplate = mock(StringRedisTemplate.class);
            ValueOperations<String, String> valueOps = mock(ValueOperations.class);
            SetOperations<String, String> setOps = mock(SetOperations.class);

            when(redisTemplate.opsForValue()).thenReturn(valueOps);
            when(redisTemplate.opsForSet()).thenReturn(setOps);

            SessionService sessionServiceReal = new SessionService(redisTemplate, 30);

            // 1. 创建会话
            String token = sessionServiceReal.createSession(501L);
            verify(valueOps).set(eq("session:" + token), eq("501"), any());
            verify(setOps).add(eq("user_sessions:501"), eq(token));

            // 2. 单 Token 注销 (例如用户主动退出)
            when(valueOps.get("session:" + token)).thenReturn("501");
            sessionServiceReal.invalidate(token);
            verify(redisTemplate).delete("session:" + token);
            verify(setOps).remove("user_sessions:501", token);

            // 3. 用户全量会话注销 (例如重置密码)
            when(setOps.members("user_sessions:501")).thenReturn(Set.of("tok-a", "tok-b"));
            sessionServiceReal.invalidateUserSessions(501L);
            verify(redisTemplate).delete("session:tok-a");
            verify(redisTemplate).delete("session:tok-b");
            verify(redisTemplate).delete("user_sessions:501");
        }
    }
}
