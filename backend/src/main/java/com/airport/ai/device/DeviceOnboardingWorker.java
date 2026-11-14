package com.airport.ai.device;

import jakarta.annotation.PreDestroy;
import org.springframework.stereotype.Component;
import org.springframework.transaction.event.TransactionPhase;
import org.springframework.transaction.event.TransactionalEventListener;

import java.time.LocalDateTime;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;

@Component
public class DeviceOnboardingWorker {
    private final DeviceService devices;
    private final DeviceMapper mapper;
    private final DeviceAgentMapper agents;
    private final DeviceCredentialService credentials;
    private final ManagedSimulatorService simulators;
    private final ExecutorService executor = Executors.newFixedThreadPool(2, runnable -> {
        Thread thread = new Thread(runnable, "device-onboarding");
        thread.setDaemon(true);
        return thread;
    });

    public DeviceOnboardingWorker(DeviceService devices, DeviceMapper mapper, DeviceAgentMapper agents,
            DeviceCredentialService credentials, ManagedSimulatorService simulators) {
        this.devices = devices; this.mapper = mapper; this.agents = agents;
        this.credentials = credentials; this.simulators = simulators;
    }

    @TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)
    public void enqueue(DeviceOnboardingRequestedEvent event) {
        executor.submit(() -> onboard(event));
    }

    @org.springframework.context.event.EventListener(org.springframework.boot.context.event.ApplicationReadyEvent.class)
    public void recoverInterrupted() {
        mapper.failInterruptedOnboarding();
    }

    void onboard(DeviceOnboardingRequestedEvent event) {
        Device device = null;
        try {
            device = requireActive(event.deviceCode());
            state(device, "STARTING", "正在下发令牌并启动仿真进程");
            simulators.restart(device, credentials.tokenFor(device));
            state(device, "CONNECTING", "正在验证设备身份与健康状态");
            long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(60);
            RuntimeException lastFailure = null;
            boolean connected = false;
            while (System.nanoTime() < deadline) {
                requireActive(event.deviceCode());
                if (!simulators.isAlive(event.deviceCode())) throw new IllegalStateException("仿真进程已退出，请检查仿真日志");
                try { devices.checkConnectionReadiness(device); connected = true; break; }
                catch (RuntimeException ex) { lastFailure = ex; }
                Thread.sleep(500);
            }
            if (!connected) throw new IllegalStateException(lastFailure == null ? "仿真连接超时" : lastFailure.getMessage());
            device = devices.testConnectionByCode(event.deviceCode(), event.operator());
            if (!"PASSED".equals(device.getConnectionTestStatus())) throw new IllegalStateException(device.getConnectionTestResult());
            requireActive(event.deviceCode());
            state(device, "BINDING", "连接通过，正在创建或绑定代理并等待真实心跳");
            LocalDateTime bindingStarted = LocalDateTime.now();
            DeviceAgent agent = devices.createAgentByCode(event.deviceCode(), event.operator());
            long reportDeadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(device.getStatusReportInterval() + 15L);
            while (System.nanoTime() < reportDeadline) {
                requireActive(event.deviceCode());
                DeviceAgent reported = agents.findById(agent.getId()).orElseThrow();
                if ("ENABLED".equals(reported.getAgentStatus()) && "ONLINE".equals(reported.getOnlineStatus())
                        && reported.getLastReportedAt() != null && !reported.getLastReportedAt().isBefore(bindingStarted)) {
                    state(device, "READY", "令牌已下发，仿真体已连接并绑定代理，真实心跳已确认");
                    return;
                }
                Thread.sleep(250);
            }
            throw new IllegalStateException("连接测试已通过，但代理绑定或心跳确认超时；请检查平台回调地址后重试");
        } catch (Exception ex) {
            if (ex instanceof InterruptedException) Thread.currentThread().interrupt();
            if (device != null) {
                String reason = ex.getMessage() == null ? "自动接入失败，请重试" : ex.getMessage();
                reason = com.airport.ai.task.SceneParamsPrivacyGuard.sanitizeText(reason);
                state(device, "FAILED", reason.substring(0, Math.min(reason.length(), 512)));
            }
        }
    }

    private Device requireActive(String code) {
        Device device = devices.getByCode(code);
        if (!"ACTIVE".equals(device.getDeviceStatus())) {
            simulators.stop(code);
            throw new IllegalStateException("设备已停用或删除，自动接入已停止");
        }
        return device;
    }

    private void state(Device device, String status, String message) {
        mapper.updateOnboarding(device.getId(), status, message);
    }

    @PreDestroy
    public void close() {
        executor.shutdownNow();
        try { executor.awaitTermination(5, TimeUnit.SECONDS); }
        catch (InterruptedException ex) { Thread.currentThread().interrupt(); }
    }
}
