package com.airport.ai.device;

import com.airport.ai.auth.OperationLogService;
import com.airport.ai.auth.User;
import com.airport.ai.common.BusinessException;
import com.airport.ai.common.ErrorCode;
import com.airport.ai.device.dto.CreateDeviceCapabilityRequest;
import com.airport.ai.device.dto.UpdateDeviceCapabilityRequest;
import com.airport.ai.devicetype.CapabilityTemplate;
import com.airport.ai.devicetype.CapabilityTemplateMapper;
import com.airport.ai.devicetype.DeviceTypeCapabilityService;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

/**
 * 对应5.2.4设备能力画像管理（实例层）。能力类型必须在5.2.4A设备类型能力边界支持范围内
 * （业务规则9），仿真体额外继承所模拟设备类型的能力（5.2.4A业务规则4）。
 */
@Service
public class DeviceCapabilityService {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private final DeviceCapabilityMapper deviceCapabilityMapper;
    private final DeviceMapper deviceMapper;
    private final CapabilityTemplateMapper capabilityTemplateMapper;
    private final DeviceTypeCapabilityService deviceTypeCapabilityService;
    private final OperationLogService operationLogService;
    private final DeviceAgentMapper agentMapper;
    private final DeviceAgentMessagingService messaging;

    public DeviceCapabilityService(DeviceCapabilityMapper deviceCapabilityMapper,
                                    DeviceMapper deviceMapper,
                                    CapabilityTemplateMapper capabilityTemplateMapper,
                                    DeviceTypeCapabilityService deviceTypeCapabilityService,
                                    OperationLogService operationLogService,
                                    DeviceAgentMapper agentMapper, DeviceAgentMessagingService messaging) {
        this.deviceCapabilityMapper = deviceCapabilityMapper;
        this.deviceMapper = deviceMapper;
        this.capabilityTemplateMapper = capabilityTemplateMapper;
        this.deviceTypeCapabilityService = deviceTypeCapabilityService;
        this.operationLogService = operationLogService;
        this.agentMapper = agentMapper;
        this.messaging = messaging;
    }

    public List<DeviceCapability> list(Long deviceId) {
        return deviceCapabilityMapper.findByDeviceId(deviceId);
    }

    public DeviceCapability get(Long deviceId, String capabilityCode) {
        return deviceCapabilityMapper.findByDeviceIdAndCapabilityCode(deviceId, capabilityCode)
                .orElseThrow(() -> new BusinessException(ErrorCode.CAPABILITY_CODE_TAKEN, "能力不存在"));
    }

    /**
     * 新增能力（对应5.2.4业务规则1、9，附录B 6.5节）。能力类型越界时拒绝保存并提示（异常路径2b），
     * 若基于标准能力模板创建，模板usage_count+1（模板停用状态不影响已引用它的能力）。
     */
    @Transactional
    public DeviceCapability create(Long deviceId, CreateDeviceCapabilityRequest request, User operator) {
        Device device = deviceMapper.findById(deviceId)
                .orElseThrow(() -> new BusinessException(ErrorCode.DEVICE_NOT_FOUND));
        if (deviceCapabilityMapper.existsByDeviceIdAndCapabilityCode(deviceId, request.getCapabilityCode())) {
            throw new BusinessException(ErrorCode.CAPABILITY_CODE_TAKEN);
        }
        if (!deviceTypeCapabilityService.isCapabilityTypeSupported(
                device.getDeviceTypeCode(), device.getSimulatedDeviceType(), request.getCapabilityType())) {
            throw new BusinessException(ErrorCode.CAPABILITY_OUT_OF_BOUNDARY);
        }

        DeviceCapability capability = new DeviceCapability();
        capability.setDeviceId(deviceId);
        capability.setCapabilityCode(request.getCapabilityCode());
        capability.setCapabilityName(request.getCapabilityName());
        capability.setCapabilityType(request.getCapabilityType());
        capability.setInputParams(writeParams(request.getInputParams()));
        capability.setOutputParams(writeParams(request.getOutputParams()));
        capability.setApplicableConditions(request.getApplicableCondition());
        capability.setCapabilityDescription(request.getCapabilityDescription());

        if (request.getTemplateId() != null) {
            CapabilityTemplate template = capabilityTemplateMapper.findById(request.getTemplateId())
                    .orElseThrow(() -> new BusinessException(ErrorCode.CAPABILITY_CODE_TAKEN, "标准能力模板不存在"));
            capability.setTemplateId(template.getId());
            template.setUsageCount((template.getUsageCount() == null ? 0 : template.getUsageCount()) + 1);
            capabilityTemplateMapper.update(template);
        }

        deviceCapabilityMapper.insert(capability);
        DeviceCapability saved = capability;
        operationLogService.record(operator.getId(), operator.getUsername(), operator.getRole(),
                "DEVICE_CAPABILITY_CREATE", device.getDeviceCode() + "/" + saved.getCapabilityCode(), "SUCCESS", null);
        return saved;
    }

