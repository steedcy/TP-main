package com.airport.ai.device;

import com.airport.ai.device.dto.DeviceAgentMessageRequest;
import com.airport.ai.device.dto.DeviceAgentReportRequest;
import com.airport.ai.task.MotionSafetyGuard;
import com.airport.ai.task.TaskExecutionOrchestrator;
import com.airport.ai.task.TaskMapper;
import com.airport.ai.task.dto.ExecutionFeedbackRequest;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.test.util.ReflectionTestUtils;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.stream.Stream;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.*;

/** SRS_F007：运动安全字段变体拦截、反馈归一与原因码、查询类消息留痕、消息时间线、绕过统一入口的边界。 */
class UnifiedMessagingF007Test {

    // ---------- R03 / DEF-S3-052
    @Test
    void camelCaseAndSeparatedVariantsOfEverySafetyFieldAreBlocked() {
        for (String key : List.of("speed", "acceleration", "attitude", "pathPoints", "path_points", "waypoints",
                "obstacleAvoidance", "emergencyStop", "emergency_stop", "speedLimit", "speed-limit",
                "lostConnectionParking", "lost_connection_parking", "safeStopOnDisconnect")) {
            assertFalse(MotionSafetyGuard.detect(Map.of("capabilityType", "CAP_NAVIGATION",
                    "inputParams", Map.of(key, 1))).isEmpty(), key + " 应被拦截");
        }
    }

    @Test
    void normalBusinessIntentsPass() {
        for (Map<String, Object> intent : List.<Map<String, Object>>of(
                Map.of("targetLocation", "F2_GATE_12", "routePreference", "SHORTEST"),
                Map.of("targetLocation", "F2_TEST", "escortMode", "WALK_WITH", "maxDuration", 300),
                Map.of("notificationType", "BOARDING", "notificationContent", "请前往12号登机口", "repeatCount", 2),
                Map.of("contentType", "TEXT", "contentData", "CA1234 延误", "displayDuration", 30),
                Map.of("flightNumber", "CA1234", "updateType", "DELAY", "updateContent", "预计15:30", "displayDuration", 60))) {
            assertTrue(MotionSafetyGuard.detect(Map.of("capabilityType", "CAP_INFO_DISPLAY", "inputParams", intent)).isEmpty(),
                    intent + " 是正常业务意图，不应被拦截");
        }
    }

    // ---------- R06 / DEF-S3-051 / DEF-S3-053
    private DeviceAgentReportService reportService(TaskExecutionOrchestrator orchestrator) {
        DeviceCommandReportMapper reports = mock(DeviceCommandReportMapper.class);
        when(reports.insertIfAbsent(anyString(), anyString(), anyString(), anyInt(), anyString())).thenReturn(1);
        return new DeviceAgentReportService(mock(DeviceAgentService.class), mock(DeviceCommandMapper.class), reports,
                orchestrator, new ObjectMapper().findAndRegisterModules());
    }

    private DeviceAgentReportRequest feedback(String result, String reason) {
        ExecutionFeedbackRequest f = new ExecutionFeedbackRequest();
        f.setCommandId("CMD-1");
        f.setAttemptNo(0);
        f.setExecutionResult(result);
        f.setReasonCode(reason);
        DeviceAgentReportRequest r = new DeviceAgentReportRequest();
        r.setReportType("EXECUTION_FEEDBACK");
        r.setReportedAt("2026-10-31T00:00:00+08:00");
        r.setFeedback(f);
        return r;
    }

    @Test
    void unrecognizedResultIsNormalizedToFailedWithReasonCodeAndRawValueKept() {
        TaskExecutionOrchestrator orchestrator = mock(TaskExecutionOrchestrator.class);
        reportService(orchestrator).accept("AGT-1", feedback("UNRECOGNIZED", null));
        ArgumentCaptor<Map<String, Object>> out = ArgumentCaptor.forClass(Map.class);
        verify(orchestrator).onExecutionFeedback(eq("AGT-1"), eq("CMD-1"), eq(0), eq("FAILED"),
                eq("ERR_FEEDBACK_UNRECOGNIZED"), out.capture());
        assertEquals("UNRECOGNIZED", out.getValue().get("rawExecutionResult"));
    }

    @Test
    void successFeedbackCarriesAReasonCodeAndExplicitOnesAreKept() {
        TaskExecutionOrchestrator orchestrator = mock(TaskExecutionOrchestrator.class);
        reportService(orchestrator).accept("AGT-1", feedback("SUCCESS", null));
        verify(orchestrator).onExecutionFeedback(eq("AGT-1"), eq("CMD-1"), eq(0), eq("SUCCESS"), eq("DEVICE_SUCCESS"), any());
        TaskExecutionOrchestrator second = mock(TaskExecutionOrchestrator.class);
        reportService(second).accept("AGT-1", feedback("TIMEOUT", "SIMULATED_TIMEOUT"));
        verify(second).onExecutionFeedback(eq("AGT-1"), eq("CMD-1"), eq(0), eq("TIMEOUT"), eq("SIMULATED_TIMEOUT"), any());
    }

