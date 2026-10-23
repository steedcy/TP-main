package com.airport.ai.taskdef;

import com.airport.ai.auth.OperationLogService;
import com.airport.ai.auth.User;
import com.airport.ai.common.BusinessException;
import com.airport.ai.common.ErrorCode;
import com.airport.ai.device.DeviceCapabilityMapper;
import com.airport.ai.devicetype.CapabilityCatalog;
import com.airport.ai.taskdef.dto.CreateTaskDefinitionRequest;
import com.airport.ai.taskdef.dto.UpdateTaskDefinitionRequest;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import java.util.stream.Collectors;

/**
 * 对应5.6.1旅客服务任务定义管理。任务定义只规定场景数据、可用能力类型、约束和完成条件，
 * 不预先写死自主规划步骤（业务规则2）——与5.3.1基线模板（预写死降级执行步骤）是互补的
 * 两个概念，本类不依赖BaselineTemplateService，两者仅在TaskPlanningOrchestrator里
 * 通过taskFamily/definitionCode关联使用。
 */
@Service
public class TaskDefinitionService {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private final TaskDefinitionMapper mapper;
    private final DeviceCapabilityMapper deviceCapabilityMapper;
    private final OperationLogService operationLogService;

    public TaskDefinitionService(TaskDefinitionMapper mapper,
                                  DeviceCapabilityMapper deviceCapabilityMapper,
                                  OperationLogService operationLogService) {
        this.mapper = mapper;
        this.deviceCapabilityMapper = deviceCapabilityMapper;
        this.operationLogService = operationLogService;
    }

    public List<TaskDefinition> listAll() {
        return mapper.findAll();
    }

    public TaskDefinition get(Long id) {
        return mapper.findById(id).orElseThrow(() -> new BusinessException(ErrorCode.TASK_DEFINITION_NOT_FOUND));
    }

    public Optional<TaskDefinition> findByCode(String definitionCode) {
        if (definitionCode == null) return Optional.empty();
        return mapper.findByDefinitionCode(definitionCode);
    }

    /** 供SubmitTaskRequest提交入口校验taskFamily合法性（对应业务规则6：引用能力类型须已启用，
     * 此处引申为任务族本身也须存在且已启用，取代此前硬编码4值枚举@Pattern的校验方式） */
    public boolean isEnabledFamily(String definitionCode) {
        return findByCode(definitionCode).map(d -> "ENABLED".equals(d.getDefinitionStatus())).orElse(false);
    }

    /** 给提交页/失败提示动态渲染当前可选任务族清单，取代硬编码4类任务族文案 */
    public List<String> listEnabledTaskNames() {
        return mapper.findByDefinitionStatus("ENABLED").stream().map(TaskDefinition::getTaskName).toList();
    }

    /**
     * 对应基本路径2~3、异常路径3a/3b：名称唯一 -> 能力类型已启用校验。definitionCode由
     * taskName派生的稳定编码自动生成（EXT_+8位随机十六进制），不暴露给前端填写，避免
     * 与预置任务族的历史taskFamily枚举值（如OVERSIZE_BAGGAGE_HANDLING）产生冲突。
     */
    @Transactional
    public TaskDefinition create(CreateTaskDefinitionRequest request, User operator) {
        if (mapper.existsByTaskName(request.getTaskName())) {
            throw new BusinessException(ErrorCode.TASK_DEFINITION_NAME_TAKEN);
        }
        validateCapabilityTypes(request.getAvailableCapabilityTypes());

        TaskDefinition def = new TaskDefinition();
        def.setDefinitionCode(generateDefinitionCode());
        def.setTaskName(request.getTaskName());
        def.setGoalTemplate(request.getGoalTemplate());
        def.setSceneParams(toJson(request.getSceneParams()));
        def.setAvailableCapabilityTypes(toJson(request.getAvailableCapabilityTypes()));
        def.setConstraintDescription(request.getConstraintDescription());
        def.setCompletionCondition(request.getCompletionCondition());
        def.setIsPreset(false);
        def.setUpdatedBy(operator.getUsername());
        mapper.insert(def);

        operationLogService.record(operator.getId(), operator.getUsername(), operator.getRole(),
                "TASK_DEFINITION_CREATE", def.getTaskName(), "SUCCESS", null);
        return def;
    }

