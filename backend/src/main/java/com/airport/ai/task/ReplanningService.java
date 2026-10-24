package com.airport.ai.task;

import com.airport.ai.baseline.BaselineTemplate;
import com.airport.ai.baseline.BaselineTemplateService;
import com.airport.ai.device.ParameterValues;
import com.airport.ai.event.TaskEventService;
import com.airport.ai.planning.PlanningModelService;
import com.airport.ai.planning.PlanningRequest;
import com.airport.ai.planning.PlanningResponse;
import com.airport.ai.risk.RiskAssessmentResult;
import com.airport.ai.risk.RiskAssessmentService;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.UUID;

/**
 * 对应5.5.4局部重新规划。每个任务最多触发一次（业务规则1，tasks.replan_used），
 * 不改变原始目标（业务规则2），保留已完成步骤结果，仅替换失败步骤及其后续步骤（业务规则3）。
 * 新版本仍受五步限制，剩余额度=5-已完成步骤数（业务规则4），复用B4~B6链路重新构建
 * 上下文、三类校验、监督判定，判高风险时仍按5.4.6自动基线降级（业务规则9）。
 */
@Service
public class ReplanningService {
    @org.springframework.beans.factory.annotation.Autowired
    private com.airport.ai.taskdef.TaskDefinitionMapper definitions;

    private static final ObjectMapper MAPPER = new ObjectMapper();
    private static final int MAX_STEPS = 5;

    private final TaskMapper taskMapper;
    private final PlanVersionMapper planVersionMapper;
    private final TaskStepAssignmentMapper assignmentMapper;
    private final ContextSnapshotService contextSnapshotService;
    private final PlanValidationService planValidationService;
    private final PlanningModelService planningModelService;
    private final RiskAssessmentService riskAssessmentService;
    private final TaskExecutionOrchestrator taskExecutionOrchestrator;
    private final TaskEventService taskEventService;
    private final BaselineTemplateService baselineTemplateService;

    public ReplanningService(TaskMapper taskMapper,
                              PlanVersionMapper planVersionMapper,
                              TaskStepAssignmentMapper assignmentMapper,
                              ContextSnapshotService contextSnapshotService,
                              PlanValidationService planValidationService,
                              PlanningModelService planningModelService,
                              RiskAssessmentService riskAssessmentService,
                              TaskExecutionOrchestrator taskExecutionOrchestrator,
                              TaskEventService taskEventService,
                              BaselineTemplateService baselineTemplateService) {
        this.taskMapper = taskMapper;
        this.planVersionMapper = planVersionMapper;
        this.assignmentMapper = assignmentMapper;
        this.contextSnapshotService = contextSnapshotService;
        this.planValidationService = planValidationService;
        this.planningModelService = planningModelService;
        this.riskAssessmentService = riskAssessmentService;
        this.taskExecutionOrchestrator = taskExecutionOrchestrator;
        this.taskEventService = taskEventService;
        this.baselineTemplateService = baselineTemplateService;
    }

