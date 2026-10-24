package com.airport.ai.task;

import com.airport.ai.auth.OperationLogService;
import com.airport.ai.device.DeviceCommandMapper;
import com.airport.ai.event.TaskEventService;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;

/** Tracks cancellation requests for which no device idle confirmation arrived. */
@Component
public class CancelConfirmationMonitor {
    private final DeviceCommandMapper commands;
    private final TaskEventService events;
    private final OperationLogService audit;
    private final int timeoutSeconds;

    public CancelConfirmationMonitor(DeviceCommandMapper commands, TaskEventService events,
                                     OperationLogService audit,
                                     @Value("${app.task.cancel-confirmation-timeout-seconds:60}") int timeoutSeconds) {
        this.commands = commands;
        this.events = events;
        this.audit = audit;
        this.timeoutSeconds = timeoutSeconds;
    }

    @Scheduled(fixedDelay = 10000)
    @Transactional
    public void check() {
        for (var command : commands.findUnconfirmedCancelBefore(LocalDateTime.now().minusSeconds(timeoutSeconds))) {
            if (commands.updateStatus(command.getAgentCode(), command.getCommandId(), "TASK_CANCEL",
                    command.getAttemptNo(), "TIMED_OUT", null) != 1) continue;
            String target = command.getAgentCode() + ":" + command.getCommandId();
            events.append(command.getTaskId(), "TASK_CANCEL_CONFIRMATION_TIMEOUT", "SYSTEM",
                    "DEVICE_CANCEL_NO_CONFIRMATION", "设备取消后未上报空闲，保留占用待核查: " + target);
            audit.record(null, "SYSTEM", null, "TASK_CANCEL_CONFIRMATION_TIMEOUT", target,
                    "FAILED", null);
        }
    }
}
