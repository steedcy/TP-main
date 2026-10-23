package com.airport.ai.device;

import com.airport.ai.auth.CurrentUser;
import com.airport.ai.auth.OperationLogService;
import com.airport.ai.common.ApiResponse;
import com.airport.ai.common.BusinessException;
import com.airport.ai.common.ErrorCode;
import com.airport.ai.common.PageResult;
import com.airport.ai.device.dto.DeviceCommandView;
import com.airport.ai.device.dto.SimulatorInstanceView;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;
import java.util.Set;

@RestController
@RequestMapping("/api/v1/simulators")
public class SimulatorManagementController {
    private final DeviceService deviceService;
    private final DeviceAgentMapper agentMapper;
    private final DeviceEventService eventService;
    private final DeviceCommandMapper commandMapper;
    private final DeviceAdapterClient adapterClient;
    private final CurrentUser currentUser;
    private final OperationLogService operationLogService;
    private final ObjectMapper objectMapper;

    public SimulatorManagementController(DeviceService deviceService, DeviceAgentMapper agentMapper,
                                         DeviceEventService eventService, DeviceCommandMapper commandMapper,
                                         DeviceAdapterClient adapterClient, CurrentUser currentUser,
                                         OperationLogService operationLogService, ObjectMapper objectMapper) {
        this.deviceService = deviceService;
        this.agentMapper = agentMapper;
        this.eventService = eventService;
        this.commandMapper = commandMapper;
        this.adapterClient = adapterClient;
        this.currentUser = currentUser;
        this.operationLogService = operationLogService;
        this.objectMapper = objectMapper;
    }

    @GetMapping
    @PreAuthorize("hasAnyRole('CONFIG_ADMIN', 'SYSTEM_ADMIN', 'OPERATOR')")
    public ApiResponse<List<SimulatorInstanceView>> list() {
        PageResult<Device> page = deviceService.list("SIMULATOR", null, null, 1, 100);
        List<SimulatorInstanceView> result = page.getContent().stream()
                .filter(device -> Boolean.TRUE.equals(device.getIsSimulator()))
                .map(device -> {
                    DeviceAgent agent = agentMapper.findByDeviceId(device.getId()).orElse(null);
                    return SimulatorInstanceView.from(device, agent, scenario(agent));
                }).toList();
        return ApiResponse.ok(result);
    }

    @PostMapping("/{deviceCode}/online")
    @PreAuthorize("hasRole('CONFIG_ADMIN')")
    public ApiResponse<Map<String, String>> online(@PathVariable String deviceCode,
                                                    @RequestBody Map<String, String> request) {
        Device device = requireSimulator(deviceCode);
        DeviceAgent agent = requireAgent(device);
        String value = request.get("onlineStatus");
        if (value == null || !Set.of("ONLINE", "OFFLINE").contains(value)) throw new BusinessException(ErrorCode.PARAM_FORMAT_ERROR, "onlineStatus必须为ONLINE/OFFLINE");
        boolean online = "ONLINE".equals(value);
        invoke(device, agent, online ? "SIMULATOR_RESUME" : "SIMULATOR_PAUSE", online ? "ONLINE" : "OFFLINE",
                () -> adapterClient.setSimulatorOnline(device, online));
        return ApiResponse.ok(Map.of("onlineStatus", value));
    }

