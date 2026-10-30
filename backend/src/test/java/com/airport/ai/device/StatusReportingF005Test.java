package com.airport.ai.device;

import com.airport.ai.auth.OperationLogService;
import com.airport.ai.auth.User;
import com.airport.ai.common.BusinessException;
import com.airport.ai.common.ErrorCode;
import com.airport.ai.event.TaskEventService;
import com.airport.ai.task.Task;
import com.airport.ai.task.TaskExceptionService;
import com.airport.ai.task.TaskMapper;
import com.airport.ai.task.TaskStatus;
import com.airport.ai.task.TaskStepAssignment;
import com.airport.ai.task.TaskStepAssignmentMapper;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.*;

/** SRS_F005：心跳阈值 10~120 配置与生效、被拒上报留事件、区域同步、离线提示、无关离线判断、关联离线走恢复。 */
class StatusReportingF005Test {

    private User operator() {
        User u = new User();
        u.setId(1L);
        u.setUsername("cfg");
        u.setRole("CONFIG_ADMIN");
        return u;
    }

    // ---------- 心跳阈值 ----------
    private final SystemSettingMapper settings = mock(SystemSettingMapper.class);
    private final OperationLogService opLog = mock(OperationLogService.class);
    private final HeartbeatSettingService heartbeat = new HeartbeatSettingService(settings, opLog, 30);

    @Test
    void defaultsToThirtyWhenNothingStoredOrStoredValueIsOutOfRange() {
        assertEquals(30, heartbeat.timeoutSeconds());
        when(settings.findValue(HeartbeatSettingService.KEY)).thenReturn("500");
        assertEquals(30, heartbeat.timeoutSeconds());
        when(settings.findValue(HeartbeatSettingService.KEY)).thenReturn("abc");
        assertEquals(30, heartbeat.timeoutSeconds());
    }

    @Test
    void acceptsBoundariesTenAndOneTwenty() {
        assertEquals(10, heartbeat.update(10, operator()));
        assertEquals(120, heartbeat.update(120, operator()));
        verify(settings).upsert(HeartbeatSettingService.KEY, "10", "cfg");
        verify(settings).upsert(HeartbeatSettingService.KEY, "120", "cfg");
        verify(opLog, times(2)).record(any(), any(), any(), eq("HEARTBEAT_TIMEOUT_UPDATE"), any(), eq("SUCCESS"), any());
    }

    @Test
    void rejectsOutsideTenToOneTwentyAndMissing() {
        for (Integer bad : new Integer[]{9, 121, 0, -5}) {
            BusinessException ex = assertThrows(BusinessException.class, () -> heartbeat.update(bad, operator()));
            assertEquals(ErrorCode.PARAM_OUT_OF_RANGE, ex.getErrorCode());
        }
        assertThrows(BusinessException.class, () -> heartbeat.update(null, operator()));
        verify(settings, never()).upsert(any(), any(), any());
    }

    @Test
    void monitorUsesTheCurrentlyConfiguredThreshold() {
        DeviceAgentMapper agents = mock(DeviceAgentMapper.class);
        HeartbeatMonitorTask task = new HeartbeatMonitorTask(agents, mock(DeviceEventService.class),
                mock(TaskEventService.class), mock(TaskExceptionService.class), 30);
        HeartbeatSettingService configured = mock(HeartbeatSettingService.class);
        when(configured.timeoutSeconds()).thenReturn(10);
        ReflectionTestUtils.setField(task, "heartbeatSettingService", configured);
        LocalDateTime before = LocalDateTime.now();
        task.checkHeartbeatTimeout();
        var captor = org.mockito.ArgumentCaptor.forClass(LocalDateTime.class);
        verify(agents).findByOnlineStatusAndLastReportedAtBefore(eq("ONLINE"), captor.capture());
        long secondsBack = java.time.Duration.between(captor.getValue(), before).getSeconds();
        assertTrue(secondsBack >= 9 && secondsBack <= 11, "阈值应为新配置的10秒，实际回溯" + secondsBack);
    }

