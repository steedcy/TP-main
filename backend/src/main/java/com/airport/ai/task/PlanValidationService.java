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
    private static final java.util.regex.Pattern REFERENCED_PREDECESSOR = java.util.regex.Pattern.compile(
            "(?:(?:前置步骤|依赖步骤|依赖第?|前置)\\s*(\\d+)(?:步)?|(?:第?\\s*(\\d+)\\s*步|步骤\\s*(\\d+))\\s*(?:完成后?|之后|后)|after\\s+step\\s*(\\d+)|depends\\s+on\\s+(?:step\\s*)?(\\d+))",
            java.util.regex.Pattern.CASE_INSENSITIVE);

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
        return validate(steps, snapshotAgents, allowedCapabilityTypes, taskFamily, 0, null);
    }

    @SuppressWarnings("unchecked")
    public PlanValidationResult validate(List<Map<String, Object>> steps, List<Map<String, Object>> snapshotAgents,
                                          List<String> allowedCapabilityTypes, String taskFamily, int completedPrefixCount) {
        return validate(steps, snapshotAgents, allowedCapabilityTypes, taskFamily, completedPrefixCount, null);
    }

    @SuppressWarnings("unchecked")
    public PlanValidationResult validate(List<Map<String, Object>> steps, List<Map<String, Object>> snapshotAgents,
                                          List<String> allowedCapabilityTypes, String taskFamily,
                                          int completedPrefixCount, Long currentTaskId) {
        PlanValidationResult result = new PlanValidationResult();
        if (steps == null || steps.isEmpty()) {
            result.failStructure("计划必须包含至少一个步骤", null, "ERR_STEP_FIELD_MISSING");
            return result;
        }

        // 1. 结构校验：步骤数≤5、字段完整、顺序与依赖合法、无循环、无无限轮次协商
        // 条件节点不计数、条件分支中的业务动作计数（SRS_F012.R01/R02）；超限直接失败，不截断
        int executableCount = PlanStepRules.executableCount(steps);
        if (executableCount > MAX_STEPS) {
            result.failStructure("可执行步骤数(" + executableCount + ")超过上限5（条件节点不计数，分支动作计数），系统不做自动截断",
                    null, "ERR_STEP_LIMIT_EXCEEDED");
        }
        if (executableCount == 0) {
            result.failStructure("计划必须包含至少一个可执行步骤", null, "ERR_STEP_FIELD_MISSING");
        }
        Set<Integer> seenStepSeq = new HashSet<>();
        Set<Integer> conditionSeqs = new HashSet<>();
        Set<Integer> actionSeqs = new HashSet<>();
        for (int i = 0; i < steps.size(); i++) {
            Map<String, Object> step = steps.get(i);
            Integer stepSeq = asInteger(step.get("stepSeq"));
            if (stepSeq == null) stepSeq = i + 1;
            if (!seenStepSeq.add(stepSeq)) {
                result.failStructure("步骤序号重复，可能存在循环引用", stepSeq, "ERR_STEP_DUPLICATE_SEQ");
            }
            if (PlanStepRules.isConditionNode(step)) {
                // 条件节点只表达分支判断：要有判断文字，不得含循环/动态代码，不要求能力和设备
                conditionSeqs.add(stepSeq);
                if (PlanStepRules.conditionText(step) == null) {
                    result.failStructure("条件节点缺少判断条件（condition）", stepSeq, "ERR_STEP_FIELD_MISSING");
                }
                for (String field : List.of("condition", "stepGoal")) {
                    String hit = unsupportedControlFlow(step.get(field));
                    if (hit != null) {
                        result.failStructure("条件节点" + field + "含不支持的控制流或动态执行内容（" + hit + "）", stepSeq, "ERR_STEP_LOOP_DETECTED");
                    }
                }
                continue;
            }
            actionSeqs.add(stepSeq);
            Integer branchOwner = PlanStepRules.branchOf(step);
            if (branchOwner != null && (!conditionSeqs.contains(branchOwner) || branchOwner >= stepSeq)) {
                result.failStructure("分支动作引用不存在或位置靠后的条件节点" + branchOwner, stepSeq, "ERR_STEP_DEPENDENCY_ORDER");
            }
            // 步骤六项（SRS_F012.R04）：目标、能力、输入参数、前置条件、完成条件、失败处理，缺任一项都不得冻结。
            // 缺失、null、空串、纯空白、非文本都算缺失，自主规划、基线模板、重规划三种来源共用本校验。
            for (String field : List.of("stepGoal", "capabilityType", "precondition", "completionCondition", "failureHandling")) {
                Object value = step.get(field);
                if (isBlank(value)) {
                    result.failStructure("步骤字段不完整，缺少: " + field, stepSeq, "ERR_STEP_FIELD_MISSING");
                } else if (!(value instanceof String)) {
                    result.failStructure("步骤字段不完整，缺少: " + field + "（须为文本）", stepSeq, "ERR_STEP_FIELD_MISSING");
                }
            }
            if (!(step.get("inputParams") instanceof Map<?, ?>)) {
                result.failStructure("步骤字段不完整，缺少: inputParams（须为对象，可为空对象）", stepSeq, "ERR_STEP_FIELD_MISSING");
            }
            // 不支持循环、动态代码生成执行和无限轮次协商（SRS_F012.R03）：文字字段里的循环/动态代码/无限协商也拒绝
            for (String field : List.of("stepGoal", "precondition", "completionCondition", "failureHandling", "branchCondition")) {
                String hit = unsupportedControlFlow(step.get(field));
                if (hit != null) {
                    result.failStructure("步骤" + field + "含不支持的控制流或动态执行内容（" + hit + "）", stepSeq, "ERR_STEP_LOOP_DETECTED");
                }
            }
            Object paramMapping = step.get("inputParams");
            if (paramMapping instanceof Map<?, ?> mapping && containsLoopMarker(mapping)) {
                result.failStructure("步骤包含循环/动态代码生成标记，平台不支持", stepSeq, "ERR_STEP_LOOP_DETECTED");
            }
            // inputParams里的文字值同样不得携带循环或动态代码（SRS_F012.R03检测范围含inputParams）
            String paramHit = unsupportedInParams(paramMapping);
            if (paramHit != null) {
                result.failStructure("步骤inputParams含不支持的控制流或动态执行内容（" + paramHit + "）", stepSeq, "ERR_STEP_LOOP_DETECTED");
            }
            if (step.get("paramMapping") instanceof List<?> mappings) {
                String mappingHit = unsupportedInParams(mappings);
                if (mappingHit != null) {
                    result.failStructure("步骤paramMapping含不支持的控制流或动态执行内容（" + mappingHit + "）", stepSeq, "ERR_STEP_LOOP_DETECTED");
                }
            }
        }
        // Execution is strictly sequential. A step may depend only on a prior
        // business step; a forward/self reference creates an impossible order.
        for (int i = 0; i < steps.size(); i++) {
            Map<String, Object> step = steps.get(i);
            if (PlanStepRules.isConditionNode(step)) continue;
            Integer seq = asInteger(step.get("stepSeq"));
            if (seq == null) seq = i + 1;
            for (String field : List.of("precondition", "completionCondition", "stepGoal")) {
                Object raw = step.get(field);
                if (!(raw instanceof String text)) continue;
                java.util.regex.Matcher references = REFERENCED_PREDECESSOR.matcher(text);
                while (references.find()) {
                    Integer predecessor = null;
                    for (int group = 1; group <= references.groupCount(); group++) {
                        if (references.group(group) != null) {
                            predecessor = Integer.parseInt(references.group(group));
                            break;
                        }
                    }
                    if (predecessor != null && ((!actionSeqs.contains(predecessor)
                            && predecessor > completedPrefixCount) || predecessor >= seq)) {
                        result.failStructure("步骤" + seq + "依赖不存在或尚未完成的步骤" + predecessor,
                                seq, "ERR_STEP_DEPENDENCY_ORDER");
                    }
                }
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
            if (PlanStepRules.isConditionNode(step)) continue;
            String capabilityType = asString(step.get("capabilityType"));
            if (capabilityType == null || capabilityType.isBlank()) {
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

            List<String> motionSafetyHits = PlanStepRules.isConditionNode(step)
                    ? MotionSafetyGuard.detect(Map.of("stepGoal", String.valueOf(PlanStepRules.conditionText(step))))
                    : MotionSafetyGuard.detect(step);
            if (!motionSafetyHits.isEmpty()) {
                result.failConstraint("步骤包含运动安全控制字段: " + motionSafetyHits, stepSeq, "ERR_MOTION_SAFETY_FIELD");
            }
            if (PlanStepRules.isConditionNode(step)) continue;
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
            // 对应TC-039.S2、TC-041.S2、SRS_F013.R03：无资源冲突硬性校验
            // 当步骤所需能力存在在线候选代理，但所有候选代理均处于占用状态（零空闲可用候选设备）时，构成确定的硬性资源冲突，
            // 约束校验直接硬拦截拒绝，原因码 ERR_RESOURCE_CONFLICT，计划未冻结且不进入监督判定；
            // 仍有空闲候选但备用数量偏少的情况则放行给5.4.5监督智能体风险判定（RULE_RESOURCE_CRITICAL软风险评估）。
            String capabilityType = asString(step.get("capabilityType"));
            if (capabilityType != null && !capabilityType.isBlank()) {
                boolean flightExempt = partialFlightAvailable && CoreScenarioChannelPolicy.isFlightChannel(taskFamily, capabilityType);
                if (!flightExempt) {
                    long onlineCandidates = countOnlineCandidates(snapshotAgents, capabilityType, taskFamily);
                    long idleCandidates = countIdleCandidates(snapshotAgents, capabilityType, taskFamily, currentTaskId);
                    if (onlineCandidates > 0 && idleCandidates == 0) {
                        result.failConstraint("步骤" + stepSeq + "所需能力" + capabilityType + "候选设备已被其他任务占用，存在资源冲突（零空闲可用候选设备）",
                                stepSeq, "ERR_RESOURCE_CONFLICT");
                    }
                }
            }

            // 对应5.6.1业务规则7：任务定义约束条件参与约束校验，落地为能力类型范围约束
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
                    Object online = agent.get("onlineStatus");
                    if (online != null && !"ONLINE".equalsIgnoreCase(String.valueOf(online).trim())) {
                        return false;
                    }
                    Object caps = agent.get("capabilities");
                    return caps instanceof List<?> list && list.contains(capabilityType)
                            && CoreScenarioChannelPolicy.matches(taskFamily, capabilityType,
                            String.valueOf(agent.get("deviceTypeCode")), String.valueOf(agent.get("simulatedDeviceType")));
                })
                .count();
    }

    private boolean isAgentIdle(Map<String, Object> agent, Long currentTaskId) {
        Object online = agent.get("onlineStatus");
        if (online != null && !"ONLINE".equalsIgnoreCase(String.valueOf(online).trim())) {
            return false;
        }

        // 若已被当前任务自身占用，则不构成外部资源冲突（适用于同一任务内部或局部重规划）
        Object rawTaskId = agent.get("currentTaskId");
        if (currentTaskId != null && rawTaskId != null) {
            try {
                long agentTaskId = Long.parseLong(String.valueOf(rawTaskId).trim());
                if (agentTaskId == currentTaskId) {
                    return true;
                }
            } catch (NumberFormatException ignored) {}
        }

        Object workload = agent.get("workload");
        if (workload == null) workload = agent.get("workStatus");
        if (workload == null) workload = agent.get("workloadStatus");

        if (workload != null && "BUSY".equalsIgnoreCase(String.valueOf(workload).trim())) {
            return false;
        }

        if (rawTaskId != null) {
            String tidStr = String.valueOf(rawTaskId).trim();
            if (!tidStr.isEmpty() && !"null".equalsIgnoreCase(tidStr) && !"0".equals(tidStr)) {
                return false;
            }
        }

        return true;
    }

    private long countIdleCandidates(List<Map<String, Object>> snapshotAgents, String capabilityType,
                                     String taskFamily, Long currentTaskId) {
        if (snapshotAgents == null || capabilityType == null) {
            return 0;
        }
        return snapshotAgents.stream()
                .filter(agent -> {
                    if (!isAgentIdle(agent, currentTaskId)) {
                        return false;
                    }
                    Object caps = agent.get("capabilities");
                    return caps instanceof List<?> list && list.contains(capabilityType)
                            && CoreScenarioChannelPolicy.matches(taskFamily, capabilityType,
                            String.valueOf(agent.get("deviceTypeCode")), String.valueOf(agent.get("simulatedDeviceType")));
                })
                .count();
    }

    /**
     * 循环、动态代码执行、无限重试/协商的文字表述。只匹配明确的控制流写法，正常业务描述
     * （如“重试一次”“等待设备就绪”“展示直到完成”）不命中。
     */
    private static final String BOUNDED_REPEAT_TAIL = "(?!.{0,24}(once|twice|one\\s+time|\\d+\\s*(times|x)\\b|一次|两次|二次|\\d+\\s*次))";

    private static final List<java.util.regex.Pattern> CONTROL_FLOW = List.of(
            java.util.regex.Pattern.compile("\\bwhile\\s*(\\(|true\\b|1\\b|\\w+\\s*:)", java.util.regex.Pattern.CASE_INSENSITIVE),
            // for(;;) / for (int i=0;;i++)：三段式循环头；不误伤"wait for (30 seconds)"这类普通文字
            java.util.regex.Pattern.compile("\\bfor\\s*\\([^)]*;[^)]*;[^)]*\\)", java.util.regex.Pattern.CASE_INSENSITIVE),
            java.util.regex.Pattern.compile("\\b(goto\\s+step|go\\s+back\\s+to\\s+step|jump\\s+back\\s+to\\s+step)", java.util.regex.Pattern.CASE_INSENSITIVE),
            java.util.regex.Pattern.compile("\\b(os\\.system|__import__|child_process|powershell|bash\\s+-c|cmd(\\.exe)?\\s+/c)\\b|<script\\b|\\b(javascript|vbscript):", java.util.regex.Pattern.CASE_INSENSITIVE),
            // repeat：带明确次数（once/twice/3 times/一次）的有限重复不算循环
            java.util.regex.Pattern.compile("\\brepeat(ed|edly|ing|s)?\\b" + BOUNDED_REPEAT_TAIL, java.util.regex.Pattern.CASE_INSENSITIVE),
            java.util.regex.Pattern.compile("(反复|不停地|重试直到|重复直到|回到步骤\\s*\\d+|返回步骤\\s*\\d+|跳回步骤|无上限重试|无限期|直到成功为止)"),
            java.util.regex.Pattern.compile("循环(往复|直到|重复|调用|处理|下发|发送|等待|询问|协商)|(不断|持续|永久)\\s*重复|(for|while)\\s*循环|进入循环"),
            java.util.regex.Pattern.compile("__loop__", java.util.regex.Pattern.CASE_INSENSITIVE),
            java.util.regex.Pattern.compile("\\bdo\\s*\\{", java.util.regex.Pattern.CASE_INSENSITIVE),
            java.util.regex.Pattern.compile("\\b(eval|exec|exec\\w*|system|runtime\\.getruntime|new\\s+function|import\\s+os|subprocess)\\s*\\(", java.util.regex.Pattern.CASE_INSENSITIVE),
            java.util.regex.Pattern.compile("\\b(forever|infinite(ly)?|endless(ly)?|indefinite(ly)?|unlimited\\s+(negotiat\\w+|rounds?|loops?|retr(y|ies)))\\b", java.util.regex.Pattern.CASE_INSENSITIVE),
            java.util.regex.Pattern.compile("\\b(loop|repeat)\\s+(until|forever|endlessly|while)\\b", java.util.regex.Pattern.CASE_INSENSITIVE),
            java.util.regex.Pattern.compile("(无限|无穷|永远|不断|一直|无上限)\\s*(循环|重复|重试|协商|询问|轮次)|无限协商|循环执行|死循环|无限轮|动态生成代码|生成并执行代码|执行脚本"));

    private String unsupportedControlFlow(Object value) {
        if (!(value instanceof String text) || text.isBlank()) return null;
        for (java.util.regex.Pattern pattern : CONTROL_FLOW) {
            java.util.regex.Matcher m = pattern.matcher(text);
            if (m.find()) return m.group().trim();
        }
        return null;
    }

    /** inputParams（及paramMapping）的键和所有层级的文字值：循环/动态代码文字一律拒绝，返回首个命中说明。 */
    private String unsupportedInParams(Object value) {
        if (value instanceof Map<?, ?> map) {
            for (Map.Entry<?, ?> entry : map.entrySet()) {
                String keyHit = unsupportedControlFlow(String.valueOf(entry.getKey()));
                if (keyHit != null) return String.valueOf(entry.getKey()) + ": " + keyHit;
                String hit = unsupportedInParams(entry.getValue());
                if (hit != null) return hit;
            }
        } else if (value instanceof Iterable<?> items) {
            for (Object item : items) {
                String hit = unsupportedInParams(item);
                if (hit != null) return hit;
            }
        } else if (value instanceof String) {
            return unsupportedControlFlow(value);
        }
        return null;
    }

    private boolean containsLoopMarker(Map<?, ?> map) {
        for (Map.Entry<?, ?> entry : map.entrySet()) {
            if ("__loop__".equals(String.valueOf(entry.getKey()))) return true;
            if (entry.getValue() instanceof Map<?, ?> nested && containsLoopMarker(nested)) return true;
        }
        return false;
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
