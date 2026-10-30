package com.airport.ai.device;

import com.airport.ai.auth.CurrentUser;
import com.airport.ai.common.ApiResponse;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

/** 心跳超时阈值配置（SRS_F005，TC-014.S3）：配置管理员可改，三类角色可读。 */
@RestController
@RequestMapping("/api/v1/settings/heartbeat-timeout")
public class HeartbeatSettingController {
    private final HeartbeatSettingService service;
    private final CurrentUser currentUser;

    public HeartbeatSettingController(HeartbeatSettingService service, CurrentUser currentUser) {
        this.service = service;
        this.currentUser = currentUser;
    }

    @GetMapping
    @PreAuthorize("hasAnyRole('CONFIG_ADMIN', 'SYSTEM_ADMIN', 'OPERATOR')")
    public ApiResponse<Map<String, Integer>> get() {
        return ApiResponse.ok(Map.of("seconds", service.timeoutSeconds(),
                "min", HeartbeatSettingService.MIN_SECONDS, "max", HeartbeatSettingService.MAX_SECONDS));
    }

    @PutMapping
    @PreAuthorize("hasRole('CONFIG_ADMIN')")
    public ApiResponse<Map<String, Integer>> update(@RequestBody Map<String, Integer> body) {
        int seconds = service.update(body.get("seconds"), currentUser.get());
        return ApiResponse.ok(Map.of("seconds", seconds));
    }
}
