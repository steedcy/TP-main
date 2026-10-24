package com.airport.ai.demo;

import com.airport.ai.auth.CurrentUser;
import com.airport.ai.common.ApiResponse;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
@RequestMapping("/api/v1/demo-data")
@PreAuthorize("hasRole('SYSTEM_ADMIN')")
public class DemoResetController {
    private final DemoResetService service;
    private final CurrentUser currentUser;

    public DemoResetController(DemoResetService service, CurrentUser currentUser) {
        this.service = service;
        this.currentUser = currentUser;
    }

    @GetMapping("/reset-preview")
    public ApiResponse<Map<String, Object>> preview() { return ApiResponse.ok(service.preview()); }

    @PostMapping("/reset")
    public ApiResponse<Map<String, Object>> reset(@RequestBody ResetRequest request) {
        return ApiResponse.ok(service.restore(request.confirmationPhrase(), request.confirmed(), currentUser.get()));
    }

    public record ResetRequest(String confirmationPhrase, boolean confirmed) {}
}
