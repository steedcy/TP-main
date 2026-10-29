package com.airport.ai.device;

import com.airport.ai.auth.OperationLogService;
import com.airport.ai.auth.User;
import com.airport.ai.common.BusinessException;
import com.airport.ai.common.ErrorCode;
import com.airport.ai.device.dto.CreateDeviceRequest;
import com.airport.ai.task.TaskExceptionService;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.context.ApplicationEventPublisher;

import java.math.BigDecimal;
import java.net.ConnectException;
import java.net.SocketTimeoutException;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.*;

/** SRS_F003：R01 冲突编码提示、R04 仿真体加载仿真状态能力、R06 删除/停用占用、启用须连接测试通过、失败原因区分。 */
class DeviceServiceF003Test {

    private final DeviceMapper deviceMapper = mock(DeviceMapper.class);
    private final DeviceAgentMapper agentMapper = mock(DeviceAgentMapper.class);
    private final DeviceCapabilityMapper capabilityMapper = mock(DeviceCapabilityMapper.class);
    private final TaskExceptionService taskExceptionService = mock(TaskExceptionService.class);
    private final com.airport.ai.devicetype.CapabilityTemplateMapper templateMapper =
            mock(com.airport.ai.devicetype.CapabilityTemplateMapper.class);
    private final DeviceEventService eventService = mock(DeviceEventService.class);
    private final DeviceService service = new DeviceService(deviceMapper, agentMapper, mock(OperationLogService.class),
            eventService, mock(DeviceAdapterClient.class), mock(ApplicationEventPublisher.class), 20,
            capabilityMapper, taskExceptionService, "F2_TEST,T2_B", templateMapper);

    private User operator() {
        User u = new User();
        u.setId(1L);
        u.setUsername("cfg");
        u.setRole("CONFIG_ADMIN");
        return u;
    }

    private CreateDeviceRequest request(boolean simulator) {
        CreateDeviceRequest r = new CreateDeviceRequest();
        r.setDeviceCode("SIM_X");
        r.setDeviceName("n");
        r.setDeviceTypeCode(simulator ? "SIMULATOR" : "SMART_DISPLAY");
        r.setIsSimulator(simulator);
        r.setSimulatedDeviceType(simulator ? "SMART_DISPLAY" : null);
        r.setAreaCode("F2_TEST");
        r.setPositionX(BigDecimal.ONE);
        r.setPositionY(BigDecimal.ONE);
        r.setAccessEndpoint("http://127.0.0.1:1");
        r.setAccessCredentialRef("cred");
        r.setStatusReportInterval(15);
        return r;
    }

    private Device device(String status, String test) {
        Device d = new Device();
        d.setId(5L);
        d.setDeviceCode("D5");
        d.setDeviceStatus(status);
        d.setConnectionTestStatus(test);
        when(deviceMapper.findById(5L)).thenReturn(Optional.of(d));
        return d;
    }

    private DeviceAgent agent(Long currentTaskId) {
        DeviceAgent a = new DeviceAgent();
        a.setId(9L);
        a.setAgentCode("AGT-9");
        a.setAgentStatus("ENABLED");
        a.setCurrentTaskId(currentTaskId);
        when(agentMapper.findByDeviceId(5L)).thenReturn(Optional.of(a));
        return a;
    }

    @Test
    void duplicateCodeMessageNamesConflictingCode() {
        when(deviceMapper.existsByDeviceCode("SIM_X")).thenReturn(true);
        BusinessException ex = assertThrows(BusinessException.class, () -> service.create(request(true), operator()));
        assertEquals(ErrorCode.DEVICE_CODE_TAKEN, ex.getErrorCode());
        assertTrue(ex.getMessage().contains("SIM_X"));
    }

