package com.airport.ai.planning;

import com.airport.ai.auth.CurrentUser;
import com.airport.ai.common.ApiResponse;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

/**
 * System-admin endpoint for configuring the primary (Kimi) and secondary (Anthropic Claude)
 * planning model API keys and automatic failover.
 */
@RestController
@RequestMapping("/api/v1/system-settings/planning-models")
@PreAuthorize("hasRole('SYSTEM_ADMIN')")
public class PlanningModelConfigController {
    private final PlanningModelConfigService service;
    private final CurrentUser currentUser;

    public PlanningModelConfigController(PlanningModelConfigService service, CurrentUser currentUser) {
        this.service = service;
        this.currentUser = currentUser;
    }

    @GetMapping
    public ApiResponse<Map<String, Object>> get() {
        return ApiResponse.ok(service.currentView());
    }

    @PutMapping
    public ApiResponse<Map<String, Object>> update(@RequestBody PlanningModelConfigService.UpdateRequest request) {
        return ApiResponse.ok(service.update(request, currentUser.get()));
    }
}
