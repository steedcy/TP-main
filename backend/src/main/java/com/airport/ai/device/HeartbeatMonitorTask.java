package com.airport.ai.device;

import com.airport.ai.event.TaskEventService;
import com.airport.ai.task.TaskExceptionService;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.util.List;

/**
 * 对应5.2.3设备状态上报与离线判断：心跳超时默认30秒（可配置10~120秒），
 * 超时后标记离线、退出候选集合（online_status=OFFLINE即天然退出候选池，因规划上下文查询只取ONLINE代理），
 * 并无条件生成离线异常事件（对应业务规则2）；若代理正占用某任务步骤，额外写入该任务的事件时间线
 * 供5.5异常恢复流程判断"是否可继续"（对应业务规则5、6）。
 */
@Component
public class HeartbeatMonitorTask {

    private final DeviceAgentMapper deviceAgentMapper;
    private final DeviceEventService deviceEventService;
    private final TaskEventService taskEventService;
    private final TaskExceptionService taskExceptionService;
    private final int heartbeatTimeoutSeconds;
    /** 配置管理员可调的阈值（10~120秒，DEF-S3-015）；未注入时回退到启动配置 */
    @org.springframework.beans.factory.annotation.Autowired(required = false)
    private HeartbeatSettingService heartbeatSettingService;

    public HeartbeatMonitorTask(DeviceAgentMapper deviceAgentMapper,
                                 DeviceEventService deviceEventService,
                                 TaskEventService taskEventService,
                                 TaskExceptionService taskExceptionService,
                                 @Value("${app.device.heartbeat-timeout-seconds:30}") int heartbeatTimeoutSeconds) {
        this.deviceAgentMapper = deviceAgentMapper;
        this.deviceEventService = deviceEventService;
        this.taskEventService = taskEventService;
        this.taskExceptionService = taskExceptionService;
        this.heartbeatTimeoutSeconds = heartbeatTimeoutSeconds;
    }

    @Scheduled(fixedRate = 10000)
    public void checkHeartbeatTimeout() {
        int timeoutSeconds = heartbeatSettingService == null ? heartbeatTimeoutSeconds : heartbeatSettingService.timeoutSeconds();
        LocalDateTime threshold = LocalDateTime.now().minusSeconds(timeoutSeconds);
        List<DeviceAgent> timedOut = deviceAgentMapper.findByOnlineStatusAndLastReportedAtBefore("ONLINE", threshold);
        for (DeviceAgent agent : timedOut) {
            agent.setOnlineStatus("OFFLINE");
            deviceAgentMapper.update(agent);

            deviceEventService.append(agent.getId(), "AGENT_OFFLINE_DETECTED", "SYSTEM",
                    "ERR_HEARTBEAT_TIMEOUT",
                    "设备代理" + agent.getAgentCode() + "超过" + timeoutSeconds + "秒未上报，判定离线");

            if (agent.getCurrentTaskId() != null) {
                taskEventService.append(agent.getCurrentTaskId(), "AGENT_OFFLINE_DETECTED", "SYSTEM",
                        "ERR_HEARTBEAT_TIMEOUT",
                        "设备代理" + agent.getAgentCode() + "心跳超时，判定离线，待5.5异常恢复流程判断是否影响任务");
            }
            // 对应5.5.3业务规则2/5：仅当离线设备正占用某任务步骤才触发异常恢复流程；
            // 未占用或占用其他已终止任务的离线仅记录设备事件，不触发任何流程（TaskExceptionService内部判断）
            taskExceptionService.handleAgentOffline(agent);
        }
    }
}
