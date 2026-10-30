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
        event.setEventType(eventType);
        event.setTrigger(trigger);
        event.setReasonCode(reasonCode);
        event.setDetailSummary(detailSummary);
        deviceEventMapper.insert(event);
        return event;
    }

    /** 统一业务消息事件：带结构化指令编号与结果，供代理时间线直接展示（SRS_F007.R07） */
    public DeviceEvent appendMessage(Long deviceAgentId, String eventType, String commandId, String result,
                                     String reasonCode, String detailSummary) {
        DeviceEvent event = new DeviceEvent();
        event.setDeviceAgentId(deviceAgentId);
        event.setEventType(eventType);
        event.setTrigger("SYSTEM");
        event.setCommandId(commandId);
        event.setResult(result);
        event.setReasonCode(reasonCode);
        event.setDetailSummary(detailSummary);
        deviceEventMapper.insert(event);
        return event;
    }

    public List<DeviceEvent> listByAgent(Long deviceAgentId) {
        return deviceEventMapper.findByDeviceAgentIdOrderByOccurredAtAsc(deviceAgentId);
    }
}
