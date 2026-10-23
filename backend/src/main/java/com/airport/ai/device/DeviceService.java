package com.airport.ai.device;

import com.airport.ai.auth.OperationLogService;
import com.airport.ai.auth.User;
import com.airport.ai.common.BusinessException;
import com.airport.ai.common.ErrorCode;
import com.airport.ai.device.dto.CreateDeviceRequest;
import com.airport.ai.device.dto.UpdateDeviceRequest;
import com.airport.ai.common.PageResult;
import com.github.pagehelper.PageHelper;
import com.github.pagehelper.PageInfo;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.UUID;

/**
 * 对应5.2.1设备档案与连接测试、5.2.2设备代理生命周期管理。接入总量上限为TBD-01拍板结论：
 * 演示配置≤10，系统性能设计上限≤20，做成可配置项而非硬编码常量。
 */
@Service
public class DeviceService {

    private final DeviceMapper deviceMapper;
    private final DeviceAgentMapper deviceAgentMapper;
    private final OperationLogService operationLogService;
    private final DeviceEventService deviceEventService;
    private final DeviceAdapterClient deviceAdapterClient;
    private final ApplicationEventPublisher eventPublisher;
    private final int maxAccessObjectsSystem;

    public DeviceService(DeviceMapper deviceMapper,
                          DeviceAgentMapper deviceAgentMapper,
                          OperationLogService operationLogService,
                          DeviceEventService deviceEventService,
                          DeviceAdapterClient deviceAdapterClient,
                          ApplicationEventPublisher eventPublisher,
                          @Value("${app.device.max-access-objects-system:20}") int maxAccessObjectsSystem) {
        this.deviceMapper = deviceMapper;
        this.deviceAgentMapper = deviceAgentMapper;
        this.operationLogService = operationLogService;
        this.deviceEventService = deviceEventService;
        this.deviceAdapterClient = deviceAdapterClient;
        this.eventPublisher = eventPublisher;
        this.maxAccessObjectsSystem = maxAccessObjectsSystem;
    }

    @Transactional
    public Device create(CreateDeviceRequest request, User operator) {
        if (deviceMapper.existsByDeviceCode(request.getDeviceCode())) {
            throw new BusinessException(ErrorCode.DEVICE_CODE_TAKEN);
        }
        // 接入总量上限（对应5.2.1业务规则5、TBD-01拍板结论），按系统性能设计上限校验，可配置，已删除设备不计入
        long currentCount = deviceMapper.countByDeviceStatusNot("DELETED");
        if (currentCount >= maxAccessObjectsSystem) {
            throw new BusinessException(ErrorCode.ACCESS_OBJECT_LIMIT_EXCEEDED,
                    "接入对象数量已达上限(" + maxAccessObjectsSystem + ")");
        }
        // 仿真体必须指定所模拟的设备类型（对应5.2.1业务规则4）
        if (Boolean.TRUE.equals(request.getIsSimulator())) {
            if (!"SIMULATOR".equals(request.getDeviceTypeCode())) {
                throw new BusinessException(ErrorCode.PARAM_FORMAT_ERROR, "仿真设备档案的deviceTypeCode必须为SIMULATOR");
            }
            String simulatedType = request.getSimulatedDeviceType();
            if (simulatedType == null || !java.util.Set.of("SMART_DISPLAY", "BAGGAGE_SCANNER",
                    "FLIGHT_DELAY_BOARD", "MOBILE_ROBOT").contains(simulatedType)) {
                throw new BusinessException(ErrorCode.PARAM_FORMAT_ERROR,
                        "仿真设备必须指定有效的simulatedDeviceType");
            }
        } else if ("SIMULATOR".equals(request.getDeviceTypeCode())) {
            throw new BusinessException(ErrorCode.PARAM_FORMAT_ERROR, "SIMULATOR类型档案必须标记为仿真设备");
        }

        Device device = new Device();
        device.setDeviceCode(request.getDeviceCode());
        device.setDeviceName(request.getDeviceName());
        device.setDeviceTypeCode(request.getDeviceTypeCode());
        device.setIsSimulator(Boolean.TRUE.equals(request.getIsSimulator()));
        device.setSimulatedDeviceType(request.getSimulatedDeviceType());
        device.setAreaCode(request.getAreaCode());
        device.setPositionX(request.getPositionX());
        device.setPositionY(request.getPositionY());
        device.setAccessEndpoint(request.getAccessEndpoint());
        device.setAccessCredentialRef(request.getAccessCredentialRef());
        device.setStatusReportInterval(request.getStatusReportInterval());
        device.setRemark(request.getRemark());
        device.setCreatedBy(operator.getUsername());
        device.setUpdatedBy(operator.getUsername());
        deviceMapper.insert(device);
        Device saved = device;

        java.util.Map<String, Object> detail = new java.util.HashMap<>();
        detail.put("deviceName", saved.getDeviceName());
        detail.put("deviceTypeCode", saved.getDeviceTypeCode());
        detail.put("accessEndpoint", saved.getAccessEndpoint());
        detail.put("accessCredentialRef", saved.getAccessCredentialRef());
        operationLogService.record(operator.getId(), operator.getUsername(), operator.getRole(),
                "DEVICE_CREATE", saved.getDeviceCode(), "SUCCESS", null, detail);
        return saved;
    }

