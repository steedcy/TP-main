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
import org.springframework.dao.DataAccessResourceFailureException;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** NT-S3-001 / TC-002.S4 的进程内部分：认证服务或数据库异常时返回统一提示、不建立会话，不泄露内部细节。 */
@WebMvcTest(AuthController.class)
@Import({SecurityConfig.class, AccessDeniedHandlerImpl.class, AuthEntryPoint.class,
        TokenAuthenticationFilter.class, DeviceTokenAuthenticationFilter.class, GlobalExceptionHandler.class})
class LoginFaultResponseTest {

    @Autowired MockMvc mvc;
    @MockBean AuthService authService;
    @MockBean SessionService sessionService;
    @MockBean UserMapper userMapper;
    @MockBean OperationLogService operationLogService;
    @MockBean DeviceCredentialService deviceCredentialService;

    private static final String BODY = "{\"username\":\"alice\",\"password\":\"Passw0rd!x\"}";

    @Test
    void authServiceFailureReturnsBusyMessageWithoutSession() throws Exception {
        when(authService.login(any(), anyString())).thenThrow(new IllegalStateException("auth backend down"));

        mvc.perform(post("/api/v1/auth/login").contentType(MediaType.APPLICATION_JSON).content(BODY))
                .andExpect(status().isInternalServerError())
                .andExpect(jsonPath("$.message").value("系统繁忙，请稍后重试"))
                .andExpect(jsonPath("$.data").doesNotExist());
    }

    @Test
    void databaseFailureReturnsBusyMessageWithoutLeakingDetail() throws Exception {
        when(authService.login(any(), anyString()))
                .thenThrow(new DataAccessResourceFailureException("jdbc:postgresql://db-host:5432 refused"));

        mvc.perform(post("/api/v1/auth/login").contentType(MediaType.APPLICATION_JSON).content(BODY))
                .andExpect(status().isInternalServerError())
                .andExpect(jsonPath("$.message").value("系统繁忙，请稍后重试"))
                .andExpect(jsonPath("$.data").doesNotExist());
    }
}
