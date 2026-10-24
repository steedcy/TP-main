package com.airport.ai.situation;

import com.airport.ai.common.ApiResponse;
import com.airport.ai.common.PageResult;
import com.airport.ai.device.Device;
import com.airport.ai.device.DeviceAgent;
import com.airport.ai.device.DeviceAgentService;
import com.airport.ai.device.DeviceCapabilityMapper;
import com.airport.ai.device.dto.DeviceAgentView;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.time.OffsetDateTime;
import java.util.List;

@RestController
@RequestMapping("/api/v1/situation")
@PreAuthorize("hasAnyRole('CONFIG_ADMIN', 'SYSTEM_ADMIN', 'OPERATOR')")
public class SituationController {
    private final DeviceAgentService agentService;
    private final DeviceCapabilityMapper capabilityMapper;
    public SituationController(DeviceAgentService agentService, DeviceCapabilityMapper capabilityMapper) {
        this.agentService = agentService;
        this.capabilityMapper = capabilityMapper;
    }

    @GetMapping("/snapshot")
    public ApiResponse<Snapshot> snapshot() {
        // SRS 5.6.2 displays enabled agents only; archived test agents must not
        // inflate the live situation snapshot even when their history is retained.
        PageResult<DeviceAgent> agents = agentService.list("ENABLED", null, 1, 100);
        List<Marker> devices = agents.getContent().stream().map(agent -> {
            Device device = agentService.getDeviceOf(agent);
            return new Marker(agent.getAgentCode(), device.getDeviceCode(), device.getDeviceName(),
                    device.getDeviceTypeCode(), Boolean.TRUE.equals(device.getIsSimulator()) ? device.getSimulatedDeviceType() : null,
                    agent.getAgentStatus(), new Location(device.getPositionX(), device.getPositionY(), device.getAreaCode()),
                    agent.getOnlineStatus(), agent.getWorkStatus(), agent.getCurrentTaskId(), agent.getCurrentStepSeq(), agent.getLastReportedAt(),
                    capabilityMapper.findByDeviceIdAndCapabilityStatus(device.getId(), "ENABLED").stream()
                            .map(com.airport.ai.device.DeviceCapability::getCapabilityType).distinct().toList());
        }).toList();
        return ApiResponse.ok(new Snapshot(devices, OffsetDateTime.now().toString(), 5));
    }

    public record Snapshot(List<Marker> agents, String generatedAt, int refreshIntervalSeconds) {}
    public record Location(java.math.BigDecimal x, java.math.BigDecimal y, String zone) {}
    public record Marker(String agentId, String deviceCode, String deviceName, String deviceTypeCode,
                         String simulatedDeviceType, String agentStatus, Location location,
                         String onlineStatus, String workStatus, Long currentTaskId, Integer currentStepSeq,
                         java.time.LocalDateTime lastReportedAt, List<String> capabilityTypes) {}
}
