package com.airport.ai.device;

import com.airport.ai.device.dto.DeviceBindingRequest;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.transaction.event.TransactionPhase;
import org.springframework.transaction.event.TransactionalEventListener;

@Component
public class DeviceAgentBindingService {
    private final DeviceAgentMapper agentMapper;
    private final DeviceMapper deviceMapper;
    private final DeviceAdapterClient adapterClient;
    private final DeviceEventService eventService;
    private final int heartbeatTimeoutSeconds;

    public DeviceAgentBindingService(DeviceAgentMapper agentMapper,
                                     DeviceMapper deviceMapper,
                                     DeviceAdapterClient adapterClient,
                                     DeviceEventService eventService,
                                     @Value("${app.device.heartbeat-timeout-seconds:30}") int heartbeatTimeoutSeconds) {
        this.agentMapper = agentMapper;
        this.deviceMapper = deviceMapper;
        this.adapterClient = adapterClient;
        this.eventService = eventService;
        this.heartbeatTimeoutSeconds = heartbeatTimeoutSeconds;
    }

    @TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)
    public void bind(DeviceAgentBindingRequestedEvent event) {
        DeviceAgent agent = agentMapper.findById(event.agentId()).orElse(null);
        if (agent == null) return;
        Device device = deviceMapper.findById(agent.getDeviceId()).orElse(null);
        if (device == null) return;
        try {
            adapterClient.bind(device, agent, heartbeatTimeoutSeconds);
            eventService.append(agent.getId(), "AGENT_BOUND_TO_RUNTIME", "SYSTEM", null,
                    "平台代理编号已绑定至设备运行时");
        } catch (RuntimeException ex) {
            eventService.append(agent.getId(), "AGENT_BIND_FAILED", "SYSTEM", "DEVICE_BIND_FAILED",
                    "设备运行时绑定失败: " + ex.getMessage());
        }
    }
}
