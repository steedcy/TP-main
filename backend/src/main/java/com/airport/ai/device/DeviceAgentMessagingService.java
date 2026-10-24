package com.airport.ai.device;

import com.airport.ai.common.BusinessException;
import com.airport.ai.common.ErrorCode;
import com.airport.ai.device.dto.DeviceCommandRequest;
import com.airport.ai.task.Task;
import com.airport.ai.task.TaskMapper;
import com.airport.ai.task.MotionSafetyGuard;
import com.airport.ai.devicetype.DeviceTypeCapabilityService;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.time.OffsetDateTime;
import java.util.Map;

/** Sole platform-side gateway for agent messages and device command transport. */
@Service
public class DeviceAgentMessagingService {
    @org.springframework.beans.factory.annotation.Autowired
    private org.springframework.context.ApplicationEventPublisher events;
    public record DeliveryFailure(String agentCode, String commandId, String commandType, int attemptNo) {}
    private final DeviceAgentMapper agentMapper;
    private final DeviceMapper deviceMapper;
    private final DeviceCommandMapper commandMapper;
    private final DeviceCapabilityMapper capabilityMapper;
    private final TaskMapper taskMapper;
    private final DeviceAdapterClient adapterClient;
    private final int commandTimeoutSeconds;
    private final ObjectMapper objectMapper;
    private final DeviceTypeCapabilityService deviceTypeCapabilityService;

    public DeviceAgentMessagingService(DeviceAgentMapper agentMapper,
                                       DeviceMapper deviceMapper,
                                       DeviceCommandMapper commandMapper,
                                       DeviceCapabilityMapper capabilityMapper,
                                       TaskMapper taskMapper,
                                       DeviceAdapterClient adapterClient,
                                       @Value("${app.device.command-timeout-seconds:60}") int commandTimeoutSeconds,
                                       ObjectMapper objectMapper,
                                       DeviceTypeCapabilityService deviceTypeCapabilityService) {
        this.agentMapper = agentMapper;
        this.deviceMapper = deviceMapper;
        this.commandMapper = commandMapper;
        this.capabilityMapper = capabilityMapper;
        this.taskMapper = taskMapper;
        this.adapterClient = adapterClient;
        this.commandTimeoutSeconds = commandTimeoutSeconds;
        this.objectMapper = objectMapper;
        this.deviceTypeCapabilityService = deviceTypeCapabilityService;
    }

    public void requestTaskAcceptance(String agentCode, String commandId, Long taskId, Integer stepSeq,
                                      String capabilityType, Map<String, Object> inputParams) {
        send(agentCode, taskId, stepSeq, capabilityType, commandId, "TASK_ACCEPT", 0, inputParams);
    }

    public void executeCapability(String agentCode, String commandId, Long taskId, Integer stepSeq,
                                  String capabilityType, Integer attemptNo, Map<String, Object> inputParams) {
        send(agentCode, taskId, stepSeq, capabilityType, commandId, "EXECUTE_CAPABILITY", attemptNo, inputParams);
    }

    public void cancelTask(String agentCode, String commandId, Long taskId, Integer stepSeq) {
        send(agentCode, taskId, stepSeq, null, commandId, "TASK_CANCEL", 0, Map.of());
    }

    public java.util.Map<String, Object> testCapability(Device device, DeviceAgent agent, DeviceCapability capability,
                                                       java.util.Map<String, Object> params) {
        if (!"ENABLED".equals(agent.getAgentStatus()) || !"ONLINE".equals(agent.getOnlineStatus())
                || !"IDLE".equals(agent.getWorkStatus()) || !"ACTIVE".equals(device.getDeviceStatus()))
            throw new BusinessException(ErrorCode.DEVICE_OFFLINE);
        if (!deviceTypeCapabilityService.isCapabilityTypeSupported(device.getDeviceTypeCode(),
                device.getSimulatedDeviceType(), capability.getCapabilityType()))
            throw new BusinessException(ErrorCode.CAPABILITY_OUT_OF_BOUNDARY);
        if (!MotionSafetyGuard.detect(java.util.Map.of("inputParams", params)).isEmpty())
            throw new BusinessException(ErrorCode.MOTION_SAFETY_FIELD_DETECTED);
        String commandId = "TEST-" + java.util.UUID.randomUUID().toString().replace("-", "").substring(0, 26);
        DeviceCommandRecord record = new DeviceCommandRecord();
        record.setCommandId(commandId); record.setAgentCode(agent.getAgentCode());
        record.setCommandType("CAPABILITY_TEST"); record.setAttemptNo(0);
        record.setCapabilityType(capability.getCapabilityType());
        record.setCommandPayload(toJson(java.util.Map.of("capabilityType", capability.getCapabilityType(), "inputParams", params)));
        record.setCommandStatus("PENDING");
        record.setCreatedAt(java.time.LocalDateTime.now()); record.setUpdatedAt(record.getCreatedAt());
        commandMapper.insertIfAbsent(record);
        try {
            java.util.Map<String, Object> response = adapterClient.testCapability(device, agent.getAgentCode(), commandId,
                    capability.getCapabilityType(), params);
            boolean passed = response != null && commandId.equals(response.get("commandId")) && "SUCCESS".equals(response.get("result"));
            commandMapper.updateStatus(agent.getAgentCode(), commandId, "CAPABILITY_TEST", 0,
                    passed ? "SUCCEEDED" : "FAILED", toJson(response));
            if (!passed) throw new BusinessException(ErrorCode.PARAM_FORMAT_ERROR, "设备能力测试未通过");
            return response;
        } catch (RuntimeException ex) {
            commandMapper.updateStatus(agent.getAgentCode(), commandId, "CAPABILITY_TEST", 0, "FAILED", null);
            throw ex;
        }
    }