    /**
     * @param failedStepSeq 触发重规划的失败步骤序号，其之前（不含）的COMPLETED步骤原样保留，
     *                      该步骤及其后续步骤全部替换为新计划
     * @param reason        重规划原因（异常类型+原因码），写入tasks.replanning_reason
     */
    @Transactional
    public void replan(Long taskId, Integer failedStepSeq, String reason) {
        Task task = taskMapper.findById(taskId).orElseThrow();
        if (Boolean.TRUE.equals(task.getReplanUsed())) {
            toPendingManual(task, "重新规划机会已使用，不允许第二次请求");
            return;
        }
        // 备选路径2a：剩余额度为0直接判无法重规划（异常发生步骤本身即占用了一个步骤名额，
        // 但该步骤已失败不计入"已完成"，故剩余额度=5-已完成步骤数，允许等于1时仍可重规划1个替换步骤）
        List<TaskStepAssignment> assignments = assignmentMapper.findByPlanVersionIdOrderByStepSeqAsc(task.getCurrentPlanVersionId());
        long completedCount = assignments.stream().filter(a -> "COMPLETED".equals(a.getStepStatus())).count();
        int remainingQuota = MAX_STEPS - (int) completedCount;
        if (remainingQuota <= 0) {
            taskEventService.append(taskId, "REPLAN_FAILED", "SYSTEM", "ERR_STEP_QUOTA_EXHAUSTED",
                    "已完成步骤数达到5步上限，无剩余步骤额度，无法重新规划");
            toPendingManual(task, "重新规划失败：已完成步骤数达到5步上限，无剩余额度");
            return;
        }

        PlanVersion originalVersion = planVersionMapper.findById(task.getCurrentPlanVersionId()).orElseThrow();
        List<Map<String, Object>> originalSteps = parseSteps(originalVersion.getPlanSteps());
        Map<Integer, TaskStepAssignment> completedAssignments = assignments.stream()
                .filter(a -> "COMPLETED".equals(a.getStepStatus()) && a.getStepSeq() < failedStepSeq)
                .collect(java.util.stream.Collectors.toMap(TaskStepAssignment::getStepSeq, a -> a));
        List<Map<String, Object>> completedSteps = new ArrayList<>();
        for (Map<String, Object> original : originalSteps) {
            Integer seq = asInteger(original.get("stepSeq"));
            if (seq == null || seq >= failedStepSeq) continue;
            TaskStepAssignment completed = completedAssignments.get(seq);
            if (completed == null) {
                toPendingManual(task, "重规划前序步骤缺少实际完成记录，不允许假定为已完成");
                return;
            }
            Map<String, Object> preserved = new java.util.LinkedHashMap<>(original);
            preserved.put("executionResult", completed.getExecutionResult());
            preserved.put("outputParams", parseObject(completed.getOutputParams()));
            preserved.put("originalCommandId", completed.getCommandId());
            completedSteps.add(preserved);
        }

        List<String> allowedTypes=null;
        String definitionConstraint=null;
        if (definitions!=null && task.getTaskFamily()!=null) {
            var definition=definitions.findByDefinitionCode(task.getTaskFamily());
            if (definition.isPresent()) {
                String description=definition.get().getConstraintDescription();
                definitionConstraint=description;
                try { allowedTypes=MAPPER.readValue(definition.get().getAvailableCapabilityTypes(),List.class); }
                catch (Exception ex) { toPendingManual(task,"任务定义能力范围无法解析，禁止重新规划执行"); return; }
            }
        }

        List<String> requiredCapabilities = originalSteps.stream()
                .filter(s -> asInteger(s.get("stepSeq")) >= failedStepSeq)
                .map(s -> String.valueOf(s.get("capabilityType")))
                .distinct().toList();

        List<String> contextCapabilities=allowedTypes==null ? requiredCapabilities : allowedTypes;
        ContextSnapshot snapshot = contextSnapshotService.buildSnapshot(taskId, contextCapabilities);
        taskEventService.append(taskId, "CONTEXT_SNAPSHOT_GENERATED", "SYSTEM", null,
                "局部重新规划重建上下文快照" + snapshot.getSnapshotCode());

        PlanningRequest request = new PlanningRequest();
        request.setRequestId(UUID.randomUUID().toString());
        request.setTaskGoal(task.getTaskGoal());
        request.setTaskFamily(task.getTaskFamily());
        request.setSceneParams(parseObject(task.getSceneParams()));
        request.setCapabilityContext(contextSnapshotService.capabilityContext(snapshot, contextCapabilities));
        List<String> constraints=new ArrayList<>(List.of("不得下发运动安全控制指令", "保留已完成步骤不变", "仅替换步骤" + failedStepSeq + "及其后续步骤", "本次异常: " + reason));
        Object originalConstraints=parseObject(task.getGoalParsingResult()).get("constraints");
        if (originalConstraints instanceof List<?> values) values.stream().filter(java.util.Objects::nonNull).map(String::valueOf).forEach(constraints::add);
        if (definitionConstraint!=null && !definitionConstraint.isBlank()) constraints.add(definitionConstraint);
        request.setConstraints(constraints.stream().distinct().toList());
        request.setRemainingStepQuota(remainingQuota);
        request.setCompletedSteps(completedSteps);

        // A failed/timeout attempt still consumes the single opportunity required by SRS_F019.
        if (taskMapper.claimReplan(taskId,reason)!=1) {
            taskEventService.append(taskId,"REPLAN_DUPLICATE_IGNORED","SYSTEM",null,"重新规划机会已由另一请求占用，未重复调用模型");
            return;
        }
        task.setReplanUsed(true);
        task.setReplanningReason(reason);
        taskMapper.update(task);

        PlanningResponse response;
        try {
            response = planningModelService.generatePlan(request);
        } catch (Exception e) {
            response = null;
        }

        // 异常路径4a：规划请求超时或模型不可用
        if (response == null || !response.isSuccess()) {
            taskEventService.append(taskId, "REPLAN_FAILED", "SYSTEM", "ERR_REPLANNING_MODEL_FAILED",
                    "局部重新规划调用模型失败: " + (response == null ? "响应为空" : response.getErrorMessage()));
            toPendingManual(task, "局部重新规划失败：规划模型服务不可用或超时");
            return;
        }

        List<Map<String, Object>> newTailSteps = response.getPlanSteps();
        if (newTailSteps == null || newTailSteps.isEmpty() || newTailSteps.size() > remainingQuota) {
            taskEventService.append(taskId, "REPLAN_FAILED", "SYSTEM", "ERR_STEP_LIMIT_EXCEEDED",
                    "新计划替换步骤数超过剩余额度" + remainingQuota + "或为空");
            toPendingManual(task, "局部重新规划失败：新计划步骤数超过剩余额度");
            return;
        }

        // 模型返回的替换步骤stepSeq通常从1起算，须重新编号以衔接在已完成步骤之后，避免序号冲突
        List<Map<String, Object>> renumberedTail = new ArrayList<>();
        int nextSeq = failedStepSeq;
        for (Map<String, Object> step : newTailSteps) {
            Map<String, Object> copy = new java.util.LinkedHashMap<>(step);
            copy.put("stepSeq", nextSeq++);
            renumberedTail.add(copy);
        }
        List<Map<String, Object>> mergedSteps = new ArrayList<>(completedSteps);
        mergedSteps.addAll(renumberedTail);

        List<Map<String, Object>> snapshotAgents = contextSnapshotService.parseAgents(snapshot.getAgents());
        // Completed frozen actions retain their actual results and do not require currently online devices.
        PlanValidationResult validation = planValidationService.validate(renumberedTail, snapshotAgents, allowedTypes, task.getTaskFamily());
        planValidationService.requireCoreScenarioCoverage(mergedSteps, task.getTaskFamily(), validation);
        if (mergedSteps.size() > MAX_STEPS) validation.failStructure("最终路径超过五步", null, "ERR_STEP_LIMIT_EXCEEDED");

        PlanVersion newVersion = new PlanVersion();
        newVersion.setTaskId(taskId);
        newVersion.setVersionNo((int) (planVersionMapper.countByTaskId(taskId) + 1));
        newVersion.setSource("AUTONOMOUS");
        newVersion.setSnapshotId(snapshot.getSnapshotCode());
        newVersion.setPlanSteps(toJson(mergedSteps));
        newVersion.setConfidence(response.getConfidence());
        newVersion.setStructureCheckResult(validation.getStructureCheckResult());
        newVersion.setCapabilityCheckResult(validation.getCapabilityCheckResult());
        newVersion.setConstraintCheckResult(validation.getConstraintCheckResult());
        newVersion.setValidationErrors(toJson(validation.getErrors()));
        planVersionMapper.insert(newVersion);

        task.setReplanUsed(true);
        task.setReplanningReason(reason);
        taskMapper.update(task);

        // 异常路径5b：新版本三类校验不通过
        if (!validation.isAllPassed()) {
            taskEventService.append(taskId, "REPLAN_FAILED", "SYSTEM", "ERR_VALIDATION_FAILED",
                    "重新规划后新计划版本" + newVersion.getVersionNo() + "三类校验未通过: " + validation.getErrors().size() + "项错误");
            toPendingManual(task, "局部重新规划失败：新计划版本三类校验未通过");
            return;
        }

        newVersion.setFrozenAt(LocalDateTime.now());
        planVersionMapper.update(newVersion);
        taskEventService.append(taskId, "PLAN_VALIDATED", "SYSTEM", null,
                "重新规划后新计划版本" + newVersion.getVersionNo() + "三类校验全部通过，已冻结");

        // 5.4.5：新版本仍须过监督判定，判高风险则按5.4.6自动基线降级（业务规则9）
        int minCandidateCount = renumberedTail.stream().map(step -> String.valueOf(step.get("capabilityType"))).distinct()
                .mapToInt(cap -> contextSnapshotService.countOnlineCandidates(snapshot, cap))
                .min().orElse(0);
        RiskAssessmentResult riskResult;
        try {
            riskResult = riskAssessmentService.assess(newVersion, task.getTaskFamily(), snapshot.getGeneratedAt(),
                    Boolean.TRUE.equals(response.getCandidateDiverse()), minCandidateCount);
        } catch (Exception e) {
            taskEventService.append(taskId, "SUPERVISION_JUDGED", "SYSTEM", "ERR_SUPERVISION_UNAVAILABLE",
                    "重新规划后监督服务不可用: " + e.getMessage());
            toPendingManual(task, "局部重新规划后监督判定失败：" + e.getMessage());
            return;
        }

        newVersion.setRiskLevel(riskResult.getRiskLevel());
        newVersion.setRiskReasonCode(riskResult.getRiskReasonCode());
        newVersion.setJudgmentBasis(riskResult.getJudgmentBasis());
        newVersion.setRuleSetVersion(riskResult.getRuleSetVersion());
        planVersionMapper.update(newVersion);
        taskEventService.append(taskId, "SUPERVISION_JUDGED", "SYSTEM", riskResult.getRiskReasonCode(),
                "重新规划后监督判定: " + riskResult.getRiskLevel() + "，" + riskResult.getJudgmentBasis());

        if ("HIGH".equals(riskResult.getRiskLevel())) {
            downgradeReplanned(task, completedSteps, failedStepSeq, remainingQuota, riskResult);
            return;
        }
        if (!"LOW".equals(riskResult.getRiskLevel())) {
            taskEventService.append(taskId, "REPLAN_FAILED", "SYSTEM", "ERR_REPLAN_RISK_UNDETERMINED",
                    "重新规划后新计划版本风险无法确定，转人工处理");
            toPendingManual(task, "局部重新规划后监督风险无法确定");
            return;
        }

        task.setCurrentPlanVersionId(newVersion.getId());
        task.setStatus(TaskStatus.PENDING_ASSIGNMENT);
        task.setFailureReason(null);
        task.setUpdatedAt(LocalDateTime.now());
        taskMapper.update(task);
        taskEventService.append(taskId, "REPLAN_SUCCEEDED", "SYSTEM", null,
                "局部重新规划成功，新计划版本" + newVersion.getVersionNo() + "已冻结，任务重新进入待分配");

        taskExecutionOrchestrator.startExecution(taskId, newVersion.getId(), failedStepSeq);
    }