    @Test
    void areaOutsidePresetListIsRejected() {
        CreateDeviceRequest r = request(true);
        r.setAreaCode("NOT_PRESET");
        BusinessException ex = assertThrows(BusinessException.class, () -> service.create(r, operator()));
        assertEquals(ErrorCode.PARAM_FORMAT_ERROR, ex.getErrorCode());
        assertTrue(ex.getMessage().contains("F2_TEST"));
    }

    @Test
    void simulatorCreationLoadsSimStatusCapabilityUntested() {
        when(deviceMapper.existsByDeviceCode(any())).thenReturn(false);
        service.create(request(true), operator());
        ArgumentCaptor<DeviceCapability> cap = ArgumentCaptor.forClass(DeviceCapability.class);
        verify(capabilityMapper).insert(cap.capture());
        assertEquals("CAP_SIM_STATUS", cap.getValue().getCapabilityCode());
        assertEquals("UNTESTED", cap.getValue().getCapabilityStatus());
    }

    @Test
    void realDeviceCreationLoadsNoSimCapability() {
        service.create(request(false), operator());
        verify(capabilityMapper, never()).insert(any());
    }

    @Test
    void deleteBlockedWhenAgentHasActiveTaskAssignment() {
        device("ACTIVE", "PASSED");
        agent(null);
        when(agentMapper.countActiveTaskAssignments(9L)).thenReturn(1L);
        BusinessException ex = assertThrows(BusinessException.class, () -> service.delete(5L, operator()));
        assertEquals(ErrorCode.DEVICE_HAS_ACTIVE_TASK, ex.getErrorCode());
        verify(deviceMapper, never()).update(any());
    }

    @Test
    void deleteAllowedWithoutActiveTasksArchivesAgent() {
        Device d = device("ACTIVE", "PASSED");
        DeviceAgent a = agent(null);
        service.delete(5L, operator());
        assertEquals("DELETED", d.getDeviceStatus());
        assertEquals("ARCHIVED", a.getAgentStatus());
    }

    @Test
    void enablingRequiresPassedConnectionTest() {
        device("INACTIVE", "FAILED");
        BusinessException ex = assertThrows(BusinessException.class, () -> service.updateStatus(5L, "ACTIVE", operator()));
        assertEquals(ErrorCode.DEVICE_CONNECTION_TEST_FAILED, ex.getErrorCode());
    }

    @Test
    void enablingAllowedAfterPassedTest() {
        Device d = device("INACTIVE", "PASSED");
        service.updateStatus(5L, "ACTIVE", operator());
        assertEquals("ACTIVE", d.getDeviceStatus());
    }

    @Test
    void disablingOccupiedDeviceRunsRecoveryThenReleasesOccupation() {
        device("ACTIVE", "PASSED");
        DeviceAgent a = agent(77L);
        a.setCurrentStepSeq(2);
        when(taskExceptionService.handleAgentDisabled(a)).thenReturn(1);
        service.updateStatus(5L, "INACTIVE", operator());
        verify(taskExceptionService).handleAgentDisabled(a);
        assertNull(a.getCurrentTaskId());
        assertNull(a.getCurrentStepSeq());
        assertEquals("DISABLED", a.getAgentStatus());
        verify(eventService).append(eq(9L), eq("AGENT_OCCUPATION_RELEASED"), any(), any(), any());
    }

    @Test
    void disablingIdleDeviceSkipsRecovery() {
        device("ACTIVE", "PASSED");
        agent(null);
        service.updateStatus(5L, "INACTIVE", operator());
        verify(taskExceptionService, never()).handleAgentOffline(any());
    }

    @Test
    void failureCausesAreDistinguishable() {
        String refused = DeviceAdapterClient.describeFailure(new RuntimeException(new ConnectException("refused")));
        String read = DeviceAdapterClient.describeFailure(new RuntimeException(new SocketTimeoutException("Read timed out")));
        String connect = DeviceAdapterClient.describeFailure(new RuntimeException(new SocketTimeoutException("connect timed out")));
        assertTrue(refused.contains("不可达"));
        assertTrue(read.contains("读取超时"));
        assertTrue(connect.contains("连接超时"));
        assertNotEquals(refused, read);
        assertNotEquals(read, connect);
    }

