package com.airport.ai.event;

import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class TaskEventService {

    private final TaskEventMapper taskEventMapper;

    public TaskEventService(TaskEventMapper taskEventMapper) {
        this.taskEventMapper = taskEventMapper;
    }

    public TaskEvent append(Long taskId, String eventType, String trigger, String reasonCode, String detailSummary) {
        TaskEvent event = new TaskEvent();
        event.setTaskId(taskId);
        event.setEventType(safeCodeColumn(eventType == null || eventType.isBlank() ? "UNKNOWN" : eventType, 128));
        event.setTrigger("OPERATOR".equalsIgnoreCase(trigger) ? "OPERATOR" : "SYSTEM");
        // 每条事件都要有原因码（F027.R02）：调用方给了就保留，没给则按事件类型补默认码
        String resolvedReason = EventReasonCodes.resolve(eventType, reasonCode);
        event.setReasonCode(safeCodeColumn(resolvedReason, 256));
        event.setDetailSummary(com.airport.ai.task.SceneParamsPrivacyGuard.sanitizeText(detailSummary));
        taskEventMapper.insert(event);
        return event;
    }

    private String safeCodeColumn(String input, int maxCodePoints) {
        if (input == null) return null;
        if (input.length() <= maxCodePoints) return input;
        int count = input.codePointCount(0, input.length());
        if (count <= maxCodePoints) return input;
        return input.substring(0, input.offsetByCodePoints(0, maxCodePoints));
    }

    public List<TaskEvent> listByTask(Long taskId) {
        return taskEventMapper.findByTaskIdOrderByOccurredAtAsc(taskId);
    }
}
