package com.airport.ai.baseline;

import com.airport.ai.auth.OperationLogService;
import com.airport.ai.auth.User;
import com.airport.ai.baseline.dto.CreateBaselineTemplateRequest;
import com.airport.ai.baseline.dto.ParamMapping;
import com.airport.ai.baseline.dto.TemplateStep;
import com.airport.ai.baseline.dto.UpdateBaselineTemplateRequest;
import com.airport.ai.common.BusinessException;
import com.airport.ai.common.ErrorCode;
import com.airport.ai.device.DeviceCapabilityMapper;
import com.airport.ai.devicetype.dto.ParamDefinition;
import com.airport.ai.taskdef.TaskDefinitionService;
import com.airport.ai.task.MotionSafetyGuard;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.*;
import java.util.stream.Collectors;

/**
 * 对应5.3.1基线服务模板定义 + 5.4.6高风险基线降级匹配
 */
@Service
public class BaselineTemplateService {

    private static final int MAX_STEPS = 5;
    private static final ObjectMapper MAPPER = new ObjectMapper();

    private final BaselineTemplateMapper mapper;
    private final DeviceCapabilityMapper deviceCapabilityMapper;
    private final OperationLogService operationLogService;
    private final TaskDefinitionService taskDefinitionService;

    public BaselineTemplateService(BaselineTemplateMapper mapper,
                                    DeviceCapabilityMapper deviceCapabilityMapper,
                                    OperationLogService operationLogService,
                                    TaskDefinitionService taskDefinitionService) {
        this.mapper = mapper;
        this.deviceCapabilityMapper = deviceCapabilityMapper;
        this.operationLogService = operationLogService;
        this.taskDefinitionService = taskDefinitionService;
    }

    public List<BaselineTemplate> listAll() {
        return mapper.findAll();
    }

    public BaselineTemplate get(Long templateId) {
        return mapper.findById(templateId)
                .orElseThrow(() -> new BusinessException(ErrorCode.BASELINE_TEMPLATE_NOT_FOUND));
    }

    /**
     * 静态校验通过后保存为草稿（对应5.3.1业务规则3、异常路径4a-4d）。
     * 校验顺序：名称唯一 -> 步骤数≤5 -> 步骤所需能力已启用 -> 参数映射来源合法。
     */
    @Transactional
    public BaselineTemplate create(CreateBaselineTemplateRequest request, User operator) {
        if (mapper.existsByTemplateName(request.getTemplateName())) {
            throw new BusinessException(ErrorCode.TEMPLATE_NAME_TAKEN);
        }
        // 对应5.6.1联动：模板意图须为已存在的任务定义编码，取代此前硬编码4值枚举@Pattern，
        // 使扩展任务族也能配置对应的降级基线模板
        if (taskDefinitionService.findByCode(request.getTemplateIntent()).isEmpty()) {
            throw new BusinessException(ErrorCode.TASK_FAMILY_INVALID,
                    "模板意图不是已存在的任务定义编码: " + request.getTemplateIntent());
        }
        validateSteps(request.getSteps(), request.getInputParams());

        BaselineTemplate template = new BaselineTemplate();
        template.setTemplateName(request.getTemplateName());
        template.setTaskFamily(request.getTemplateIntent());
        template.setIsPreset(false);
        template.setInputParams(toJson(request.getInputParams()));
        template.setSteps(toJson(assignStepSeq(request.getSteps())));
        template.setTemplateVersion("V1.0");
        template.setUpdatedBy(operator.getUsername());
        mapper.insert(template);

        operationLogService.record(operator.getId(), operator.getUsername(), operator.getRole(),
                "BASELINE_TEMPLATE_CREATE", template.getTemplateName(), "SUCCESS", null);
        return template;
    }

