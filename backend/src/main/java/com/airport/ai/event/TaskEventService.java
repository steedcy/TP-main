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
        event.setReasonCode(reasonCode);
        event.setDetailSummary(detailSummary);
        taskEventMapper.insert(event);
        return event;
    }

    public List<TaskEvent> listByTask(Long taskId) {
        return taskEventMapper.findByTaskIdOrderByOccurredAtAsc(taskId);
    }
}
