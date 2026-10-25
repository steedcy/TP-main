package com.airport.ai.task;

import com.airport.ai.baseline.BaselineTemplate;
import com.airport.ai.baseline.BaselineTemplateService;
import com.airport.ai.event.TaskEventService;
import com.airport.ai.planning.PlanningModelService;
import com.airport.ai.planning.PlanningRequest;
import com.airport.ai.planning.PlanningResponse;
import com.airport.ai.risk.RiskAssessmentResult;
import com.airport.ai.risk.RiskAssessmentService;
import com.airport.ai.taskdef.TaskDefinition;
import com.airport.ai.taskdef.TaskDefinitionService;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

/**
 * 对应5.4.2~5.4.6，串联规划上下文构建、候选计划生成、三类校验、监督判定、基线降级。
 * 由TaskService在目标理解完成（infoComplete=true）后调用advance()触发，同步执行到底，
 * 不引入消息队列或异步任务（与BaselineDryRunService的同步执行风格一致）。
 * 任一环节异常均归口到PENDING_MANUAL或保持原状态，不下发任何设备指令（业务规则贯穿要求）。
 */
@Service
public class TaskPlanningOrchestrator {

    private static final ObjectMapper MAPPER = new ObjectMapper();
    private static final int MAX_STEPS = 5;

    private final TaskMapper taskMapper;
    private final PlanVersionMapper planVersionMapper;
    private final ContextSnapshotService contextSnapshotService;
    private final PlanValidationService planValidationService;
    private final PlanningModelService planningModelService;
    private final RiskAssessmentService riskAssessmentService;
    private final BaselineTemplateService baselineTemplateService;
    private final TaskEventService taskEventService;
    private final TaskExecutionOrchestrator taskExecutionOrchestrator;
    private final TaskDefinitionService taskDefinitionService;

    public TaskPlanningOrchestrator(TaskMapper taskMapper,
                                     PlanVersionMapper planVersionMapper,
                                     ContextSnapshotService contextSnapshotService,
                                     PlanValidationService planValidationService,
                                     PlanningModelService planningModelService,
                                     RiskAssessmentService riskAssessmentService,
                                     BaselineTemplateService baselineTemplateService,
                                     TaskEventService taskEventService,
                                     TaskExecutionOrchestrator taskExecutionOrchestrator,
                                     TaskDefinitionService taskDefinitionService) {
        this.taskMapper = taskMapper;
        this.planVersionMapper = planVersionMapper;
        this.contextSnapshotService = contextSnapshotService;
        this.planValidationService = planValidationService;
        this.planningModelService = planningModelService;
        this.riskAssessmentService = riskAssessmentService;
        this.baselineTemplateService = baselineTemplateService;
        this.taskEventService = taskEventService;
        this.taskExecutionOrchestrator = taskExecutionOrchestrator;
        this.taskDefinitionService = taskDefinitionService;
    }

    /**
     * 目标理解完成后的推进入口，对应基本路径：5.4.2构建上下文 -&gt; 5.4.3候选计划生成 -&gt;
     * 5.4.4三类校验 -&gt; 5.4.5监督判定 -&gt; 低风险进PENDING_ASSIGNMENT / 高风险进5.4.6降级。
     */
    @Transactional
    public void advance(Long taskId) {
        Task task = taskMapper.findById(taskId).orElseThrow();
        if (task.getStatus() != TaskStatus.PLANNING) {
            return; // 已推进过或已终止，避免重复触发（如clarify多次补充但均已完整的边界情况）
        }
        try {
            doAdvance(task);
        } catch (RuntimeException e) {
            // 兜底：任何未预期异常（JSON解析失败、空指针等）都不得向上传播——本方法由TaskService.submit/
            // clarify在同一事务内调用，未捕获的非BusinessException会导致刚创建的任务记录一并回滚，
            // 与"生成任务实例是强制后置条件"矛盾。统一归口待人工处理，不下发任何设备指令。
            taskEventService.append(taskId, "PLAN_GENERATED", "SYSTEM", "ERR_PLANNING_UNEXPECTED",
                    "规划链路执行异常: " + e.getMessage());
            toPendingManual(task, "规划链路执行异常: " + e.getMessage());
        }
    }

