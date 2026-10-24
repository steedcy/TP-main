package com.airport.ai.task;

import com.airport.ai.auth.CurrentUser;
import com.airport.ai.auth.User;
import com.airport.ai.event.TaskEventService;
import com.airport.ai.task.dto.SubmitTaskRequest;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.config.annotation.method.configuration.EnableMethodSecurity;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.test.context.junit.jupiter.SpringJUnitConfig;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

@SpringJUnitConfig(TaskAuthorizationTest.Config.class)
class TaskAuthorizationTest {
    @org.springframework.beans.factory.annotation.Autowired TaskController controller;
    @org.springframework.beans.factory.annotation.Autowired TaskService tasks;

    @AfterEach void clear() {
        SecurityContextHolder.clearContext();
        reset(tasks);
    }

    @Test void configAdminCannotCreateTaskOrReadTraceEvenThroughDirectControllerInvocation() {
        authenticate("CONFIG_ADMIN");
        assertThrows(AccessDeniedException.class, () -> controller.submit(new SubmitTaskRequest()));
        assertThrows(AccessDeniedException.class, () -> controller.get(7L));
        assertThrows(AccessDeniedException.class, () -> controller.events(7L));
        verifyNoInteractions(tasks);
    }

    @Test void systemAdminCanReadHistoryButCannotCreateTask() {
        authenticate("SYSTEM_ADMIN");
        when(tasks.get(7L)).thenReturn(new Task());
        assertNotNull(controller.get(7L));
        assertThrows(AccessDeniedException.class, () -> controller.submit(new SubmitTaskRequest()));
        verify(tasks).get(7L);
        verify(tasks, never()).submit(any(), any());
    }

    @Test void operatorCanCreateTask() {
        authenticate("OPERATOR");
        when(tasks.submit(any(), any())).thenReturn(new Task());
        assertNotNull(controller.submit(new SubmitTaskRequest()));
        verify(tasks).submit(any(), any());
    }

    private void authenticate(String role) {
        SecurityContextHolder.getContext().setAuthentication(new UsernamePasswordAuthenticationToken(
                "test", "n/a", java.util.List.of(new SimpleGrantedAuthority("ROLE_" + role))));
    }

    @Configuration
    @EnableMethodSecurity
    static class Config {
        @Bean TaskService tasks() { return mock(TaskService.class); }
        @Bean TaskEventService events() { return mock(TaskEventService.class); }
        @Bean CurrentUser user() { return mock(CurrentUser.class); }
        @Bean TaskController controller(TaskService tasks, TaskEventService events, CurrentUser user) {
            return new TaskController(tasks, events, user);
        }
    }
}