    /** 对应备选路径2a：预置任务族的场景参数与约束可编辑，但taskName/definitionCode不可改 */
    @Transactional
    public TaskDefinition update(Long id, UpdateTaskDefinitionRequest request, User operator) {
        TaskDefinition def = get(id);
        validateCapabilityTypes(request.getAvailableCapabilityTypes());

        def.setGoalTemplate(request.getGoalTemplate());
        def.setSceneParams(toJson(request.getSceneParams()));
        def.setAvailableCapabilityTypes(toJson(request.getAvailableCapabilityTypes()));
        def.setConstraintDescription(request.getConstraintDescription());
        def.setCompletionCondition(request.getCompletionCondition());
        def.setUpdatedBy(operator.getUsername());
        def.setUpdatedAt(LocalDateTime.now());
        mapper.update(def);

        operationLogService.record(operator.getId(), operator.getUsername(), operator.getRole(),
                "TASK_DEFINITION_UPDATE", def.getTaskName(), "SUCCESS", null);
        return def;
    }

    /** 对应备选路径4a：停用后提交页不再展示，已有任务不受影响（既有Task记录不引用本表，无需处理） */
    @Transactional
    public void disable(Long id, User operator) {
        TaskDefinition def = get(id);
        def.setDefinitionStatus("DISABLED");
        def.setUpdatedAt(LocalDateTime.now());
        mapper.update(def);
        operationLogService.record(operator.getId(), operator.getUsername(), operator.getRole(),
                "TASK_DEFINITION_DISABLE", def.getTaskName(), "SUCCESS", null);
    }

    @Transactional
    public void enable(Long id, User operator) {
        TaskDefinition def = get(id);
        def.setDefinitionStatus("ENABLED");
        def.setUpdatedAt(LocalDateTime.now());
        mapper.update(def);
        operationLogService.record(operator.getId(), operator.getUsername(), operator.getRole(),
                "TASK_DEFINITION_ENABLE", def.getTaskName(), "SUCCESS", null);
    }

    /** 对应异常路径3c：预置任务族不可删除 */
    @Transactional
    public void delete(Long id, User operator) {
        TaskDefinition def = get(id);
        if (Boolean.TRUE.equals(def.getIsPreset())) {
            throw new BusinessException(ErrorCode.PRESET_DEFINITION_CANNOT_DELETE);
        }
        mapper.deleteById(def.getId());
        operationLogService.record(operator.getId(), operator.getUsername(), operator.getRole(),
                "TASK_DEFINITION_DELETE", def.getTaskName(), "SUCCESS", null);
    }

    /** 对应业务规则6：引用能力类型须为预置8类之一且存在已启用实例，否则拒绝保存并提示能力缺口 */
    private void validateCapabilityTypes(List<String> capabilityTypes) {
        List<String> invalid = capabilityTypes.stream()
                .filter(c -> !CapabilityCatalog.ALL_CODES.contains(c))
                .collect(Collectors.toList());
        if (!invalid.isEmpty()) {
            throw new BusinessException(ErrorCode.TASK_DEFINITION_CAPABILITY_GAP, "非法能力类型: " + invalid);
        }
        List<String> gaps = capabilityTypes.stream()
                .distinct()
                .filter(c -> !deviceCapabilityMapper.existsByCapabilityTypeAndCapabilityStatus(c, "ENABLED"))
                .collect(Collectors.toList());
        if (!gaps.isEmpty()) {
            throw new BusinessException(ErrorCode.TASK_DEFINITION_CAPABILITY_GAP, "以下能力类型未存在已启用实例: " + gaps);
        }
    }

    private String generateDefinitionCode() {
        String code;
        do {
            code = "EXT_" + UUID.randomUUID().toString().replace("-", "").substring(0, 8).toUpperCase();
        } while (mapper.existsByDefinitionCode(code));
        return code;
    }

    private String toJson(Object value) {
        try {
            return MAPPER.writeValueAsString(value);
        } catch (Exception e) {
            throw new BusinessException(ErrorCode.PARAM_FORMAT_ERROR, "序列化失败: " + e.getMessage());
        }
    }

    @SuppressWarnings("unchecked")
    List<String> parseCapabilityTypes(String json) {
        if (json == null || json.isBlank()) return List.of();
        try {
            return MAPPER.readValue(json, List.class);
        } catch (Exception e) {
            return List.of();
        }
    }
}
