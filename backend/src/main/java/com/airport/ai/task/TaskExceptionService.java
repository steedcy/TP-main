package com.airport.ai.task;

import com.airport.ai.device.DeviceAgent;
import com.airport.ai.device.DeviceAgentMapper;
import com.airport.ai.event.TaskEventService;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Lazy;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

/**
 * 对应5.5.3异常识别与恢复。核心口径"先恢复，再按计划影响判断是否重规划"（业务规则3/4/6/7/8）：
 * 三类异常（设备离线、步骤失败、执行超时）先尝试一次指令重试或候选设备切换，仅当恢复失败且
 * 计划确实不可继续时才触发（一次）局部重新规划；无关设备离线仅记录不触发任何流程（业务规则5）。
 */
@Service
public class TaskExceptionService {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    @Autowired
    private com.airport.ai.baseline.BaselineDryRunLifecycle dryRunLifecycle;
    private final TaskMapper taskMapper;
    private final TaskStepAssignmentMapper assignmentMapper;
    private final TaskExceptionMapper taskExceptionMapper;
    private final DeviceAgentMapper deviceAgentMapper;
    private final TaskEventService taskEventService;
    private final TaskExecutionOrchestrator taskExecutionOrchestrator;
    private final ReplanningService replanningService;
    private final PlanVersionMapper planVersionMapper;
    private final java.util.concurrent.ConcurrentHashMap<Long, List<TaskException>> activeExceptions = new java.util.concurrent.ConcurrentHashMap<>();

    private List<TaskException> getTaskExceptions(Long taskId) {
        List<TaskException> persisted = taskExceptionMapper.findByTaskIdOrderByOccurredAtDesc(taskId);
        if (persisted != null && !persisted.isEmpty()) {
            return persisted;
        }
        return activeExceptions.getOrDefault(taskId, List.of());
    }

    public TaskExceptionService(TaskMapper taskMapper,
                                 TaskStepAssignmentMapper assignmentMapper,
                                 TaskExceptionMapper taskExceptionMapper,
                                 DeviceAgentMapper deviceAgentMapper,
                                 TaskEventService taskEventService,
                                 @Lazy TaskExecutionOrchestrator taskExecutionOrchestrator,
                                 @Lazy ReplanningService replanningService) {
        this(taskMapper, assignmentMapper, taskExceptionMapper, deviceAgentMapper, taskEventService,
                taskExecutionOrchestrator, replanningService, null);
    }

    @Autowired
    public TaskExceptionService(TaskMapper taskMapper,
                                 TaskStepAssignmentMapper assignmentMapper,
                                 TaskExceptionMapper taskExceptionMapper,
                                 DeviceAgentMapper deviceAgentMapper,
                                 TaskEventService taskEventService,
                                 @Lazy TaskExecutionOrchestrator taskExecutionOrchestrator,
                                 @Lazy ReplanningService replanningService,
                                 @Lazy PlanVersionMapper planVersionMapper) {
        this.taskMapper = taskMapper;
        this.assignmentMapper = assignmentMapper;
        this.taskExceptionMapper = taskExceptionMapper;
        this.deviceAgentMapper = deviceAgentMapper;
        this.taskEventService = taskEventService;
        this.taskExecutionOrchestrator = taskExecutionOrchestrator;
        this.replanningService = replanningService;
        this.planVersionMapper = planVersionMapper;
    }

