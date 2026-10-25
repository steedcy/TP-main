package com.airport.ai.task;

import com.airport.ai.device.DeviceCapabilityMapper;
import org.springframework.stereotype.Service;

import java.util.*;

/**
 * 对应5.4.4计划三类校验（结构/能力/约束），为硬性闸门，通过前不得分配设备、不得下发
 * 任何指令（业务规则9）。B4候选计划生成与B7基线模板降级共用本校验器，输入统一为
 * List&lt;Map&lt;String,Object&gt;&gt;格式的步骤清单，不关心计划来源。能力是否存在的
 * 设备类型边界判定（5.2.4A）已在快照构建阶段完成——ContextSnapshotService只采集
 * DeviceCapability.capabilityStatus=ENABLED的能力，这些能力创建时已通过越界校验，
 * 故本类不重复调用DeviceTypeCapabilityService。
 */
@Service
public class PlanValidationService {

    private static final int MAX_STEPS = 5;

    private final DeviceCapabilityMapper deviceCapabilityMapper;

    public PlanValidationService(DeviceCapabilityMapper deviceCapabilityMapper) {
        this.deviceCapabilityMapper = deviceCapabilityMapper;
    }

    /**
     * @param steps           待校验步骤清单
     * @param snapshotAgents  规划上下文快照中的代理清单（ContextSnapshotService.parseAgents的产出），
     *                        用于能力校验"存在可承接该步骤的候选代理、代理在线"
     */
    public PlanValidationResult validate(List<Map<String, Object>> steps, List<Map<String, Object>> snapshotAgents) {
        return validate(steps, snapshotAgents, null);
    }

    /**
     * @param allowedCapabilityTypes 任务定义（5.6.1）声明的可用能力类型清单，非null时约束校验
     *                                要求每个步骤所需能力必须在该清单内，超出即判定约束不通过——
     *                                这是把任务定义"约束条件"自由文本落地为可执行校验的折中方案：
     *                                自由文本本身不做语义解析，只有能力类型范围是可执行约束。
     *                                传null表示不做该项约束（供无任务定义关联的历史/降级路径兼容）。
     */
    @SuppressWarnings("unchecked")
    public PlanValidationResult validate(List<Map<String, Object>> steps, List<Map<String, Object>> snapshotAgents,
                                          List<String> allowedCapabilityTypes) {
        return validate(steps, snapshotAgents, allowedCapabilityTypes, null);
    }

