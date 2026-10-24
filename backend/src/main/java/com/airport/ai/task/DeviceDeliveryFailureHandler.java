package com.airport.ai.task;

import com.airport.ai.auth.OperationLogService;
import com.airport.ai.device.DeviceAgentMessagingService.DeliveryFailure;
import com.airport.ai.device.DeviceCommandMapper;
import com.airport.ai.event.TaskEventService;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Component;

@Component
public class DeviceDeliveryFailureHandler {
    private final TaskExecutionOrchestrator execution;
    private final DeviceCommandMapper commands;
    private final TaskEventService events;
    private final OperationLogService audit;

    public DeviceDeliveryFailureHandler(TaskExecutionOrchestrator execution, DeviceCommandMapper commands,
                                        TaskEventService events, OperationLogService audit) {
        this.execution = execution;
        this.commands = commands;
        this.events = events;
        this.audit = audit;
    }

    @EventListener
    public void failed(DeliveryFailure failure) {
        if ("TASK_ACCEPT".equals(failure.commandType()))
            execution.onTaskResponse(failure.agentCode(), failure.commandId(), false, "DEVICE_API_ERROR");
        else if ("EXECUTE_CAPABILITY".equals(failure.commandType()))
            execution.onExecutionFeedback(failure.agentCode(), failure.commandId(), failure.attemptNo(),
                    "FAILED", "DEVICE_API_ERROR", java.util.Map.of());
        else if ("TASK_CANCEL".equals(failure.commandType())) {
            commands.findByKey(failure.agentCode(), failure.commandId(), "TASK_CANCEL", failure.attemptNo())
                    .ifPresent(command -> {
                        String target = failure.agentCode() + ":" + failure.commandId();
                        events.append(command.getTaskId(), "TASK_CANCEL_DELIVERY_FAILED", "SYSTEM",
                                "DEVICE_API_ERROR", "设备取消请求未获传输确认，设备可能仍在运行: " + target);
                        audit.record(null, "SYSTEM", null, "TASK_CANCEL_DELIVERY_FAILED", target,
                                "FAILED", null);
                    });
        }
    }
}
