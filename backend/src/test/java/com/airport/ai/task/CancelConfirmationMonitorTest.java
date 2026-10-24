package com.airport.ai.task;

import com.airport.ai.auth.OperationLogService;
import com.airport.ai.device.*;
import com.airport.ai.event.TaskEventService;
import org.junit.jupiter.api.Test;
import java.time.LocalDateTime;
import java.util.List;
import static org.mockito.Mockito.*;

class CancelConfirmationMonitorTest {
    @Test void missingIdleConfirmationIsRecordedOnceWithAgentAndCommand() {
        DeviceCommandMapper commands = mock(DeviceCommandMapper.class);
        TaskEventService events = mock(TaskEventService.class);
        OperationLogService audit = mock(OperationLogService.class);
        DeviceCommandRecord command = new DeviceCommandRecord();
        command.setAgentCode("AGT-3");
        command.setCommandId("CMD-3");
        command.setTaskId(3L);
        command.setAttemptNo(0);
        when(commands.findUnconfirmedCancelBefore(any(LocalDateTime.class))).thenReturn(List.of(command));
        when(commands.updateStatus("AGT-3", "CMD-3", "TASK_CANCEL", 0, "TIMED_OUT", null))
                .thenReturn(1, 0);
        CancelConfirmationMonitor monitor = new CancelConfirmationMonitor(commands, events, audit, 60);

        monitor.check();
        monitor.check();

        verify(events).append(eq(3L), eq("TASK_CANCEL_CONFIRMATION_TIMEOUT"), eq("SYSTEM"),
                eq("DEVICE_CANCEL_NO_CONFIRMATION"), contains("AGT-3:CMD-3"));
        verify(audit).record(isNull(), eq("SYSTEM"), isNull(), eq("TASK_CANCEL_CONFIRMATION_TIMEOUT"),
                eq("AGT-3:CMD-3"), eq("FAILED"), isNull());
    }
}