    /**
     * 步骤失败/执行超时的统一入口。对应基本路径：记录异常 -&gt; 冻结未执行步骤 -&gt;
     * 尝试候选设备切换（恢复动作） -&gt; 恢复成功则续跑，失败则判断计划是否可继续。
     */
    @Transactional
    public void onStepFirstFailure(Long taskId, Integer stepSeq, String exceptionType, String reasonCode, String failureDetail) {
        Task task = taskMapper.findById(taskId).orElse(null);
        if (task == null || isTerminalOrManual(task.getStatus())) return;

        TaskException exception = new TaskException();
        exception.setTaskId(taskId);
        exception.setStepSeq(stepSeq);
        exception.setExceptionType(exceptionType);
        exception.setReasonCode(reasonCode != null ? reasonCode : "ERR_STEP_FAILED");
        exception.setRecoveryAction("指令重试");
        exception.setRecoveryResult(null);
        exception.setExceptionStatus("PROCESSING");
        exception.setOccurredAt(LocalDateTime.now());
        exception.setImpactConclusion("尝试指令重试1次，若成功则计划继续执行");
        taskExceptionMapper.insert(exception);
        activeExceptions.computeIfAbsent(taskId, k -> new java.util.concurrent.CopyOnWriteArrayList<>()).add(exception);

        taskEventService.append(taskId, "EXCEPTION_DETECTED", "SYSTEM", reasonCode != null ? reasonCode : exceptionType,
                "识别到异常: " + exceptionType + "，步骤" + stepSeq + "，详情: " + failureDetail);
    }

    @Transactional
    public void handleException(Long taskId, Integer stepSeq, String exceptionType, String detail) {
        String code = null;
        if (detail != null && detail.contains("原因: ")) {
            code = detail.substring(detail.indexOf("原因: ") + "原因: ".length()).trim();
        }
        handleException(taskId, stepSeq, exceptionType, code, detail);
    }

    @Transactional
    public void handleException(Long taskId, Integer stepSeq, String exceptionType, String reasonCode, String detail) {
        Task task = taskMapper.findById(taskId).orElseThrow();
        if (isTerminalOrManual(task.getStatus())) {
            return; // 任务已终止/待人工/终态，异常记录仍写但不再驱动流程
        }

        // 优先查找该步骤是否已有重试产生的 PROCESSING 异常记录；若无则新建
        TaskException exception = taskExceptionMapper.findByTaskIdOrderByOccurredAtDesc(taskId).stream()
                .filter(e -> stepSeq != null && stepSeq.equals(e.getStepSeq()) && "PROCESSING".equals(e.getExceptionStatus()))
                .findFirst().orElse(null);

        if (exception == null) {
            exception = new TaskException();
            exception.setTaskId(taskId);
            exception.setStepSeq(stepSeq);
            exception.setExceptionType(exceptionType);
            exception.setReasonCode(reasonCode != null ? reasonCode : detail);
            exception.setExceptionStatus("PROCESSING");
            exception.setOccurredAt(LocalDateTime.now());
            taskExceptionMapper.insert(exception);
            activeExceptions.computeIfAbsent(taskId, k -> new java.util.concurrent.CopyOnWriteArrayList<>()).add(exception);
            taskEventService.append(taskId, "EXCEPTION_DETECTED", "SYSTEM", reasonCode != null ? reasonCode : exceptionType,
                    "识别到异常: " + exceptionType + "，步骤" + stepSeq + "，详情: " + detail);
        } else {
            exception.setExceptionType(exceptionType);
            if (reasonCode != null) exception.setReasonCode(reasonCode);
        }

        if (Boolean.TRUE.equals(task.getIsDryRun())) {
            dryRunLifecycle.finish(taskId, false, detail);
            return;
        }
        freezeRemainingSteps(task.getId(), stepSeq);

        // 业务规则4/6/7：先尝试一次候选设备切换作为恢复动作（能力缺口无候选可切换时恢复直接失败）
        String excludeAgentCode = findOfflineAgentCode(taskId, stepSeq);
        boolean canRetry = ("CAPABILITY_GAP".equals(exceptionType) || "ASSIGNMENT_FAILED".equals(exceptionType))
                ? false // 无候选场景或全部候选已拒绝场景下"切换候选"已尝试穷尽，不重复
                : taskExecutionOrchestrator.hasAvailableCandidate(task.getCurrentPlanVersionId(), stepSeq,
                        excludeAgentCode == null ? List.of() : List.of(excludeAgentCode));

        // DEF-S3-108: "首次恢复动作"保持不可变，绝不被后续候选切换或无候选覆盖
        if (exception.getRecoveryAction() == null) {
            exception.setRecoveryAction(canRetry ? "候选设备切换"
                    : ("ASSIGNMENT_FAILED".equals(exceptionType) ? "全部候选设备均拒绝，恢复动作未执行" : "无可用候选设备，恢复动作未执行"));
        }

        if (canRetry) {
            exception.setRecoveryResult(null);
            exception.setExceptionStatus("PROCESSING");
            exception.setImpactConclusion("已尝试候选设备切换，等待新设备承接与执行反馈以确认最终恢复结果");
            taskExceptionMapper.update(exception);

            taskExecutionOrchestrator.retryAssignmentExcluding(task.getId(), task.getCurrentPlanVersionId(),
                    stepSeq, excludeAgentCode);
            // 重新分配本身可能立即失败并触发嵌套的异常处理（转人工、重规划等）。恢复结果以重新分配之后的
            // 任务实际状态为准，不能在任务已待人工/终止时再追加“恢复成功”（DEF-S3-066、F015.R08/F018.R09）
            Task after = taskMapper.findById(taskId).orElse(task);
            if (isTerminalOrManual(after.getStatus())) {
                markAllUnresolvedFailed(taskId, "候选设备切换后重新分配仍失败，任务已转入" + after.getStatus() + "，恢复未成功");
                taskEventService.append(taskId, "EXCEPTION_RECOVERY_FAILED", "SYSTEM", exceptionType,
                        "恢复动作: 候选设备切换，结果: 失败（重新分配后任务状态为" + after.getStatus() + "），异常类型: " + exceptionType
                                + "，影响结论: 候选设备切换恢复失败");
                return;
            }
            // 候选设备切换已下发，等待新设备承接并执行成功后再确认恢复成功（DEF-S3-066）
            return;
        }

        exception.setRecoveryResult("FAILED");
        taskExceptionMapper.update(exception);
        taskEventService.append(taskId, "EXCEPTION_RECOVERY_FAILED", "SYSTEM", exceptionType,
                "恢复动作: " + exception.getRecoveryAction() + "，结果: 失败，异常类型: " + exceptionType
                        + "，影响结论: 候选设备切换恢复失败，判断计划是否可继续");

        handleUnrecoverable(task, exception, stepSeq);
    }

