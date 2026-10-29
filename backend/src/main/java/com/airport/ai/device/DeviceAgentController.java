package com.airport.ai.device;

import com.airport.ai.auth.CurrentUser;
import com.airport.ai.common.ApiResponse;
import com.airport.ai.common.PageResult;
import com.airport.ai.device.dto.DeviceAgentReportRequest;
import com.airport.ai.device.dto.DeviceAgentView;
import com.airport.ai.device.dto.StatusReportRequest;
import com.airport.ai.task.dto.ExecutionFeedbackRequest;
import com.airport.ai.task.dto.TaskResponseRequest;
import jakarta.validation.Valid;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

import java.time.OffsetDateTime;
import java.util.Map;

/** Device-agent lifecycle endpoints and compatibility adapters for older device callbacks. */
@RestController
@RequestMapping("/api/v1/device-agents")
public class DeviceAgentController {

    private final DeviceAgentService deviceAgentService;
    private final DeviceService deviceService;
    private final DeviceAgentReportService reportService;
    private final CurrentUser currentUser;

    public DeviceAgentController(DeviceAgentService deviceAgentService, DeviceService deviceService,
                                 DeviceAgentReportService reportService, CurrentUser currentUser) {
        this.deviceAgentService = deviceAgentService;
        this.deviceService = deviceService;
        this.reportService = reportService;
        this.currentUser = currentUser;
    }

    @PostMapping
    @PreAuthorize("hasRole('CONFIG_ADMIN')")
    public ApiResponse<DeviceAgentView> create(@RequestBody Map<String, String> body) {
        DeviceAgent agent = deviceService.createAgentByCode(body.get("deviceCode"), currentUser.get());
        return ApiResponse.ok(DeviceAgentView.from(agent, deviceAgentService.getDeviceOf(agent)));
    }

    @GetMapping
    @PreAuthorize("hasAnyRole('CONFIG_ADMIN', 'SYSTEM_ADMIN', 'OPERATOR')")
    public ApiResponse<PageResult<DeviceAgentView>> list(@RequestParam(required = false) String agentStatus,
                                                          @RequestParam(required = false) String onlineStatus,
                                                          @RequestParam(defaultValue = "1") int page,
                                                          @RequestParam(defaultValue = "20") int size) {
        PageResult<DeviceAgent> result = deviceAgentService.list(agentStatus, onlineStatus, page, size);
        return ApiResponse.ok(result.map(agent -> DeviceAgentView.from(agent, deviceAgentService.getDeviceOf(agent))
                .withEnabledCapabilities(deviceAgentService.enabledCapabilitySummary(agent))));
    }

    @GetMapping("/{agentId}")
    @PreAuthorize("hasAnyRole('CONFIG_ADMIN', 'SYSTEM_ADMIN', 'OPERATOR')")
    public ApiResponse<DeviceAgentView> get(@PathVariable String agentId) {
        DeviceAgent agent = deviceAgentService.getByCode(agentId);
        return ApiResponse.ok(DeviceAgentView.from(agent, deviceAgentService.getDeviceOf(agent))
                .withEnabledCapabilities(deviceAgentService.enabledCapabilitySummary(agent)));
    }

    @PostMapping("/{agentId}/disable")
    @PreAuthorize("hasRole('CONFIG_ADMIN')")
    public ApiResponse<Void> disable(@PathVariable String agentId, @RequestBody Map<String, Boolean> body) {
        boolean confirmed = Boolean.TRUE.equals(body.get("confirmed"));
        deviceAgentService.disableByCode(agentId, confirmed, currentUser.get());
        return ApiResponse.ok(null);
    }

    /** Compatibility route: new clients should use /device-api/v1/agents/{agentCode}/report. */
    @PostMapping("/report/{deviceCode}")
    public ApiResponse<Void> report(@PathVariable String deviceCode, @Valid @RequestBody StatusReportRequest request) {
        deviceAgentService.reportStatus(deviceCode, request);
        return ApiResponse.ok(null);
    }

    /** Compatibility adapter; all reports use the same validation, dedupe and state-transition service. */
    @PostMapping("/{agentCode}/task-response")
    public ApiResponse<Void> taskResponse(@PathVariable String agentCode, @Valid @RequestBody TaskResponseRequest request) {
        DeviceAgentReportRequest report = new DeviceAgentReportRequest();
        report.setReportType("TASK_RESPONSE");
        report.setReportedAt(OffsetDateTime.now().toString());
        report.setResponse(request);
        reportService.accept(agentCode, report);
        return ApiResponse.ok(null);
    }

    /** Compatibility adapter; all reports use the same validation, dedupe and state-transition service. */
    @PostMapping("/{agentCode}/execution-feedback")
    public ApiResponse<Void> executionFeedback(@PathVariable String agentCode,
                                                @Valid @RequestBody ExecutionFeedbackRequest request) {
        DeviceAgentReportRequest report = new DeviceAgentReportRequest();
        report.setReportType("EXECUTION_FEEDBACK");
        report.setReportedAt(OffsetDateTime.now().toString());
        report.setFeedback(request);
        reportService.accept(agentCode, report);
        return ApiResponse.ok(null);
    }
}