    /** Explicit manual choice skips the autonomous model and uses the same validated downgrade gate. */
    @Transactional
    public void switchToBaseline(Long taskId) {
        Task task = taskMapper.findById(taskId).orElseThrow();
        if (task.getStatus() != TaskStatus.PLANNING) return;
        try {
            downgradeOrManual(task, "运行操作员选择基线模板");
        } catch (RuntimeException ex) {
            taskEventService.append(taskId, "BASELINE_DOWNGRADED", "SYSTEM", "ERR_TEMPLATE_VALIDATION_FAILED",
                    "人工切换基线失败: " + ex.getMessage());
            toPendingManual(task, "人工切换基线失败: " + ex.getMessage());
        }
    }
    private void doAdvance(Task task) {
        Long taskId = task.getId();
        List<String> requiredCapabilities = extractRequiredCapabilities(task);

        // 5.4.2 规划上下文构建
        ContextSnapshot snapshot = contextSnapshotService.buildSnapshot(taskId, requiredCapabilities);
        taskEventService.append(taskId, "CONTEXT_SNAPSHOT_GENERATED", "SYSTEM", null,
                "生成规划上下文快照" + snapshot.getSnapshotCode());

        Map<String, Object> coverage = parseMap(snapshot.getCapabilityCoverage());
        List<String> missingCapabilities = (List<String>) coverage.getOrDefault("missing", List.of());
        if (!requiredCapabilities.isEmpty() && missingCapabilities.size() == requiredCapabilities.size()) {
            // 业务规则7：任务族所需能力类型完全缺失时，直接生成能力缺口异常，不再调用规划模型
            taskEventService.append(taskId, "PLAN_GENERATED", "SYSTEM", "ERR_CAPABILITY_GAP_ALL_MISSING",
                    "任务族所需能力类型完全缺失: " + missingCapabilities);
            downgradeOrManual(task, "能力缺口: 任务族所需能力类型" + missingCapabilities + "完全缺失");
            return;
        }

        // 5.4.3 候选计划生成
        PlanningResponse planningResponse = callPlanningModel(task, snapshot, requiredCapabilities);
        if (planningResponse == null) {
            // 模型服务不可用/超时/结构无法解析，转基线模板降级或待人工，不下发设备指令
            downgradeOrManual(task, "候选计划生成失败或模型服务不可用");
            return;
        }

        List<Map<String, Object>> steps = planningResponse.getPlanSteps();
        if (steps == null || steps.size() > MAX_STEPS) {
            // 备选路径2a：模型返回步骤数超过5，直接判定结构校验失败，不做自动截断
            taskEventService.append(taskId, "PLAN_VALIDATED", "SYSTEM", "ERR_STEP_LIMIT_EXCEEDED",
                    "候选计划步骤数" + (steps == null ? 0 : steps.size()) + "超过上限5或为空");
            downgradeOrManual(task, "候选计划结构校验失败：步骤数超过5或响应为空");
            return;
        }

        PlanVersion planVersion = new PlanVersion();
        planVersion.setTaskId(taskId);
        planVersion.setVersionNo((int) (planVersionMapper.countByTaskId(taskId) + 1));
        planVersion.setSource("AUTONOMOUS");
        planVersion.setSnapshotId(snapshot.getSnapshotCode());
        planVersion.setPlanSteps(toJson(steps));
        planVersion.setConfidence(planningResponse.getConfidence());
        planVersionMapper.insert(planVersion);
        task.setCurrentPlanVersionId(planVersion.getId());
        taskMapper.update(task);
        taskEventService.append(taskId, "PLAN_GENERATED", "SYSTEM", null,
                "候选计划生成完成，来源AUTONOMOUS，版本" + planVersion.getVersionNo());

        // 5.4.4 计划三类校验，约束校验维度接入5.6.1任务定义声明的可用能力类型范围
        List<Map<String, Object>> snapshotAgents = contextSnapshotService.parseAgents(snapshot.getAgents());
        List<String> allowedCapabilityTypes = allowedCapabilityTypes(task.getTaskFamily());
        PlanValidationResult validation = planValidationService.validate(steps, snapshotAgents, allowedCapabilityTypes, task.getTaskFamily());
        planValidationService.requireCoreScenarioCoverage(steps, task.getTaskFamily(), validation);
        applyValidationResult(planVersion, validation);

        if (!validation.isAllPassed()) {
            taskEventService.append(taskId, "PLAN_VALIDATED", "SYSTEM", "ERR_VALIDATION_FAILED",
                    "候选计划三类校验未通过: " + validation.getErrors().size() + "项错误");
            downgradeOrManual(task, "候选计划三类校验未通过，转基线模板降级");
            return;
        }

        planVersion.setFrozenAt(LocalDateTime.now());
        planVersionMapper.update(planVersion);
        taskEventService.append(taskId, "PLAN_VALIDATED", "SYSTEM", null, "候选计划三类校验全部通过，已冻结版本");

        task.setStatus(TaskStatus.SUPERVISING);
        task.setUpdatedAt(LocalDateTime.now());
        taskMapper.update(task);

        // 5.4.5 监督智能体风险判定
        judgeAndRoute(task, planVersion, snapshot, planningResponse);
    }

