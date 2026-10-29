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
    private final DeviceCapabilityMapper deviceCapabilityMapper;
    private final com.airport.ai.task.TaskExceptionService taskExceptionService;
    private final java.util.Set<String> presetAreas;
    private final com.airport.ai.devicetype.CapabilityTemplateMapper capabilityTemplateMapper;

    public DeviceService(DeviceMapper deviceMapper,
                          DeviceAgentMapper deviceAgentMapper,
                          OperationLogService operationLogService,
                          DeviceEventService deviceEventService,
                          DeviceAdapterClient deviceAdapterClient,
                          ApplicationEventPublisher eventPublisher,
                          @Value("${app.device.max-access-objects-system:20}") int maxAccessObjectsSystem,
                          DeviceCapabilityMapper deviceCapabilityMapper,
                          @org.springframework.context.annotation.Lazy com.airport.ai.task.TaskExceptionService taskExceptionService,
                          @Value("${app.device.preset-areas:F2_TEST}") String presetAreas,
                          com.airport.ai.devicetype.CapabilityTemplateMapper capabilityTemplateMapper) {
        this.capabilityTemplateMapper = capabilityTemplateMapper;
        this.deviceCapabilityMapper = deviceCapabilityMapper;
        this.taskExceptionService = taskExceptionService;
        this.presetAreas = java.util.Arrays.stream(presetAreas.split(",")).map(String::trim)
                .filter(v -> !v.isEmpty()).collect(java.util.stream.Collectors.toCollection(java.util.LinkedHashSet::new));
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
            throw new BusinessException(ErrorCode.DEVICE_CODE_TAKEN, "设备编码已存在：" + request.getDeviceCode());
        }
        requirePresetArea(request.getAreaCode());
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
        if (Boolean.TRUE.equals(saved.getIsSimulator())) {
            loadSimulatorProfile(saved);
        }

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
                (keyword == null || keyword.isBlank()) ? null : keyword,
                (onlineFilter == null || onlineFilter.isBlank()) ? null : onlineFilter);
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

        if (!java.util.Objects.equals(device.getAreaCode(), request.getAreaCode())) {
            requirePresetArea(request.getAreaCode());
        }
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
        if ("DELETED".equals(device.getDeviceStatus())) {
            throw new BusinessException(ErrorCode.DEVICE_NOT_FOUND, "设备已删除，不可测试");
        }
        long startedAt = System.nanoTime();
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
        device.setConnectionTestDurationMs((System.nanoTime() - startedAt) / 1_000_000L);
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
                    boolean wasDisabled = "DISABLED".equals(existing.getAgentStatus());
                    existing.setAgentStatus("ENABLED");
                    deviceAgentMapper.update(existing);
                    if (wasDisabled) {
                        deviceEventService.append(existing.getId(), "AGENT_ENABLED", "OPERATOR", null,
                                "配置管理员" + operator.getUsername() + "重新启用设备代理" + existing.getAgentCode());
                        operationLogService.record(operator.getId(), operator.getUsername(), operator.getRole(),
                                "DEVICE_AGENT_ENABLE", existing.getAgentCode(), "SUCCESS", null);
                    }
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
        if ("ACTIVE".equals(status) && "INACTIVE".equals(device.getDeviceStatus())
                && !"PASSED".equals(device.getConnectionTestStatus())) {
            throw new BusinessException(ErrorCode.DEVICE_CONNECTION_TEST_FAILED, "启用前须连接测试通过");
        }
        if ("INACTIVE".equals(status)) {
            releaseAgentOccupation(device);
        }
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
        if ("ACTIVE".equals(status)) {
            deviceAgentMapper.findByDeviceId(deviceId).ifPresent(agent -> {
                if ("DISABLED".equals(agent.getAgentStatus())) {
                    agent.setAgentStatus("ENABLED");
                    deviceAgentMapper.update(agent);
                    deviceEventService.append(agent.getId(), "AGENT_ENABLED", "OPERATOR", null,
                            "设备" + device.getDeviceCode() + "重新启用，代理同步启用并恢复绑定");
                    operationLogService.record(operator.getId(), operator.getUsername(), operator.getRole(),
                            "DEVICE_AGENT_ENABLE", agent.getAgentCode(), "SUCCESS", null);
                    eventPublisher.publishEvent(new DeviceAgentBindingRequestedEvent(agent.getId()));
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
            if (agent.getCurrentTaskId() != null || deviceAgentMapper.countActiveTaskAssignments(agent.getId()) > 0) {
                throw new BusinessException(ErrorCode.DEVICE_HAS_ACTIVE_TASK);
            }
            agent.setAgentStatus("ARCHIVED");
            agent.setOnlineStatus("OFFLINE");
            deviceAgentMapper.update(agent);
            deviceEventService.append(agent.getId(), "AGENT_ARCHIVED", "OPERATOR", null,
                    "设备" + device.getDeviceCode() + "被删除，代理同步归档，不可恢复");
            operationLogService.record(operator.getId(), operator.getUsername(), operator.getRole(),
                    "DEVICE_AGENT_ARCHIVE", agent.getAgentCode(), "SUCCESS", null);
        });
        device.setDeviceStatus("DELETED");
        device.setUpdatedBy(operator.getUsername());
        device.setUpdatedAt(java.time.LocalDateTime.now());
        deviceMapper.update(device);
        operationLogService.record(operator.getId(), operator.getUsername(), operator.getRole(),
                "DEVICE_DELETE", device.getDeviceCode(), "SUCCESS", null);
    }

    private void requirePresetArea(String areaCode) {
        if (areaCode == null || !presetAreas.contains(areaCode)) {
            throw new BusinessException(ErrorCode.PARAM_FORMAT_ERROR,
                    "所属区域须为预置区域：" + String.join("、", presetAreas));
        }
    }

    public java.util.Set<String> presetAreas() {
        return presetAreas;
    }

    /**
     * 仿真体能力画像加载（SRS_F003.R04、5.2.4A业务规则4）：继承所模拟设备类型的全部启用标准能力模板，
     * 并加载仿真状态生成能力。均为未测试，须逐项能力测试通过后才可启用。幂等，返回新增能力数。
     */
    int loadSimulatorProfile(Device device) {
        int added = 0;
        loadSimulatorStatusCapability(device);
        if (device.getSimulatedDeviceType() == null) return added;
        for (com.airport.ai.devicetype.CapabilityTemplate t
                : capabilityTemplateMapper.findByDeviceTypeCode(device.getSimulatedDeviceType())) {
            if (!"ACTIVE".equals(t.getTemplateStatus())
                    || deviceCapabilityMapper.existsByDeviceIdAndCapabilityCode(device.getId(), t.getTemplateCode())) {
                continue;
            }
            DeviceCapability c = new DeviceCapability();
            c.setDeviceId(device.getId());
            c.setTemplateId(t.getId());
            c.setCapabilityCode(t.getTemplateCode());
            c.setCapabilityName(t.getTemplateName());
            c.setCapabilityType(t.getCapabilityType());
            c.setInputParams(t.getInputParams());
            c.setOutputParams(t.getOutputParams());
            c.setCapabilityDescription(t.getTemplateDescription());
            deviceCapabilityMapper.insert(c);
            t.setUsageCount((t.getUsageCount() == null ? 0 : t.getUsageCount()) + 1);
            capabilityTemplateMapper.update(t);
            added++;
        }
        return added;
    }

    /** 对既有仿真体重新加载继承能力（可重复，仅补缺），供配置管理员使用并留操作记录 */
    @Transactional
    public int reloadSimulatorProfile(String deviceCode, User operator) {
        Device device = getByCode(deviceCode);
        if (!Boolean.TRUE.equals(device.getIsSimulator())) {
            throw new BusinessException(ErrorCode.PARAM_FORMAT_ERROR, "仅仿真体可加载继承能力画像");
        }
        int added = loadSimulatorProfile(device);
        operationLogService.record(operator.getId(), operator.getUsername(), operator.getRole(),
                "DEVICE_PROFILE_RELOAD", device.getDeviceCode() + " +" + added, "SUCCESS", null);
        return added;
    }

    /** 仿真体加载仿真状态生成能力（SRS_F003.R04、DEF-S3-020），初始为未测试，须能力测试通过后才可启用 */
    void loadSimulatorStatusCapability(Device device) {
        if (deviceCapabilityMapper.existsByDeviceIdAndCapabilityCode(device.getId(), "CAP_SIM_STATUS")) {
            return;
        }
        DeviceCapability capability = new DeviceCapability();
        capability.setDeviceId(device.getId());
        capability.setCapabilityCode("CAP_SIM_STATUS");
        capability.setCapabilityName("仿真状态生成");
        capability.setCapabilityType("CAP_SIM_STATUS");
        capability.setInputParams("[]");
        capability.setOutputParams("[]");
        capability.setCapabilityDescription("仿真体生成并上报模拟设备状态");
        deviceCapabilityMapper.insert(capability);
    }

    /**
     * 停用设备时先释放代理占用（SRS_F003.R06）：占用中的任务步骤按5.5.3异常恢复流程处理
     * （候选切换/重新规划/转人工），再清除代理占用并记录设备事件。
     */
    private void releaseAgentOccupation(Device device) {
        deviceAgentMapper.findByDeviceId(device.getId()).ifPresent(agent -> {
            if ("ARCHIVED".equals(agent.getAgentStatus())) return;
            Long taskId = agent.getCurrentTaskId();
            agent.setAgentStatus("DISABLED");
            agent.setOnlineStatus("OFFLINE");
            deviceAgentMapper.update(agent);
            // 占用以步骤关联为准：待分配阶段current_task_id可能仍为空，但关联已存在（DEF-S3-077）
            int released = taskExceptionService.handleAgentDisabled(agent);
            if (taskId != null || released > 0) {
                agent.setCurrentTaskId(null);
                agent.setCurrentStepSeq(null);
                agent.setWorkStatus("IDLE");
                deviceAgentMapper.update(agent);
                deviceEventService.append(agent.getId(), "AGENT_OCCUPATION_RELEASED", "OPERATOR", null,
                        "设备" + device.getDeviceCode() + "停用，已按异常恢复流程处理" + released + "个进行中步骤并释放占用");
            }
        });
    }
}
