package com.airport.ai.device;

import com.airport.ai.auth.OperationLogService;
import com.airport.ai.auth.User;
import com.airport.ai.common.BusinessException;
import com.airport.ai.device.dto.DeviceAgentMessageRequest;
import com.airport.ai.event.TaskEventService;
import com.airport.ai.task.TaskExceptionService;
import jakarta.validation.Validation;
import jakarta.validation.Validator;
import org.junit.jupiter.api.Test;
import org.mockito.InOrder;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.*;

/** SRS_F004：R03 设备启停同步代理、R05 占用代理停用先恢复再释放、R08 启用/归档留痕、六类消息校验位置。 */
class AgentLifecycleF004Test {

    private final DeviceAgentMapper agentMapper = mock(DeviceAgentMapper.class);
    private final DeviceMapper deviceMapper = mock(DeviceMapper.class);
    private final DeviceEventService deviceEvents = mock(DeviceEventService.class);
    private final OperationLogService opLog = mock(OperationLogService.class);
    private final TaskExceptionService taskExceptions = mock(TaskExceptionService.class);
    private final ApplicationEventPublisher publisher = mock(ApplicationEventPublisher.class);

    private User operator() {
        User u = new User();
        u.setId(1L);
        u.setUsername("cfg");
        u.setRole("CONFIG_ADMIN");
        return u;
    }

    private DeviceAgent agent(String status, Long task) {
        DeviceAgent a = new DeviceAgent();
        a.setId(9L);
        a.setAgentCode("AGT-9");
        a.setDeviceId(5L);
        a.setAgentStatus(status);
        a.setOnlineStatus("ONLINE");
        a.setWorkStatus(task == null ? "IDLE" : "BUSY");
        a.setCurrentTaskId(task);
        a.setCurrentStepSeq(task == null ? null : 2);
        when(agentMapper.findById(9L)).thenReturn(Optional.of(a));
        when(agentMapper.findByDeviceId(5L)).thenReturn(Optional.of(a));
        return a;
    }

    private DeviceService deviceService() {
        return new DeviceService(deviceMapper, agentMapper, opLog, deviceEvents, mock(DeviceAdapterClient.class), publisher, 20,
                mock(DeviceCapabilityMapper.class), taskExceptions, "F2_TEST",
                mock(com.airport.ai.devicetype.CapabilityTemplateMapper.class));
    }

    private Device device(String status) {
        Device d = new Device();
        d.setId(5L);
        d.setDeviceCode("D5");
        d.setDeviceStatus(status);
        d.setConnectionTestStatus("PASSED");
        when(deviceMapper.findById(5L)).thenReturn(Optional.of(d));
        return d;
    }

    @Test
    void reEnablingDeviceReEnablesDisabledAgentWithEventAndOperationLog() {
        device("INACTIVE");
        DeviceAgent a = agent("DISABLED", null);
        deviceService().updateStatus(5L, "ACTIVE", operator());
        assertEquals("ENABLED", a.getAgentStatus());
        verify(deviceEvents).append(eq(9L), eq("AGENT_ENABLED"), any(), any(), any());
        verify(opLog).record(any(), any(), any(), eq("DEVICE_AGENT_ENABLE"), eq("AGT-9"), eq("SUCCESS"), any());
        verify(publisher).publishEvent(any(DeviceAgentBindingRequestedEvent.class));
    }

    @Test
    void reEnablingDoesNotTouchArchivedAgent() {
        device("INACTIVE");
        DeviceAgent a = agent("ARCHIVED", null);
        deviceService().updateStatus(5L, "ACTIVE", operator());
        assertEquals("ARCHIVED", a.getAgentStatus());
        verify(deviceEvents, never()).append(eq(9L), eq("AGENT_ENABLED"), any(), any(), any());
    }

    @Test
    void deviceDeleteArchivesAgentWithOperationLog() {
        device("ACTIVE");
        DeviceAgent a = agent("ENABLED", null);
        deviceService().delete(5L, operator());
        assertEquals("ARCHIVED", a.getAgentStatus());
        verify(deviceEvents).append(eq(9L), eq("AGENT_ARCHIVED"), any(), any(), any());
        verify(opLog).record(any(), any(), any(), eq("DEVICE_AGENT_ARCHIVE"), eq("AGT-9"), eq("SUCCESS"), any());
    }

