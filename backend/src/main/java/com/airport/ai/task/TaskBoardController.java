package com.airport.ai.task;

import com.airport.ai.auth.CurrentUser;
import com.airport.ai.common.ApiResponse;
import com.airport.ai.common.BusinessException;
import com.airport.ai.common.ErrorCode;
import com.airport.ai.device.DeviceCommandMapper;
import com.airport.ai.device.DeviceCommandRecord;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.math.BigDecimal;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Collaborative task board queries and operator-managed F2 terminal map POIs/regions.
 */
@RestController
@RequestMapping("/api/v1/task-board")
@PreAuthorize("hasAnyRole('OPERATOR', 'SYSTEM_ADMIN')")
public class TaskBoardController {

    private static final ObjectMapper MAPPER = new ObjectMapper();
    private static final Set<String> POI_CATEGORIES = Set.of("GATE", "CHECKIN", "BAGGAGE", "SECURITY", "MEASURE", "SERVICE");
    private static final Set<String> REGION_TYPES = Set.of("ISOLATED_ZONE", "CORRIDOR");

    private final TaskService taskService;
    private final DeviceCommandMapper deviceCommandMapper;
    private final TerminalMapMapper terminalMapMapper;
    private final CurrentUser currentUser;

    public TaskBoardController(TaskService taskService,
                               DeviceCommandMapper deviceCommandMapper,
                               TerminalMapMapper terminalMapMapper,
                               CurrentUser currentUser) {
        this.taskService = taskService;
        this.deviceCommandMapper = deviceCommandMapper;
        this.terminalMapMapper = terminalMapMapper;
        this.currentUser = currentUser;
    }

    @GetMapping("/tasks/{taskId}/commands")
    public ApiResponse<List<Map<String, Object>>> commands(@PathVariable Long taskId) {
        taskService.get(taskId);
        List<DeviceCommandRecord> records = deviceCommandMapper.findByTaskId(taskId);
        return ApiResponse.ok(records.stream().map(this::toSummary).toList());
    }

    @GetMapping("/map-layout")
    public ApiResponse<Map<String, Object>> mapLayout() {
        return ApiResponse.ok(Map.of(
                "pois", terminalMapMapper.findAllPois(),
                "regions", terminalMapMapper.findAllRegions()
        ));
    }

    @PostMapping("/pois")
    @PreAuthorize("hasRole('OPERATOR')")
    public ApiResponse<List<Map<String, Object>>> createPoi(@RequestBody Map<String, Object> body) {
        String code = requireText(body.get("poiCode"), "POI编码不能为空");
        String name = requireText(body.get("poiName"), "POI名称不能为空");
        String category = requireText(body.get("category"), "POI类型不能为空");
        if (!POI_CATEGORIES.contains(category)) {
            throw new BusinessException(ErrorCode.PARAM_FORMAT_ERROR, "不支持的POI类型：" + category);
        }
        BigDecimal x = parseCoord(body.get("x"), "X坐标无效");
        BigDecimal y = parseCoord(body.get("y"), "Y坐标无效");
        String zone = body.get("zone") == null ? null : String.valueOf(body.get("zone")).trim();
        String linkedDevice = body.get("linkedDeviceCode") == null ? null : String.valueOf(body.get("linkedDeviceCode")).trim();
        terminalMapMapper.insertPoi(code, name, category, x, y, zone, linkedDevice, currentUser.get().getUsername());
        return ApiResponse.ok(terminalMapMapper.findAllPois());
    }

    @PutMapping("/pois/{id}")
    @PreAuthorize("hasRole('OPERATOR')")
    public ApiResponse<List<Map<String, Object>>> updatePoi(@PathVariable Long id, @RequestBody Map<String, Object> body) {
        if (terminalMapMapper.findPoiById(id) == null) {
            throw new BusinessException(ErrorCode.RESOURCE_NOT_FOUND, "POI不存在");
        }
        String name = requireText(body.get("poiName"), "POI名称不能为空");
        String category = requireText(body.get("category"), "POI类型不能为空");
        if (!POI_CATEGORIES.contains(category)) {
            throw new BusinessException(ErrorCode.PARAM_FORMAT_ERROR, "不支持的POI类型：" + category);
        }
        BigDecimal x = parseCoord(body.get("x"), "X坐标无效");
        BigDecimal y = parseCoord(body.get("y"), "Y坐标无效");
        String zone = body.get("zone") == null ? null : String.valueOf(body.get("zone")).trim();
        String linkedDevice = body.get("linkedDeviceCode") == null ? null : String.valueOf(body.get("linkedDeviceCode")).trim();
        terminalMapMapper.updatePoi(id, name, category, x, y, zone, linkedDevice);
        return ApiResponse.ok(terminalMapMapper.findAllPois());
    }