    /**
     * 对应业务规则2/5：设备心跳超时离线时调用。仅当离线设备正占用当前任务的步骤才视为
     * "当前任务设备离线"并走完整恢复流程；占用其他任务或未占用任何任务的离线仅记录，不冻结不重规划。
     */
    @Transactional
    public void handleAgentOffline(DeviceAgent agent) {
        if (agent.getCurrentTaskId() != null) {
            handleException(agent.getCurrentTaskId(), agent.getCurrentStepSeq(), "AGENT_OFFLINE",
                    "设备代理" + agent.getAgentCode() + "心跳超时离线，正占用该任务步骤");
            return;
        }
        // 待分配阶段尚未设置current_task_id但已有步骤关联：同样属于关联任务，走恢复流程
        if (recoverAssignments(agent, "心跳超时离线") > 0) return;
        // 无关设备离线（SRS_F005.R06）：不冻结、不重规划，判断结果与原因码写入进行中任务的事件时间线
        for (Task task : taskMapper.findInProgressFormal()) {
            taskEventService.append(task.getId(), "UNRELATED_AGENT_OFFLINE_JUDGED", "SYSTEM",
                    "ERR_AGENT_OFFLINE_UNRELATED",
                    "设备代理" + agent.getAgentCode() + "离线，未占用本任务任何步骤，不影响计划，不触发重新规划");
        }
    }

    /**
     * 设备停用（SRS_F003.R06）：对该代理在正式任务中尚未结束的每个步骤关联（含待分配、尚未设置
     * current_task_id的情形）走同一条5.5.3恢复流程。返回处理的步骤数。
     */
    @Transactional
    public int handleAgentDisabled(DeviceAgent agent) {
        return recoverAssignments(agent, "因设备停用被释放");
    }

