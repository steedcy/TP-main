package com.airport.ai.device;

import com.airport.ai.auth.OperationLogService;
import com.airport.ai.auth.User;
import com.airport.ai.common.BusinessException;
import com.airport.ai.common.ErrorCode;
import com.airport.ai.devicetype.CapabilityTemplateMapper;
import com.airport.ai.devicetype.DeviceTypeCapabilityService;
import com.airport.ai.task.TaskExceptionService;
import com.airport.ai.task.TaskExecutionOrchestrator;
import com.airport.ai.task.TaskStepAssignment;
import com.airport.ai.task.TaskStepAssignmentMapper;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.List;
import java.util.Map;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.*;

/** SRS_F006：测试结果含请求/响应/耗时、失败不自动启用、停用占用能力走5.5.3恢复、仍有同类能力则不受影响。 */
class DeviceCapabilityF006Test {

    private final DeviceCapabilityMapper capMapper = mock(DeviceCapabilityMapper.class);
    private final DeviceMapper deviceMapper = mock(DeviceMapper.class);
    private final DeviceAgentMapper agentMapper = mock(DeviceAgentMapper.class);
    private final DeviceAgentMessagingService messaging = mock(DeviceAgentMessagingService.class);
    private final OperationLogService opLog = mock(OperationLogService.class);
    private final TaskStepAssignmentMapper assignmentMapper = mock(TaskStepAssignmentMapper.class);
    private final TaskExecutionOrchestrator orchestrator = mock(TaskExecutionOrchestrator.class);
    private final TaskExceptionService exceptions = mock(TaskExceptionService.class);
    private final DeviceCapabilityService service = new DeviceCapabilityService(capMapper, deviceMapper,
            mock(CapabilityTemplateMapper.class), mock(DeviceTypeCapabilityService.class), opLog, agentMapper, messaging);

    DeviceCapabilityF006Test() {
        ReflectionTestUtils.setField(service, "assignmentMapper", assignmentMapper);
        ReflectionTestUtils.setField(service, "orchestrator", orchestrator);
        ReflectionTestUtils.setField(service, "taskExceptionService", exceptions);
    }

    private User operator() {
        User u = new User();
        u.setId(1L);
        u.setUsername("cfg");
        u.setRole("CONFIG_ADMIN");
        return u;
    }

    private DeviceCapability capability(String code, String type, String status) {
        DeviceCapability c = new DeviceCapability();
        c.setId((long) code.hashCode());
        c.setDeviceId(5L);
        c.setCapabilityCode(code);
        c.setCapabilityType(type);
        c.setCapabilityStatus(status);
        c.setInputParams("[{\"name\":\"contentType\",\"type\":\"String\",\"required\":true,\"defaultValue\":\"TEXT\"}]");
        c.setOutputParams("[]");
        when(capMapper.findByDeviceIdAndCapabilityCode(5L, code)).thenReturn(Optional.of(c));
        return c;
    }

    private Device device() {
        Device d = new Device();
        d.setId(5L);
        d.setDeviceCode("D5");
        when(deviceMapper.findById(5L)).thenReturn(Optional.of(d));
        return d;
    }

    private DeviceAgent agent(Long taskId) {
        DeviceAgent a = new DeviceAgent();
        a.setId(9L);
        a.setAgentCode("AGT-9");
        a.setCurrentTaskId(taskId);
        a.setCurrentStepSeq(taskId == null ? null : 1);
        when(agentMapper.findByDeviceId(5L)).thenReturn(Optional.of(a));
        return a;
    }

    // ---------- DEF-S3-024
    @Test
    void passedTestExposesRequestResponseAndDuration() {
        Device d = device();
        DeviceCapability c = capability("C1", "CAP_INFO_DISPLAY", "UNTESTED");
        DeviceAgent a = agent(null);
        when(messaging.testCapability(eq(d), eq(a), eq(c), any())).thenReturn(Map.of("commandId", "TEST-1", "result", "SUCCESS"));
        DeviceCapability r = service.test(5L, "C1", operator());
        assertEquals("TESTED_PASSED", r.getCapabilityStatus());
        assertTrue(r.getTestRequest().contains("CAP_INFO_DISPLAY"));
        assertTrue(r.getTestResponse().contains("TEST-1"));
        assertNotNull(r.getTestDurationMs());
    }