    public PageResult<Device> list(String deviceTypeCode, String onlineFilter, String keyword, int page, int size) {
        PageHelper.startPage(page, size);
        java.util.List<Device> result = deviceMapper.searchPaged(
                (deviceTypeCode == null || deviceTypeCode.isBlank()) ? null : deviceTypeCode,
                (keyword == null || keyword.isBlank()) ? null : keyword);
        return PageResult.of(new PageInfo<>(result));
    }

    public Device get(Long deviceId) {
        return deviceMapper.findById(deviceId)
                .orElseThrow(() -> new BusinessException(ErrorCode.DEVICE_NOT_FOUND));
    }

    public Device getByCode(String deviceCode) {
        return deviceMapper.findByDeviceCode(deviceCode)
                .orElseThrow(() -> new BusinessException(ErrorCode.DEVICE_NOT_FOUND));
    }

    public Device updateByCode(String deviceCode, UpdateDeviceRequest request, User operator) {
        return update(getByCode(deviceCode).getId(), request, operator);
    }

    public Device testConnectionByCode(String deviceCode, User operator) {
        return testConnection(getByCode(deviceCode).getId(), operator);
    }

    public void updateStatusByCode(String deviceCode, String status, User operator) {
        updateStatus(getByCode(deviceCode).getId(), status, operator);
    }

    public void deleteByCode(String deviceCode, User operator) {
        delete(getByCode(deviceCode).getId(), operator);
    }

    @Transactional
    public DeviceAgent createAgentByCode(String deviceCode, User operator) {
        return createAgent(getByCode(deviceCode).getId(), operator);
    }

