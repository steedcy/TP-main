package com.airport.ai.device;

import com.airport.ai.common.BusinessException;
import com.airport.ai.common.ErrorCode;
import com.airport.ai.device.dto.DeviceAgentReportRequest;
import com.airport.ai.device.dto.DeviceAgentMessageRequest;
import com.airport.ai.device.dto.DeviceCapabilityView;
import com.airport.ai.task.dto.TaskResponseRequest;
import com.airport.ai.task.Task;
import com.airport.ai.task.TaskMapper;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Map;

/** Single internal dispatch point for the six Appendix B device-agent message types. */
@Service
public class DeviceAgentInternalMessageService {
    private final DeviceAgentMapper agentMapper;
    private final TaskMapper taskMapper;
    private final DeviceAgentMessagingService messagingService;
    private final DeviceAgentReportService reportService;
    private final ObjectMapper objectMapper;
    @org.springframework.beans.factory.annotation.Autowired(required = false)
    private DeviceEventService deviceEventService;

    public DeviceAgentInternalMessageService(DeviceAgentMapper agentMapper, TaskMapper taskMapper,
                                             DeviceAgentMessagingService messagingService,
                                             DeviceAgentReportService reportService,
                                             ObjectMapper objectMapper) {
        this.agentMapper = agentMapper;
        this.taskMapper = taskMapper;
        this.messagingService = messagingService;
        this.reportService = reportService;
        this.objectMapper = objectMapper;
    }

    @Transactional
    public Map<String, Object> dispatch(DeviceAgentMessageRequest request) {
        DeviceAgent agent = agentMapper.findByAgentCode(request.getAgentId())
                .orElseThrow(() -> new BusinessException(ErrorCode.DEVICE_AGENT_NOT_FOUND));
        Map<String, Object> payload = request.getPayload() == null ? Map.of() : request.getPayload();

        return switch (request.getMessageType()) {
            case "CAPABILITY_QUERY" -> capabilityQuery(request, agent, payload);
            case "STATUS_QUERY" -> statusQuery(request, agent, payload);
            case "TASK_ACCEPT" -> {
                ensureOnline(agent);
                Task task = requireTask(payload);
                int stepSeq = requiredInteger(payload, "stepSeq");
                String capabilityType = requiredString(payload, "capabilityType");
                messagingService.requestTaskAcceptance(agent.getAgentCode(), request.getCommandId(), task.getId(),
                        stepSeq, capabilityType, mapValue(payload.get("inputParams")));
                yield Map.of("commandId", request.getCommandId(), "status", "SENT");
            }
            case "TASK_REJECT" -> {
                ensureEnabled(agent);
                String reason = requiredString(payload, "rejectReasonCode");
                TaskResponseRequest response = new TaskResponseRequest();
                response.setCommandId(request.getCommandId());
                response.setAccepted(false);
                response.setRejectReason(reason);
                DeviceAgentReportRequest report = new DeviceAgentReportRequest();
                report.setReportType("TASK_RESPONSE");
                report.setReportedAt(java.time.OffsetDateTime.now().toString());
                report.setResponse(response);
                reportService.accept(agent.getAgentCode(), report);
                yield Map.of("commandId", request.getCommandId(), "status", "REJECTED");
            }
            case "EXECUTION_FEEDBACK" -> {
                ensureEnabled(agent);
                String result = requiredString(payload, "executionResult");
                if (!List.of("SUCCESS", "FAILED", "TIMEOUT").contains(result)) {
                    throw new BusinessException(ErrorCode.PARAM_FORMAT_ERROR, "executionResult取值非法");
                }
                String reason = optionalString(payload, "reasonCode");
                Map<String, Object> output = mapValue(payload.get("outputParams"));
                int attemptNo = optionalInteger(payload, "attemptNo", 0);
                com.airport.ai.task.dto.ExecutionFeedbackRequest feedback =
                        new com.airport.ai.task.dto.ExecutionFeedbackRequest();
                feedback.setCommandId(request.getCommandId());
                feedback.setAttemptNo(attemptNo);
                feedback.setExecutionResult(result);
                feedback.setReasonCode(reason);
                feedback.setOutputParams(output);
                DeviceAgentReportRequest report = new DeviceAgentReportRequest();
                report.setReportType("EXECUTION_FEEDBACK");
                report.setReportedAt(java.time.OffsetDateTime.now().toString());
                report.setFeedback(feedback);
                reportService.accept(agent.getAgentCode(), report);
                yield Map.of("commandId", request.getCommandId(), "status", "PROCESSED");
            }
            case "TASK_CANCEL" -> {
                ensureOnline(agent);
                Task task = requireTask(payload);
                int stepSeq = requiredInteger(payload, "stepSeq");
                messagingService.cancelTask(agent.getAgentCode(), request.getCommandId(), task.getId(), stepSeq);
                yield Map.of("commandId", request.getCommandId(), "status", "SENT");
            }
            default -> throw new BusinessException(ErrorCode.PARAM_FORMAT_ERROR, "messageType不支持");
        };
    }