    @DeleteMapping("/pois/{id}")
    @PreAuthorize("hasRole('OPERATOR')")
    public ApiResponse<List<Map<String, Object>>> deletePoi(@PathVariable Long id) {
        terminalMapMapper.deletePoi(id);
        return ApiResponse.ok(terminalMapMapper.findAllPois());
    }

    @PostMapping("/pois/sync-scanners")
    @PreAuthorize("hasRole('OPERATOR')")
    public ApiResponse<List<Map<String, Object>>> syncScanners() {
        List<Map<String, Object>> scanners = terminalMapMapper.findBaggageScanners();
        for (Map<String, Object> scanner : scanners) {
            String devCode = String.valueOf(scanner.get("deviceCode"));
            BigDecimal x = new BigDecimal(String.valueOf(scanner.get("x")));
            BigDecimal y = new BigDecimal(String.valueOf(scanner.get("y")));
            int updated = terminalMapMapper.syncPoiByDeviceCode(devCode, x, y);
            if (updated == 0) {
                String devName = String.valueOf(scanner.getOrDefault("deviceName", devCode));
                String zone = scanner.get("zone") == null ? null : String.valueOf(scanner.get("zone"));
                terminalMapMapper.insertPoi("测量点_" + devCode, devName + "测量点", "MEASURE",
                        x, y, zone, devCode, currentUser.get().getUsername());
            }
        }
        return ApiResponse.ok(terminalMapMapper.findAllPois());
    }

    @PostMapping("/regions")
    @PreAuthorize("hasRole('OPERATOR')")
    public ApiResponse<List<Map<String, Object>>> createRegion(@RequestBody Map<String, Object> body) {
        String code = requireText(body.get("regionCode"), "区域编码不能为空");
        String name = requireText(body.get("regionName"), "区域名称不能为空");
        String type = requireText(body.get("regionType"), "区域类型不能为空");
        if (!REGION_TYPES.contains(type)) {
            throw new BusinessException(ErrorCode.PARAM_FORMAT_ERROR, "不支持的区域类型：" + type);
        }
        String geometryJson = requireText(body.get("geometryJson"), "区域几何数据不能为空");
        terminalMapMapper.insertRegion(code, name, type, geometryJson, currentUser.get().getUsername());
        return ApiResponse.ok(terminalMapMapper.findAllRegions());
    }

    @DeleteMapping("/regions/{id}")
    @PreAuthorize("hasRole('OPERATOR')")
    public ApiResponse<List<Map<String, Object>>> deleteRegion(@PathVariable Long id) {
        terminalMapMapper.deleteRegion(id);
        return ApiResponse.ok(terminalMapMapper.findAllRegions());
    }

    private String requireText(Object value, String message) {
        String text = value == null ? "" : String.valueOf(value).trim();
        if (text.isEmpty()) {
            throw new BusinessException(ErrorCode.PARAM_FORMAT_ERROR, message);
        }
        return text;
    }

    private BigDecimal parseCoord(Object value, String message) {
        try {
            return new BigDecimal(String.valueOf(value));
        } catch (Exception ex) {
            throw new BusinessException(ErrorCode.PARAM_FORMAT_ERROR, message);
        }
    }

    private Map<String, Object> toSummary(DeviceCommandRecord record) {
        Map<String, Object> item = new LinkedHashMap<>();
        item.put("id", record.getId());
        item.put("commandId", record.getCommandId());
        item.put("commandType", record.getCommandType());
        item.put("attemptNo", record.getAttemptNo());
        item.put("taskId", record.getTaskId());
        item.put("stepSeq", record.getStepSeq());
        item.put("capabilityType", record.getCapabilityType());
        item.put("agentCode", record.getAgentCode());
        item.put("commandStatus", record.getCommandStatus());
        item.put("inputParams", extractInputParams(record.getCommandPayload()));
        item.put("createdAt", record.getCreatedAt());
        item.put("updatedAt", record.getUpdatedAt());
        return item;
    }

    private Map<String, Object> extractInputParams(String payload) {
        if (payload == null || payload.isBlank()) {
            return Map.of();
        }
        try {
            Map<String, Object> root = MAPPER.readValue(payload, new TypeReference<>() {});
            Object input = root.get("inputParams");
            if (input instanceof Map<?, ?> map) {
                Map<String, Object> result = new LinkedHashMap<>();
                map.forEach((k, v) -> result.put(String.valueOf(k), v));
                return result;
            }
            return Map.of();
        } catch (Exception ignored) {
            return Map.of();
        }
    }
}
