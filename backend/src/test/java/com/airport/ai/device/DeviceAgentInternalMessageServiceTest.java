package com.airport.ai.device;

import com.airport.ai.device.dto.DeviceAgentMessageRequest;
import com.airport.ai.task.Task;
import com.airport.ai.task.TaskMapper;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

import java.util.Map;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class DeviceAgentInternalMessageServiceTest {

    @Test
    void dispatchesAllAppendixBMessageTypesThroughSharedGateways() {
        DeviceAgentMapper agents = mock(DeviceAgentMapper.class);
        TaskMapper tasks = mock(TaskMapper.class);
        DeviceAgentMessagingService messaging = mock(DeviceAgentMessagingService.class);
        DeviceAgentReportService reports = mock(DeviceAgentReportService.class);
        DeviceAgent agent = new DeviceAgent();
        agent.setId(41L);
        agent.setAgentCode("AGT-41");
        agent.setDeviceId(41L);
        agent.setAgentStatus("ENABLED");
        agent.setOnlineStatus("ONLINE");
        agent.setWorkStatus("IDLE");
        when(agents.findByAgentCode("AGT-41")).thenReturn(Optional.of(agent));
        Task task = new Task();
        task.setId(900L);
        task.setTaskCode("TASK-900");
        when(tasks.findByTaskCode("TASK-900")).thenReturn(Optional.of(task));
        when(messaging.enabledCapabilities(41L)).thenReturn(java.util.List.of());
        DeviceAgentInternalMessageService service = new DeviceAgentInternalMessageService(agents, tasks,
                messaging, reports, new ObjectMapper().findAndRegisterModules());

        assertEquals("CMD-CAP", service.dispatch(request("CAPABILITY_QUERY", "CMD-CAP", Map.of())).get("commandId"));
        assertEquals("CMD-STATUS", service.dispatch(request("STATUS_QUERY", "CMD-STATUS", Map.of())).get("commandId"));
        assertEquals("SENT", service.dispatch(request("TASK_ACCEPT", "CMD-ACCEPT", Map.of(
                "taskId", "TASK-900", "stepSeq", 1, "capabilityType", "CAP_INFO_DISPLAY",
                "inputParams", Map.of("contentType", "TEXT")))).get("status"));
        assertEquals("REJECTED", service.dispatch(request("TASK_REJECT", "CMD-REJECT",
                Map.of("rejectReasonCode", "DEVICE_BUSY"))).get("status"));
        assertEquals("PROCESSED", service.dispatch(request("EXECUTION_FEEDBACK", "CMD-FEEDBACK", Map.of(
                "executionResult", "SUCCESS", "attemptNo", 0, "outputParams", Map.of("completed", true))))
                .get("status"));
        assertEquals("SENT", service.dispatch(request("TASK_CANCEL", "CMD-CANCEL",
                Map.of("taskId", "TASK-900", "stepSeq", 1))).get("status"));

        verify(messaging).requestTaskAcceptance("AGT-41", "CMD-ACCEPT", 900L, 1,
                "CAP_INFO_DISPLAY", Map.of("contentType", "TEXT"));
        verify(reports, times(2)).accept(eq("AGT-41"), any());
        verify(messaging).cancelTask("AGT-41", "CMD-CANCEL", 900L, 1);
    }

    private static DeviceAgentMessageRequest request(String type, String commandId, Map<String, Object> payload) {
        DeviceAgentMessageRequest request = new DeviceAgentMessageRequest();
        request.setMessageType(type);
        request.setCommandId(commandId);
        request.setAgentId("AGT-41");
        request.setPayload(payload);
        return request;
    }
}
