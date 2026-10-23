package com.airport.ai.device;

import com.airport.ai.auth.OperationLogService;
import com.airport.ai.auth.User;
import com.airport.ai.common.BusinessException;
import com.airport.ai.common.ErrorCode;
import com.airport.ai.device.dto.StatusReportRequest;
import com.airport.ai.common.PageResult;
import com.airport.ai.event.TaskEventService;
import com.airport.ai.task.TaskExceptionService;
import com.github.pagehelper.PageHelper;
import com.github.pagehelper.PageInfo;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;

/**
 * 对应5.2.2设备代理生命周期管理、5.2.3设备状态上报与离线判断
 */
@Service
public class DeviceAgentService {

    private final DeviceAgentMapper deviceAgentMapper;
    private final DeviceMapper deviceMapper;
    private final OperationLogService operationLogService;
    private final TaskEventService taskEventService;
    private final DeviceEventService deviceEventService;
    private final TaskExceptionService taskExceptionService;

    public DeviceAgentService(DeviceAgentMapper deviceAgentMapper,
                               DeviceMapper deviceMapper,
                               OperationLogService operationLogService,
                               TaskEventService taskEventService,
                               DeviceEventService deviceEventService,
                               TaskExceptionService taskExceptionService) {
        this.deviceAgentMapper = deviceAgentMapper;
        this.deviceMapper = deviceMapper;
        this.operationLogService = operationLogService;
        this.taskEventService = taskEventService;
        this.deviceEventService = deviceEventService;
        this.taskExceptionService = taskExceptionService;
    }

    public PageResult<DeviceAgent> list(String agentStatus, String onlineStatus, int page, int size) {
        PageHelper.startPage(page, size);
        java.util.List<DeviceAgent> result = deviceAgentMapper.searchPaged(
                (agentStatus == null || agentStatus.isBlank()) ? null : agentStatus,
                (onlineStatus == null || onlineStatus.isBlank()) ? null : onlineStatus);
        return PageResult.of(new PageInfo<>(result));
    }

    public DeviceAgent get(Long agentId) {
        return deviceAgentMapper.findById(agentId)
                .orElseThrow(() -> new BusinessException(ErrorCode.DEVICE_AGENT_NOT_FOUND));
    }

    public DeviceAgent getByCode(String agentCode) {
        return deviceAgentMapper.findByAgentCode(agentCode)
                .orElseThrow(() -> new BusinessException(ErrorCode.DEVICE_AGENT_NOT_FOUND));
    }

    public Device getDeviceOf(DeviceAgent agent) {
        return deviceMapper.findById(agent.getDeviceId())
                .orElseThrow(() -> new BusinessException(ErrorCode.DEVICE_NOT_FOUND));
    }

    public void disableByCode(String agentCode, boolean confirmed, User operator) {
        disable(getByCode(agentCode).getId(), confirmed, operator);
    }

    /**
     * 停用代理需二次确认（对应附录B 6.3.3节confirmed标记）。若存在占用中的任务步骤，
     * 先按5.5.3异常恢复流程处理再释放占用（对应5.2.2业务规则5）——本模块记录待处理事件，
     * 实际候选切换/重新规划判断属于5.5执行监督模块职责，此处仅确保停用前置条件与占用释放动作完整。
     */
    @Transactional
    public void disable(Long agentId, boolean confirmed, User operator) {
        if (!confirmed) {
            throw new BusinessException(ErrorCode.PARAM_MISSING, "请二次确认停用操作");
        }
        DeviceAgent agent = get(agentId);
        if ("ARCHIVED".equals(agent.getAgentStatus())) {
            throw new BusinessException(ErrorCode.DEVICE_AGENT_NOT_FOUND, "代理已归档，不可再次停用");
        }
        if (agent.getCurrentTaskId() != null) {
            taskEventService.append(agent.getCurrentTaskId(), "AGENT_DISABLED_WITH_OCCUPATION", "OPERATOR",
                    null, "设备代理" + agent.getAgentCode() + "在占用任务步骤期间被手动停用，待5.5异常恢复流程处理占用释放");
        }
        agent.setAgentStatus("DISABLED");
        agent.setOnlineStatus("OFFLINE");
        deviceAgentMapper.update(agent);
        deviceEventService.append(agent.getId(), "AGENT_DISABLED", "OPERATOR", null,
                "配置管理员" + operator.getUsername() + "停用了设备代理" + agent.getAgentCode());
        operationLogService.record(operator.getId(), operator.getUsername(), operator.getRole(),
                "DEVICE_AGENT_DISABLE", agent.getAgentCode(), "SUCCESS", null);
    }

