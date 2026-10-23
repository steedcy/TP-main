package com.airport.ai.device;

import com.airport.ai.common.ApiResponse;
import com.airport.ai.device.dto.DeviceAgentMessageRequest;
import jakarta.validation.Valid;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

/** Appendix B internal device-agent message endpoint. */
@RestController
@RequestMapping("/internal/v1/device-agent/messages")
public class DeviceAgentInternalMessageController {
    private final DeviceAgentInternalMessageService messageService;

    public DeviceAgentInternalMessageController(DeviceAgentInternalMessageService messageService) {
        this.messageService = messageService;
    }

    @PostMapping
    @PreAuthorize("hasRole('SYSTEM_ADMIN')")
    public ApiResponse<Map<String, Object>> dispatch(@Valid @RequestBody DeviceAgentMessageRequest request) {
        return ApiResponse.ok(messageService.dispatch(request));
    }
}
