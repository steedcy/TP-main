package com.airport.ai.task;

import com.airport.ai.device.DeviceAgentMessagingService.DeliveryFailure;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Component;

@Component
public class DeviceDeliveryFailureHandler {
    private final TaskExecutionOrchestrator execution;
    public DeviceDeliveryFailureHandler(TaskExecutionOrchestrator execution) { this.execution = execution; }
    @EventListener
    public void failed(DeliveryFailure failure) {
        if ("TASK_ACCEPT".equals(failure.commandType()))
            execution.onTaskResponse(failure.agentCode(), failure.commandId(), false, "DEVICE_API_ERROR");
        else if ("EXECUTE_CAPABILITY".equals(failure.commandType()))
            execution.onExecutionFeedback(failure.agentCode(), failure.commandId(), failure.attemptNo(),
                    "FAILED", "DEVICE_API_ERROR", java.util.Map.of());
    }
}