    /**
     * 修改模板：已启用模板被修改时生成新版本，原版本仍供执行中任务使用（对应业务规则7）；
     * 修改后需重新静态校验，且原试运行结论不继承至新版本（对应5.3.2业务规则6），
     * 故状态统一回退为DRAFT，需重新试运行方可再次启用。
     */
    @Transactional
    public BaselineTemplate update(Long templateId, UpdateBaselineTemplateRequest request, User operator) {
        BaselineTemplate template = get(templateId);
        validateSteps(request.getSteps(), request.getInputParams());

        template.setInputParams(toJson(request.getInputParams()));
        template.setSteps(toJson(assignStepSeq(request.getSteps())));
        template.setTemplateStatus("DRAFT");
        template.setUpdatedBy(operator.getUsername());
        template.setUpdatedAt(LocalDateTime.now());
        // Draft edits must also invalidate trials already running against an earlier configuration.
        template.setTemplateVersion(nextVersion(template.getTemplateVersion()));
        mapper.update(template);

        operationLogService.record(operator.getId(), operator.getUsername(), operator.getRole(),
                "BASELINE_TEMPLATE_UPDATE", template.getTemplateName(), "SUCCESS", null);
        return template;
    }

    /** 校验步骤所需能力已启用、参数映射来源合法，失败时抛出携带详细缺口清单的异常 */
    private void validateSteps(List<TemplateStep> steps, List<ParamDefinition> inputParams) {
        if (steps.size() > MAX_STEPS) {
            throw new BusinessException(ErrorCode.TEMPLATE_STEP_LIMIT_EXCEEDED);
        }

        List<String> capabilityGaps = steps.stream()
                .map(TemplateStep::getCapabilityType)
                .distinct()
                .filter(cap -> !deviceCapabilityMapper.existsByCapabilityTypeAndCapabilityStatus(cap, "ENABLED"))
                .collect(Collectors.toList());
        if (!capabilityGaps.isEmpty()) {
            throw new BusinessException(ErrorCode.TEMPLATE_CAPABILITY_GAP, "以下能力类型未存在已启用实例: " + capabilityGaps);
        }

        Set<String> definedInputs = inputParams.stream().map(ParamDefinition::getName).collect(Collectors.toSet());
        Set<String> requiredInputs = inputParams.stream()
                .filter(p -> Boolean.TRUE.equals(p.getRequired()))
                .map(ParamDefinition::getName)
                .collect(Collectors.toSet());
        Set<String> suppliedByMapping = new HashSet<>();

        List<String> mappingErrors = new ArrayList<>();
        for (int i = 0; i < steps.size(); i++) {
            TemplateStep step = steps.get(i);
            int stepSeq = i + 1;
            Map<String, Object> safetyCheck = new LinkedHashMap<>();
            safetyCheck.put("capabilityType", step.getCapabilityType());
            safetyCheck.put("completionCondition", step.getCompletionCondition());
            Map<String, Object> mappedInputs = new LinkedHashMap<>();
            for (ParamMapping mapping : step.getParamMapping()) {
                mappedInputs.put(mapping.getTarget(), mapping.getSource());
            }
            safetyCheck.put("inputParams", mappedInputs);
            List<String> safetyHits = MotionSafetyGuard.detect(safetyCheck);
            if (!safetyHits.isEmpty()) {
                mappingErrors.add("步骤" + stepSeq + "参数映射含运动安全控制字段: " + safetyHits);
            }
            for (ParamMapping mapping : step.getParamMapping()) {
                String source = mapping.getSource();
                if (source.startsWith("TEMPLATE_INPUT.")) {
                    String paramName = source.substring("TEMPLATE_INPUT.".length());
                    if (!definedInputs.contains(paramName)) {
                        mappingErrors.add("步骤" + stepSeq + "参数映射引用未定义的模板输入参数: " + paramName);
                    } else {
                        suppliedByMapping.add(paramName);
                    }
                } else if (source.matches("STEP\\d+_OUTPUT\\..+")) {
                    int refStepSeq = Integer.parseInt(source.substring(4, source.indexOf("_OUTPUT")));
                    if (refStepSeq >= stepSeq) {
                        mappingErrors.add("步骤" + stepSeq + "参数映射引用了非前序步骤的输出: " + source);
                    }
                } else {
                    mappingErrors.add("步骤" + stepSeq + "参数映射来源格式非法（须为TEMPLATE_INPUT.*或STEP{n}_OUTPUT.*): " + source);
                }
            }
        }
        // 必填模板输入参数须至少被一处参数映射引用，否则视为"无来源"（对应业务规则5异常路径4d）
        requiredInputs.stream()
                .filter(p -> !suppliedByMapping.contains(p))
                .forEach(p -> mappingErrors.add("必填模板输入参数无步骤映射来源: " + p));

        if (!mappingErrors.isEmpty()) {
            throw new BusinessException(ErrorCode.TEMPLATE_PARAM_MAPPING_INVALID, mappingErrors.toString());
        }
    }