    /**
     * 设备/仿真体状态上报入口（对应5.2.3业务规则1）。格式非法时丢弃并记录格式异常事件，
     * 不影响在线判断之外的业务状态（业务规则8）——即上报失败不会把代理错误地标记为在线或离线，
     * 只是简单丢弃本次数据，在线状态仍由心跳超时任务统一判断。
     */
    @Transactional
    public void reportStatus(String deviceCode, StatusReportRequest request) {
        Device device = deviceMapper.findByDeviceCode(deviceCode)
                .orElseThrow(() -> new BusinessException(ErrorCode.DEVICE_NOT_FOUND));
        DeviceAgent agent = deviceAgentMapper.findByDeviceId(device.getId())
                .orElseThrow(() -> new BusinessException(ErrorCode.DEVICE_AGENT_NOT_FOUND));

        reportStatus(agent, device, "ONLINE", request.getWorkStatus(), request.getPositionX(), request.getPositionY());
    }

    @Transactional
    public void reportStatus(String agentCode, String onlineStatus, String workStatus,
                             java.math.BigDecimal positionX, java.math.BigDecimal positionY) {
        reportStatus(agentCode, onlineStatus, workStatus, positionX, positionY, null);
    }

    @Transactional
    public void reportStatus(String agentCode, String onlineStatus, String workStatus,
                             java.math.BigDecimal positionX, java.math.BigDecimal positionY, String businessStatus) {
        DeviceAgent agent = getByCode(agentCode);
        Device device = getDeviceOf(agent);
        reportStatus(agent, device, onlineStatus, workStatus, positionX, positionY, businessStatus);
    }

    private void reportStatus(DeviceAgent agent, Device device, String onlineStatus, String workStatus,
                              java.math.BigDecimal positionX, java.math.BigDecimal positionY) {
        reportStatus(agent, device, onlineStatus, workStatus, positionX, positionY, null);
    }

    private void reportStatus(DeviceAgent agent, Device device, String onlineStatus, String workStatus,
                              java.math.BigDecimal positionX, java.math.BigDecimal positionY, String businessStatus) {
        if (!"ENABLED".equals(agent.getAgentStatus())) {
            throw new BusinessException(ErrorCode.DEVICE_AGENT_NOT_FOUND, "设备代理未启用");
        }
        if (!"ONLINE".equals(onlineStatus) && !"OFFLINE".equals(onlineStatus)) {
            throw new BusinessException(ErrorCode.PARAM_FORMAT_ERROR, "onlineStatus取值非法");
        }
        if (!"IDLE".equals(workStatus) && !"BUSY".equals(workStatus)) {
            // 格式非法：丢弃本次上报，记录格式异常事件，不改变在线状态（对应业务规则8）
            if (agent.getCurrentTaskId() != null) {
                taskEventService.append(agent.getCurrentTaskId(), "STATUS_REPORT_FORMAT_INVALID", "SYSTEM",
                        "ERR_INVALID_FORMAT", "设备" + device.getDeviceCode() + "上报workStatus取值非法: " + workStatus);
            }
            throw new BusinessException(ErrorCode.PARAM_FORMAT_ERROR, "workStatus取值非法");
        }

        boolean wasOffline = "OFFLINE".equals(agent.getOnlineStatus());
        agent.setOnlineStatus(onlineStatus);
        agent.setWorkStatus(workStatus);
        if (businessStatus != null) agent.setBusinessStatus(businessStatus);
        agent.setLastReportedAt(LocalDateTime.now());
        deviceAgentMapper.update(agent);

        if (positionX != null && positionY != null) {
            device.setPositionX(positionX);
            device.setPositionY(positionY);
            deviceMapper.update(device);
        }

        if ("OFFLINE".equals(onlineStatus) && !wasOffline) {
            deviceEventService.append(agent.getId(), "AGENT_OFFLINE_REPORTED", "SYSTEM",
                    "DEVICE_REPORTED_OFFLINE", "设备代理" + agent.getAgentCode() + "主动上报离线");
            if (agent.getCurrentTaskId() != null) taskExceptionService.handleAgentOffline(agent);
            return;
        }

        // 离线恢复上报后自动置为在线并重新纳入候选集合，恢复事件写入设备事件（对应5.2.3业务规则7、TC_DEVICE_004）
        if (wasOffline) {
            deviceEventService.append(agent.getId(), "AGENT_ONLINE_RECOVERED", "SYSTEM",
                    null, "设备代理" + agent.getAgentCode() + "恢复上报，重新置为在线并纳入候选集合");
            if (agent.getCurrentTaskId() != null) {
                taskEventService.append(agent.getCurrentTaskId(), "AGENT_ONLINE_RECOVERED", "SYSTEM",
                        null, "设备代理" + agent.getAgentCode() + "恢复上报，重新置为在线并纳入候选集合");
            }
        }
    }
}
