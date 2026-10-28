package com.airport.ai.auth;

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
import com.airport.ai.task.TaskController;
import com.airport.ai.event.TaskEventService;
import com.airport.ai.task.TaskService;
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

/** DEF-S3-072：无权角色对其他写接口的缺字段请求也先得403并留痕；有权角色仍做参数校验。 */
@WebMvcTest({DeviceController.class, TaskController.class})
@Import({SecurityConfig.class, AccessDeniedHandlerImpl.class, AuthEntryPoint.class,
        TokenAuthenticationFilter.class, DeviceTokenAuthenticationFilter.class, GlobalExceptionHandler.class,
        PreAuthorizeInterceptor.class, WebMvcAuthorizationConfig.class})
class WriteEndpointAuthorizationOrderTest {

    @Autowired MockMvc mvc;
    @MockBean DeviceService deviceService;
    @MockBean DeviceCredentialService deviceCredentialService;
    @MockBean TaskService taskService;
    @MockBean TaskEventService taskEventService;
    @MockBean CurrentUser currentUser;
    @MockBean SessionService sessionService;
    @MockBean UserMapper userMapper;
    @MockBean OperationLogService operationLogService;

    private void login(String token, long id, String role) {
        User u = new User();
        u.setId(id);
        u.setUsername(role.toLowerCase() + "-" + id);
        u.setRole(role);
        when(sessionService.touchAndGetUserId(token)).thenReturn(id);
        when(userMapper.findById(id)).thenReturn(Optional.of(u));
    }

    private void denied(String token, String path, long id, String user, String role) throws Exception {
        mvc.perform(post(path).header("Authorization", "Bearer " + token)
                        .contentType(MediaType.APPLICATION_JSON).content("{}"))
                .andExpect(status().isForbidden())
                .andExpect(jsonPath("$.code").value(2003));
        verify(operationLogService).record(eq(id), eq(user), eq(role), eq("ACCESS_DENIED"),
                eq(path), eq("FAILED"), any());
    }

    @Test
    void operatorInvalidDeviceCreateIs403Audited() throws Exception {
        login("op", 7L, "OPERATOR");
        denied("op", "/api/v1/devices", 7L, "operator-7", "OPERATOR");
        verifyNoInteractions(deviceService);
    }

    @Test
    void systemAdminInvalidDeviceCreateIs403Audited() throws Exception {
        login("sa", 1L, "SYSTEM_ADMIN");
        denied("sa", "/api/v1/devices", 1L, "system_admin-1", "SYSTEM_ADMIN");
    }

    @Test
    void configAdminInvalidTaskSubmitIs403Audited() throws Exception {
        login("ca", 5L, "CONFIG_ADMIN");
        denied("ca", "/api/v1/tasks", 5L, "config_admin-5", "CONFIG_ADMIN");
        verifyNoInteractions(taskService);
    }

    @Test
    void systemAdminInvalidTaskSubmitIs403Audited() throws Exception {
        login("sa", 1L, "SYSTEM_ADMIN");
        denied("sa", "/api/v1/tasks", 1L, "system_admin-1", "SYSTEM_ADMIN");
    }

    @Test
    void configAdminInvalidTerminateIs403Audited() throws Exception {
        login("ca", 5L, "CONFIG_ADMIN");
        denied("ca", "/api/v1/tasks/999999/terminate", 5L, "config_admin-5", "CONFIG_ADMIN");
        verifyNoInteractions(taskService);
    }

    @Test
    void authorizedRolesStillGetBodyValidation400() throws Exception {
        login("ca", 5L, "CONFIG_ADMIN");
        login("op", 7L, "OPERATOR");
        mvc.perform(post("/api/v1/devices").header("Authorization", "Bearer ca")
                        .contentType(MediaType.APPLICATION_JSON).content("{}"))
                .andExpect(status().isBadRequest());
        mvc.perform(post("/api/v1/tasks").header("Authorization", "Bearer op")
                        .contentType(MediaType.APPLICATION_JSON).content("{}"))
                .andExpect(status().isBadRequest());
        mvc.perform(post("/api/v1/tasks/1/terminate").header("Authorization", "Bearer op")
                        .contentType(MediaType.APPLICATION_JSON).content("{}"))
                .andExpect(status().isBadRequest());
    }
}
