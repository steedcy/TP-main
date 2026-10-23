package com.airport.ai.devicetype;

import com.airport.ai.auth.OperationLogService;
import com.airport.ai.auth.User;
import com.airport.ai.common.BusinessException;
import com.airport.ai.common.ErrorCode;
import com.airport.ai.device.DeviceMapper;
import com.airport.ai.devicetype.dto.CapabilityBoundaryView;
import com.airport.ai.devicetype.dto.CreateCapabilityTemplateRequest;
import com.airport.ai.devicetype.dto.UpdateCapabilityBoundaryRequest;
import com.airport.ai.devicetype.dto.UpdateCapabilityTemplateRequest;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;

/**
 * 对应5.2.4A设备类型能力边界管理（类型层）。五类设备类型和八类标准能力类型均系统预置，
 * 不可新增或删除（业务规则1、2），本Service只提供查询和边界内容维护。
 */
@Service
public class DeviceTypeCapabilityService {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private final DeviceTypeCapabilityMapper deviceTypeCapabilityMapper;
    private final CapabilityTemplateMapper capabilityTemplateMapper;
    private final DeviceMapper deviceMapper;
    private final OperationLogService operationLogService;

    public DeviceTypeCapabilityService(DeviceTypeCapabilityMapper deviceTypeCapabilityMapper,
                                        CapabilityTemplateMapper capabilityTemplateMapper,
                                        DeviceMapper deviceMapper,
                                        OperationLogService operationLogService) {
        this.deviceTypeCapabilityMapper = deviceTypeCapabilityMapper;
        this.capabilityTemplateMapper = capabilityTemplateMapper;
        this.deviceMapper = deviceMapper;
        this.operationLogService = operationLogService;
    }

    public List<DeviceTypeCapability> listAll() {
        return deviceTypeCapabilityMapper.findAll();
    }

    public DeviceTypeCapability get(String deviceTypeCode) {
        return deviceTypeCapabilityMapper.findByDeviceTypeCode(deviceTypeCode)
                .orElseThrow(() -> new BusinessException(ErrorCode.DEVICE_NOT_FOUND, "设备类型不存在"));
    }

    public CapabilityBoundaryView getBoundaryView(String deviceTypeCode) {
        DeviceTypeCapability entity = get(deviceTypeCode);
        List<CapabilityTemplate> templates = capabilityTemplateMapper.findByDeviceTypeCode(deviceTypeCode);
        long instanceCount = deviceMapper.countByDeviceTypeCodeAndDeviceStatusNot(deviceTypeCode, "DELETED");
        return CapabilityBoundaryView.from(entity, templates, (int) instanceCount);
    }