    private int recoverAssignments(DeviceAgent agent, String cause) {
        List<TaskStepAssignment> active = assignmentMapper.findActiveByAgentId(agent.getId());
        for (TaskStepAssignment assignment : active) {
            handleException(assignment.getTaskId(), assignment.getStepSeq(), "AGENT_OFFLINE",
                    "设备代理" + agent.getAgentCode() + cause + "，正占用该任务步骤");
        }
        return active.size();
    }

    /**
     * 对应异常路径4a/4b、5.5.3业务规则1a（降级任务基线执行失败不再二次自动降级）：
     * 恢复失败且判定计划不可继续，若重规划额度未用则触发5.5.4局部重新规划；
     * 额度已用或任务本身即为降级执行（DOWNGRADING）则直接转人工处理，不再自动降级。
     */
    /**
     * 对应DEF-S3-066与DEF-S3-105：指令重试成功或候选设备切换执行成功（完成条件满足）后，
     * 确认恢复成功并写入EXCEPTION_RECOVERED，补全恢复闭环与影响留痕。
     */
    @Transactional
    public void onStepRecovered(Long taskId, Integer stepSeq) {
        List<TaskException> list = getTaskExceptions(taskId);
        Task task = taskMapper.findById(taskId).orElse(null);
        boolean hasCandidateSwitched = false;
        boolean isOriginalRetrySuccess = false;
        if (task != null && task.getCurrentPlanVersionId() != null) {
            TaskStepAssignment assignment = assignmentMapper.findByPlanVersionIdOrderByStepSeqAsc(task.getCurrentPlanVersionId())
                    .stream()
                    .filter(a -> stepSeq != null && stepSeq.equals(a.getStepSeq()) && "COMPLETED".equals(a.getStepStatus()))
                    .findFirst().orElse(null);
            if (assignment != null) {
                if (assignment.getRejectedAgentIds() != null
                        && !assignment.getRejectedAgentIds().isBlank()
                        && !"[]".equals(assignment.getRejectedAgentIds().trim())) {
                    hasCandidateSwitched = true;
                } else if (assignment.getRetryCount() != null && assignment.getRetryCount() > 0) {
                    isOriginalRetrySuccess = true;
                }
            }
        }
        for (TaskException ex : list) {
            if (stepSeq != null && stepSeq.equals(ex.getStepSeq()) && !"RESOLVED".equals(ex.getExceptionStatus())) {
                boolean switched = hasCandidateSwitched
                        || (ex.getImpactConclusion() != null && ex.getImpactConclusion().contains("候选设备切换"))
                        || (ex.getRecoveryAction() != null && ex.getRecoveryAction().contains("候选设备切换"));
                boolean isRetry = !switched && (isOriginalRetrySuccess || (ex.getRecoveryAction() != null && ex.getRecoveryAction().contains("重试")));
                ex.setRecoveryResult("SUCCESS");
                ex.setExceptionStatus("RESOLVED");
                ex.setResolvedAt(LocalDateTime.now());
                ex.setResolvedBy("SYSTEM");
                String impact = isRetry
                        ? "自动重试成功，计划可继续执行，不触发重新规划"
                        : "已切换候选设备重新分配，计划可继续执行，不触发重新规划";
                ex.setImpactConclusion(impact);
                taskExceptionMapper.update(ex);
                String detail = isRetry
                        ? "恢复动作: 指令重试，结果: 成功，步骤" + stepSeq + "重试成功，异常类型: " + ex.getExceptionType()
                                + "，影响结论: 计划可继续执行，不触发重新规划"
                        : "恢复动作: 候选设备切换，结果: 成功，步骤" + stepSeq + "已重新分配，异常类型: " + ex.getExceptionType()
                                + "，影响结论: 计划可继续执行";
                taskEventService.append(taskId, "EXCEPTION_RECOVERED", "SYSTEM",
                        ex.getExceptionType(),
                        detail);
            }
        }
        // DEF-S3-122: 恢复成功后解冻合法未执行尾部步骤，允许后续编排继续推进
        if (task != null && task.getCurrentPlanVersionId() != null && !isTerminalOrManual(task.getStatus())) {
            for (TaskStepAssignment a : assignmentMapper.findByPlanVersionIdOrderByStepSeqAsc(task.getCurrentPlanVersionId())) {
                if (stepSeq != null && a.getStepSeq() > stepSeq && "FROZEN".equals(a.getStepStatus())) {
                    a.setStepStatus("PENDING_ASSIGNMENT");
                    a.setUpdatedAt(LocalDateTime.now());
                    assignmentMapper.update(a);
                }
            }
        }
    }

