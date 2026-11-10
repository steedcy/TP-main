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