    @Test
    void blankResultIsStillRejectedByValidation() {
        var validator = jakarta.validation.Validation.buildDefaultValidatorFactory().getValidator();
        ExecutionFeedbackRequest f = new ExecutionFeedbackRequest();
        f.setCommandId("CMD-1");
        f.setExecutionResult(" ");
        assertFalse(validator.validate(f).isEmpty());
    }

    // ---------- R07 / DEF-S3-054
    @Test
    void successfulQueriesWriteDeviceEvents() {
        DeviceAgentMapper agents = mock(DeviceAgentMapper.class);
        DeviceAgentMessagingService messaging = mock(DeviceAgentMessagingService.class);
        DeviceAgent agent = new DeviceAgent();
        agent.setId(9L);
        agent.setAgentCode("AGT-9");
        agent.setDeviceId(5L);
        agent.setAgentStatus("ENABLED");
        agent.setOnlineStatus("ONLINE");
        agent.setWorkStatus("IDLE");
        when(agents.findByAgentCode("AGT-9")).thenReturn(Optional.of(agent));
        when(messaging.enabledCapabilities(5L)).thenReturn(List.of());
        DeviceEventService events = mock(DeviceEventService.class);
        DeviceAgentInternalMessageService service = new DeviceAgentInternalMessageService(agents, mock(TaskMapper.class),
                messaging, mock(DeviceAgentReportService.class), new ObjectMapper().findAndRegisterModules());
        ReflectionTestUtils.setField(service, "deviceEventService", events);
        service.dispatch(query("CAPABILITY_QUERY", "REAL-UNIQUE-1"));
        service.dispatch(query("STATUS_QUERY", "REAL-UNIQUE-2"));
        // DEF-S3-082：结构化指令号与结果，而不只在摘要文本里
        verify(events).appendMessage(eq(9L), eq("AGENT_MESSAGE_CAPABILITY_QUERY"), eq("REAL-UNIQUE-1"), eq("SUCCESS"),
                any(), org.mockito.ArgumentMatchers.contains("REAL-UNIQUE-1"));
        verify(events).appendMessage(eq(9L), eq("AGENT_MESSAGE_STATUS_QUERY"), eq("REAL-UNIQUE-2"), eq("SUCCESS"),
                any(), org.mockito.ArgumentMatchers.contains("REAL-UNIQUE-2"));
    }

    private DeviceAgentMessageRequest query(String type, String commandId) {
        DeviceAgentMessageRequest r = new DeviceAgentMessageRequest();
        r.setCommandId(commandId);
        r.setMessageType(type);
        r.setAgentId("AGT-9");
        return r;
    }

    // ---------- TC-023.S2 时间线
    @Test
    void timelineMergesEventsAndCommandsNewestFirst() {
        DeviceEventService events = mock(DeviceEventService.class);
        DeviceCommandMapper commands = mock(DeviceCommandMapper.class);
        DeviceAgent agent = new DeviceAgent();
        agent.setId(9L);
        agent.setAgentCode("AGT-9");
        DeviceEvent e = new DeviceEvent();
        e.setEventType("AGENT_MESSAGE_STATUS_QUERY");
        e.setOccurredAt(LocalDateTime.of(2026, 10, 31, 10, 0, 0));
        e.setDetailSummary("状态查询");
        when(events.listByAgent(9L)).thenReturn(List.of(e));
        DeviceCommandRecord c = new DeviceCommandRecord();
        c.setCommandId("CMD-7");
        c.setCommandType("EXECUTE_CAPABILITY");
        c.setAttemptNo(0);
        c.setTaskId(3L);
        c.setStepSeq(1);
        c.setCapabilityType("CAP_INFO_DISPLAY");
        c.setCommandStatus("SUCCEEDED");
        c.setCreatedAt(LocalDateTime.of(2026, 10, 31, 11, 0, 0));
        when(commands.findRecentByAgentCode("AGT-9", DeviceAgentTimelineService.LIMIT)).thenReturn(List.of(c));
        e.setCommandId("QRY-1");
        e.setResult("SUCCESS");
        var items = new DeviceAgentTimelineService(events, commands).timeline(agent);
        assertEquals(2, items.size());
        var query = items.stream().filter(i -> "EVENT".equals(i.get("kind"))).findFirst().orElseThrow();
        assertEquals("QRY-1", query.get("commandId"), "查询事件的结构化指令号");
        assertEquals("SUCCESS", query.get("result"), "查询事件的结构化结果");
        assertEquals("COMMAND", items.get(0).get("kind"));
        assertEquals("CMD-7", items.get(0).get("commandId"));
        assertEquals("SUCCEEDED", items.get(0).get("result"));
        assertEquals("EVENT", items.get(1).get("kind"));
    }