    private void markAllUnresolvedFailed(Long taskId, String reason) {
        List<TaskException> list = getTaskExceptions(taskId);
        for (TaskException ex : list) {
            if (!"RESOLVED".equals(ex.getExceptionStatus())) {
                ex.setRecoveryResult("FAILED");
                ex.setExceptionStatus("RESOLVED");
                ex.setResolvedAt(LocalDateTime.now());
                ex.setResolvedBy("SYSTEM");
                ex.setImpactConclusion(reason != null ? reason : "候选设备切换后重新分配仍失败（候选设备穷尽），任务转入人工处理，恢复未成功");
                taskExceptionMapper.update(ex);
            }
        }
    }

    @Transactional
    public void archiveAllUnresolvedOnTaskComplete(Long taskId) {
        List<TaskException> list = getTaskExceptions(taskId);
        for (TaskException ex : list) {
            if (!"RESOLVED".equals(ex.getExceptionStatus()) && !"IGNORED".equals(ex.getExceptionStatus())) {
                if (ex.getRecoveryResult() == null) {
                    ex.setRecoveryResult("FAILED");
                }
                ex.setExceptionStatus("RESOLVED");
                ex.setResolvedAt(LocalDateTime.now());
                ex.setResolvedBy("SYSTEM");
                if (ex.getImpactConclusion() == null) {
                    ex.setImpactConclusion("任务已完成，异常自动归档");
                }
                taskExceptionMapper.update(ex);
            }
        }
    }