    @PostMapping("/{deviceCode}/scenario")
    @PreAuthorize("hasRole('CONFIG_ADMIN')")
    public ApiResponse<Map<String, String>> scenario(@PathVariable String deviceCode,
                                                      @RequestBody Map<String, String> request) {
        Device device = requireSimulator(deviceCode);
        DeviceAgent agent = requireAgent(device);
        String value = request.get("scenarioResult");
        Set<String> supported = switch (device.getSimulatedDeviceType()) {
            case "BAGGAGE_SCANNER" -> Set.of("SUCCESS", "FAILED", "TIMEOUT", "NO_OBJECT");
            case "MOBILE_ROBOT" -> Set.of("SUCCESS", "FAILED", "TIMEOUT", "LOST_TARGET");
            default -> Set.of("SUCCESS", "FAILED", "TIMEOUT");
        };
        if (value == null || !supported.contains(value)) throw new BusinessException(ErrorCode.PARAM_FORMAT_ERROR, "当前仿真类型不支持该场景结果");
        invoke(device, agent, "SIMULATOR_SCENARIO_CHANGED", value, () -> adapterClient.setSimulatorScenario(device, value));
        return ApiResponse.ok(Map.of("scenarioResult", value));
    }

    @GetMapping("/{deviceCode}/events")
    @PreAuthorize("hasAnyRole('CONFIG_ADMIN', 'SYSTEM_ADMIN', 'OPERATOR')")
    public ApiResponse<List<DeviceEvent>> events(@PathVariable String deviceCode) {
        DeviceAgent agent = requireAgent(requireSimulator(deviceCode));
        List<DeviceEvent> all = eventService.listByAgent(agent.getId());
        return ApiResponse.ok(all.stream().skip(Math.max(0, all.size() - 100L)).toList());
    }

    @GetMapping("/{deviceCode}/commands")
    @PreAuthorize("hasAnyRole('CONFIG_ADMIN', 'SYSTEM_ADMIN', 'OPERATOR')")
    public ApiResponse<List<DeviceCommandView>> commands(@PathVariable String deviceCode) {
        DeviceAgent agent = requireAgent(requireSimulator(deviceCode));
        return ApiResponse.ok(commandMapper.findRecentByAgentCode(agent.getAgentCode(), 100).stream()
                .map(DeviceCommandView::from).toList());
    }

    private Device requireSimulator(String deviceCode) {
        Device device = deviceService.getByCode(deviceCode);
        if (!Boolean.TRUE.equals(device.getIsSimulator()) || !"SIMULATOR".equals(device.getDeviceTypeCode())) {
            throw new BusinessException(ErrorCode.PARAM_FORMAT_ERROR, "目标设备不是仿真体");
        }
        return device;
    }

    private DeviceAgent requireAgent(Device device) {
        return agentMapper.findByDeviceId(device.getId())
                .orElseThrow(() -> new BusinessException(ErrorCode.DEVICE_AGENT_NOT_FOUND, "仿真体尚未绑定设备代理"));
    }

    private void invoke(Device device, DeviceAgent agent, String eventType, String value, Runnable action) {
        var operator = currentUser.get();
        try {
            action.run();
            eventService.append(agent.getId(), eventType, "OPERATOR", null,
                    "配置管理员" + operator.getUsername() + "设置" + device.getDeviceCode() + "=" + value);
            operationLogService.record(operator.getId(), operator.getUsername(), operator.getRole(), eventType,
                    device.getDeviceCode(), "SUCCESS", null, Map.of("value", value));
        } catch (RuntimeException ex) {
            operationLogService.record(operator.getId(), operator.getUsername(), operator.getRole(), eventType,
                    device.getDeviceCode(), "FAILED", null, Map.of("value", value, "reason", safeMessage(ex)));
            throw ex;
        }
    }

    private String scenario(DeviceAgent agent) {
        if (agent == null || agent.getBusinessStatus() == null || agent.getBusinessStatus().isBlank()) return "UNKNOWN";
        try {
            return objectMapper.readValue(agent.getBusinessStatus(), new TypeReference<Map<String, String>>() {})
                    .getOrDefault("scenarioResult", "UNKNOWN");
        } catch (Exception ignored) { return "UNKNOWN"; }
    }

    private String safeMessage(RuntimeException exception) {
        String message = exception.getMessage();
        return message == null ? exception.getClass().getSimpleName() : message.substring(0, Math.min(message.length(), 160));
    }
}