    private void send(String agentCode, Long taskId, Integer stepSeq, String capabilityType,
                      String commandId, String commandType, Integer attemptNo,
                      Map<String, Object> inputParams) {
        DeviceAgent agent = agentMapper.findByAgentCode(agentCode)
                .orElseThrow(() -> new BusinessException(ErrorCode.DEVICE_AGENT_NOT_FOUND));
        if (!"ENABLED".equals(agent.getAgentStatus()) || !"ONLINE".equals(agent.getOnlineStatus())) {
            throw new BusinessException(ErrorCode.DEVICE_OFFLINE);
        }
        Device device = deviceMapper.findById(agent.getDeviceId())
                .orElseThrow(() -> new BusinessException(ErrorCode.DEVICE_NOT_FOUND));
        if (!"ACTIVE".equals(device.getDeviceStatus())) throw new BusinessException(ErrorCode.DEVICE_OFFLINE);
        Task task = taskId == null ? null : taskMapper.findById(taskId)
                .orElseThrow(() -> new BusinessException(ErrorCode.TASK_NOT_FOUND));
        inputParams = inputParams == null ? Map.of() : inputParams;
        if (!MotionSafetyGuard.detect(Map.of("inputParams", inputParams)).isEmpty())
            throw new BusinessException(ErrorCode.MOTION_SAFETY_FIELD_DETECTED);
        if (("TASK_ACCEPT".equals(commandType) || "EXECUTE_CAPABILITY".equals(commandType))) {
            if (capabilityType == null || capabilityType.isBlank()) {
                throw new BusinessException(ErrorCode.PARAM_MISSING, "capabilityType不可为空");
            }
            if (!capabilityMapper.existsByDeviceIdAndCapabilityTypeAndCapabilityStatus(
                    device.getId(), capabilityType, "ENABLED")) {
                throw new BusinessException(ErrorCode.CAPABILITY_DISABLED, "设备未启用此能力");
            }
            if (!deviceTypeCapabilityService.isCapabilityTypeSupported(device.getDeviceTypeCode(),
                    device.getSimulatedDeviceType(), capabilityType)) {
                throw new BusinessException(ErrorCode.CAPABILITY_OUT_OF_BOUNDARY);
            }
            DeviceCapability configured = capabilityMapper.findByDeviceIdAndCapabilityStatus(device.getId(), "ENABLED")
                    .stream().filter(capability -> capabilityType.equals(capability.getCapabilityType())).findFirst().orElseThrow();
            try { inputParams = ParameterValues.materialize(configured.getInputParams(), inputParams); }
            catch (IllegalArgumentException ex) { throw new BusinessException(ErrorCode.PARAM_FORMAT_ERROR, ex.getMessage()); }
        }
        if (!MotionSafetyGuard.detect(Map.of("inputParams", inputParams == null ? Map.of() : inputParams)).isEmpty()) {
            throw new BusinessException(ErrorCode.MOTION_SAFETY_FIELD_DETECTED,
                    "设备业务消息包含运动安全控制字段");
        }

        DeviceCommandRequest request = new DeviceCommandRequest();
        request.setCommandId(commandId);
        request.setCommandType(commandType);
        request.setAttemptNo(attemptNo);
        request.setTaskId(task == null ? null : task.getTaskCode());
        request.setStepSeq(stepSeq);
        request.setCapabilityType(capabilityType);
        request.setInputParams(inputParams);
        request.setIssuedAt(OffsetDateTime.now());
        request.setDeadline(request.getIssuedAt().plusSeconds(commandTimeoutSeconds));
        String serialized = toJson(request);

        DeviceCommandRecord record = new DeviceCommandRecord();
        record.setCommandId(commandId);
        record.setAgentCode(agentCode);
        record.setCommandType(commandType);
        record.setAttemptNo(attemptNo);
        record.setTaskId(taskId);
        record.setStepSeq(stepSeq);
        record.setCapabilityType(capabilityType);
        record.setCommandPayload(serialized);
        record.setCommandStatus("PENDING");
        record.setCreatedAt(java.time.LocalDateTime.now());
        record.setUpdatedAt(record.getCreatedAt());
        int inserted = commandMapper.insertIfAbsent(record);
        DeviceCommandRecord existing = commandMapper.findByKey(agentCode, commandId, commandType, attemptNo)
                .orElseThrow(() -> new IllegalStateException("command record insert/read failed"));
        DeviceCommandRequest effectiveRequest;
        try {
            effectiveRequest = inserted == 1 ? request
                    : objectMapper.readValue(existing.getCommandPayload(), DeviceCommandRequest.class);
        } catch (Exception ex) {
            throw new IllegalStateException("已存储设备命令无法解析", ex);
        }
        if (!sameBusinessCommand(request, effectiveRequest)) {
            throw new BusinessException(ErrorCode.PARAM_FORMAT_ERROR,
                    "同一commandId/commandType/attemptNo对应了不同的命令内容");
        }
        if (inserted == 0 && !("PENDING".equals(existing.getCommandStatus())
                || "DELIVERY_FAILED".equals(existing.getCommandStatus()))) return;

        if ("TASK_ACCEPT".equals(commandType) && (!"IDLE".equals(agent.getWorkStatus())
                || agent.getCurrentTaskId() != null)) {
            throw new BusinessException(ErrorCode.STEP_STATUS_NOT_ALLOWED, "设备代理已有占用，不能接受新任务");
        }
        if ("EXECUTE_CAPABILITY".equals(commandType) && (taskId == null
                || !"BUSY".equals(agent.getWorkStatus())
                || !taskId.equals(agent.getCurrentTaskId()))) {
            throw new BusinessException(ErrorCode.STEP_STATUS_NOT_ALLOWED, "执行命令与代理当前占用任务不匹配");
        }

        Runnable delivery = () -> {
            try {
                adapterClient.sendCommand(device, agentCode, effectiveRequest);
                commandMapper.updateStatus(agentCode, commandId, commandType, attemptNo, "SENT", null);
            } catch (RuntimeException ex) {
                commandMapper.updateStatus(agentCode, commandId, commandType, attemptNo, "DELIVERY_FAILED", null);
                if (events != null) events.publishEvent(new DeliveryFailure(agentCode, commandId, commandType, attemptNo));
                else throw ex;
            }
        };
        // Device callbacks must see the committed assignment and command rows.
        if (org.springframework.transaction.support.TransactionSynchronizationManager.isActualTransactionActive()) {
            org.springframework.transaction.support.TransactionSynchronizationManager.registerSynchronization(
                new org.springframework.transaction.support.TransactionSynchronization() {
                    @Override public void afterCommit() { java.util.concurrent.CompletableFuture.runAsync(delivery); }
                });
        } else delivery.run();
    }

    private boolean sameBusinessCommand(DeviceCommandRequest first, DeviceCommandRequest second) {
        return java.util.Objects.equals(first.getCommandId(), second.getCommandId())
                && java.util.Objects.equals(first.getCommandType(), second.getCommandType())
                && java.util.Objects.equals(first.getAttemptNo(), second.getAttemptNo())
                && java.util.Objects.equals(first.getTaskId(), second.getTaskId())
                && java.util.Objects.equals(first.getStepSeq(), second.getStepSeq())
                && java.util.Objects.equals(first.getCapabilityType(), second.getCapabilityType())
                && java.util.Objects.equals(first.getInputParams(), second.getInputParams());
    }

    public void updateCommandStatus(String agentCode, String commandId, String commandType,
                                    Integer attemptNo, String status, Object response) {
        commandMapper.updateStatus(agentCode, commandId, commandType, attemptNo, status,
                response == null ? null : toJson(response));
    }

    public java.util.List<DeviceCapability> enabledCapabilities(Long deviceId) {
        return capabilityMapper.findByDeviceIdAndCapabilityStatus(deviceId, "ENABLED");
    }

    private String toJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (Exception ex) {
            throw new IllegalStateException("无法序列化设备命令", ex);
        }
    }
}