    @SuppressWarnings("unchecked")
    public PlanValidationResult validate(List<Map<String, Object>> steps, List<Map<String, Object>> snapshotAgents,
                                          List<String> allowedCapabilityTypes, String taskFamily) {
        PlanValidationResult result = new PlanValidationResult();
        if (steps == null || steps.isEmpty()) {
            result.failStructure("计划必须包含至少一个步骤", null, "ERR_STEP_FIELD_MISSING");
            return result;
        }

        // 1. 结构校验：步骤数≤5、字段完整、顺序与依赖合法、无循环、无无限轮次协商
        if (steps.size() > MAX_STEPS) {
            result.failStructure("可执行步骤数(" + steps.size() + ")超过上限5，系统不做自动截断", null, "ERR_STEP_LIMIT_EXCEEDED");
        }
        Set<Integer> seenStepSeq = new HashSet<>();
        for (int i = 0; i < steps.size(); i++) {
            Map<String, Object> step = steps.get(i);
            Integer stepSeq = asInteger(step.get("stepSeq"));
            if (stepSeq == null) stepSeq = i + 1;
            if (!seenStepSeq.add(stepSeq)) {
                result.failStructure("步骤序号重复，可能存在循环引用", stepSeq, "ERR_STEP_DUPLICATE_SEQ");
            }
            for (String field : List.of("stepGoal", "capabilityType", "completionCondition")) {
                if (isBlank(step.get(field))) {
                    result.failStructure("步骤字段不完整，缺少: " + field, stepSeq, "ERR_STEP_FIELD_MISSING");
                }
            }
            Object paramMapping = step.get("inputParams");
            if (paramMapping instanceof Map<?, ?> mapping && mapping.containsKey("__loop__")) {
                result.failStructure("步骤包含循环/动态代码生成标记，平台不支持", stepSeq, "ERR_STEP_LOOP_DETECTED");
            }
        }

        // 5.6.5备选路径5a：航班变更允许缺席的物理渠道留在计划中并在执行时标为未覆盖。
        // 至少一个发布渠道必须实际可用；未知能力和其他任务族仍走原有硬闸门。
        boolean partialFlightAvailable = "FLIGHT_CHANGE_RESPONSE".equals(taskFamily)
                && List.of("CAP_FLIGHT_UPDATE", "CAP_INFO_DISPLAY", "CAP_NOTIFICATION").stream()
                .anyMatch(type -> countOnlineCandidates(snapshotAgents, type, taskFamily) > 0);

        // 2. 能力校验：所需能力存在且已启用、存在可承接该步骤的候选代理、代理在线
        for (int i = 0; i < steps.size(); i++) {
            Map<String, Object> step = steps.get(i);
            Integer stepSeq = asInteger(step.get("stepSeq"));
            if (stepSeq == null) stepSeq = i + 1;
            String capabilityType = asString(step.get("capabilityType"));
            if (capabilityType == null) {
                continue; // 结构校验已报告字段缺失，避免重复报错
            }
            boolean existsEnabledInstance = deviceCapabilityMapper.existsByCapabilityTypeAndCapabilityStatus(
                    capabilityType, "ENABLED");
            if (!existsEnabledInstance) {
                if (!partialFlightAvailable || !CoreScenarioChannelPolicy.isFlightChannel(taskFamily, capabilityType)) {
                    result.failCapability("能力类型" + capabilityType + "不存在已启用实例", stepSeq, "ERR_CAPABILITY_GAP");
                }
                continue;
            }
            long onlineCandidates = countOnlineCandidates(snapshotAgents, capabilityType, taskFamily);
            if (onlineCandidates == 0) {
                if (!partialFlightAvailable || !CoreScenarioChannelPolicy.isFlightChannel(taskFamily, capabilityType)) {
                    String required = CoreScenarioChannelPolicy.requiredType(taskFamily, capabilityType);
                    result.failCapability("能力类型" + capabilityType + "无在线候选代理"
                            + (required == null ? "" : "（要求渠道" + required + "）"), stepSeq, "ERR_NO_ONLINE_CANDIDATE");
                }
            }
        }

        // 3. 约束校验：输入参数完整合法、无资源冲突、不含运动安全指令、满足任务族约束
        for (int i = 0; i < steps.size(); i++) {
            Map<String, Object> step = steps.get(i);
            Integer stepSeq = asInteger(step.get("stepSeq"));
            if (stepSeq == null) stepSeq = i + 1;

            List<String> motionSafetyHits = MotionSafetyGuard.detect(step);
            if (!motionSafetyHits.isEmpty()) {
                result.failConstraint("步骤包含运动安全控制字段: " + motionSafetyHits, stepSeq, "ERR_MOTION_SAFETY_FIELD");
            }
            // Where schemas are available, reject invented/malformed inputs before freezing a plan.
            if (!(step.get("paramMapping") instanceof List<?>) && step.get("inputParams") instanceof Map<?,?> inputs) {
                List<Map<String,Object>> schemas=new ArrayList<>();
                for (var agent:snapshotAgents) {
                    if (!CoreScenarioChannelPolicy.matches(taskFamily, String.valueOf(step.get("capabilityType")),
                            String.valueOf(agent.get("deviceTypeCode")), String.valueOf(agent.get("simulatedDeviceType")))) continue;
                    if (!(agent.get("capabilitySchemas") instanceof List<?> declared)) continue;
                    for (Object item:declared) if (item instanceof Map<?,?> schema && java.util.Objects.equals(schema.get("capabilityType"),step.get("capabilityType")))
                        schemas.add((Map<String,Object>)schema);
                }
                if (!schemas.isEmpty()) {
                    boolean valid=false;
                    for (var schema:schemas) try {
                        String json=new com.fasterxml.jackson.databind.ObjectMapper().writeValueAsString(schema.get("inputParams"));
                        com.airport.ai.device.ParameterValues.materialize(json,(Map<String,Object>)inputs); valid=true; break;
                    } catch (Exception ignored) { }
                    if (!valid) result.failConstraint("输入参数与当前能力定义不匹配",stepSeq,"ERR_CAPABILITY_PARAMETER_INVALID");
                }
            }
            // 候选设备数量是否低于阈值属于5.4.5风险信号判定（RULE_RESOURCE_CRITICAL），
            // 零候选的硬拦截已在能力校验环节处理，本环节不重复判定资源冲突

            // 对应5.6.1业务规则7：任务定义约束条件参与约束校验，落地为能力类型范围约束
            String capabilityType = asString(step.get("capabilityType"));
            if (allowedCapabilityTypes != null && capabilityType != null
                    && !allowedCapabilityTypes.contains(capabilityType)) {
                result.failConstraint("步骤所需能力" + capabilityType + "超出任务定义声明的可用能力类型范围: "
                        + allowedCapabilityTypes, stepSeq, "ERR_CAPABILITY_NOT_IN_TASK_DEFINITION");
            }
        }

        return result;
    }

