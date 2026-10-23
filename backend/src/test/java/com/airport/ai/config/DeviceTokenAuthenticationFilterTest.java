package com.airport.ai.config;

import com.airport.ai.device.DeviceCredentialService;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;
import org.springframework.mock.web.MockFilterChain;
import org.springframework.security.core.context.SecurityContextHolder;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class DeviceTokenAuthenticationFilterTest {

    @AfterEach
    void clearSecurityContext() {
        SecurityContextHolder.clearContext();
    }

    @Test
    void authenticatesCanonicalReportWithTokenBoundToAgentCode() throws Exception {
        DeviceCredentialService credentials = mock(DeviceCredentialService.class);
        when(credentials.matchesAgentCode("AGT-41", "runtime-token")).thenReturn(true);
        DeviceTokenAuthenticationFilter filter = new DeviceTokenAuthenticationFilter(credentials);
        MockHttpServletRequest request = new MockHttpServletRequest("POST",
                "/device-api/v1/agents/AGT-41/report");
        request.setServletPath("/device-api/v1/agents/AGT-41/report");
        request.addHeader("Authorization", "Bearer runtime-token");

        filter.doFilter(request, new MockHttpServletResponse(), new MockFilterChain());

        var authentication = SecurityContextHolder.getContext().getAuthentication();
        assertNotNull(authentication);
        assertTrue(authentication.getAuthorities().stream().anyMatch(authority ->
                "ROLE_DEVICE_AGENT".equals(authority.getAuthority())));
        verify(credentials).matchesAgentCode("AGT-41", "runtime-token");
    }

    @Test
    void doesNotAcceptAUserSessionOrAnInvalidDeviceToken() throws Exception {
        DeviceCredentialService credentials = mock(DeviceCredentialService.class);
        when(credentials.matchesAgentCode("AGT-41", "user-session")).thenReturn(false);
        DeviceTokenAuthenticationFilter filter = new DeviceTokenAuthenticationFilter(credentials);
        MockHttpServletRequest request = new MockHttpServletRequest("POST",
                "/device-api/v1/agents/AGT-41/report");
        request.setServletPath("/device-api/v1/agents/AGT-41/report");
        request.addHeader("Authorization", "Bearer user-session");

        filter.doFilter(request, new MockHttpServletResponse(), new MockFilterChain());

        assertNull(SecurityContextHolder.getContext().getAuthentication());
        verify(credentials).matchesAgentCode("AGT-41", "user-session");
    }
}