    /**
     * 对应5.4.5：低风险自动进待分配；高风险自动进基线降级；无法确定/服务不可用进待人工处理。
     */
    private void judgeAndRoute(Task task, PlanVersion planVersion, ContextSnapshot snapshot,
                                PlanningResponse planningResponse) {
        int minCandidateCount = minCandidateCount(planVersion, snapshot, task.getTaskFamily());
        RiskAssessmentResult riskResult;
        try {
            riskResult = riskAssessmentService.assess(planVersion, task.getTaskFamily(), snapshot.getGeneratedAt(),
                    Boolean.TRUE.equals(planningResponse.getCandidateDiverse()), minCandidateCount);
        } catch (Exception e) {
            // 异常路径4b：监督服务不可用或判定超时，进入待人工处理，不下发设备指令
            taskEventService.append(task.getId(), "SUPERVISION_JUDGED", "SYSTEM", "ERR_SUPERVISION_UNAVAILABLE",
                    "监督服务不可用或判定异常: " + e.getMessage());
            toPendingManual(task, "监督服务不可用或判定异常: " + e.getMessage());
            return;
        }

        planVersion.setRiskLevel(riskResult.getRiskLevel());
        planVersion.setRiskReasonCode(riskResult.getRiskReasonCode());
        planVersion.setJudgmentBasis(riskResult.getJudgmentBasis());
        planVersion.setRuleSetVersion(riskResult.getRuleSetVersion());
        planVersionMapper.update(planVersion);

        taskEventService.append(task.getId(), "SUPERVISION_JUDGED", "SYSTEM", riskResult.getRiskReasonCode(),
                "监督判定: " + riskResult.getRiskLevel() + "，" + riskResult.getJudgmentBasis());

        switch (riskResult.getRiskLevel()) {
            case "LOW" -> {
                task.setStatus(TaskStatus.PENDING_ASSIGNMENT);
                task.setUpdatedAt(LocalDateTime.now());
                taskMapper.update(task);
                // 对应5.5.1前置条件：低风险计划冻结后立即启动执行监督链路，开始设备分配
                taskExecutionOrchestrator.startExecution(task.getId(), planVersion.getId());
            }
            case "HIGH" -> downgradeOrManual(task, "监督判定高风险: " + riskResult.getRiskReasonCode());
            default -> toPendingManual(task, "监督智能体输出无法确定");
        }
    }

    /** 单次任务申请资源时的最小可用候选设备数量，跨全部步骤取最小值（对应RULE_RESOURCE_CRITICAL） */
    @SuppressWarnings("unchecked")
    private int minCandidateCount(PlanVersion planVersion, ContextSnapshot snapshot, String taskFamily) {
        List<Map<String, Object>> steps = parseSteps(planVersion.getPlanSteps());
        int min = Integer.MAX_VALUE;
        for (Map<String, Object> step : steps) {
            String capabilityType = String.valueOf(step.get("capabilityType"));
            int count = contextSnapshotService.countAvailableCandidates(snapshot, capabilityType, taskFamily);
            min = Math.min(min, count);
        }
        return min == Integer.MAX_VALUE ? 0 : min;
    }