    private DeviceAgentService agentService() {
        DeviceAgentService s = new DeviceAgentService(agentMapper, deviceMapper, opLog, mock(TaskEventService.class),
                deviceEvents, taskExceptions);
        return s;
    }

    @Test
    void disablingOccupiedAgentExitsCandidatesThenRecoversThenReleases() {
        DeviceAgent a = agent("ENABLED", 77L);
        when(taskExceptions.handleAgentDisabled(a)).thenAnswer(inv -> {
            assertEquals("DISABLED", a.getAgentStatus(), "恢复前代理须已退出候选");
            assertEquals("OFFLINE", a.getOnlineStatus());
            return 1;
        });
        agentService().disable(9L, true, operator());
        InOrder order = inOrder(taskExceptions, deviceEvents);
        order.verify(taskExceptions).handleAgentDisabled(a);
        order.verify(deviceEvents).append(eq(9L), eq("AGENT_OCCUPATION_RELEASED"), any(), any(), any());
        assertNull(a.getCurrentTaskId());
        assertNull(a.getCurrentStepSeq());
        assertEquals("IDLE", a.getWorkStatus());
        verify(opLog).record(any(), any(), any(), eq("DEVICE_AGENT_DISABLE"), eq("AGT-9"), eq("SUCCESS"), any());
    }

    @Test
    void disablingWithPendingAssignmentButNullCurrentTaskStillRecovers() {
        DeviceAgent a = agent("ENABLED", null);
        when(taskExceptions.handleAgentDisabled(a)).thenReturn(2);
        agentService().disable(9L, true, operator());
        verify(deviceEvents).append(eq(9L), eq("AGENT_OCCUPATION_RELEASED"), any(), any(), any());
    }

    @Test
    void disablingIdleAgentDoesNotEmitReleaseEvent() {
        DeviceAgent a = agent("ENABLED", null);
        agentService().disable(9L, true, operator());
        verify(deviceEvents, never()).append(eq(9L), eq("AGENT_OCCUPATION_RELEASED"), any(), any(), any());
        assertEquals("DISABLED", a.getAgentStatus());
    }

    @Test
    void disableRequiresConfirmationAndRejectsArchived() {
        agent("ENABLED", null);
        assertThrows(BusinessException.class, () -> agentService().disable(9L, false, operator()));
        agent("ARCHIVED", null);
        assertThrows(BusinessException.class, () -> agentService().disable(9L, true, operator()));
    }

    @Test
    void enabledCapabilitySummaryListsCodeAndName() {
        DeviceAgent a = agent("ENABLED", null);
        DeviceCapabilityMapper caps = mock(DeviceCapabilityMapper.class);
        DeviceCapability c = new DeviceCapability();
        c.setCapabilityCode("CAP_INFO_DISPLAY");
        c.setCapabilityName("综合信息展示");
        when(caps.findByDeviceIdAndCapabilityStatus(5L, "ENABLED")).thenReturn(List.of(c));
        DeviceAgentService s = agentService();
        ReflectionTestUtils.setField(s, "capabilityMapper", caps);
        assertEquals("CAP_INFO_DISPLAY", s.enabledCapabilitySummary(a).get(0).get("capabilityCode"));
        assertEquals("综合信息展示", s.enabledCapabilitySummary(a).get(0).get("capabilityName"));
    }

    @Test
    void sixMessageTypesValidateOnMessageTypeNotCommandId() {
        Validator validator = Validation.buildDefaultValidatorFactory().getValidator();
        DeviceAgentMessageRequest ok = new DeviceAgentMessageRequest();
        ok.setCommandId("CMD-0001-REAL-UNIQUE");
        ok.setMessageType("STATUS_QUERY");
        ok.setAgentId("AGT-9");
        assertTrue(validator.validate(ok).isEmpty(), "真实唯一指令号应通过");

        DeviceAgentMessageRequest badType = new DeviceAgentMessageRequest();
        badType.setCommandId("CMD-0002");
        badType.setMessageType("DELETE_EVERYTHING");
        badType.setAgentId("AGT-9");
        assertFalse(validator.validate(badType).isEmpty(), "非六类消息类型应被拒绝");

        DeviceAgentMessageRequest blank = new DeviceAgentMessageRequest();
        blank.setCommandId(" ");
        blank.setMessageType("CAPABILITY_QUERY");
        blank.setAgentId("AGT-9");
        assertFalse(validator.validate(blank).isEmpty(), "指令号不能为空");
    }
}