    // ---------- 被拒上报 ----------
    private final DeviceAgentMapper agentMapper = mock(DeviceAgentMapper.class);
    private final DeviceEventService events = mock(DeviceEventService.class);

    @Test
    void rejectedReportWritesOneSanitizedEventAndIsThrottled() {
        DeviceAgent agent = new DeviceAgent();
        agent.setId(9L);
        when(agentMapper.findByAgentCode("AGT-9")).thenReturn(Optional.of(agent));
        ReportRejectionRecorder recorder = new ReportRejectionRecorder(agentMapper, events);
        assertTrue(recorder.record("AGT-9", ReportRejectionRecorder.INVALID_FORMAT, "workStatus取值非法\n含换行"));
        assertFalse(recorder.record("AGT-9", ReportRejectionRecorder.INVALID_FORMAT, "again"), "窗口内重复被节流");
        assertTrue(recorder.record("AGT-9", ReportRejectionRecorder.AUTH_FAILED, "x"), "不同原因各记一次");
        verify(events, times(2)).append(eq(9L), eq("STATUS_REPORT_REJECTED"), any(), any(), any());
    }

    @Test
    void unknownAgentOrBlankCodeRecordsNothing() {
        ReportRejectionRecorder recorder = new ReportRejectionRecorder(agentMapper, events);
        when(agentMapper.findByAgentCode("NOPE")).thenReturn(Optional.empty());
        assertFalse(recorder.record("NOPE", ReportRejectionRecorder.AUTH_FAILED, "x"));
        assertFalse(recorder.record(null, ReportRejectionRecorder.AUTH_FAILED, "x"));
        verifyNoInteractions(events);
    }

    @Test
    void agentCodeIsResolvedFromReportPaths() {
        assertEquals("AGT-1", ReportRejectionRecorder.agentCodeFromPath("/device-api/v1/agents/AGT-1/report"));
        assertEquals("AGT-2", ReportRejectionRecorder.agentCodeFromPath("/api/v1/device-agents/AGT-2/execution-feedback"));
        assertNull(ReportRejectionRecorder.agentCodeFromPath("/api/v1/device-agents/report/DEV-1"));
        assertNull(ReportRejectionRecorder.agentCodeFromPath(null));
    }

    // ---------- 区域同步 ----------
    private DeviceAgentService agentService(Device device, DeviceAgent agent) {
        DeviceMapper devices = mock(DeviceMapper.class);
        when(devices.findById(device.getId())).thenReturn(Optional.of(device));
        when(agentMapper.findByAgentCode(agent.getAgentCode())).thenReturn(Optional.of(agent));
        DeviceAgentService s = new DeviceAgentService(agentMapper, devices, opLog, mock(TaskEventService.class),
                events, mock(TaskExceptionService.class));
        ReflectionTestUtils.setField(s, "presetAreasConfig", "F2_TEST,F2_ZONE_B");
        return s;
    }

    private DeviceAgent onlineAgent() {
        DeviceAgent a = new DeviceAgent();
        a.setId(9L);
        a.setAgentCode("AGT-9");
        a.setDeviceId(5L);
        a.setAgentStatus("ENABLED");
        a.setOnlineStatus("ONLINE");
        return a;
    }

    private Device deviceIn(String area) {
        Device d = new Device();
        d.setId(5L);
        d.setDeviceCode("D5");
        d.setAreaCode(area);
        return d;
    }

    @Test
    void reportedPresetZoneIsSyncedToDeviceArea() {
        Device device = deviceIn("F2_TEST");
        DeviceAgentService s = agentService(device, onlineAgent());
        s.reportStatus("AGT-9", "ONLINE", "IDLE", new BigDecimal("1"), new BigDecimal("2"), null, "F2_ZONE_B");
        assertEquals("F2_ZONE_B", device.getAreaCode());
    }

