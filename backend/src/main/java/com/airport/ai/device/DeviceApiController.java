package com.airport.ai.device;

import com.airport.ai.common.ApiResponse;
import com.airport.ai.device.dto.DeviceAgentReportRequest;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/** Canonical device-facing report ingress defined by the P0 communication contract. */
@RestController
@RequestMapping("/device-api/v1/agents")
public class DeviceApiController {
    private final DeviceAgentReportService reportService;

    public DeviceApiController(DeviceAgentReportService reportService) {
        this.reportService = reportService;
    }

    @PostMapping("/{agentCode}/report")
    public ApiResponse<Void> report(@PathVariable String agentCode,
                                    @Valid @RequestBody DeviceAgentReportRequest request) {
        reportService.accept(agentCode, request);
        return ApiResponse.ok(null);
    }
}
