package com.airport.ai.device;

import com.airport.ai.common.BusinessException;
import com.airport.ai.common.ErrorCode;
import com.airport.ai.device.dto.DeviceAgentReportRequest;
import com.airport.ai.task.TaskExecutionOrchestrator;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.HexFormat;

/** Validates, deduplicates and dispatches every device-side report through one service. */
@Service
public class DeviceAgentReportService {
    private final DeviceAgentService deviceAgentService;
    private final DeviceCommandMapper commandMapper;
    private final DeviceCommandReportMapper reportMapper;
    private final TaskExecutionOrchestrator taskExecutionOrchestrator;
    private final ObjectMapper objectMapper;

    public DeviceAgentReportService(DeviceAgentService deviceAgentService,
                                    DeviceCommandMapper commandMapper,
                                    DeviceCommandReportMapper reportMapper,
                                    TaskExecutionOrchestrator taskExecutionOrchestrator,
                                    ObjectMapper objectMapper) {
        this.deviceAgentService = deviceAgentService;
        this.commandMapper = commandMapper;
        this.reportMapper = reportMapper;
        this.taskExecutionOrchestrator = taskExecutionOrchestrator;
        this.objectMapper = objectMapper;
    }

    @Transactional
    public void accept(String agentCode, DeviceAgentReportRequest request) {
        validatePayload(request);
        switch (request.getReportType()) {
            case "STATUS" -> {
                var status = request.getStatus();
                BigDecimal x = status.getLocation() == null ? null : status.getLocation().getX();
                BigDecimal y = status.getLocation() == null ? null : status.getLocation().getY();
                String zone = status.getLocation() == null ? null : status.getLocation().getZone();
                deviceAgentService.reportStatus(agentCode, status.getOnlineStatus(), status.getWorkStatus(), x, y,
                        status.getBusinessStatus() == null ? null : toJson(status.getBusinessStatus()), zone);
            }
            case "TASK_RESPONSE" -> {
                var response = request.getResponse();
                boolean fresh = record(agentCode, response.getCommandId(), "TASK_RESPONSE", 0, request);
                if (!fresh) return;
                taskExecutionOrchestrator.onTaskResponse(agentCode, response.getCommandId(),
                        Boolean.TRUE.equals(response.getAccepted()), response.getRejectReason());
                commandMapper.updateStatus(agentCode, response.getCommandId(), "TASK_ACCEPT", 0,
                        Boolean.TRUE.equals(response.getAccepted()) ? "ACCEPTED" : "REJECTED", toJson(response));
            }
            case "EXECUTION_FEEDBACK" -> {
                var feedback = request.getFeedback();
                int attemptNo = feedback.getAttemptNo();
                boolean fresh = record(agentCode, feedback.getCommandId(), "EXECUTION_FEEDBACK", attemptNo, request);
                if (!fresh) return;
                taskExecutionOrchestrator.onExecutionFeedback(agentCode, feedback.getCommandId(), attemptNo,
                        feedback.getExecutionResult(), feedback.getReasonCode(), feedback.getOutputParams());
                String status = switch (feedback.getExecutionResult()) {
                    case "SUCCESS" -> "SUCCEEDED";
                    case "TIMEOUT" -> "TIMED_OUT";
                    default -> "FAILED";
                };
                commandMapper.updateStatus(agentCode, feedback.getCommandId(), "EXECUTE_CAPABILITY", attemptNo,
                        status, toJson(feedback));
            }
            default -> throw new BusinessException(ErrorCode.PARAM_FORMAT_ERROR, "reportType不支持");
        }
    }