    /** 修改接入参数（接口地址或凭据标识）后连接测试结果重置为未测试（对应5.2.1备选路径3a） */
    @Transactional
    public Device update(Long deviceId, UpdateDeviceRequest request, User operator) {
        Device device = get(deviceId);
        boolean credentialChanged = request.getAccessCredentialRef() != null
                && !request.getAccessCredentialRef().isBlank()
                && !device.getAccessCredentialRef().equals(request.getAccessCredentialRef());
        boolean endpointChanged = !device.getAccessEndpoint().equals(request.getAccessEndpoint());

        device.setDeviceName(request.getDeviceName());
        device.setAreaCode(request.getAreaCode());
        device.setPositionX(request.getPositionX());
        device.setPositionY(request.getPositionY());
        device.setAccessEndpoint(request.getAccessEndpoint());
        if (credentialChanged) {
            device.setAccessCredentialRef(request.getAccessCredentialRef());
        }
        device.setStatusReportInterval(request.getStatusReportInterval());
        device.setRemark(request.getRemark());
        device.setUpdatedBy(operator.getUsername());
        device.setUpdatedAt(java.time.LocalDateTime.now());

        // 修改接入参数（接口地址或凭据）后连接测试结果重置为未测试（对应5.2.1备选路径3a）
        if (endpointChanged || credentialChanged) {
            device.setConnectionTestStatus("UNTESTED");
            device.setConnectionTestResult(null);
        }

        deviceMapper.update(device);
        Device saved = device;
        java.util.Map<String, Object> detail = new java.util.HashMap<>();
        detail.put("deviceName", saved.getDeviceName());
        detail.put("accessEndpoint", saved.getAccessEndpoint());
        detail.put("accessCredentialRef", saved.getAccessCredentialRef());
        detail.put("credentialChanged", credentialChanged);
        operationLogService.record(operator.getId(), operator.getUsername(), operator.getRole(),
                "DEVICE_UPDATE", saved.getDeviceCode(), "SUCCESS", null, detail);
        return saved;
    }

    /** Validate identity and one valid state snapshot from the configured device endpoint. */
    @Transactional
    public Device testConnection(Long deviceId, User operator) {
        Device device = get(deviceId);
        if ("INACTIVE".equals(device.getDeviceStatus())) {
            throw new BusinessException(ErrorCode.DEVICE_NOT_FOUND, "设备已停用，请先启用后再测试");
        }
        try {
            var health = deviceAdapterClient.testConnection(device);
            device.setPositionX(health.getLocation().getX());
            device.setPositionY(health.getLocation().getY());
            device.setConnectionTestStatus("PASSED");
            device.setConnectionTestResult("身份、协议版本及状态快照校验通过");
        } catch (RuntimeException ex) {
            device.setConnectionTestStatus("FAILED");
            device.setConnectionTestResult(ex.getMessage() == null ? "设备连接测试失败" : ex.getMessage());
        }
        deviceMapper.update(device);
        Device saved = device;
        operationLogService.record(operator.getId(), operator.getUsername(), operator.getRole(),
                "DEVICE_CONNECTION_TEST", saved.getDeviceCode(), saved.getConnectionTestStatus().equals("PASSED") ? "SUCCESS" : "FAILED", null);
        return saved;
    }

    /** 创建设备代理前置要求连接测试通过（对应5.2.1规则2），一设备仅对应一启用代理（对应5.2.2规则1） */
    @Transactional
    public DeviceAgent createAgent(Long deviceId, User operator) {
        Device device = get(deviceId);
        if (!"PASSED".equals(device.getConnectionTestStatus())) {
            throw new BusinessException(ErrorCode.DEVICE_CONNECTION_TEST_FAILED);
        }
        // 设备已存在启用代理时不重复创建，仅刷新代理绑定信息（对应5.2.2备选路径2a）
        DeviceAgent agent = deviceAgentMapper.findByDeviceId(deviceId)
                .map(existing -> {
                    if ("ARCHIVED".equals(existing.getAgentStatus())) {
                        throw new BusinessException(ErrorCode.DEVICE_AGENT_ALREADY_EXISTS,
                                "设备代理已归档，归档后不可恢复");
                    }
                    existing.setAgentStatus("ENABLED");
                    deviceAgentMapper.update(existing);
                    return existing;
                })
                .orElseGet(() -> {
                    DeviceAgent createdAgent = new DeviceAgent();
                    createdAgent.setAgentCode("AGT-" + UUID.randomUUID().toString().substring(0, 8).toUpperCase());
                    createdAgent.setDeviceId(deviceId);
                    deviceAgentMapper.insert(createdAgent);
                    DeviceAgent saved = createdAgent;
                    deviceEventService.append(saved.getId(), "AGENT_CREATED", "OPERATOR", null,
                            "配置管理员" + operator.getUsername() + "为设备" + device.getDeviceCode() + "创建启用代理");
                    operationLogService.record(operator.getId(), operator.getUsername(), operator.getRole(),
                            "DEVICE_AGENT_CREATE", saved.getAgentCode(), "SUCCESS", null);
                    return saved;
                });
        eventPublisher.publishEvent(new DeviceAgentBindingRequestedEvent(agent.getId()));
        return agent;
    }