    /** High-risk replanning follows 5.4.6 while retaining actually completed actions. */
    private void downgradeReplanned(Task task, List<Map<String, Object>> completedSteps,
                                    int failedStepSeq, int remainingQuota, RiskAssessmentResult risk) {
        Long taskId = task.getId();
        Optional<BaselineTemplate> matched = task.getTaskFamily() == null ? Optional.empty()
                : baselineTemplateService.matchForDowngrade(task.getTaskFamily());
        if (matched.isEmpty()) {
            baselineUnavailable(task, "无匹配的已启用基线模板");
            return;
        }
        BaselineTemplate template = matched.get();
        List<Map<String, Object>> templateSteps;
        Map<String, Object> scene = new java.util.LinkedHashMap<>(parseObject(task.getSceneParams()));
        try {
            templateSteps = normalizeTemplateSteps(parseSteps(template.getSteps()));
            @SuppressWarnings("unchecked")
            List<Map<String, Object>> fields = MAPPER.readValue(template.getInputParams(), List.class);
            Map<String, Object> supplied = new java.util.LinkedHashMap<>();
            for (Map<String, Object> field : fields) {
                String name = String.valueOf(field.get("name"));
                if (scene.containsKey(name)) supplied.put(name, scene.get(name));
            }
            scene.putAll(ParameterValues.materialize(template.getInputParams(), supplied));
        } catch (Exception ex) {
            baselineUnavailable(task, "基线模板步骤或输入无法绑定: " + ex.getMessage());
            return;
        }

        // A completed action may only be skipped when the template has the same
        // capability and completion condition at that position. Otherwise an
        // automatic switch could silently repeat or omit a physical action.
        if (templateSteps.size() <= completedSteps.size()) {
            baselineUnavailable(task, "基线模板没有可替换的剩余步骤");
            return;
        }
        for (int index = 0; index < completedSteps.size(); index++) {
            Map<String, Object> completed = completedSteps.get(index);
            Map<String, Object> baseline = templateSteps.get(index);
            Object completedCondition = completed.get("completionCondition");
            Object baselineCondition = baseline.get("completionCondition");
            if (!Objects.equals(completed.get("capabilityType"), baseline.get("capabilityType"))
                    || completedCondition == null || String.valueOf(completedCondition).isBlank()
                    || !Objects.equals(completedCondition, baselineCondition)) {
                baselineUnavailable(task, "基线模板前缀与已完成步骤不一致，禁止重复或跳过动作");
                return;
            }
        }
        List<Map<String, Object>> tail = new ArrayList<>();
        int sequence = failedStepSeq;
        for (Map<String, Object> step : templateSteps.subList(completedSteps.size(), templateSteps.size())) {
            Map<String, Object> copy = new java.util.LinkedHashMap<>(step);
            copy.put("stepSeq", sequence++);
            tail.add(copy);
        }
        if (tail.size() > remainingQuota) {
            baselineUnavailable(task, "基线模板剩余步骤超过五步路径额度" + remainingQuota);
            return;
        }
        List<Map<String, Object>> merged = new ArrayList<>(completedSteps);
        merged.addAll(tail);
        List<String> capabilities = tail.stream().map(s -> String.valueOf(s.get("capabilityType"))).distinct().toList();
        ContextSnapshot snapshot = contextSnapshotService.buildSnapshot(taskId, capabilities);
        taskEventService.append(taskId, "CONTEXT_SNAPSHOT_GENERATED", "SYSTEM", null,
                "重规划高风险基线降级快照" + snapshot.getSnapshotCode());
        PlanValidationResult validation = planValidationService.validate(tail,
                contextSnapshotService.parseAgents(snapshot.getAgents()), null, task.getTaskFamily());
        planValidationService.requireCoreScenarioCoverage(merged, task.getTaskFamily(), validation);
        if (merged.size() > MAX_STEPS) validation.failStructure("最终路径超过五步", null, "ERR_STEP_LIMIT_EXCEEDED");

        PlanVersion baselineVersion = new PlanVersion();
        baselineVersion.setTaskId(taskId);
        baselineVersion.setVersionNo((int) (planVersionMapper.countByTaskId(taskId) + 1));
        baselineVersion.setSource("BASELINE_TEMPLATE");
        baselineVersion.setBaselineTemplateId(template.getId());
        baselineVersion.setSnapshotId(snapshot.getSnapshotCode());
        baselineVersion.setPlanSteps(toJson(merged));
        baselineVersion.setStructureCheckResult(validation.getStructureCheckResult());
        baselineVersion.setCapabilityCheckResult(validation.getCapabilityCheckResult());
        baselineVersion.setConstraintCheckResult(validation.getConstraintCheckResult());
        baselineVersion.setValidationErrors(toJson(validation.getErrors()));
        if (!validation.isAllPassed()) {
            planVersionMapper.insert(baselineVersion);
            baselineUnavailable(task, "基线模板三类校验未通过");
            return;
        }
        baselineVersion.setFrozenAt(LocalDateTime.now());
        planVersionMapper.insert(baselineVersion);

        task.setSceneParams(toJson(scene));
        task.setCurrentPlanVersionId(baselineVersion.getId());
        task.setDowngradeReason("局部重新规划后监督判定高风险: " + risk.getRiskReasonCode());
        task.setFailureReason(null);
        task.setStatus(TaskStatus.DOWNGRADING);
        task.setUpdatedAt(LocalDateTime.now());
        taskMapper.update(task);
        taskEventService.append(taskId, "BASELINE_DOWNGRADED", "SYSTEM", risk.getRiskReasonCode(),
                "局部重规划后切换至基线模板" + template.getTemplateName() + "(" + template.getTemplateVersion()
                        + ")，保留" + completedSteps.size() + "个已完成步骤，剩余额度" + remainingQuota);
        taskExecutionOrchestrator.startExecution(taskId, baselineVersion.getId(), failedStepSeq);
    }