    @Test
    void failedTestKeepsReasonAndDoesNotEnable() {
        Device d = device();
        DeviceCapability c = capability("C1", "CAP_INFO_DISPLAY", "UNTESTED");
        DeviceAgent a = agent(null);
        when(messaging.testCapability(eq(d), eq(a), eq(c), any()))
                .thenThrow(new BusinessException(ErrorCode.PARAM_FORMAT_ERROR, "设备能力测试未通过"));
        DeviceCapability r = service.test(5L, "C1", operator());
        assertEquals("TESTED_FAILED", r.getCapabilityStatus());
        assertTrue(r.getTestResult().contains("设备能力测试未通过"), "失败原因被保存");
        assertTrue(r.getTestResponse().contains("FAILED"));
        BusinessException ex = assertThrows(BusinessException.class, () -> service.updateStatus(5L, "C1", "ENABLED", operator()));
        assertEquals(ErrorCode.CAPABILITY_NOT_TESTED, ex.getErrorCode());
        assertEquals("TESTED_FAILED", c.getCapabilityStatus());
    }

    // ---------- R06 / NT-S3-015 / NT-S3-016
    private TaskStepAssignment assignment(long taskId, int seq) {
        TaskStepAssignment s = new TaskStepAssignment();
        s.setTaskId(taskId);
        s.setPlanVersionId(100L + taskId);
        s.setStepSeq(seq);
        return s;
    }

    @Test
    void disablingTheCapabilityUsedByAnInProgressStepRunsRecoveryAndReleasesOccupation() {
        device();
        DeviceCapability c = capability("C1", "CAP_INFO_DISPLAY", "ENABLED");
        DeviceAgent a = agent(77L);
        TaskStepAssignment s = assignment(77L, 1);
        when(capMapper.findByDeviceIdAndCapabilityStatus(5L, "ENABLED")).thenReturn(List.of());
        when(assignmentMapper.findActiveByAgentId(9L)).thenReturn(List.of(s));
        when(orchestrator.stepCapabilityType(177L, 1)).thenReturn("CAP_INFO_DISPLAY");
        service.updateStatus(5L, "C1", "DISABLED", operator());
        assertEquals("DISABLED", c.getCapabilityStatus());
        verify(exceptions).handleException(eq(77L), eq(1), eq("STEP_FAILED"), org.mockito.ArgumentMatchers.contains("ERR_CAPABILITY_DISABLED"));
        assertNull(a.getCurrentTaskId());
        assertEquals("IDLE", a.getWorkStatus());
    }

    @Test
    void stepsUsingAnotherCapabilityTypeAreLeftAlone() {
        device();
        capability("C1", "CAP_INFO_DISPLAY", "ENABLED");
        agent(77L);
        when(capMapper.findByDeviceIdAndCapabilityStatus(5L, "ENABLED")).thenReturn(List.of());
        when(assignmentMapper.findActiveByAgentId(9L)).thenReturn(List.of(assignment(77L, 1)));
        when(orchestrator.stepCapabilityType(177L, 1)).thenReturn("CAP_NAVIGATION");
        service.updateStatus(5L, "C1", "DISABLED", operator());
        verify(exceptions, never()).handleException(anyLong(), any(), any(), any());
    }

    @Test
    void anotherEnabledCapabilityOfTheSameTypeKeepsTheStepRunning() {
        device();
        capability("C1", "CAP_INFO_DISPLAY", "ENABLED");
        DeviceCapability other = new DeviceCapability();
        other.setCapabilityType("CAP_INFO_DISPLAY");
        agent(77L);
        when(capMapper.findByDeviceIdAndCapabilityStatus(5L, "ENABLED")).thenReturn(List.of(other));
        service.updateStatus(5L, "C1", "DISABLED", operator());
        verifyNoInteractions(exceptions);
    }

    @Test
    void disablingAnIdleCapabilityNeverTouchesTasks() {
        device();
        capability("C1", "CAP_INFO_DISPLAY", "ENABLED");
        agent(null);
        when(capMapper.findByDeviceIdAndCapabilityStatus(5L, "ENABLED")).thenReturn(List.of());
        when(assignmentMapper.findActiveByAgentId(9L)).thenReturn(List.of());
        service.updateStatus(5L, "C1", "DISABLED", operator());
        verify(exceptions, never()).handleException(anyLong(), any(), any(), any());
    }

