package com.airport.ai.device;

import com.airport.ai.auth.OperationLogService;
import com.airport.ai.auth.User;
import com.airport.ai.common.BusinessException;
import com.airport.ai.common.ErrorCode;
import com.airport.ai.device.dto.CreateDeviceRequest;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/** Registration and credential issuance commit together, before any child process starts. */
@Service
public class DeviceRegistrationService {
    private final DeviceService devices;
    private final DeviceMapper mapper;
    private final DeviceAgentMapper agents;
    private final DeviceCredentialService credentials;
    private final ManagedSimulatorService simulators;
    private final ApplicationEventPublisher events;
    private final OperationLogService logs;

    public DeviceRegistrationService(DeviceService devices, DeviceMapper mapper, DeviceAgentMapper agents,
            DeviceCredentialService credentials, ManagedSimulatorService simulators,
            ApplicationEventPublisher events, OperationLogService logs) {
        this.devices = devices; this.mapper = mapper; this.agents = agents;
        this.credentials = credentials; this.simulators = simulators; this.events = events; this.logs = logs;
    }

    @Transactional
    public Device create(CreateDeviceRequest request, User operator) {
        if (Boolean.TRUE.equals(request.getIsSimulator())) {
            if (request.getAccessEndpoint() == null || request.getAccessEndpoint().isBlank()) {
                request.setAccessEndpoint(simulators.allocateEndpoint(request.getDeviceCode()));
                if (org.springframework.transaction.support.TransactionSynchronizationManager.isSynchronizationActive())
                    org.springframework.transaction.support.TransactionSynchronizationManager.registerSynchronization(
                            new org.springframework.transaction.support.TransactionSynchronization() {
                                @Override public void afterCompletion(int status) { simulators.releaseReservation(request.getDeviceCode()); }
                            });
            }
            if (request.getAccessCredentialRef() == null || request.getAccessCredentialRef().isBlank())
                request.setAccessCredentialRef("device-token:" + request.getDeviceCode());
        }
        Device device = devices.create(request, operator);
        credentials.rotate(device.getDeviceCode());
        logs.record(operator.getId(), operator.getUsername(), operator.getRole(), "DEVICE_TOKEN_ISSUE", device.getDeviceCode(), "SUCCESS", null);
        Device saved = devices.getByCode(device.getDeviceCode());
        if (Boolean.TRUE.equals(saved.getIsSimulator())) queue(saved, operator);
        return saved;
    }

    @Transactional
    public void retry(String code, User operator) {
        Device device = requireRestartable(code);
        if (!Boolean.TRUE.equals(device.getIsSimulator()))
            throw new BusinessException(ErrorCode.PARAM_FORMAT_ERROR, "真实设备请手工配置令牌后连接测试");
        if (device.getDeviceTokenCiphertext() == null || device.getDeviceTokenCiphertext().isBlank()) credentials.rotate(code);
        queue(device, operator);
    }

    @Transactional
    public DeviceCredentialService.IssuedToken rotate(String code, User operator) {
        Device device = requireRestartable(code);
        DeviceCredentialService.IssuedToken issued = credentials.rotate(code);
        logs.record(operator.getId(), operator.getUsername(), operator.getRole(), "DEVICE_TOKEN_ROTATE", code, "SUCCESS", null);
        if (Boolean.TRUE.equals(device.getIsSimulator())) queue(device, operator);
        return issued;
    }

    Device requireRestartable(String code) {
        Device device = mapper.findByDeviceCodeForUpdate(code)
                .orElseThrow(() -> new BusinessException(ErrorCode.DEVICE_NOT_FOUND));
        if (!"ACTIVE".equals(device.getDeviceStatus()))
            throw new BusinessException(ErrorCode.PARAM_FORMAT_ERROR, "设备须为启用状态");
        if (PENDING_STATES.contains(device.getOnboardingStatus()))
            throw new BusinessException(ErrorCode.DATA_CONCURRENCY_CONFLICT, "自动接入正在执行，请稍后重试");
        requireIdle(device);
        return device;
    }

    private static final java.util.Set<String> PENDING_STATES = java.util.Set.of("PENDING", "STARTING", "CONNECTING", "BINDING");

    void requireIdle(Device device) {
        agents.findByDeviceId(device.getId()).ifPresent(agent -> {
            if ("ARCHIVED".equals(agent.getAgentStatus()))
                throw new BusinessException(ErrorCode.DEVICE_AGENT_ALREADY_EXISTS, "已归档代理不可恢复");
            if (agent.getCurrentTaskId() != null || "BUSY".equals(agent.getWorkStatus())
                    || agents.countActiveTaskAssignments(agent.getId()) > 0)
                throw new BusinessException(ErrorCode.DEVICE_HAS_ACTIVE_TASK, "设备存在进行中任务，不可重启或轮换令牌");
        });
    }

    private void queue(Device device, User operator) {
        agents.findByDeviceId(device.getId()).flatMap(agent -> agents.findByIdForUpdate(agent.getId())).ifPresent(agent -> {
            if (agent.getCurrentTaskId() != null || "BUSY".equals(agent.getWorkStatus())
                    || agents.countActiveTaskAssignments(agent.getId()) > 0)
                throw new BusinessException(ErrorCode.DEVICE_HAS_ACTIVE_TASK, "设备存在进行中任务，不可重启或轮换令牌");
            agent.setAgentStatus("DISABLED");
            agent.setOnlineStatus("OFFLINE");
            agents.update(agent);
        });
        mapper.updateOnboarding(device.getId(), "PENDING", "等待启动仿真体并验证连接");
        device.setOnboardingStatus("PENDING");
        device.setOnboardingMessage("等待启动仿真体并验证连接");
        User actor = new User();
        actor.setId(operator.getId()); actor.setUsername(operator.getUsername()); actor.setRole(operator.getRole());
        events.publishEvent(new DeviceOnboardingRequestedEvent(device.getDeviceCode(), actor));
    }
}
