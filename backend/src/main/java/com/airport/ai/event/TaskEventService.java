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
        event.setEventType(eventType);
        event.setTrigger(trigger);
        // 每条事件都要有原因码（F027.R02）：调用方给了就保留，没给则按事件类型补默认码
        event.setReasonCode(EventReasonCodes.resolve(eventType, reasonCode));
        event.setDetailSummary(com.airport.ai.task.SceneParamsPrivacyGuard.sanitizeText(detailSummary));
        taskEventMapper.insert(event);
        return event;
    }

    public List<TaskEvent> listByTask(Long taskId) {
        return taskEventMapper.findByTaskIdOrderByOccurredAtAsc(taskId);
    }
}