    @Test
    void everyCommandRowCarriesCommandIdAndResultAndFailureReasonsAreSurfaced() {
        DeviceEventService events = mock(DeviceEventService.class);
        DeviceCommandMapper commands = mock(DeviceCommandMapper.class);
        DeviceAgent agent = new DeviceAgent();
        agent.setId(9L);
        agent.setAgentCode("AGT-9");
        when(events.listByAgent(9L)).thenReturn(List.of());
        List<DeviceCommandRecord> rows = new java.util.ArrayList<>();
        String[][] spec = {{"TASK_ACCEPT", "ACCEPTED", null}, {"TASK_ACCEPT", "REJECTED", "{\"rejectReason\":\"DEVICE_BUSY\"}"},
                {"EXECUTE_CAPABILITY", "SUCCEEDED", "{\"reasonCode\":\"DEVICE_SUCCESS\"}"},
                {"EXECUTE_CAPABILITY", "FAILED", "{\"reasonCode\":\"SIMULATED_DEVICE_ERROR\"}"},
                {"EXECUTE_CAPABILITY", "TIMED_OUT", "{\"reasonCode\":\"SIMULATED_TIMEOUT\"}"},
                {"TASK_CANCEL", "SENT", null}};
        for (int i = 0; i < spec.length; i++) {
            DeviceCommandRecord c = new DeviceCommandRecord();
            c.setCommandId("CMD-" + i);
            c.setCommandType(spec[i][0]);
            c.setCommandStatus(spec[i][1]);
            c.setResponsePayload(spec[i][2]);
            c.setCreatedAt(LocalDateTime.of(2026, 10, 31, 9, i, 0));
            rows.add(c);
        }
        when(commands.findRecentByAgentCode("AGT-9", DeviceAgentTimelineService.LIMIT)).thenReturn(rows);
        var items = new DeviceAgentTimelineService(events, commands).timeline(agent);
        assertEquals(6, items.size());
        for (var item : items) {
            assertNotNull(item.get("commandId"), "每条消息行都有指令号");
            assertNotNull(item.get("result"), "每条消息行都有结果");
        }
        var byId = items.stream().collect(java.util.stream.Collectors.toMap(i -> (String) i.get("commandId"), i -> i));
        assertEquals("DEVICE_BUSY", byId.get("CMD-1").get("reasonCode"));
        assertEquals("DEVICE_SUCCESS", byId.get("CMD-2").get("reasonCode"));
        assertEquals("SIMULATED_DEVICE_ERROR", byId.get("CMD-3").get("reasonCode"));
        assertEquals("SIMULATED_TIMEOUT", byId.get("CMD-4").get("reasonCode"));
        assertNull(byId.get("CMD-0").get("reasonCode"));
        assertNull(DeviceAgentTimelineService.reasonOf("not json"));
        assertNull(DeviceAgentTimelineService.reasonOf(null));
    }

    // ---------- DEF-S3-083：统一消息入口与设备report入口对未知结果的处理一致
    private DeviceAgentInternalMessageService unifiedEntrance(DeviceAgentReportService reports) {
        DeviceAgentMapper agents = mock(DeviceAgentMapper.class);
        DeviceAgent agent = new DeviceAgent();
        agent.setId(9L);
        agent.setAgentCode("AGT-1");
        agent.setDeviceId(5L);
        agent.setAgentStatus("ENABLED");
        agent.setOnlineStatus("ONLINE");
        when(agents.findByAgentCode("AGT-1")).thenReturn(Optional.of(agent));
        return new DeviceAgentInternalMessageService(agents, mock(TaskMapper.class),
                mock(DeviceAgentMessagingService.class), reports, new ObjectMapper().findAndRegisterModules());
    }

    private DeviceAgentMessageRequest feedbackMessage(Map<String, Object> payload) {
        DeviceAgentMessageRequest r = new DeviceAgentMessageRequest();
        r.setCommandId("CMD-1");
        r.setMessageType("EXECUTION_FEEDBACK");
        r.setAgentId("AGT-1");
        r.setPayload(payload);
        return r;
    }