    /** Every preset scenario must plan its required actions on the correct physical channels. */
    public void requireCoreScenarioCoverage(List<Map<String, Object>> fullSteps, String taskFamily,
                                            PlanValidationResult result) {
        if (taskFamily == null || !Set.of("FLIGHT_CHANGE_RESPONSE", "OVERSIZE_BAGGAGE_HANDLING", "SPECIAL_PASSENGER_SERVICE")
                .contains(taskFamily)) return;
        Set<String> capabilities = new HashSet<>();
        if (fullSteps != null) for (Map<String, Object> step : fullSteps) {
            capabilities.add(String.valueOf(step.get("capabilityType")));
        }
        List<String> requiredCapabilities = switch (taskFamily) {
            case "FLIGHT_CHANGE_RESPONSE" -> List.of("CAP_FLIGHT_UPDATE", "CAP_INFO_DISPLAY");
            case "OVERSIZE_BAGGAGE_HANDLING" -> List.of("CAP_BAGGAGE_MEASURE", "CAP_OVERSIZE_ALERT", "CAP_INFO_DISPLAY", "CAP_NAVIGATION");
            case "SPECIAL_PASSENGER_SERVICE" -> List.of("CAP_INFO_DISPLAY", "CAP_NOTIFICATION", "CAP_ESCORT");
            default -> List.of();
        };
        for (String required : requiredCapabilities) {
            if (!capabilities.contains(required)) {
                result.failCapability("核心场景计划缺少必需渠道" + CoreScenarioChannelPolicy.requiredType(taskFamily, required)
                                + "的能力" + required,
                        null, "ERR_REQUIRED_CHANNEL_MISSING");
            }
        }
        if ("FLIGHT_CHANGE_RESPONSE".equals(taskFamily)
                && !capabilities.contains("CAP_NOTIFICATION") && !capabilities.contains("CAP_NAVIGATION")) {
            result.failCapability("航班变更计划缺少机器人现场通知或引导渠道", null, "ERR_REQUIRED_CHANNEL_MISSING");
        }
        if ("OVERSIZE_BAGGAGE_HANDLING".equals(taskFamily) && fullSteps != null) {
            int measureSeq = fullSteps.stream().filter(s -> "CAP_BAGGAGE_MEASURE".equals(s.get("capabilityType")))
                    .mapToInt(s -> asInteger(s.get("stepSeq")) == null ? 0 : asInteger(s.get("stepSeq"))).min().orElse(0);
            for (Map<String, Object> step : fullSteps) {
                String capability = String.valueOf(step.get("capabilityType"));
                Integer seq = asInteger(step.get("stepSeq"));
                if (measureSeq > 0 && seq != null && seq < measureSeq
                        && Set.of("CAP_OVERSIZE_ALERT", "CAP_INFO_DISPLAY").contains(capability)) {
                    result.failStructure("超规处置步骤不得早于测量判定", seq, "ERR_BAGGAGE_BRANCH_ORDER");
                }
            }
        }
    }

    private long countOnlineCandidates(List<Map<String, Object>> snapshotAgents, String capabilityType, String taskFamily) {
        if (snapshotAgents == null) {
            return 0;
        }
        return snapshotAgents.stream()
                .filter(agent -> {
                    Object caps = agent.get("capabilities");
                    return caps instanceof List<?> list && list.contains(capabilityType)
                            && CoreScenarioChannelPolicy.matches(taskFamily, capabilityType,
                            String.valueOf(agent.get("deviceTypeCode")), String.valueOf(agent.get("simulatedDeviceType")));
                })
                .count();
    }

    private boolean isBlank(Object value) {
        return value == null || (value instanceof String s && s.isBlank());
    }

    private String asString(Object value) {
        return value == null ? null : String.valueOf(value);
    }

    private Integer asInteger(Object value) {
        if (value == null) return null;
        if (value instanceof Integer i) return i;
        if (value instanceof Number n) return n.intValue();
        try {
            return Integer.parseInt(value.toString());
        } catch (NumberFormatException e) {
            return null;
        }
    }
}