    /**
     * 对应5.4.6：自动选择满足任务目标、能力和五步限制的已启用基线模板，模板仍须通过三类校验；
     * 无匹配模板或模板校验失败时才进入待人工处理。
     */
    private void downgradeOrManual(Task task, String downgradeReason) {
        Long taskId = task.getId();
        String taskFamily = task.getTaskFamily();
        Optional<BaselineTemplate> matched = taskFamily == null ? Optional.empty()
                : baselineTemplateService.matchForDowngrade(taskFamily);

        if (matched.isEmpty()) {
            taskEventService.append(taskId, "BASELINE_DOWNGRADED", "SYSTEM", "ERR_NO_BASELINE_TEMPLATE",
                    "无匹配的已启用基线模板: " + downgradeReason);
            toPendingManual(task, downgradeReason + "；且无匹配的已启用基线模板");
            return;
        }

        BaselineTemplate template = matched.get();
        // Bind typed template defaults before real execution while retaining original scene context.
        try {
            Map<String,Object> scene = task.getSceneParams()==null ? new java.util.LinkedHashMap<>()
                    : new java.util.LinkedHashMap<>(MAPPER.readValue(task.getSceneParams(),Map.class));
            List<Map<String,Object>> fields=MAPPER.readValue(template.getInputParams(),List.class);
            Map<String,Object> supplied=new java.util.LinkedHashMap<>();
            for (var field:fields) if (scene.containsKey(field.get("name"))) supplied.put(String.valueOf(field.get("name")),scene.get(field.get("name")));
            scene.putAll(com.airport.ai.device.ParameterValues.materialize(template.getInputParams(),supplied));
            task.setSceneParams(toJson(scene)); taskMapper.update(task);
        } catch (Exception ex) {
            toPendingManual(task,"基线模板输入无法绑定: " + ex.getMessage()); return;
        }
        List<Map<String, Object>> templateSteps = normalizeTemplateSteps(parseSteps(template.getSteps()));

        // 重新构建上下文快照供模板校验使用（模板步骤同样需要能力/在线候选校验）
        List<String> requiredCapabilities = templateSteps.stream()
                .map(s -> String.valueOf(s.get("capabilityType"))).distinct().toList();
        ContextSnapshot snapshot = contextSnapshotService.buildSnapshot(taskId, requiredCapabilities);
        List<Map<String, Object>> snapshotAgents = contextSnapshotService.parseAgents(snapshot.getAgents());

        PlanValidationResult validation = planValidationService.validate(templateSteps, snapshotAgents, null, task.getTaskFamily());
        planValidationService.requireCoreScenarioCoverage(templateSteps, task.getTaskFamily(), validation);

        PlanVersion downgradedVersion = new PlanVersion();
        downgradedVersion.setTaskId(taskId);
        downgradedVersion.setVersionNo((int) (planVersionMapper.countByTaskId(taskId) + 1));
        downgradedVersion.setSource("BASELINE_TEMPLATE");
        downgradedVersion.setBaselineTemplateId(template.getId());
        downgradedVersion.setSnapshotId(snapshot.getSnapshotCode());
        downgradedVersion.setPlanSteps(toJson(templateSteps));
        applyValidationResult(downgradedVersion, validation);

        if (!validation.isAllPassed()) {
            downgradedVersion.setValidationErrors(toJson(validation.getErrors()));
            planVersionMapper.insert(downgradedVersion);
            taskEventService.append(taskId, "BASELINE_DOWNGRADED", "SYSTEM", "ERR_TEMPLATE_VALIDATION_FAILED",
                    "所选基线模板" + template.getTemplateName() + "三类校验未通过");
            toPendingManual(task, downgradeReason + "；所选基线模板校验失败");
            return;
        }

        downgradedVersion.setFrozenAt(LocalDateTime.now());
        planVersionMapper.insert(downgradedVersion);

        task.setCurrentPlanVersionId(downgradedVersion.getId());
        task.setDowngradeReason(downgradeReason);
        task.setFailureReason(null);
        task.setStatus(TaskStatus.DOWNGRADING);
        task.setUpdatedAt(LocalDateTime.now());
        taskMapper.update(task);

        taskEventService.append(taskId, "BASELINE_DOWNGRADED", "SYSTEM", null,
                "已自动切换至基线模板" + template.getTemplateName() + "(" + template.getTemplateVersion() + ")，原因: " + downgradeReason);

        // 对应5.5.1前置条件：降级执行同样立即启动执行监督链路
        taskExecutionOrchestrator.startExecution(taskId, downgradedVersion.getId());
    }

    private void toPendingManual(Task task, String reason) {
        task.setStatus(TaskStatus.PENDING_MANUAL);
        task.setFailureReason(reason);
        task.setUpdatedAt(LocalDateTime.now());
        taskMapper.update(task);
    }

    private void applyValidationResult(PlanVersion planVersion, PlanValidationResult validation) {
        planVersion.setStructureCheckResult(validation.getStructureCheckResult());
        planVersion.setCapabilityCheckResult(validation.getCapabilityCheckResult());
        planVersion.setConstraintCheckResult(validation.getConstraintCheckResult());
        planVersion.setValidationErrors(toJson(validation.getErrors()));
        planVersionMapper.update(planVersion);
    }

