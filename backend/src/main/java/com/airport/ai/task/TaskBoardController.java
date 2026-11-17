package com.airport.ai.task;

import com.airport.ai.common.ApiResponse;
import com.airport.ai.device.DeviceCommandMapper;
import com.airport.ai.device.DeviceCommandRecord;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Read-only query endpoint for the collaborative task board to display
 * sanitized per-device command inputs alongside execution feedback.
 */
@RestController
@RequestMapping("/api/v1/task-board")
@PreAuthorize("hasAnyRole('OPERATOR', 'SYSTEM_ADMIN')")
public class TaskBoardController {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private final TaskService taskService;
    private final DeviceCommandMapper deviceCommandMapper;

    public TaskBoardController(TaskService taskService, DeviceCommandMapper deviceCommandMapper) {
        this.taskService = taskService;
        this.deviceCommandMapper = deviceCommandMapper;
    }

    @GetMapping("/tasks/{taskId}/commands")
    public ApiResponse<List<Map<String, Object>>> commands(@PathVariable Long taskId) {
        taskService.get(taskId);
        List<DeviceCommandRecord> records = deviceCommandMapper.findByTaskId(taskId);
        return ApiResponse.ok(records.stream().map(this::toSummary).toList());
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