    /**
     * 更新设备类型能力边界（对应附录B 6.4.1节PUT接口、5.2.4A业务规则3/9）。
     * 缩小supportedCapabilityTypes范围时不联动处理已有能力模板/设备实例能力——
     * 这些历史数据校验属于创建/更新能力模板、设备能力时的越界校验职责（规则6/7），
     * 本操作只负责保存边界定义本身，不做级联清理。
     */
    @Transactional
    public DeviceTypeCapability updateBoundary(String deviceTypeCode, UpdateCapabilityBoundaryRequest request, User operator) {
        DeviceTypeCapability entity = get(deviceTypeCode);

        List<String> invalid = request.getSupportedCapabilityTypes().stream()
                .filter(c -> !CapabilityCatalog.ALL_CODES.contains(c))
                .toList();
        if (!invalid.isEmpty()) {
            throw new BusinessException(ErrorCode.PARAM_FORMAT_ERROR, "包含未知能力类型: " + invalid);
        }

        try {
            entity.setSupportedCapabilityTypes(MAPPER.writeValueAsString(request.getSupportedCapabilityTypes()));
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
        entity.setTypeDescription(request.getTypeDescription());
        entity.setConstraintRules(request.getConstraintRules());
        entity.setTypicalScenarios(request.getTypicalScenarios());
        entity.setUpdatedBy(operator.getUsername());
        entity.setUpdatedAt(LocalDateTime.now());
        deviceTypeCapabilityMapper.update(entity);
        DeviceTypeCapability saved = entity;

        operationLogService.record(operator.getId(), operator.getUsername(), operator.getRole(),
                "DEVICE_TYPE_BOUNDARY_UPDATE", deviceTypeCode, "SUCCESS", null);
        return saved;
    }

    /**
     * 判断某能力类型是否在设备类型的支持范围内（对应业务规则6/7的越界校验），
     * 仿真体额外继承所模拟设备类型的能力（业务规则4）。
     */
    public boolean isCapabilityTypeSupported(String deviceTypeCode, String simulatedDeviceType, String capabilityType) {
        List<String> supported = parseSupportedTypes(deviceTypeCode);
        if (supported.contains(capabilityType)) {
            return true;
        }
        if ("SIMULATOR".equals(deviceTypeCode) && simulatedDeviceType != null) {
            return parseSupportedTypes(simulatedDeviceType).contains(capabilityType);
        }
        return false;
    }

    public List<String> parseSupportedTypes(String deviceTypeCode) {
        DeviceTypeCapability entity = get(deviceTypeCode);
        try {
            return MAPPER.readValue(entity.getSupportedCapabilityTypes(),
                    MAPPER.getTypeFactory().constructCollectionType(List.class, String.class));
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }

    // ------------------------ 能力模板管理 ------------------------

    public List<CapabilityTemplate> listTemplates(String deviceTypeCode) {
        return capabilityTemplateMapper.findByDeviceTypeCode(deviceTypeCode);
    }

    public CapabilityTemplate getTemplate(String deviceTypeCode, String templateCode) {
        return capabilityTemplateMapper.findByDeviceTypeCodeAndTemplateCode(deviceTypeCode, templateCode)
                .orElseThrow(() -> new BusinessException(ErrorCode.CAPABILITY_CODE_TAKEN, "能力模板不存在"));
    }

    /** 对应附录B 6.4.2节、5.2.4A业务规则7/10/11：能力类型必须在设备类型支持范围内，输入输出参数必须完整定义 */
    @Transactional
    public CapabilityTemplate createTemplate(String deviceTypeCode, CreateCapabilityTemplateRequest request, User operator) {
        get(deviceTypeCode); // 确认设备类型存在
        if (!parseSupportedTypes(deviceTypeCode).contains(request.getCapabilityType())) {
            throw new BusinessException(ErrorCode.CAPABILITY_OUT_OF_BOUNDARY, "该设备类型不支持此能力类型");
        }
        if (capabilityTemplateMapper.existsByDeviceTypeCodeAndTemplateCode(deviceTypeCode, request.getTemplateCode())) {
            throw new BusinessException(ErrorCode.CAPABILITY_CODE_TAKEN, "模板编码在该设备类型下已存在");
        }

        CapabilityTemplate template = new CapabilityTemplate();
        template.setDeviceTypeCode(deviceTypeCode);
        template.setTemplateCode(request.getTemplateCode());
        template.setTemplateName(request.getTemplateName());
        template.setCapabilityType(request.getCapabilityType());
        template.setInputParams(writeParams(request.getInputParams()));
        template.setOutputParams(writeParams(request.getOutputParams()));
        template.setTemplateDescription(request.getTemplateDescription());
        template.setTemplateVersion("V1.0");
        capabilityTemplateMapper.insert(template);
        CapabilityTemplate saved = template;

        operationLogService.record(operator.getId(), operator.getUsername(), operator.getRole(),
                "CAPABILITY_TEMPLATE_CREATE", deviceTypeCode + "/" + saved.getTemplateCode(), "SUCCESS", null);
        return saved;
    }

    /** 修改后自动分配新版本号（对应业务规则12），版本号格式V{major}.{minor}，每次编辑minor+1 */
    @Transactional
    public CapabilityTemplate updateTemplate(String deviceTypeCode, String templateCode,
                                              UpdateCapabilityTemplateRequest request, User operator) {
        CapabilityTemplate template = getTemplate(deviceTypeCode, templateCode);
        template.setTemplateName(request.getTemplateName());
        template.setInputParams(writeParams(request.getInputParams()));
        template.setOutputParams(writeParams(request.getOutputParams()));
        template.setTemplateDescription(request.getTemplateDescription());
        template.setTemplateVersion(nextVersion(template.getTemplateVersion()));
        template.setUpdatedAt(LocalDateTime.now());
        capabilityTemplateMapper.update(template);
        CapabilityTemplate saved = template;

        operationLogService.record(operator.getId(), operator.getUsername(), operator.getRole(),
                "CAPABILITY_TEMPLATE_UPDATE", deviceTypeCode + "/" + templateCode, "SUCCESS", null);
        return saved;
    }

    /** 停用模板：不再出现在新设备实例的模板列表中，但已使用该模板的设备实例不受影响（对应备选路径6a） */
    @Transactional
    public void updateTemplateStatus(String deviceTypeCode, String templateCode, String status, User operator) {
        CapabilityTemplate template = getTemplate(deviceTypeCode, templateCode);
        template.setTemplateStatus(status);
        template.setUpdatedAt(LocalDateTime.now());
        capabilityTemplateMapper.update(template);
        operationLogService.record(operator.getId(), operator.getUsername(), operator.getRole(),
                "CAP_TEMPLATE_STATUS_CHANGE", deviceTypeCode + "/" + templateCode + " -> " + status, "SUCCESS", null);
    }

    /** 已被设备实例使用的能力模板不可删除，只能停用（对应业务规则8、异常路径6b） */
    @Transactional
    public void deleteTemplate(String deviceTypeCode, String templateCode, User operator) {
        CapabilityTemplate template = getTemplate(deviceTypeCode, templateCode);
        if (template.getUsageCount() != null && template.getUsageCount() > 0) {
            throw new BusinessException(ErrorCode.CAPABILITY_TEMPLATE_IN_USE,
                    "该模板已被" + template.getUsageCount() + "个设备实例使用，不可删除");
        }
        capabilityTemplateMapper.deleteById(template.getId());
        operationLogService.record(operator.getId(), operator.getUsername(), operator.getRole(),
                "CAPABILITY_TEMPLATE_DELETE", deviceTypeCode + "/" + templateCode, "SUCCESS", null);
    }

    private String nextVersion(String current) {
        try {
            String[] parts = current.replace("V", "").split("\\.");
            int major = Integer.parseInt(parts[0]);
            int minor = Integer.parseInt(parts[1]);
            return "V" + major + "." + (minor + 1);
        } catch (Exception e) {
            return "V1.1";
        }
    }

    private String writeParams(List<?> params) {
        try {
            return MAPPER.writeValueAsString(params);
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }
}