    @Test
    void disablingWithPendingAssignmentAndNullCurrentTaskStillRecoversAndReleases() {
        device("ACTIVE", "PASSED");
        DeviceAgent a = agent(null);
        when(taskExceptionService.handleAgentDisabled(a)).thenReturn(1);
        service.updateStatus(5L, "INACTIVE", operator());
        verify(taskExceptionService).handleAgentDisabled(a);
        verify(eventService).append(eq(9L), eq("AGENT_OCCUPATION_RELEASED"), any(), any(), any());
        assertEquals("DISABLED", a.getAgentStatus());
    }

    private com.airport.ai.devicetype.CapabilityTemplate template(String deviceType, String code) {
        com.airport.ai.devicetype.CapabilityTemplate t = new com.airport.ai.devicetype.CapabilityTemplate();
        t.setId((long) code.hashCode());
        t.setDeviceTypeCode(deviceType);
        t.setTemplateCode(code);
        t.setTemplateName(code);
        t.setCapabilityType(code);
        t.setInputParams("[]");
        t.setOutputParams("[]");
        return t;
    }

    @Test
    void simulatorInheritsSimulatedTypeTemplatesAndSimStatus() {
        when(templateMapper.findByDeviceTypeCode("SMART_DISPLAY")).thenReturn(java.util.List.of(
                template("SMART_DISPLAY", "CAP_INFO_DISPLAY"), template("SMART_DISPLAY", "CAP_NAVIGATION")));
        service.create(request(true), operator());
        ArgumentCaptor<DeviceCapability> cap = ArgumentCaptor.forClass(DeviceCapability.class);
        verify(capabilityMapper, times(3)).insert(cap.capture());
        java.util.List<String> codes = cap.getAllValues().stream().map(DeviceCapability::getCapabilityCode).toList();
        assertTrue(codes.containsAll(java.util.List.of("CAP_SIM_STATUS", "CAP_INFO_DISPLAY", "CAP_NAVIGATION")));
        assertTrue(cap.getAllValues().stream().allMatch(c -> "UNTESTED".equals(c.getCapabilityStatus())));
    }

    @Test
    void inactiveTemplatesAndExistingCapabilitiesAreSkipped() {
        com.airport.ai.devicetype.CapabilityTemplate off = template("SMART_DISPLAY", "CAP_INFO_DISPLAY");
        off.setTemplateStatus("INACTIVE");
        when(templateMapper.findByDeviceTypeCode("SMART_DISPLAY")).thenReturn(java.util.List.of(off));
        service.create(request(true), operator());
        verify(capabilityMapper, times(1)).insert(any());
    }

    @Test
    void reloadIsIdempotentAndRejectsRealDevices() {
        Device d = device("ACTIVE", "PASSED");
        d.setIsSimulator(true);
        d.setSimulatedDeviceType("SMART_DISPLAY");
        d.setDeviceCode("D5");
        when(deviceMapper.findByDeviceCode("D5")).thenReturn(Optional.of(d));
        when(templateMapper.findByDeviceTypeCode("SMART_DISPLAY"))
                .thenReturn(java.util.List.of(template("SMART_DISPLAY", "CAP_INFO_DISPLAY")));
        when(capabilityMapper.existsByDeviceIdAndCapabilityCode(5L, "CAP_SIM_STATUS")).thenReturn(true);
        when(capabilityMapper.existsByDeviceIdAndCapabilityCode(5L, "CAP_INFO_DISPLAY")).thenReturn(false, true);
        assertEquals(1, service.reloadSimulatorProfile("D5", operator()));
        assertEquals(0, service.reloadSimulatorProfile("D5", operator()));
        d.setIsSimulator(false);
        assertThrows(BusinessException.class, () -> service.reloadSimulatorProfile("D5", operator()));
    }
}