    private void baselineUnavailable(Task task, String detail) {
        taskEventService.append(task.getId(), "REPLAN_FAILED", "SYSTEM", "ERR_REPLAN_BASELINE_UNAVAILABLE", detail);
        toPendingManual(task, "局部重规划高风险降级失败：" + detail);
    }

    private List<Map<String, Object>> normalizeTemplateSteps(List<Map<String, Object>> steps) {
        return steps.stream().map(step -> {
            Map<String, Object> normalized = new java.util.LinkedHashMap<>(step);
            normalized.putIfAbsent("stepGoal", "执行" + normalized.get("capabilityType") + "能力（基线模板步骤）");
            normalized.putIfAbsent("precondition", "候选设备在线且空闲");
            normalized.putIfAbsent("failureHandling", "重试一次或转人工处理");
            normalized.putIfAbsent("inputParams", Map.of());
            return normalized;
        }).toList();
    }

    private void toPendingManual(Task task, String reason) {
        task.setStatus(TaskStatus.PENDING_MANUAL);
        task.setFailureReason(reason);
        task.setUpdatedAt(LocalDateTime.now());
        taskMapper.update(task);
    }

    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> parseSteps(String json) {
        try {
            return MAPPER.readValue(json, List.class);
        } catch (Exception e) {
            throw new RuntimeException("解析计划步骤失败", e);
        }
    }

    private Integer asInteger(Object value) {
        if (value == null) return null;
        if (value instanceof Integer i) return i;
        if (value instanceof Number n) return n.intValue();
        try { return Integer.parseInt(value.toString()); } catch (NumberFormatException e) { return null; }
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> parseObject(String json) {
        if (json == null || json.isBlank()) return Map.of();
        try { return MAPPER.readValue(json, Map.class); }
        catch (Exception ex) { throw new IllegalStateException("任务场景或已完成结果无法解析", ex); }
    }

    private String toJson(Object value) {
        try {
            return MAPPER.writeValueAsString(value);
        } catch (Exception e) {
            throw new RuntimeException("序列化失败", e);
        }
    }
}