    @Test
    void unknownReportedZoneIsIgnoredButStatusStillSaved() {
        Device device = deviceIn("F2_TEST");
        DeviceAgent agent = onlineAgent();
        DeviceAgentService s = agentService(device, agent);
        s.reportStatus("AGT-9", "ONLINE", "BUSY", new BigDecimal("1"), new BigDecimal("2"), null, "MADE_UP_ZONE");
        assertEquals("F2_TEST", device.getAreaCode());
        assertEquals("BUSY", agent.getWorkStatus());
    }

    // ---------- 离线提示 ----------
    @Test
    void offlineInfoCarriesReasonCodeAndTaskImpactOnlyWhenOffline() {
        DeviceAgent agent = onlineAgent();
        DeviceAgentService s = agentService(deviceIn("F2_TEST"), agent);
        DeviceEventMapper eventMapper = mock(DeviceEventMapper.class);
        ReflectionTestUtils.setField(s, "eventMapper", eventMapper);
        assertNull(s.offlineInfo(agent), "在线不展示离线信息");

        agent.setOnlineStatus("OFFLINE");
        agent.setCurrentTaskId(88L);
        DeviceEvent event = new DeviceEvent();
        event.setReasonCode("ERR_HEARTBEAT_TIMEOUT");
        event.setDetailSummary("超过30秒未上报");
        when(eventMapper.findLatestOffline(9L)).thenReturn(event);
        var info = s.offlineInfo(agent);
        assertEquals("ERR_HEARTBEAT_TIMEOUT", info.get("reasonCode"));
        assertEquals(true, info.get("affectsTask"));
        assertEquals("AGT-9", info.get("agentCode"));
    }

    // ---------- 关联/无关离线判断 ----------
    private final TaskMapper taskMapper = mock(TaskMapper.class);
    private final TaskStepAssignmentMapper assignmentMapper = mock(TaskStepAssignmentMapper.class);
    private final TaskEventService taskEvents = mock(TaskEventService.class);
    private final TaskExceptionService exceptions = new TaskExceptionService(taskMapper, assignmentMapper,
            mock(com.airport.ai.task.TaskExceptionMapper.class), agentMapper, taskEvents,
            mock(com.airport.ai.task.TaskExecutionOrchestrator.class), mock(com.airport.ai.task.ReplanningService.class));

    private Task inProgress(long id) {
        Task t = new Task();
        t.setId(id);
        t.setStatus(TaskStatus.EXECUTING);
        return t;
    }

    @Test
    void unrelatedOfflineWritesJudgementToInProgressTasksWithoutReplanning() {
        DeviceAgent agent = onlineAgent();
        when(assignmentMapper.findActiveByAgentId(9L)).thenReturn(List.of());
        when(taskMapper.findInProgressFormal()).thenReturn(List.of(inProgress(1L), inProgress(2L)));
        exceptions.handleAgentOffline(agent);
        verify(taskEvents).append(eq(1L), eq("UNRELATED_AGENT_OFFLINE_JUDGED"), any(), eq("ERR_AGENT_OFFLINE_UNRELATED"), any());
        verify(taskEvents).append(eq(2L), eq("UNRELATED_AGENT_OFFLINE_JUDGED"), any(), eq("ERR_AGENT_OFFLINE_UNRELATED"), any());
        verify(taskEvents, never()).append(anyLong(), eq("EXCEPTION_DETECTED"), any(), any(), any());
    }

    @Test
    void offlineAgentWithPendingAssignmentButNoCurrentTaskIsTreatedAsRelated() {
        DeviceAgent agent = onlineAgent();
        TaskStepAssignment a = new TaskStepAssignment();
        a.setTaskId(7L);
        a.setStepSeq(1);
        Task t = inProgress(7L);
        t.setStatus(TaskStatus.COMPLETED); // 已结束任务：handleException 直接返回，但该代理有步骤关联，不能再被当作“无关”离线判断
        when(taskMapper.findById(7L)).thenReturn(Optional.of(t));
        when(assignmentMapper.findActiveByAgentId(9L)).thenReturn(List.of(a));
        exceptions.handleAgentOffline(agent);
        verify(taskMapper, never()).findInProgressFormal();
    }
}