    /** 查询类消息成功交互也写设备事件，供过程追溯（SRS_F007.R07） */
    private void recordQuery(DeviceAgent agent, String messageType, String commandId, String summary) {
        if (deviceEventService == null) return;
        deviceEventService.appendMessage(agent.getId(), "AGENT_MESSAGE_" + messageType, commandId, "SUCCESS", null,
                "指令" + commandId + "：" + summary);
    }

    private Map<String, Object> capabilityQuery(DeviceAgentMessageRequest request, DeviceAgent agent,
                                                Map<String, Object> payload) {
        ensureEnabled(agent);
        String filter = optionalString(payload, "capabilityType");
        List<DeviceCapabilityView> capabilities = messagingService.enabledCapabilities(agent.getDeviceId()).stream()
                .filter(capability -> filter == null || filter.equals(capability.getCapabilityType()))
                .map(DeviceCapabilityView::from)
                .toList();
        recordQuery(agent, "CAPABILITY_QUERY", request.getCommandId(), "能力查询返回" + capabilities.size() + "项");
        return Map.of("commandId", request.getCommandId(), "capabilities", capabilities);
    }

    private Map<String, Object> statusQuery(DeviceAgentMessageRequest request, DeviceAgent agent,
                                            Map<String, Object> payload) {
        ensureEnabled(agent);
        Object businessStatus = Map.of();
        if (agent.getBusinessStatus() != null) {
            try {
                businessStatus = objectMapper.readValue(agent.getBusinessStatus(), Object.class);
            } catch (Exception ex) {
                throw new IllegalStateException("代理业务状态快照格式无效", ex);
            }
        }
        recordQuery(agent, "STATUS_QUERY", request.getCommandId(), "状态查询返回本地最新状态");
        return Map.of("commandId", request.getCommandId(),
                "agentId", agent.getAgentCode(),
                "agentStatus", agent.getAgentStatus(),
                "onlineStatus", agent.getOnlineStatus(),
                "workStatus", agent.getWorkStatus(),
                "businessStatus", businessStatus,
                "lastReportedAt", agent.getLastReportedAt() == null ? "" : agent.getLastReportedAt().toString(),
                "capabilities", messagingService.enabledCapabilities(agent.getDeviceId()).stream()
                        .map(DeviceCapability::getCapabilityType).distinct().toList());
    }

    private Task requireTask(Map<String, Object> payload) {
        String taskRef = requiredString(payload, "taskId");
        Task task = taskMapper.findByTaskCode(taskRef).orElseGet(() -> {
            try {
                return taskMapper.findById(Long.valueOf(taskRef)).orElse(null);
            } catch (NumberFormatException ex) {
                return null;
            }
        });
        if (task == null) throw new BusinessException(ErrorCode.TASK_NOT_FOUND);
        return task;
    }

    private void ensureEnabled(DeviceAgent agent) {
        if (!"ENABLED".equals(agent.getAgentStatus())) {
            throw new BusinessException(ErrorCode.DEVICE_AGENT_NOT_FOUND, "设备代理未启用");
        }
    }

    private void ensureOnline(DeviceAgent agent) {
        ensureEnabled(agent);
        if (!"ONLINE".equals(agent.getOnlineStatus())) throw new BusinessException(ErrorCode.DEVICE_OFFLINE);
    }

    private String requiredString(Map<String, Object> payload, String field) {
        String value = optionalString(payload, field);
        if (value == null) throw new BusinessException(ErrorCode.PARAM_MISSING, field + "不可为空");
        return value;
    }

    private String optionalString(Map<String, Object> payload, String field) {
        Object value = payload.get(field);
        if (value == null || value.toString().isBlank()) return null;
        return value.toString();
    }

    private int requiredInteger(Map<String, Object> payload, String field) {
        return optionalInteger(payload, field, null);
    }

    private int optionalInteger(Map<String, Object> payload, String field, Integer defaultValue) {
        Object value = payload.get(field);
        if (value == null) {
            if (defaultValue != null) return defaultValue;
            throw new BusinessException(ErrorCode.PARAM_MISSING, field + "不可为空");
        }
        if (value instanceof Number number) return number.intValue();
        try {
            return Integer.parseInt(value.toString());
        } catch (NumberFormatException ex) {
            throw new BusinessException(ErrorCode.PARAM_FORMAT_ERROR, field + "必须为整数");
        }
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> mapValue(Object value) {
        if (value == null) return Map.of();
        if (!(value instanceof Map<?, ?> map)) {
            throw new BusinessException(ErrorCode.PARAM_FORMAT_ERROR, "inputParams/outputParams必须为对象");
        }
        return (Map<String, Object>) map;
    }
}