    @Test
    @SuppressWarnings("unchecked")
    void unifiedEntranceNormalizesAnUnrecognizedResultLikeTheDeviceReportEntrance() {
        TaskExecutionOrchestrator viaUnified = mock(TaskExecutionOrchestrator.class);
        var out = unifiedEntrance(reportService(viaUnified)).dispatch(feedbackMessage(Map.of(
                "executionResult", "UNRECOGNIZED", "attemptNo", 0)));
        assertEquals("PROCESSED", out.get("status"));
        ArgumentCaptor<Map<String, Object>> unifiedOut = ArgumentCaptor.forClass(Map.class);
        verify(viaUnified).onExecutionFeedback(eq("AGT-1"), eq("CMD-1"), eq(0), eq("FAILED"),
                eq("ERR_FEEDBACK_UNRECOGNIZED"), unifiedOut.capture());

        TaskExecutionOrchestrator viaReport = mock(TaskExecutionOrchestrator.class);
        reportService(viaReport).accept("AGT-1", feedback("UNRECOGNIZED", null));
        ArgumentCaptor<Map<String, Object>> reportOut = ArgumentCaptor.forClass(Map.class);
        verify(viaReport).onExecutionFeedback(eq("AGT-1"), eq("CMD-1"), eq(0), eq("FAILED"),
                eq("ERR_FEEDBACK_UNRECOGNIZED"), reportOut.capture());
        assertEquals(reportOut.getValue(), unifiedOut.getValue(), "两个入口归一后的输出一致，且都保留原始取值");
        assertEquals("UNRECOGNIZED", unifiedOut.getValue().get("rawExecutionResult"));
    }

    @Test
    void unifiedEntranceStillRejectsMissingOrBlankResults() {
        DeviceAgentInternalMessageService service = unifiedEntrance(mock(DeviceAgentReportService.class));
        for (Map<String, Object> payload : List.<Map<String, Object>>of(Map.of(), Map.of("executionResult", " "))) {
            var ex = assertThrows(com.airport.ai.common.BusinessException.class,
                    () -> service.dispatch(feedbackMessage(payload)));
            assertEquals(com.airport.ai.common.ErrorCode.PARAM_MISSING, ex.getErrorCode());
        }
    }

    @Test
    void reportServiceRejectsABlankResultInsteadOfTurningItIntoFailure() {
        TaskExecutionOrchestrator orchestrator = mock(TaskExecutionOrchestrator.class);
        for (String blank : new String[]{null, "", "  "}) {
            var ex = assertThrows(com.airport.ai.common.BusinessException.class,
                    () -> reportService(orchestrator).accept("AGT-1", feedback(blank, null)));
            assertEquals(com.airport.ai.common.ErrorCode.PARAM_MISSING, ex.getErrorCode());
        }
        verifyNoInteractions(orchestrator);
    }

    @Test
    void unifiedEntranceKeepsRecognizedResultsUnchanged() {
        for (String result : List.of("SUCCESS", "FAILED", "TIMEOUT")) {
            TaskExecutionOrchestrator orchestrator = mock(TaskExecutionOrchestrator.class);
            unifiedEntrance(reportService(orchestrator)).dispatch(feedbackMessage(Map.of(
                    "executionResult", result, "reasonCode", "R-" + result, "attemptNo", 0)));
            verify(orchestrator).onExecutionFeedback(eq("AGT-1"), eq("CMD-1"), eq(0), eq(result), eq("R-" + result), any());
        }
    }

    // ---------- R05：业务模块只经统一消息服务与设备交互
    @Test
    void onlyDeviceManagementClassesTouchTheDeviceAdapterClient() throws IOException {
        Set<String> allowed = Set.of("DeviceAdapterClient.java", "DeviceAgentBindingService.java",
                "DeviceAgentMessagingService.java", "DeviceService.java", "SimulatorManagementController.java");
        Path root = Path.of("src/main/java");
        try (Stream<Path> files = Files.walk(root)) {
            List<String> offenders = files.filter(p -> p.toString().endsWith(".java"))
                    .filter(p -> !allowed.contains(p.getFileName().toString()))
                    .filter(p -> read(p).contains("DeviceAdapterClient"))
                    .map(Path::toString).toList();
            assertTrue(offenders.isEmpty(), "以下业务类绕过统一消息服务直接使用设备适配器: " + offenders);
        }
    }

    @Test
    void taskModulesDoNotImportTheAdapterOrHttpClients() throws IOException {
        Path root = Path.of("src/main/java/com/airport/ai/task");
        try (Stream<Path> files = Files.walk(root)) {
            List<String> offenders = files.filter(p -> p.toString().endsWith(".java"))
                    .filter(p -> {
                        String src = read(p);
                        return src.contains("RestTemplate") || src.contains("WebClient") || src.contains("HttpClient");
                    }).map(Path::toString).toList();
            assertTrue(offenders.isEmpty(), "任务模块不得直连设备: " + offenders);
        }
    }

    private static String read(Path p) {
        try { return Files.readString(p); } catch (IOException e) { throw new IllegalStateException(e); }
    }
}
