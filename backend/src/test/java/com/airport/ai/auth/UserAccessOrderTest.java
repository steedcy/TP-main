package com.airport.ai.auth;

import com.airport.ai.common.GlobalExceptionHandler;
import com.airport.ai.config.AccessDeniedHandlerImpl;
import com.airport.ai.config.AuthEntryPoint;
import com.airport.ai.config.DeviceTokenAuthenticationFilter;
import com.airport.ai.config.SecurityConfig;
import com.airport.ai.config.TokenAuthenticationFilter;
import com.airport.ai.device.DeviceCredentialService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import java.util.Optional;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** DEF-S3-001 / TC-003.S2：无权限请求先得到403并留痕，不因缺字段先返回400，且不触达业务层。 */
@WebMvcTest(UserController.class)
@Import({SecurityConfig.class, AccessDeniedHandlerImpl.class, AuthEntryPoint.class,
        TokenAuthenticationFilter.class, DeviceTokenAuthenticationFilter.class, GlobalExceptionHandler.class})
class UserAccessOrderTest {

    @Autowired MockMvc mvc;
    @MockBean UserService userService;
    @MockBean AuthService authService;
    @MockBean CurrentUser currentUser;
    @MockBean SessionService sessionService;
    @MockBean UserMapper userMapper;
    @MockBean OperationLogService operationLogService;
    @MockBean DeviceCredentialService deviceCredentialService;

    private User login(String token, long id, String role) {
        User u = new User();
        u.setId(id);
        u.setUsername(role.toLowerCase() + "-" + id);
        u.setRole(role);
        when(sessionService.touchAndGetUserId(token)).thenReturn(id);
        when(userMapper.findById(id)).thenReturn(Optional.of(u));
        return u;
    }

    @Test
    void operatorWithInvalidBodyGets403AndAuditNotValidation400() throws Exception {
        login("op-token", 7L, "OPERATOR");

        mvc.perform(post("/api/v1/users").header("Authorization", "Bearer op-token")
                        .contentType(MediaType.APPLICATION_JSON).content("{}"))
                .andExpect(status().isForbidden())
                .andExpect(jsonPath("$.code").value(2003));

        verify(operationLogService).record(eq(7L), eq("operator-7"), eq("OPERATOR"), eq("ACCESS_DENIED"),
                eq("/api/v1/users"), eq("FAILED"), any());
        verifyNoInteractions(userService);
    }

    @Test
    void operatorWithValidBodyStillGets403() throws Exception {
        login("op-token", 7L, "OPERATOR");
        String body = "{\"username\":\"u1\",\"password\":\"Passw0rd!x\",\"realName\":\"n\","
                + "\"role\":\"OPERATOR\",\"contact\":\"c\"}";

        mvc.perform(post("/api/v1/users").header("Authorization", "Bearer op-token")
                        .contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isForbidden());
        verifyNoInteractions(userService);
    }

    @Test
    void adminWithInvalidBodyStillGets400() throws Exception {
        login("admin-token", 1L, "SYSTEM_ADMIN");

        mvc.perform(post("/api/v1/users").header("Authorization", "Bearer admin-token")
                        .contentType(MediaType.APPLICATION_JSON).content("{}"))
                .andExpect(status().isBadRequest());
    }

    @Test
    void unauthenticatedRequestIs401() throws Exception {
        mvc.perform(post("/api/v1/users").contentType(MediaType.APPLICATION_JSON).content("{}"))
                .andExpect(status().isUnauthorized());
    }
}