    /** 修改输入输出参数时可用状态重置为未测试（对应业务规则5） */
    @Transactional
    public DeviceCapability update(Long deviceId, String capabilityCode, UpdateDeviceCapabilityRequest request, User operator) {
        DeviceCapability capability = get(deviceId, capabilityCode);
        capability.setCapabilityName(request.getCapabilityName());
        capability.setInputParams(writeParams(request.getInputParams()));
        capability.setOutputParams(writeParams(request.getOutputParams()));
        capability.setApplicableConditions(request.getApplicableCondition());
        capability.setCapabilityDescription(request.getCapabilityDescription());
        capability.setCapabilityStatus("UNTESTED");
        capability.setTestResult(null);
        capability.setUpdatedAt(LocalDateTime.now());
        deviceCapabilityMapper.update(capability);
        DeviceCapability saved = capability;

        Device device = deviceMapper.findById(deviceId).orElseThrow(() -> new BusinessException(ErrorCode.DEVICE_NOT_FOUND));
        operationLogService.record(operator.getId(), operator.getUsername(), operator.getRole(),
                "DEVICE_CAPABILITY_UPDATE", device.getDeviceCode() + "/" + capabilityCode, "SUCCESS", null);
        return saved;
    }

    /**
     * 模拟调用测试（对应5.2.4业务规则4、8）：能力测试通过统一设备代理消息完成，不得绕过代理。
     * 首期以模拟适配器实现，固定返回通过；真实设备接入后替换为通过DeviceAgent发起实际调用。
     */
    @Transactional
    public DeviceCapability test(Long deviceId, String capabilityCode, User operator) {
        DeviceCapability capability = get(deviceId, capabilityCode);
        Device device = deviceMapper.findById(deviceId).orElseThrow(() -> new BusinessException(ErrorCode.DEVICE_NOT_FOUND));
        try {
            DeviceAgent agent = agentMapper.findByDeviceId(deviceId).orElseThrow();
            var params = ParameterValues.materialize(capability.getInputParams(), java.util.Map.of());
            var response = messaging.testCapability(device, agent, capability, params);
            capability.setCapabilityStatus("TESTED_PASSED");
            capability.setTestResult("实际设备代理调用通过，指令 " + response.get("commandId"));
        } catch (RuntimeException ex) {
            capability.setCapabilityStatus("TESTED_FAILED");
            capability.setTestResult("实际设备代理调用失败: " + ex.getMessage());
        }
        capability.setLastTestAt(LocalDateTime.now());
        deviceCapabilityMapper.update(capability);
        DeviceCapability saved = capability;

        operationLogService.record(operator.getId(), operator.getUsername(), operator.getRole(),
                "DEVICE_CAPABILITY_TEST", device.getDeviceCode() + "/" + capabilityCode,
                "TESTED_PASSED".equals(capability.getCapabilityStatus()) ? "SUCCESS" : "FAILED", null);
        return saved;
    }

    /**
     * 启用/停用能力（对应业务规则4、6）。仅测试通过的能力可启用；停用后立即退出规划可用能力集合。
     * 若存在使用该能力的进行中步骤，按5.5.3处理——本方法只做状态切换与事件记录，
     * 候选切换/重新规划判断属于5.5执行监督模块职责。
     */
    @Transactional
    public void updateStatus(Long deviceId, String capabilityCode, String status, User operator) {
        DeviceCapability capability = get(deviceId, capabilityCode);
        // 仅TESTED_PASSED或DISABLED（曾测试通过后停用，参数未再修改，测试结论仍有效）可启用；
        // UNTESTED/TESTED_FAILED不得启用（对应业务规则4、异常路径5c）
        if ("ENABLED".equals(status)
                && !"TESTED_PASSED".equals(capability.getCapabilityStatus())
                && !"DISABLED".equals(capability.getCapabilityStatus())) {
            throw new BusinessException(ErrorCode.CAPABILITY_NOT_TESTED);
        }
        capability.setCapabilityStatus(status);
        capability.setUpdatedAt(LocalDateTime.now());
        deviceCapabilityMapper.update(capability);

        Device device = deviceMapper.findById(deviceId).orElseThrow(() -> new BusinessException(ErrorCode.DEVICE_NOT_FOUND));
        operationLogService.record(operator.getId(), operator.getUsername(), operator.getRole(),
                "DEVICE_CAPABILITY_STATUS_CHANGE", device.getDeviceCode() + "/" + capabilityCode + " -> " + status, "SUCCESS", null);
    }

    private String writeParams(List<?> params) {
        try {
            return MAPPER.writeValueAsString(params);
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }
}
