package com.airport.ai.task;

import com.airport.ai.auth.OperationLogService;
import com.airport.ai.device.*;
import com.airport.ai.event.TaskEventService;
import org.junit.jupiter.api.Test;
import java.util.Optional;
import static org.mockito.Mockito.*;

class DeviceDeliveryFailureHandlerTest {
    @Test void failedCancelDeliveryIsTraceableAfterAsyncSend() {
        TaskExecutionOrchestrator execution = mock(TaskExecutionOrchestrator.class);
        DeviceCommandMapper commands = mock(DeviceCommandMapper.class);
        TaskEventService events = mock(TaskEventService.class);
        OperationLogService audit = mock(OperationLogService.class);
        DeviceCommandRecord command = new DeviceCommandRecord();
        command.setTaskId(17L);
        when(commands.findByKey("AGT-17", "CMD-17", "TASK_CANCEL", 0)).thenReturn(Optional.of(command));

        new DeviceDeliveryFailureHandler(execution, commands, events, audit)
                .failed(new DeviceAgentMessagingService.DeliveryFailure("AGT-17", "CMD-17", "TASK_CANCEL", 0));

        verify(events).append(eq(17L), eq("TASK_CANCEL_DELIVERY_FAILED"), eq("SYSTEM"),
                eq("DEVICE_API_ERROR"), contains("AGT-17"));
        verify(audit).record(isNull(), eq("SYSTEM"), isNull(), eq("TASK_CANCEL_DELIVERY_FAILED"),
                eq("AGT-17:CMD-17"), eq("FAILED"), isNull());
        verifyNoInteractions(execution);
    }
}
