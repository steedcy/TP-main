package com.airport.ai.device;

import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 代理详情的消息与事件时间线（SRS_F007.R07、TC-023.S2）：把设备事件与统一消息指令记录合并，
 * 每条含类型、时间、唯一指令号、请求/响应摘要与结果；摘要不返回完整载荷，避免泄露输入内容。
 */
@Service
public class DeviceAgentTimelineService {
    static final int LIMIT = 100;

    private final DeviceEventService eventService;
    private final DeviceCommandMapper commandMapper;

    public DeviceAgentTimelineService(DeviceEventService eventService, DeviceCommandMapper commandMapper) {
        this.eventService = eventService;
        this.commandMapper = commandMapper;
    }

    public List<Map<String, Object>> timeline(DeviceAgent agent) {
        List<Map<String, Object>> items = new ArrayList<>();
        for (DeviceEvent e : eventService.listByAgent(agent.getId())) {
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("kind", "EVENT");
            m.put("type", e.getEventType());
            m.put("at", e.getOccurredAt());
            m.put("commandId", null);
            m.put("summary", e.getDetailSummary());
            m.put("result", null);
            m.put("reasonCode", e.getReasonCode());
            items.add(m);
        }
        for (DeviceCommandRecord c : commandMapper.findRecentByAgentCode(agent.getAgentCode(), LIMIT)) {
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("kind", "COMMAND");
            m.put("type", c.getCommandType());
            m.put("at", c.getCreatedAt());
            m.put("commandId", c.getCommandId());
            m.put("attemptNo", c.getAttemptNo());
            m.put("summary", "任务" + c.getTaskId() + "步骤" + c.getStepSeq() + " " + c.getCapabilityType());
            m.put("result", c.getCommandStatus());
            m.put("reasonCode", null);
            items.add(m);
        }
        items.sort(Comparator.comparing((Map<String, Object> m) -> (LocalDateTime) m.get("at"),
                Comparator.nullsLast(Comparator.naturalOrder())).reversed());
        return items.size() > LIMIT ? items.subList(0, LIMIT) : items;
    }
}