    private List<TemplateStep> assignStepSeq(List<TemplateStep> steps) {
        for (int i = 0; i < steps.size(); i++) {
            steps.get(i).setStepSeq(i + 1);
        }
        return steps;
    }

    /** 仅试运行成功的模板版本可启用（对应5.3.2业务规则4、异常路径5b） */
    @Transactional
    public BaselineTemplate enable(Long templateId, User operator) {
        BaselineTemplate template = get(templateId);
        if (!"DRY_RUN_PASSED".equals(template.getTemplateStatus())) {
            throw new BusinessException(ErrorCode.TEMPLATE_NOT_DRY_RUN_PASSED);
        }
        template.setTemplateStatus("ENABLED");
        template.setUpdatedAt(LocalDateTime.now());
        mapper.update(template);
        operationLogService.record(operator.getId(), operator.getUsername(), operator.getRole(),
                "BASELINE_TEMPLATE_ENABLE", template.getTemplateName(), "SUCCESS", null);
        return template;
    }

    /** 停用模板：退出降级可选集合（对应备选路径5b） */
    @Transactional
    public void disable(Long templateId, User operator) {
        BaselineTemplate template = get(templateId);
        template.setTemplateStatus("DISABLED");
        template.setUpdatedAt(LocalDateTime.now());
        mapper.update(template);
        operationLogService.record(operator.getId(), operator.getUsername(), operator.getRole(),
                "BASELINE_TEMPLATE_DISABLE", template.getTemplateName(), "SUCCESS", null);
    }

    @Transactional
    public void delete(Long templateId, User operator) {
        BaselineTemplate template = get(templateId);
        if (Boolean.TRUE.equals(template.getIsPreset())) {
            throw new BusinessException(ErrorCode.PRESET_TEMPLATE_CANNOT_DELETE);
        }
        mapper.deleteById(template.getId());
        operationLogService.record(operator.getId(), operator.getUsername(), operator.getRole(),
                "BASELINE_TEMPLATE_DELETE", template.getTemplateName(), "SUCCESS", null);
    }

    /**
     * 匹配优先级：任务族精确匹配 > 步骤数少优先 > 最近试运行通过优先（对应5.4.6业务规则7）。
     * "最近试运行通过优先"按updated_at倒序：enable()/试运行通过（DRY_RUN_PASSED）都会刷新该字段，
     * 比此前用模板版本号倒序近似排序更贴近"最近一次试运行通过时间"的字面语义。
     */
    public Optional<BaselineTemplate> matchForDowngrade(String taskFamily) {
        List<BaselineTemplate> candidates = mapper.findByTaskFamilyAndTemplateStatus(taskFamily, "ENABLED");
        return candidates.stream()
                .sorted(Comparator
                        .comparingInt((BaselineTemplate t) -> fromJsonSteps(t.getSteps()).size())
                        .thenComparing(BaselineTemplate::getUpdatedAt, Comparator.reverseOrder()))
                .findFirst();
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

    private String toJson(Object value) {
        try {
            return MAPPER.writeValueAsString(value);
        } catch (Exception e) {
            throw new BusinessException(ErrorCode.TEMPLATE_PARAM_MAPPING_INVALID, "序列化失败: " + e.getMessage());
        }
    }

    /** steps为JSON字符串（entity.getSteps()），此处反序列化仅用于读取步骤数等只读用途 */
    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> fromJsonSteps(String stepsJson) {
        if (stepsJson == null || stepsJson.isBlank()) {
            return Collections.emptyList();
        }
        try {
            return MAPPER.readValue(stepsJson, List.class);
        } catch (Exception e) {
            throw new BusinessException(ErrorCode.TEMPLATE_PARAM_MAPPING_INVALID, "反序列化失败: " + e.getMessage());
        }
    }
}