    /**
     * 对应异常路径4a/4b、5.5.3业务规则1a（降级任务基线执行失败不再二次自动降级）：
     * 恢复失败且判定计划不可继续，若重规划额度未用则触发5.5.4局部重新规划；
     * 额度已用或任务本身即为降级执行（DOWNGRADING）则直接转人工处理，不再自动降级；
     * 对应DEF-S3-106：若恢复失败但为非关键步骤且原目标完成条件已满足，则步骤跳过、计划可继续执行，不触发重新规划。
     */
    private void handleUnrecoverable(Task task, TaskException exception, Integer stepSeq) {
        // 先评估当前或后续计划是否可继续执行（TC-058.S1 / SRS_F018.R03/R06/R08 / DEF-S3-106）
        if (isPlanContinuable(task, stepSeq)) {
            // 收口该步骤所有处于未完成状态的异常（DEF-S3-106: 解决529/540中旧异常206/224遗留PROCESSING问题）
            List<TaskException> list = getTaskExceptions(task.getId());
            for (TaskException ex : list) {
                if (stepSeq != null && stepSeq.equals(ex.getStepSeq()) && !"RESOLVED".equals(ex.getExceptionStatus()) && !"IGNORED".equals(ex.getExceptionStatus())) {
                    if (ex.getRecoveryResult() == null) {
                        ex.setRecoveryResult("FAILED");
                    }
                    ex.setExceptionStatus("RESOLVED");
                    ex.setResolvedAt(LocalDateTime.now());
                    ex.setResolvedBy("SYSTEM");
                    ex.setImpactConclusion("非关键步骤恢复失败但原目标完成条件已满足，步骤跳过，计划可继续执行，不触发重新规划");
                    taskExceptionMapper.update(ex);
                }
            }
            // 标记失败步骤为 SKIPPED
            assignmentMapper.findByPlanVersionIdOrderByStepSeqAsc(task.getCurrentPlanVersionId()).stream()
                    .filter(a -> stepSeq != null && stepSeq.equals(a.getStepSeq()))
                    .findFirst()
                    .ifPresent(a -> {
                        a.setStepStatus("SKIPPED");
                        a.setReasonCode("NON_CRITICAL_SKIPPED");
                        a.setUpdatedAt(LocalDateTime.now());
                        assignmentMapper.update(a);
                    });
            // 解冻后续步骤
            for (TaskStepAssignment a : assignmentMapper.findByPlanVersionIdOrderByStepSeqAsc(task.getCurrentPlanVersionId())) {
                if (a.getStepSeq() > stepSeq && "FROZEN".equals(a.getStepStatus())) {
                    a.setStepStatus("PENDING_ASSIGNMENT");
                    a.setUpdatedAt(LocalDateTime.now());
                    assignmentMapper.update(a);
                }
            }
            taskEventService.append(task.getId(), "PLAN_CONTINUATION_JUDGED", "SYSTEM", "STEP_SKIPPED",
                    "步骤" + stepSeq + "为非关键步骤且原目标完成条件已满足，影响结论: 计划可继续执行，步骤跳过，不触发重新规划");
            taskExecutionOrchestrator.advanceAfterStepCompleted(task.getId(), task.getCurrentPlanVersionId(), stepSeq);
            return;
        }

        exception.setRecoveryResult("FAILED");
        exception.setImpactConclusion("候选设备切换恢复失败，当前计划不可继续执行");
        exception.setExceptionStatus("PROCESSING");
        taskExceptionMapper.update(exception);

        // 降级任务的判断不能只看状态：基线首步被承接后任务已转EXECUTING，状态不再是DOWNGRADING；
        // 以当前计划版本的来源为准，基线模板计划执行失败恢复穷尽后直接待人工，不再局部重规划（DEF-S3-065、F015.R08）
        boolean isDowngradedTask = task.getStatus() == TaskStatus.DOWNGRADING
                || currentPlanIsBaseline(task)
                || task.getDowngradeReason() != null;
        if (Boolean.TRUE.equals(task.getReplanUsed()) || isDowngradedTask) {
            String reason = isDowngradedTask
                    ? "基线降级任务执行异常且恢复失败，按业务规则不再二次自动降级"
                    : "重新规划机会已用，恢复失败，转人工处理";
            markUnresolvable(task, exception, reason);
            return;
        }

        exception.setRecoveryResult("FAILED");
        exception.setExceptionStatus("RESOLVED");
        exception.setResolvedAt(LocalDateTime.now());
        exception.setResolvedBy("SYSTEM");
        taskExceptionMapper.update(exception);
        markAllUnresolvedFailed(task.getId(), "步骤" + stepSeq + "恢复失败且计划不可继续，触发重新规划");
        taskEventService.append(task.getId(), "REPLANNING_TRIGGERED", "SYSTEM", null,
                "步骤" + stepSeq + "恢复失败且计划不可继续，重新规划机会未用，触发5.5.4局部重新规划");
        replanningService.replan(task.getId(), stepSeq, exception.getExceptionType() + ": " + exception.getReasonCode());
    }