    @Test
    void enablingDoesNotRunRecovery() {
        device();
        capability("C1", "CAP_INFO_DISPLAY", "TESTED_PASSED").setTestPassed(true);
        service.updateStatus(5L, "C1", "ENABLED", operator());
        verifyNoInteractions(exceptions);
    }

    // ---------- DEF-S3-080：不得经 DISABLED 绕过测试门禁
    private void assertCannotEnable(String code) {
        BusinessException ex = assertThrows(BusinessException.class, () -> service.updateStatus(5L, code, "ENABLED", operator()));
        assertEquals(ErrorCode.CAPABILITY_NOT_TESTED, ex.getErrorCode());
    }

    @Test
    void neverTestedCapabilityCannotBeEnabledEvenAfterDisableEnableRoundTrip() {
        device();
        DeviceCapability c = capability("C1", "CAP_INFO_DISPLAY", "UNTESTED");
        assertCannotEnable("C1");
        service.updateStatus(5L, "C1", "DISABLED", operator());
        assertEquals("DISABLED", c.getCapabilityStatus());
        assertCannotEnable("C1");
        assertEquals("DISABLED", c.getCapabilityStatus(), "被拒绝后状态不变");
        assertNull(c.getLastTestAt());
    }

    @Test
    void failedTestCapabilityCannotBeEnabledViaDisable() {
        Device d = device();
        DeviceCapability c = capability("C1", "CAP_INFO_DISPLAY", "UNTESTED");
        DeviceAgent a = agent(null);
        when(messaging.testCapability(eq(d), eq(a), eq(c), any()))
                .thenThrow(new BusinessException(ErrorCode.PARAM_FORMAT_ERROR, "设备能力测试未通过"));
        service.test(5L, "C1", operator());
        assertFalse(c.isTestPassed());
        service.updateStatus(5L, "C1", "DISABLED", operator());
        assertCannotEnable("C1");
    }

    @Test
    void editingAnEnabledCapabilityResetsItAndDisableCannotRestoreTheOldPass() {
        device();
        DeviceCapability c = capability("C1", "CAP_INFO_DISPLAY", "ENABLED");
        c.setTestPassed(true);
        var req = new com.airport.ai.device.dto.UpdateDeviceCapabilityRequest();
        req.setCapabilityName("n");
        req.setInputParams(List.of());
        req.setOutputParams(List.of());
        service.update(5L, "C1", req, operator());
        assertEquals("UNTESTED", c.getCapabilityStatus());
        assertFalse(c.isTestPassed(), "改参数后原测试结论失效");
        service.updateStatus(5L, "C1", "DISABLED", operator());
        assertCannotEnable("C1");
    }

    @Test
    void genuinelyPassedCapabilityCanBeDisabledAndReEnabledWithoutRetest() {
        Device d = device();
        DeviceCapability c = capability("C1", "CAP_INFO_DISPLAY", "UNTESTED");
        DeviceAgent a = agent(null);
        when(messaging.testCapability(eq(d), eq(a), eq(c), any())).thenReturn(Map.of("commandId", "TEST-1", "result", "SUCCESS"));
        service.test(5L, "C1", operator());
        assertTrue(c.isTestPassed());
        service.updateStatus(5L, "C1", "ENABLED", operator());
        when(capMapper.findByDeviceIdAndCapabilityStatus(5L, "ENABLED")).thenReturn(List.of());
        service.updateStatus(5L, "C1", "DISABLED", operator());
        assertEquals("DISABLED", c.getCapabilityStatus());
        service.updateStatus(5L, "C1", "ENABLED", operator());
        assertEquals("ENABLED", c.getCapabilityStatus(), "真正测试通过后的停用/再启用按规则保留");
    }

    @Test
    void aFailedRetestRevokesAnEarlierPassEvenForADisabledCapability() {
        Device d = device();
        DeviceCapability c = capability("C1", "CAP_INFO_DISPLAY", "DISABLED");
        c.setTestPassed(true);
        DeviceAgent a = agent(null);
        when(messaging.testCapability(eq(d), eq(a), eq(c), any()))
                .thenThrow(new BusinessException(ErrorCode.PARAM_FORMAT_ERROR, "设备能力测试未通过"));
        service.test(5L, "C1", operator());
        assertFalse(c.isTestPassed());
        assertCannotEnable("C1");
    }
}