    @SuppressWarnings("unchecked")
    private PlanningResponse callPlanningModel(Task task, ContextSnapshot snapshot, List<String> requiredCapabilities) {
        PlanningRequest request = new PlanningRequest();
        request.setRequestId(UUID.randomUUID().toString());
        request.setTaskGoal(task.getTaskGoal());
        request.setTaskFamily(task.getTaskFamily());
        request.setSceneParams(parseMap(task.getSceneParams()));
        request.setConstraints(List.of("不得下发运动安全控制指令", "步骤数不超过5"));

        request.setCapabilityContext(contextSnapshotService.capabilityContext(snapshot, requiredCapabilities));
        request.setRemainingStepQuota(MAX_STEPS);
        request.setCompletedSteps(List.of());

        PlanningResponse response = planningModelService.generatePlan(request);
        if (response == null || !response.isSuccess()) {
            String errorMessage = response == null ? "响应为空" : response.getErrorMessage();
            taskEventService.append(task.getId(), "PLAN_GENERATED", "SYSTEM", "ERR_PLANNING_MODEL_FAILED",
                    "候选计划生成调用失败: " + errorMessage);
            return null;
        }
        return response;
    }

    /**
     * 基线模板步骤（5.3.1定义：capabilityType/paramMapping/stepTimeout/completionCondition）
     * 与自主规划步骤（5.4.3业务规则4：stepGoal/capabilityType/inputParams/precondition/
     * completionCondition/failureHandling六要素）字段结构不同——基线模板本身没有stepGoal/
     * precondition/failureHandling字段。PlanValidationService的结构校验对两种来源步骤
     * 一视同仁要求六要素齐全，若不做归一化，任何基线模板都会在此处必然结构校验失败，
     * 等于废掉"降级到基线模板"这条安全兜底路径。此处补齐缺失字段为固定业务语义占位值，
     * 不改变步骤实际执行内容（paramMapping/completionCondition等原样保留）。
     */
    private List<Map<String, Object>> normalizeTemplateSteps(List<Map<String, Object>> templateSteps) {
        return templateSteps.stream().map(step -> {
            Map<String, Object> normalized = new java.util.LinkedHashMap<>(step);
            normalized.putIfAbsent("stepGoal", "执行" + normalized.get("capabilityType") + "能力（基线模板步骤）");
            normalized.putIfAbsent("precondition", "候选设备在线且空闲");
            normalized.putIfAbsent("failureHandling", "重试一次或转人工处理");
            if (!normalized.containsKey("inputParams") && normalized.get("paramMapping") != null) {
                normalized.put("inputParams", Map.of());
            }
            return normalized;
        }).toList();
    }

    /**
     * 任务族所需能力类型清单：优先取5.6.1任务定义声明的可用能力类型（权威来源），
     * 任务族未关联任务定义（如历史数据或纯基线模板任务族）时兜底取基线模板步骤能力集合。
     */
    private List<String> extractRequiredCapabilities(Task task) {
        if (task.getTaskFamily() == null) {
            return List.of();
        }
        Optional<TaskDefinition> definition = taskDefinitionService.findByCode(task.getTaskFamily());
        if (definition.isPresent()) {
            return parseCapabilityTypesJson(definition.get().getAvailableCapabilityTypes());
        }
        return baselineTemplateService.listAll().stream()
                .filter(t -> task.getTaskFamily().equals(t.getTaskFamily()))
                .flatMap(t -> parseSteps(t.getSteps()).stream())
                .map(s -> String.valueOf(s.get("capabilityType")))
                .filter(c -> c != null && !"null".equals(c))
                .distinct()
                .toList();
    }

    /** 供5.4.4约束校验使用：任务族无关联任务定义时不做能力范围约束（返回null） */
    private List<String> allowedCapabilityTypes(String taskFamily) {
        if (taskFamily == null) return null;
        return taskDefinitionService.findByCode(taskFamily)
                .map(d -> parseCapabilityTypesJson(d.getAvailableCapabilityTypes()))
                .orElse(null);
    }

    @SuppressWarnings("unchecked")
    private List<String> parseCapabilityTypesJson(String json) {
        if (json == null || json.isBlank()) return List.of();
        try {
            return MAPPER.readValue(json, List.class);
        } catch (Exception e) {
            return List.of();
        }
    }

    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> parseSteps(String json) {
        if (json == null || json.isBlank()) {
            return List.of();
        }
        try {
            return MAPPER.readValue(json, List.class);
        } catch (Exception e) {
            throw new RuntimeException("解析失败: " + json, e);
        }
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> parseMap(String json) {
        if (json == null || json.isBlank()) {
            return Map.of();
        }
        try {
            return MAPPER.readValue(json, Map.class);
        } catch (Exception e) {
            throw new RuntimeException("解析失败: " + json, e);
        }
    }

    private String toJson(Object value) {
        try {
            return MAPPER.writeValueAsString(value);
        } catch (Exception e) {
            throw new RuntimeException("序列化失败", e);
        }
    }
}
