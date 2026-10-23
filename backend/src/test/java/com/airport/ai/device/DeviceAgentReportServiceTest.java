package com.airport.ai.device;

import com.airport.ai.device.dto.DeviceAgentReportRequest;
import com.airport.ai.task.TaskExecutionOrchestrator;
import com.airport.ai.task.dto.TaskResponseRequest;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;
import java.util.concurrent.atomic.AtomicReference;

class DeviceAgentReportServiceTest {

    @Test
    void duplicateTaskResponseIsAcknowledgedWithoutRepeatingTaskTransition() {
        DeviceAgentService deviceAgentService = mock(DeviceAgentService.class);
        DeviceCommandMapper commandMapper = mock(DeviceCommandMapper.class);
        DeviceCommandReportMapper reportMapper = mock(DeviceCommandReportMapper.class);
        TaskExecutionOrchestrator orchestrator = mock(TaskExecutionOrchestrator.class);
        AtomicReference<String> storedHash = new AtomicReference<>();
        when(reportMapper.insertIfAbsent(eq("AGT-41"), eq("CMD-41"), eq("TASK_RESPONSE"), eq(0), anyString()))
                .thenAnswer(invocation -> {
                    String hash = invocation.getArgument(4);
                    return storedHash.compareAndSet(null, hash) ? 1 : 0;
                });
        when(reportMapper.findPayloadHash("AGT-41", "CMD-41", "TASK_RESPONSE", 0))
                .thenAnswer(invocation -> storedHash.get());
        DeviceAgentReportService service = new DeviceAgentReportService(deviceAgentService, commandMapper,
                reportMapper, orchestrator, new ObjectMapper().findAndRegisterModules());

        DeviceAgentReportRequest report = new DeviceAgentReportRequest();
        report.setReportType("TASK_RESPONSE");
        report.setReportedAt("2026-10-13T05:00:00+08:00");
        TaskResponseRequest response = new TaskResponseRequest();
        response.setCommandId("CMD-41");
        response.setAccepted(true);
        report.setResponse(response);

        assertDoesNotThrow(() -> service.accept("AGT-41", report));
        assertDoesNotThrow(() -> service.accept("AGT-41", report));

        verify(orchestrator, times(1)).onTaskResponse("AGT-41", "CMD-41", true, null);
        verify(commandMapper, times(1)).updateStatus("AGT-41", "CMD-41", "TASK_ACCEPT", 0,
                "ACCEPTED", "{\"commandId\":\"CMD-41\",\"accepted\":true,\"rejectReason\":null}");
    }

    @Test
    void rejectsStatusReportsWithoutLocationSnapshot() {
        DeviceAgentReportService service = new DeviceAgentReportService(mock(DeviceAgentService.class),
                mock(DeviceCommandMapper.class), mock(DeviceCommandReportMapper.class),
                mock(TaskExecutionOrchestrator.class), new ObjectMapper().findAndRegisterModules());
        DeviceAgentReportRequest report = new DeviceAgentReportRequest();
        report.setReportType("STATUS");
        report.setReportedAt("2026-10-13T05:00:00+08:00");
        DeviceAgentReportRequest.StatusPayload status = new DeviceAgentReportRequest.StatusPayload();
        status.setOnlineStatus("ONLINE");
        status.setWorkStatus("IDLE");
        report.setStatus(status);

        org.junit.jupiter.api.Assertions.assertThrows(RuntimeException.class, () -> service.accept("AGT-41", report));
    }

    @Test
    void rejectsDifferentPayloadReusingAnIdempotencyKey() {
        DeviceCommandReportMapper reportMapper = mock(DeviceCommandReportMapper.class);
        AtomicReference<String> storedHash = new AtomicReference<>();
        when(reportMapper.insertIfAbsent(eq("AGT-41"), eq("CMD-41"), eq("TASK_RESPONSE"), eq(0), anyString()))
                .thenAnswer(invocation -> {
                    String hash = invocation.getArgument(4);
                    return storedHash.compareAndSet(null, hash) ? 1 : 0;
                });
        when(reportMapper.findPayloadHash("AGT-41", "CMD-41", "TASK_RESPONSE", 0))
                .thenAnswer(invocation -> storedHash.get());
        DeviceAgentReportService service = new DeviceAgentReportService(mock(DeviceAgentService.class),
                mock(DeviceCommandMapper.class), reportMapper, mock(TaskExecutionOrchestrator.class),
                new ObjectMapper().findAndRegisterModules());
        DeviceAgentReportRequest report = new DeviceAgentReportRequest();
        report.setReportType("TASK_RESPONSE");
        report.setReportedAt("2026-10-13T05:00:00+08:00");
        TaskResponseRequest response = new TaskResponseRequest();
        response.setCommandId("CMD-41");
        response.setAccepted(true);
        report.setResponse(response);

        assertDoesNotThrow(() -> service.accept("AGT-41", report));
        response.setAccepted(false);
        response.setRejectReason("DEVICE_BUSY");
        assertThrows(com.airport.ai.common.BusinessException.class, () -> service.accept("AGT-41", report));
    }
}
