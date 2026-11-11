package com.airport.ai.device;

import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class DeviceEventService {

    private final DeviceEventMapper deviceEventMapper;

    public DeviceEventService(DeviceEventMapper deviceEventMapper) {
        this.deviceEventMapper = deviceEventMapper;
    }

    public DeviceEvent append(Long deviceAgentId, String eventType, String trigger, String reasonCode, String detailSummary) {
        DeviceEvent event = new DeviceEvent();
        event.setDeviceAgentId(deviceAgentId);
        event.setEventType(safeCodeColumn(eventType == null || eventType.isBlank() ? "UNKNOWN" : eventType, 128));
        event.setTrigger("OPERATOR".equalsIgnoreCase(trigger) ? "OPERATOR" : "SYSTEM");
        event.setReasonCode(safeCodeColumn(reasonCode, 256));
        event.setDetailSummary(com.airport.ai.task.SceneParamsPrivacyGuard.sanitizeText(detailSummary));
        deviceEventMapper.insert(event);
        return event;
    }

    /** 统一业务消息事件：带结构化指令编号与结果，供代理时间线直接展示（SRS_F007.R07） */
    public DeviceEvent appendMessage(Long deviceAgentId, String eventType, String commandId, String result,
                                     String reasonCode, String detailSummary) {
        DeviceEvent event = new DeviceEvent();
        event.setDeviceAgentId(deviceAgentId);
        event.setEventType(safeCodeColumn(eventType == null || eventType.isBlank() ? "UNKNOWN" : eventType, 128));
        event.setTrigger("SYSTEM");
        event.setCommandId(safeCodeColumn(commandId, 64));
        event.setResult(safeCodeColumn(result, 64));
        event.setReasonCode(safeCodeColumn(reasonCode, 256));
        event.setDetailSummary(com.airport.ai.task.SceneParamsPrivacyGuard.sanitizeText(detailSummary));
        deviceEventMapper.insert(event);
        return event;
    }

    /** 运动安全控制字段或边界拦截事件：使用独立事务持久化，确保外层业务事务回滚时拦截留痕不丢失（SRS_NF005.R01） */
    @org.springframework.transaction.annotation.Transactional(
            propagation = org.springframework.transaction.annotation.Propagation.REQUIRES_NEW)
    public DeviceEvent appendBlockedMessage(Long deviceAgentId, String eventType, String commandId,
                                            String reasonCode, String detailSummary) {
        return appendMessage(deviceAgentId, eventType, commandId, "BLOCKED", reasonCode, detailSummary);
    }

    private String safeCodeColumn(String input, int maxCodePoints) {
        if (input == null) return null;
        if (input.length() <= maxCodePoints) return input;
        int count = input.codePointCount(0, input.length());
        if (count <= maxCodePoints) return input;
        return input.substring(0, input.offsetByCodePoints(0, maxCodePoints));
    }

    public List<DeviceEvent> listByAgent(Long deviceAgentId) {
        return deviceEventMapper.findByDeviceAgentIdOrderByOccurredAtAsc(deviceAgentId);
    }
}