    private boolean isPlanContinuable(Task task, Integer stepSeq) {
        if (task == null || task.getCurrentPlanVersionId() == null || stepSeq == null) return false;
        if (planVersionMapper == null) return false;
        PlanVersion planVersion = planVersionMapper.findById(task.getCurrentPlanVersionId()).orElse(null);
        if (planVersion == null || planVersion.getPlanSteps() == null) return false;
        try {
            List<Map<String, Object>> steps = MAPPER.readValue(
                    planVersion.getPlanSteps(), new com.fasterxml.jackson.core.type.TypeReference<List<Map<String, Object>>>() {});
            Map<String, Object> currentStep = steps.stream()
                    .filter(s -> stepSeq.equals(s.get("stepSeq") instanceof Number n ? n.intValue() : Integer.parseInt(String.valueOf(s.get("stepSeq")))))
                    .findFirst().orElse(null);
            if (currentStep == null) return false;
            String failureHandling = String.valueOf(currentStep.getOrDefault("failureHandling", ""));
            if (failureHandling == null || failureHandling.isBlank()) return false;
            // 否定与严格规则判定（DEF-S3-106: 拦截"不可跳过"、"禁止跳过"、"不得跳过"、"严禁跳过"等明确否定与人工/重规划要求）
            if (failureHandling.contains("不可跳过") || failureHandling.contains("不能跳过")
                    || failureHandling.contains("禁止跳过") || failureHandling.contains("不得跳过")
                    || failureHandling.contains("严禁跳过") || failureHandling.contains("不准跳过")
                    || failureHandling.contains("不跳过") || failureHandling.contains("勿跳过")
                    || failureHandling.contains("不予跳过")
                    || failureHandling.matches(".*(不可|不能|禁止|不得|严禁|不准|勿|不予|不)\\s*跳过.*")
                    || failureHandling.matches(".*(不可|不能|禁止|不得|严禁|不准|勿|不予|不)\\s*忽略.*")
                    || failureHandling.matches(".*(不可|不能|禁止|不得|严禁|不准|勿|不予|不)\\s*省略.*")) {
                return false;
            }
            if (failureHandling.contains("关键") && !failureHandling.contains("非关键")) {
                return false;
            }
            if (failureHandling.contains("必须重规划") || failureHandling.contains("必须重新规划")
                    || failureHandling.contains("需重规划") || failureHandling.contains("应重规划")
                    || failureHandling.contains("必须转人工") || failureHandling.contains("需转人工")
                    || failureHandling.contains("应交人工") || failureHandling.contains("需交人工")
                    || failureHandling.contains("应转人工") || failureHandling.contains("交人工处理")
                    || failureHandling.contains("转人工处理")) {
                return false;
            }
            boolean skippable = failureHandling.contains("非关键")
                    || failureHandling.contains("可跳过")
                    || failureHandling.contains("允许跳过")
                    || failureHandling.contains("可以跳过")
                    || failureHandling.contains("可选");
            if (!skippable) {
                return false;
            }

            // 检查原目标或前序步骤是否已产生满足条件的结果
            List<TaskStepAssignment> completedList = assignmentMapper.findByPlanVersionIdOrderByStepSeqAsc(task.getCurrentPlanVersionId())
                    .stream()
                    .filter(a -> "COMPLETED".equals(a.getStepStatus()) && a.getStepSeq() < stepSeq)
                    .toList();
            if (completedList.isEmpty()) {
                return false;
            }

            // 解析期望任务目标完成条件
            String targetCondition = null;
            if (task.getGoalParsingResult() != null && !task.getGoalParsingResult().isBlank()) {
                try {
                    JsonNode node = MAPPER.readTree(task.getGoalParsingResult());
                    if (node.hasNonNull("completionCondition")) {
                        targetCondition = node.get("completionCondition").asText(null);
                    }
                } catch (Exception ignored) {}
            }

            for (TaskStepAssignment ca : completedList) {
                if (ca.getOutputParams() == null || ca.getOutputParams().isBlank()) continue;
                Map<String, Object> output = MAPPER.readValue(
                        ca.getOutputParams(), new com.fasterxml.jackson.core.type.TypeReference<Map<String, Object>>() {});
                if (output == null || output.isEmpty()) continue;

                // 1. 若任务定义或目标解析有明确的完成条件，使用 CompletionConditionEvaluator 校验
                if (targetCondition != null && !targetCondition.isBlank()) {
                    Map<String, Object> spec = Map.of("completionCondition", targetCondition);
                    if (CompletionConditionEvaluator.satisfied(spec, output)) {
                        return true;
                    }
                }

                // 2. 检查前序已完成步骤自身的 completionCondition 是否被满足
                Map<String, Object> caStep = steps.stream()
                        .filter(s -> ca.getStepSeq().equals(s.get("stepSeq") instanceof Number n ? n.intValue() : Integer.parseInt(String.valueOf(s.get("stepSeq")))))
                        .findFirst().orElse(null);
                if (caStep != null) {
                    if (CompletionConditionEvaluator.satisfied(caStep, output)) {
                        return true;
                    }
                }

                // 3. 兜底检查业务成功输出标记
                if (Boolean.TRUE.equals(output.get("completed"))
                        || "SUCCESS".equals(output.get("status"))
                        || "SUCCESS".equals(output.get("measureStatus"))
                        || (output.containsKey("routeGenerated") && (targetCondition == null || !targetCondition.contains("routeGenerated")))) {
                    return true;
                }
            }
            return false;
        } catch (Exception ex) {
            return false;
        }
    }