    private void validatePayload(DeviceAgentReportRequest request) {
        if (request == null || request.getReportType() == null) {
            throw new BusinessException(ErrorCode.PARAM_MISSING, "reportType不可为空");
        }
        try {
            java.time.OffsetDateTime.parse(request.getReportedAt());
        } catch (Exception ex) {
            throw new BusinessException(ErrorCode.PARAM_FORMAT_ERROR, "reportedAt必须为ISO-8601时间");
        }
        boolean valid = switch (request.getReportType()) {
            case "STATUS" -> request.getStatus() != null && request.getStatus().getLocation() != null
                    && request.getStatus().getLocation().getX() != null
                    && request.getStatus().getLocation().getY() != null
                    && request.getResponse() == null && request.getFeedback() == null;
            case "TASK_RESPONSE" -> request.getResponse() != null && request.getStatus() == null && request.getFeedback() == null;
            case "EXECUTION_FEEDBACK" -> request.getFeedback() != null && request.getStatus() == null && request.getResponse() == null;
            default -> false;
        };
        if (!valid) throw new BusinessException(ErrorCode.PARAM_FORMAT_ERROR, "reportType与payload不匹配");
        if (request.getResponse() != null && request.getResponse().getCommandId() == null) {
            throw new BusinessException(ErrorCode.PARAM_MISSING, "response.commandId不可为空");
        }
        if (request.getResponse() != null && request.getResponse().getAccepted() == null) {
            throw new BusinessException(ErrorCode.PARAM_MISSING, "response.accepted不可为空");
        }
        if (request.getResponse() != null && Boolean.FALSE.equals(request.getResponse().getAccepted())
                && (request.getResponse().getRejectReason() == null || request.getResponse().getRejectReason().isBlank())) {
            throw new BusinessException(ErrorCode.PARAM_MISSING, "拒绝承接时response.rejectReason不可为空");
        }
        if (request.getFeedback() != null && request.getFeedback().getCommandId() == null) {
            throw new BusinessException(ErrorCode.PARAM_MISSING, "feedback.commandId不可为空");
        }
        if (request.getFeedback() != null) {
            var feedback = request.getFeedback();
            String executionResult = feedback.getExecutionResult();
            // 空值不归一：缺失的结果仍是参数错误，只有“非空但无法识别”的取值才归一为失败
            if (executionResult == null || executionResult.isBlank()) {
                throw new BusinessException(ErrorCode.PARAM_MISSING, "feedback.executionResult不可为空");
            }
            if (!"SUCCESS".equals(executionResult) && !"FAILED".equals(executionResult)
                    && !"TIMEOUT".equals(executionResult)) {
                // 无法归一的反馈：保留原值于输出参数，归一为失败并带原因码，进入异常处理（DEF-S3-051）
                java.util.Map<String, Object> out = new java.util.LinkedHashMap<>();
                if (feedback.getOutputParams() != null) out.putAll(feedback.getOutputParams());
                out.put("rawExecutionResult", String.valueOf(executionResult));
                feedback.setOutputParams(out);
                feedback.setExecutionResult("FAILED");
                feedback.setReasonCode("ERR_FEEDBACK_UNRECOGNIZED");
            }
            // 成功反馈也带原因码，三类结果均可追溯（DEF-S3-053）
            if ("SUCCESS".equals(feedback.getExecutionResult())
                    && (feedback.getReasonCode() == null || feedback.getReasonCode().isBlank())) {
                feedback.setReasonCode("DEVICE_SUCCESS");
            }
            if (feedback.getAttemptNo() < 0 || feedback.getAttemptNo() > 1) {
                throw new BusinessException(ErrorCode.PARAM_OUT_OF_RANGE, "feedback.attemptNo必须为0或1");
            }
            if (!"SUCCESS".equals(feedback.getExecutionResult())
                    && (feedback.getReasonCode() == null || feedback.getReasonCode().isBlank())) {
                throw new BusinessException(ErrorCode.PARAM_MISSING, "失败反馈必须提供feedback.reasonCode");
            }
        }
    }

    private boolean record(String agentCode, String commandId, String reportType, int attemptNo, Object payload) {
        String payloadHash = hash(toJson(payload));
        if (reportMapper.insertIfAbsent(agentCode, commandId, reportType, attemptNo, payloadHash) == 1) return true;
        String originalHash = reportMapper.findPayloadHash(agentCode, commandId, reportType, attemptNo);
        if (!payloadHash.equals(originalHash)) {
            throw new BusinessException(ErrorCode.PARAM_FORMAT_ERROR,
                    "相同上报幂等键对应了不同的反馈内容");
        }
        return false;
    }

    private String toJson(Object value) {
        try { return objectMapper.writeValueAsString(value); }
        catch (Exception ex) { throw new IllegalStateException("无法规范化设备反馈", ex); }
    }

    private String hash(String value) {
        try {
            return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.UTF_8)));
        } catch (Exception ex) {
            throw new IllegalStateException("SHA-256不可用", ex);
        }
    }
}