    /**
     * 停用设备：同步停用其代理（对应5.2.1备选路径5a、5.2.2业务规则3）。
     * 代理停用前若存在占用中的任务步骤，按5.5.3异常恢复流程处理后再释放占用——本模块只做占用释放，
     * 真正的候选切换/重新规划判断属于5.5执行监督模块职责范围，此处先记录事件供该模块后续接管。
     */
    @Transactional
    public void updateStatus(Long deviceId, String status, User operator) {
        Device device = get(deviceId);
        device.setDeviceStatus(status);
        device.setUpdatedBy(operator.getUsername());
        device.setUpdatedAt(java.time.LocalDateTime.now());
        deviceMapper.update(device);

        if ("INACTIVE".equals(status)) {
            deviceAgentMapper.findByDeviceId(deviceId).ifPresent(agent -> {
                if (!"ARCHIVED".equals(agent.getAgentStatus())) {
                    agent.setAgentStatus("DISABLED");
                    agent.setOnlineStatus("OFFLINE");
                    deviceAgentMapper.update(agent);
                    deviceEventService.append(agent.getId(), "AGENT_DISABLED", "OPERATOR", null,
                            "设备" + device.getDeviceCode() + "被停用，代理同步停用（对应5.2.1备选路径5a）");
                }
            });
        }
        operationLogService.record(operator.getId(), operator.getUsername(), operator.getRole(),
                "DEVICE_STATUS_CHANGE", device.getDeviceCode() + " -> " + status, "SUCCESS", null);
    }

    /**
     * 存在进行中任务（待分配、降级执行中、执行中）的设备不得删除（对应5.2.1业务规则6）。
     * 以设备代理当前占用（current_task_id非空）作为判断依据：占用中即代理正服务于某个尚未
     * 完成/失败/终止的任务步骤，与"待分配/降级执行中/执行中"三种进行中任务状态是同一回事的另一面。
     *
     * 实现为逻辑删除而非物理DELETE：5.2.2业务规则"代理归档后不可恢复，仅保留历史记录"要求
     * device_agents记录不能物理消失，而device_agents.device_id对devices.id有外键约束，
     * 物理删除devices记录会与"保留代理历史记录"这一要求直接冲突（违反外键约束）。
     * 故删除动作实为device_status置为DELETED的软删除，列表查询按需过滤即可。
     */
    @Transactional
    public void delete(Long deviceId, User operator) {
        Device device = get(deviceId);
        deviceAgentMapper.findByDeviceId(deviceId).ifPresent(agent -> {
            if (agent.getCurrentTaskId() != null) {
                throw new BusinessException(ErrorCode.DEVICE_HAS_ACTIVE_TASK);
            }
            agent.setAgentStatus("ARCHIVED");
            agent.setOnlineStatus("OFFLINE");
            deviceAgentMapper.update(agent);
            deviceEventService.append(agent.getId(), "AGENT_ARCHIVED", "OPERATOR", null,
                    "设备" + device.getDeviceCode() + "被删除，代理同步归档，不可恢复");
        });
        device.setDeviceStatus("DELETED");
        device.setUpdatedBy(operator.getUsername());
        device.setUpdatedAt(java.time.LocalDateTime.now());
        deviceMapper.update(device);
        operationLogService.record(operator.getId(), operator.getUsername(), operator.getRole(),
                "DEVICE_DELETE", device.getDeviceCode(), "SUCCESS", null);
    }
}