    private boolean currentPlanIsBaseline(Task task) {
        if (planVersionMapper == null || task.getCurrentPlanVersionId() == null) return false;
        return planVersionMapper.findById(task.getCurrentPlanVersionId())
                .map(plan -> "BASELINE_TEMPLATE".equals(plan.getSource())).orElse(false);
    }

    private void markUnresolvable(Task task, TaskException exception, String reason) {
        if (exception != null) {
            exception.setRecoveryResult("FAILED");
            exception.setExceptionStatus("RESOLVED");
            exception.setResolvedAt(LocalDateTime.now());
            exception.setResolvedBy("SYSTEM");
            taskExceptionMapper.update(exception);
        }
        markAllUnresolvedFailed(task.getId(), reason);

        task.setStatus(TaskStatus.PENDING_MANUAL);
        task.setFailureReason(reason);
        task.setUpdatedAt(LocalDateTime.now());
        taskMapper.update(task);
        taskEventService.append(task.getId(), "TASK_PENDING_MANUAL", "SYSTEM",
                exception != null ? exception.getExceptionType() : "SYSTEM", reason);
    }

    /** 对应业务规则2："冻结未执行步骤"，已完成步骤结果保留，异常发生步骤之后的PENDING_ASSIGNMENT步骤置FROZEN */
    private void freezeRemainingSteps(Long taskId, Integer fromStepSeq) {
        Task task = taskMapper.findById(taskId).orElseThrow();
        if (task.getCurrentPlanVersionId() == null) return;
        List<TaskStepAssignment> all = assignmentMapper.findByPlanVersionIdOrderByStepSeqAsc(task.getCurrentPlanVersionId());
        for (TaskStepAssignment a : all) {
            if (a.getStepSeq() > fromStepSeq && "PENDING_ASSIGNMENT".equals(a.getStepStatus())) {
                a.setStepStatus("FROZEN");
                a.setUpdatedAt(LocalDateTime.now());
                assignmentMapper.update(a);
                if (a.getDeviceAgentId() != null) {
                    taskExecutionOrchestrator.releaseAgent(a.getDeviceAgentId(), taskId);
                }
            }
        }
    }

    private String findOfflineAgentCode(Long taskId, Integer stepSeq) {
        Task task = taskMapper.findById(taskId).orElseThrow();
        return assignmentMapper.findByPlanVersionIdAndStepSeq(task.getCurrentPlanVersionId(), stepSeq)
                .map(TaskStepAssignment::getDeviceAgentId)
                .flatMap(deviceAgentMapper::findById)
                .map(DeviceAgent::getAgentCode)
                .orElse(null);
    }

    private boolean isTerminalOrManual(TaskStatus status) {
        return status == TaskStatus.COMPLETED || status == TaskStatus.FAILED
                || status == TaskStatus.MANUAL_TERMINATED || status == TaskStatus.PENDING_MANUAL;
    }

    public List<TaskException> listByTask(Long taskId) {
        return taskExceptionMapper.findByTaskIdOrderByOccurredAtDesc(taskId);
    }

    public List<TaskException> search(String exceptionType, String exceptionStatus) {
        return taskExceptionMapper.searchPaged(
                (exceptionType == null || exceptionType.isBlank()) ? null : exceptionType,
                (exceptionStatus == null || exceptionStatus.isBlank()) ? null : exceptionStatus);
    }

    public long countPending() {
        return taskExceptionMapper.countUnhandledExceptions();
    }
}
