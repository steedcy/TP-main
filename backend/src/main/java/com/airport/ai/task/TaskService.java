package com.airport.ai.task;

import com.airport.ai.auth.OperationLogService;
import com.airport.ai.auth.User;
import com.airport.ai.common.BusinessException;
import com.airport.ai.common.ErrorCode;
import com.airport.ai.common.PageResult;
import com.airport.ai.device.DeviceAgentMapper;
import com.airport.ai.device.DeviceAgentMessagingService;
import com.airport.ai.event.TaskEventService;
import com.airport.ai.planning.GoalUnderstandingRequest;
import com.airport.ai.planning.GoalUnderstandingResponse;
import com.airport.ai.planning.GoalUnderstandingService;
import com.airport.ai.task.dto.ClarifyTaskRequest;
import com.airport.ai.task.dto.SubmitTaskRequest;
import com.airport.ai.taskdef.TaskDefinitionService;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.github.pagehelper.PageHelper;
import com.github.pagehelper.PageInfo;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

/**
 * 对应5.4.1开放式任务目标提交与理解。目标理解与候选计划生成是外部规划模型服务的
 * 两个独立端点（方案A，见附录B 5.2节），本类只负责5.4.1环节：提交、理解、澄清、取消。
 * 5.4.2起的规划上下文构建/候选计划生成/三类校验/监督判定/基线降级由后续任务实现，
 * 本类理解完整后仅将任务状态保持在PLANNING，不推进到SUPERVISING之后的状态。
 */
@Service
public class TaskService {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private final TaskMapper taskMapper;
    private final PlanVersionMapper planVersionMapper;
    private final ContextSnapshotMapper contextSnapshotMapper;
    private final DeviceAgentMapper deviceAgentMapper;
    private final GoalUnderstandingService goalUnderstandingService;
    private final TaskCodeGenerator taskCodeGenerator;
    private final TaskEventService taskEventService;
    private final OperationLogService operationLogService;
    private final TaskPlanningOrchestrator taskPlanningOrchestrator;
    private final TaskStepAssignmentMapper assignmentMapper;
    private final TaskDefinitionService taskDefinitionService;
    private final DeviceAgentMessagingService deviceAgentMessagingService;
    private final ForceBypassAuditRecorder forceBypassAuditRecorder;
    private final com.airport.ai.device.DeviceMapper deviceMapper;

    @Autowired
    public TaskService(TaskMapper taskMapper,
                        PlanVersionMapper planVersionMapper,
                        ContextSnapshotMapper contextSnapshotMapper,
                        DeviceAgentMapper deviceAgentMapper,
                        GoalUnderstandingService goalUnderstandingService,
                        TaskCodeGenerator taskCodeGenerator,
                        TaskEventService taskEventService,
                        OperationLogService operationLogService,
                        TaskPlanningOrchestrator taskPlanningOrchestrator,
                        TaskStepAssignmentMapper assignmentMapper,
                        TaskDefinitionService taskDefinitionService,
                        DeviceAgentMessagingService deviceAgentMessagingService,
                        ForceBypassAuditRecorder forceBypassAuditRecorder,
                        @Autowired(required = false) com.airport.ai.device.DeviceMapper deviceMapper) {
        this.taskMapper = taskMapper;
        this.planVersionMapper = planVersionMapper;
        this.contextSnapshotMapper = contextSnapshotMapper;
        this.deviceAgentMapper = deviceAgentMapper;
        this.goalUnderstandingService = goalUnderstandingService;
        this.taskCodeGenerator = taskCodeGenerator;
        this.taskEventService = taskEventService;
        this.operationLogService = operationLogService;
        this.taskPlanningOrchestrator = taskPlanningOrchestrator;
        this.assignmentMapper = assignmentMapper;
        this.taskDefinitionService = taskDefinitionService;
        this.deviceAgentMessagingService = deviceAgentMessagingService;
        this.forceBypassAuditRecorder = forceBypassAuditRecorder;
        this.deviceMapper = deviceMapper;
    }

    public TaskService(TaskMapper taskMapper,
                        PlanVersionMapper planVersionMapper,
                        ContextSnapshotMapper contextSnapshotMapper,
                        DeviceAgentMapper deviceAgentMapper,
                        GoalUnderstandingService goalUnderstandingService,
                        TaskCodeGenerator taskCodeGenerator,
                        TaskEventService taskEventService,
                        OperationLogService operationLogService,
                        TaskPlanningOrchestrator taskPlanningOrchestrator,
                        TaskStepAssignmentMapper assignmentMapper,
                        TaskDefinitionService taskDefinitionService,
                        DeviceAgentMessagingService deviceAgentMessagingService,
                        ForceBypassAuditRecorder forceBypassAuditRecorder) {
        this(taskMapper, planVersionMapper, contextSnapshotMapper, deviceAgentMapper,
                goalUnderstandingService, taskCodeGenerator, taskEventService,
                operationLogService, taskPlanningOrchestrator, assignmentMapper,
                taskDefinitionService, deviceAgentMessagingService,
                forceBypassAuditRecorder, null);
    }

    public TaskService(TaskMapper taskMapper,
                        PlanVersionMapper planVersionMapper,
                        ContextSnapshotMapper contextSnapshotMapper,
                        DeviceAgentMapper deviceAgentMapper,
                        GoalUnderstandingService goalUnderstandingService,
                        TaskCodeGenerator taskCodeGenerator,
                        TaskEventService taskEventService,
                        OperationLogService operationLogService,
                        TaskPlanningOrchestrator taskPlanningOrchestrator,
                        TaskStepAssignmentMapper assignmentMapper,
                        TaskDefinitionService taskDefinitionService,
                        DeviceAgentMessagingService deviceAgentMessagingService) {
        this(taskMapper, planVersionMapper, contextSnapshotMapper, deviceAgentMapper,
                goalUnderstandingService, taskCodeGenerator, taskEventService,
                operationLogService, taskPlanningOrchestrator, assignmentMapper,
                taskDefinitionService, deviceAgentMessagingService,
                new ForceBypassAuditRecorder(taskEventService, operationLogService));
    }

    public Task get(Long taskId) {
        return taskMapper.findById(taskId)
                .orElseThrow(() -> new BusinessException(ErrorCode.TASK_NOT_FOUND));
    }

    public java.util.List<PlanVersion> listPlanVersions(Long taskId) {
        return planVersionMapper.findByTaskIdOrderByVersionNoAsc(taskId);
    }

    public java.util.List<ContextSnapshot> listContextSnapshots(Long taskId) {
        return contextSnapshotMapper.findByTaskIdOrderByGeneratedAtDesc(taskId);
    }

    /** 对应5.5.1/5.5.2界面元素：任务当前计划版本下各步骤的分配设备、指令编号、执行状态 */
    public List<com.airport.ai.task.dto.TaskStepAssignmentView> listStepAssignments(Long taskId) {
        Task task = get(taskId);
        if (task.getCurrentPlanVersionId() == null) {
            return List.of();
        }
        return assignmentMapper.findByPlanVersionIdOrderByStepSeqAsc(task.getCurrentPlanVersionId()).stream()
                .map(a -> com.airport.ai.task.dto.TaskStepAssignmentView.from(a,
                        a.getDeviceAgentId() == null ? null : deviceAgentMapper.findById(a.getDeviceAgentId()).orElse(null)))
                .toList();
    }

    /** 对应5.7.1界面元素：任务编号、时间范围、任务族/状态任意组合筛选（同时供5.4任务列表复用） */
    public PageResult<Task> list(String taskCode, TaskStatus status, String taskFamily,
                                  LocalDateTime createdFrom, LocalDateTime createdTo, int page, int size) {
        return list(taskCode, status, taskFamily, null, createdFrom, createdTo, page, size);
    }

    /** 增加目标关键字筛选（SRS_F020.R06，DEF-S3-006）：对任务目标做不区分大小写的包含查询；转义 LIKE 通配符，最长100字。 */
    public PageResult<Task> list(String taskCode, TaskStatus status, String taskFamily,
                                  String goalKeyword,
                                  LocalDateTime createdFrom, LocalDateTime createdTo, int page, int size) {
        String cleanKeyword = escapeLike(goalKeyword);
        PageHelper.startPage(page, size);
        return PageResult.of(new PageInfo<>(taskMapper.searchPaged(
                blankToNull(taskCode), status, blankToNull(taskFamily), cleanKeyword, createdFrom, createdTo)));
    }

    static String escapeLike(String input) {
        if (input == null || input.isBlank()) return null;
        String trimmed = input.trim();
        if (trimmed.length() > 100) trimmed = trimmed.substring(0, 100);
        return trimmed.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_");
    }

    private String blankToNull(String value) {
        return (value == null || value.isBlank()) ? null : value;
    }

    /**
     * 对应基本路径1~4、异常路径3a：提交前校验至少存在一个启用且在线的设备代理，
     * 否则不生成任务实例。校验通过后创建任务（PLANNING）并立即触发目标理解。
     * noRollbackFor是关键：目标理解失败/超时（异常路径4b）、目标与任务族无关（异常路径4c）
     * 均以BusinessException通知调用方，但"生成任务实例"是提交的强制后置条件，
     * 已写入的任务记录与事件不应随该异常回滚，否则运行操作员看到失败提示后任务却查不到，
     * 也无法重试理解（参照AuthService.login对同类问题的处理方式）。
     */
    @Transactional(noRollbackFor = BusinessException.class)
    public Task submit(SubmitTaskRequest request, User operator) {
        if (deviceAgentMapper.findByAgentStatusAndOnlineStatus("ENABLED", "ONLINE").isEmpty()) {
            throw new BusinessException(ErrorCode.NO_AVAILABLE_DEVICE_AGENT);
        }
        // 对应5.6.1业务规则：任务族须为已启用的任务定义编码，取代此前硬编码4值枚举@Pattern。
        // 运行操作员未指定任务族时留空，由目标理解阶段的inferredTaskFamily判定，此处不校验。
        if (request.getTaskFamily() != null && !request.getTaskFamily().isBlank()
                && !taskDefinitionService.isEnabledFamily(request.getTaskFamily())) {
            throw new BusinessException(ErrorCode.TASK_FAMILY_INVALID,
                    "任务族不存在或已停用，当前可选: " + taskDefinitionService.listEnabledTaskNames());
        }
        SceneParamsPrivacyGuard.reject(request.getSceneParams());
        FlightChangeSceneValidator.validate(request.getTaskFamily(), request.getSceneParams());
        // 扩展任务定义声明的必填场景参数/类型在建任务前核对，不通过则不建任务、不调模型（DEF-S3-029）
        taskDefinitionService.findByCode(request.getTaskFamily())
                .ifPresent(def -> SceneParamsValidator.validate(def, request.getSceneParams()));

        Map<String, Object> sanitizedScene = SceneParamsPrivacyGuard.sanitize(request.getSceneParams());
        if ("OVERSIZE_BAGGAGE_HANDLING".equals(request.getTaskFamily()) && sanitizedScene != null) {
            sanitizedScene.putIfAbsent("baggageId", "BAG-" + System.currentTimeMillis() % 1000000);
            sanitizedScene.putIfAbsent("targetCounter", sanitizedScene.getOrDefault("targetLocation", "F2_TEST_GATE"));
        }

        String sanitizedGoal = SceneParamsPrivacyGuard.sanitizeGoal(request.getTaskGoal());
        Task task = new Task();
        task.setTaskCode(taskCodeGenerator.next());
        task.setTaskGoal(sanitizedGoal);
        task.setTaskFamily(request.getTaskFamily());
        task.setSceneParams(toJson(sanitizedScene));
        task.setStatus(TaskStatus.PLANNING);
        task.setCreatedBy(operator.getUsername());
        taskMapper.insert(task);

        taskEventService.append(task.getId(), "GOAL_SUBMITTED", "OPERATOR", null,
                "运行操作员" + operator.getUsername() + "提交任务目标: " + sanitizedGoal);
        operationLogService.record(operator.getId(), operator.getUsername(), operator.getRole(),
                "TASK_SUBMIT", task.getTaskCode(), "SUCCESS", null);

        runGoalUnderstanding(task, request.getSceneParams(), null);
        return task;
    }

    /**
     * 对应备选路径4a：运行操作员针对missingInfoQuestions逐条补充后，
     * 合并进原始场景参数重新执行目标理解，直至信息完整。
     * noRollbackFor理由同submit：理解失败不应回滚已合并保存的补充信息。
     */
    @Transactional(noRollbackFor = BusinessException.class)
    public Task clarify(Long taskId, ClarifyTaskRequest request, User operator) {
        Task task = get(taskId);
        if (task.getStatus() != TaskStatus.PLANNING) {
            throw new BusinessException(ErrorCode.TASK_STATUS_NOT_ALLOWED, "任务已离开待规划状态，不可补充信息");
        }

        boolean specialPassenger = "SPECIAL_PASSENGER_SERVICE".equals(task.getTaskFamily());
        if (!specialPassenger) {
            SceneParamsPrivacyGuard.reject(request.getAnswers());
        }
        List<String> pendingQuestions = fromJsonQuestions(task.getMissingInfoQuestions());
        if (specialPassenger && pendingQuestions.stream().anyMatch(SceneParamsPrivacyGuard::asksForIdentity)) {
            throw new BusinessException(ErrorCode.PARAM_FORMAT_ERROR,
                    "特殊旅客服务不得请求或接收旅客真实身份信息，请刷新任务问题后重试");
        }
        if (pendingQuestions.isEmpty() || request.getAnswers() == null
                || pendingQuestions.stream().anyMatch(q -> request.getAnswers().get(q) == null
                        || request.getAnswers().get(q).isBlank())) {
            throw new BusinessException(ErrorCode.PARAM_FORMAT_ERROR, "请逐条回答当前待补充问题");
        }

        Map<String, String> answersToStore = specialPassenger
                ? SceneParamsPrivacyGuard.sanitizeFreeTextAnswers(request.getAnswers())
                : new HashMap<>(request.getAnswers());

        Map<String, Object> mergedSceneParams = new HashMap<>(fromJsonMap(task.getSceneParams()));
        List<Map<String, Object>> rounds = new ArrayList<>();
        Object saved = mergedSceneParams.get("clarificationAnswers");
        if (saved instanceof List<?> savedRounds) {
            for (Object round : savedRounds) {
                if (round instanceof Map<?, ?> values) {
                    Map<String, Object> copy = new HashMap<>();
                    values.forEach((key, value) -> copy.put(String.valueOf(key), value));
                    if (specialPassenger) sanitizeSpecialPassengerRound(copy);
                    rounds.add(copy);
                }
            }
        } else if (saved instanceof Map<?, ?> previousAnswers) {
            Map<String, Object> legacyRound = new HashMap<>();
            legacyRound.put("answers", specialPassenger
                    ? sanitizeSpecialPassengerAnswers(previousAnswers)
                    : previousAnswers);
            rounds.add(legacyRound);
        }
        rounds.add(Map.of("questions", pendingQuestions, "answers", answersToStore));
        mergedSceneParams.put("clarificationAnswers", rounds);

        task.setSceneParams(toJson(SceneParamsPrivacyGuard.sanitize(mergedSceneParams)));
        taskMapper.update(task);

        taskEventService.append(task.getId(), "GOAL_CLARIFIED", "OPERATOR", null,
                specialPassenger
                        ? "运行操作员" + operator.getUsername() + "补充信息（问题数: " + pendingQuestions.size() + "）"
                        : "运行操作员" + operator.getUsername() + "补充信息: " + request.getAnswers());

        runGoalUnderstanding(task, mergedSceneParams, rounds);
        return task;
    }

    /**
     * 对应5.4.5异常路径4a/4b、5.4.6异常路径2b/3a：任务处于PENDING_MANUAL时，
     * 运行操作员在任务详情中处置。SWITCH_TO_BASELINE不重复走完整降级匹配流程
     * （无匹配模板才落到PENDING_MANUAL，重试同样条件通常仍无匹配），改为重新触发
     * 整条规划链路（等价于把任务打回PLANNING后再advance一次，覆盖"模型此前不可用
     * 现已恢复"等场景）；RETRY_PLANNING语义与之相同，两者均是重新走一次advance；
     * MARK_FAILED直接将任务置为失败并记录原因。
     */
    public Task manualAction(Long taskId, String action, User operator) {
        return manualAction(taskId, action, null, null, operator);
    }

    public Task manualAction(Long taskId, String action, String reason, User operator) {
        return manualAction(taskId, action, reason, null, operator);
    }

    @Transactional
    public Task manualAction(Long taskId, String action, String reason, String taskGoal, User operator) {
        Task task = get(taskId);
        String cleanReason = reason == null || reason.isBlank() ? null : reason.trim();
        String cleanGoal = taskGoal == null || taskGoal.isBlank() ? null : taskGoal.trim();
        String upperAction = action == null ? "" : action.trim().toUpperCase();

        // 对应5.4.4硬性闸门与业务规则7（SRS_F013.R07）：硬性校验失败严禁进入监督判定中，
        // 也不得由监督智能体或人工强行放行。试图强行放行必须坚决拦截，记录时间线与审计留痕。
        Set<String> forceBypassActions = Set.of(
                "FORCE_RELEASE", "BYPASS_VALIDATION", "FORCE_BYPASS", "RELEASE",
                "OVERRIDE", "APPROVE", "FORCE_PASS", "FORCE_EXECUTE",
                "REQUEST_SUPERVISION", "FORCE_SUPERVISION", "SUPERVISION_OVERRIDE"
        );
        if (forceBypassActions.contains(upperAction)) {
            forceBypassAuditRecorder.recordInterception(taskId, task.getTaskCode(), action, operator);
            throw new BusinessException(ErrorCode.FORCE_BYPASS_HARD_CHECK, "硬性校验失败的计划严禁进入监督判定或强行放行");
        }

        // 所有人工处置动作（置为失败、转基线、重试规划）均须填写处置原因（DEF-S3-062、F020.R08）
        if (cleanReason == null) {
            throw new BusinessException(ErrorCode.PARAM_MISSING, "人工处置须填写处置原因");
        }
        if (cleanReason.length() > 200) {
            throw new BusinessException(ErrorCode.PARAM_FORMAT_ERROR, "处置原因不得超过200字");
        }
        if (cleanGoal != null && cleanGoal.length() > 500) {
            throw new BusinessException(ErrorCode.PARAM_FORMAT_ERROR, "修改后的目标不得超过500字");
        }

        if (task.getStatus() != TaskStatus.PENDING_MANUAL) {
            throw new BusinessException(ErrorCode.TASK_STATUS_NOT_ALLOWED, "任务当前状态不是待人工处理，不可执行该操作");
        }

        // 三轮补充后仍缺关键信息进入待人工处理时，关键信息仍未确认：转基线/重试规划会让模板默认值
        // （如默认轮椅说明、测试登机口）顶替操作员未确认的旅客类型或起终点，须先拒绝，只能置为失败（DEF-S3-063、R04）
        if (("SWITCH_TO_BASELINE".equals(upperAction) || "RETRY_PLANNING".equals(upperAction))
                && !fromJsonQuestions(task.getMissingInfoQuestions()).isEmpty()) {
            throw new BusinessException(ErrorCode.PARAM_MISSING,
                    "任务仍有未补充的关键信息，不能转基线或重试规划，请先补齐或将任务置为失败: "
                            + fromJsonQuestions(task.getMissingInfoQuestions()));
        }

        switch (upperAction) {
            case "SWITCH_TO_BASELINE" -> {
                task.setStatus(TaskStatus.PLANNING);
                task.setUpdatedAt(LocalDateTime.now());
                taskMapper.update(task);
                taskEventService.append(taskId, "BASELINE_SWITCH_REQUESTED", "OPERATOR", null,
                        "运行操作员" + operator.getUsername() + "选择SWITCH_TO_BASELINE，原因: " + cleanReason);
                taskPlanningOrchestrator.switchToBaseline(taskId);
            }
            case "RETRY_PLANNING" -> {
                task.setStatus(TaskStatus.PLANNING);
                if (cleanGoal != null) {
                    task.setTaskGoal(cleanGoal);
                    task.setGoalParsingResult(null);
                    taskEventService.append(taskId, "TASK_GOAL_UPDATED", "OPERATOR", null,
                            "运行操作员" + operator.getUsername() + "修改任务目标为: " + cleanGoal);
                }
                task.setUpdatedAt(LocalDateTime.now());
                taskMapper.update(task);
                taskEventService.append(taskId, "REPLANNING_TRIGGERED", "OPERATOR", null,
                        "运行操作员" + operator.getUsername() + "选择RETRY_PLANNING，原因: " + cleanReason);
                if (cleanGoal != null) {
                    runGoalUnderstanding(task, fromJsonMap(task.getSceneParams()), null);
                } else {
                    taskPlanningOrchestrator.advance(taskId);
                }
            }
            case "MARK_FAILED" -> {
                task.setStatus(TaskStatus.FAILED);
                task.setFailureReason("运行操作员" + operator.getUsername() + "在待人工处理阶段手动置为失败，原因: " + cleanReason);
                task.setUpdatedAt(LocalDateTime.now());
                taskMapper.update(task);
                taskEventService.append(taskId, "TASK_FAILED", "OPERATOR", "MANUAL_MARK_FAILED", task.getFailureReason());
            }
            default -> throw new BusinessException(ErrorCode.PARAM_FORMAT_ERROR, "未知的人工处理动作: " + action);
        }

        Task result = get(taskId);
        boolean failed = result.getStatus() == TaskStatus.PENDING_MANUAL;
        if (failed) taskEventService.append(taskId, "TASK_MANUAL_ACTION_FAILED", "SYSTEM",
                "ERR_MANUAL_ACTION_FAILED", result.getFailureReason());
        Map<String, Object> actionDetail = new HashMap<>();
        actionDetail.put("action", action);
        actionDetail.put("reason", cleanReason);
        actionDetail.put("resultStatus", result.getStatus().name());
        operationLogService.record(operator.getId(), operator.getUsername(), operator.getRole(),
                "TASK_MANUAL_ACTION", task.getTaskCode() + " -> " + action, failed ? "FAILED" : "SUCCESS", null, actionDetail);
        return result;
    }

    /**
     * 对应备选路径5a：进入计划生成前可取消，任务置为人工终止并记录原因。
     * 一旦离开PLANNING（已进入计划生成/执行），须改走5.5.6人工终止流程，不可用本接口。
     */
    @Transactional
    public Task cancel(Long taskId, String reason, User operator) {
        Task task = get(taskId);
        if (task.getStatus() != TaskStatus.PLANNING) {
            throw new BusinessException(ErrorCode.TASK_CANNOT_CANCEL_AFTER_PLANNING,
                    "任务当前状态为" + task.getStatus() + "，已离开待规划阶段，不可再取消");
        }

        task.setStatus(TaskStatus.MANUAL_TERMINATED);
        task.setManualTerminateReason(reason);
        task.setUpdatedAt(LocalDateTime.now());
        taskMapper.update(task);

        String timelineSummary = "运行操作员" + operator.getUsername() + "在计划生成前取消任务: " + reason;
        Map<String, Object> cancelDetail = new LinkedHashMap<>();
        cancelDetail.put("summary", timelineSummary);
        cancelDetail.put("reason", reason);
        cancelDetail.put("previousStatus", TaskStatus.PLANNING.name());
        cancelDetail.put("operator", operator.getUsername());
        cancelDetail.put("deviceCancelResults", java.util.Collections.emptyList());
        cancelDetail.put("devices", java.util.Collections.emptyList());
        cancelDetail.put("cancelledCount", 0);

        String cancelEventJson;
        try {
            cancelEventJson = MAPPER.writeValueAsString(cancelDetail);
        } catch (Exception e) {
            cancelEventJson = "{\"summary\":\"" + reason + "\"}";
        }

        taskEventService.append(task.getId(), "MANUAL_TERMINATED", "OPERATOR", null, cancelEventJson);
        operationLogService.record(operator.getId(), operator.getUsername(), operator.getRole(),
                "TASK_CANCEL", task.getTaskCode(), "SUCCESS", null, cancelDetail);
        return task;
    }

    /**
     * 对应5.5.6人工终止：前置条件为任务处于PLANNING/SUPERVISING/PENDING_ASSIGNMENT/DOWNGRADING/
     * EXECUTING/PENDING_MANUAL（业务规则1~4、7、8）。停止后续步骤下发（未执行步骤置FROZEN，
     * 不下发任何新指令），向全部占用中的设备发TASK_CANCEL语义的释放动作并置IDLE（业务规则3/4），
     * 已完成步骤结果保留不回滚（业务规则6）。人工终止≠设备安全急停（业务规则5，由前端固定文案承载
     * 责任边界提示，本方法只负责业务状态流转）。
     */
    @Transactional
    public Task terminate(Long taskId, String reason, User operator) {
        String cleanReason = reason == null ? "" : reason.trim();
        if (cleanReason.isEmpty()) {
            throw new BusinessException(ErrorCode.TERMINATE_REASON_REQUIRED, "请填写终止原因");
        }
        if (cleanReason.length() > 200) {
            throw new BusinessException(ErrorCode.PARAM_FORMAT_ERROR, "终止原因最长200位");
        }

        Task task = get(taskId);
        Set<TaskStatus> terminable = Set.of(TaskStatus.PLANNING, TaskStatus.SUPERVISING,
                TaskStatus.PENDING_ASSIGNMENT, TaskStatus.DOWNGRADING, TaskStatus.EXECUTING, TaskStatus.PENDING_MANUAL);
        if (!terminable.contains(task.getStatus())) {
            throw new BusinessException(ErrorCode.TASK_TERMINATE_NOT_ALLOWED,
                    "任务当前状态为" + task.getStatus() + "，已处于终态，不可终止");
        }

        TaskStatus previousStatus = task.getStatus();
        List<Map<String, Object>> deviceResults = new ArrayList<>();
        Map<Long, TaskStepAssignment> activeAssignmentsByAgent = new HashMap<>();
        if (task.getCurrentPlanVersionId() != null) {
            for (TaskStepAssignment assignment : assignmentMapper.findByPlanVersionIdOrderByStepSeqAsc(task.getCurrentPlanVersionId())) {
                if ("PENDING_ASSIGNMENT".equals(assignment.getStepStatus()) || "EXECUTING".equals(assignment.getStepStatus())) {
                    if (assignment.getDeviceAgentId() != null) {
                        activeAssignmentsByAgent.put(assignment.getDeviceAgentId(), assignment);
                    }
                    assignment.setStepStatus("FROZEN");
                    assignment.setUpdatedAt(LocalDateTime.now());
                    assignmentMapper.update(assignment);
                }
            }
        }

        List<com.airport.ai.device.DeviceAgent> affectedAgents = new ArrayList<>(deviceAgentMapper.findByCurrentTaskId(taskId));
        Set<Long> includedAgentIds = affectedAgents.stream().map(com.airport.ai.device.DeviceAgent::getId)
                .collect(java.util.stream.Collectors.toSet());
        for (Long assignedAgentId : activeAssignmentsByAgent.keySet()) {
            if (!includedAgentIds.contains(assignedAgentId)) {
                deviceAgentMapper.findById(assignedAgentId).ifPresent(affectedAgents::add);
            }
        }
        for (var agentRef : affectedAgents) {
            com.airport.ai.device.DeviceAgent agent = deviceAgentMapper.findByIdForUpdate(agentRef.getId())
                    .or(() -> deviceAgentMapper.findById(agentRef.getId()))
                    .orElse(agentRef);

            // DEF-S3-103: 若该代理当前已被其他任务占有，本任务终止仅能冻结/解除本任务自身的步骤，
            // 严禁向该代理发送取消指令，严禁修改或清空归属于其他任务的工作状态与占用引用！
            if (agent.getCurrentTaskId() != null && !taskId.equals(agent.getCurrentTaskId())) {
                continue;
            }

            String agentCode = agent.getAgentCode();
            String deviceCode = agentCode;
            if (deviceMapper != null && agent.getDeviceId() != null) {
                try {
                    com.airport.ai.device.Device dev = deviceMapper.findById(agent.getDeviceId()).orElse(null);
                    if (dev != null && dev.getDeviceCode() != null && !dev.getDeviceCode().isBlank()) {
                        deviceCode = dev.getDeviceCode();
                    }
                } catch (Exception ignored) {
                }
            }

            TaskStepAssignment assignment = activeAssignmentsByAgent.get(agent.getId());
            String cancelCommandId = generateCancelCommandId();
            Map<String, Object> devResult = new LinkedHashMap<>();
            devResult.put("agentId", agentCode);
            devResult.put("agentCode", agentCode);
            devResult.put("deviceCode", deviceCode);
            devResult.put("cancelCommandId", cancelCommandId);

            try {
                deviceAgentMessagingService.cancelTask(agentCode, cancelCommandId, taskId,
                        assignment == null ? agent.getCurrentStepSeq() : assignment.getStepSeq());
                taskEventService.append(taskId, "TASK_CANCEL_REQUESTED", "OPERATOR", null,
                        "已向设备代理" + agentCode + "发送业务任务取消请求");
                devResult.put("result", "CANCEL_QUEUED");
                devResult.put("cancelStatus", "CANCEL_QUEUED");
                devResult.put("status", "CANCEL_QUEUED");
            } catch (RuntimeException ex) {
                taskEventService.append(taskId, "TASK_CANCEL_DELIVERY_FAILED", "OPERATOR", "DEVICE_API_ERROR",
                        "向设备代理" + agentCode + "发送业务任务取消请求失败: " + ex.getMessage());
                devResult.put("result", "CANCEL_FAILED");
                devResult.put("cancelStatus", "CANCEL_FAILED");
                devResult.put("status", "CANCEL_FAILED");
                devResult.put("error", ex.getMessage());
            }
            deviceResults.add(devResult);

            if (taskId.equals(agent.getCurrentTaskId())) {
                // A queued cancellation does not prove the device stopped. Keep it unavailable
                // until an IDLE status report confirms release (or an operator resolves it).
                agent.setWorkStatus("BUSY");
                agent.setCurrentTaskId(taskId);
            } else {
                // Not actively occupied by this task: release immediately to avoid false BUSY lock
                agent.setWorkStatus("IDLE");
                agent.setCurrentTaskId(null);
                agent.setCurrentStepSeq(null);
            }
            deviceAgentMapper.update(agent);
        }

        task.setStatus(TaskStatus.MANUAL_TERMINATED);
        task.setManualTerminateReason(cleanReason);
        task.setUpdatedAt(LocalDateTime.now());
        taskMapper.update(task);

        String deviceSummaryStr;
        try {
            deviceSummaryStr = MAPPER.writeValueAsString(deviceResults);
        } catch (Exception e) {
            deviceSummaryStr = deviceResults.toString();
        }

        // 人类可读时间线文本摘要（保留用于 UI 与时间线展示）
        String timelineSummary = "运行操作员" + operator.getUsername() + "人工终止任务，原因: " + cleanReason
                + "，前序状态: " + previousStatus.name()
                + "，涉及设备: " + deviceResults.stream().map(m -> m.get("agentId")).toList()
                + "，取消响应摘要: " + deviceSummaryStr;

        // 构造结构化详情 JSON（DEF-S3-059，TC-066.S3 / SRS_F021.R08）
        // 包含 reason、previousStatus、operator、deviceCancelResults 以及 summary 人类可读时间线
        Map<String, Object> eventDetailMap = new LinkedHashMap<>();
        eventDetailMap.put("summary", timelineSummary);
        eventDetailMap.put("reason", cleanReason);
        eventDetailMap.put("previousStatus", previousStatus.name());
        eventDetailMap.put("operator", operator.getUsername());
        eventDetailMap.put("deviceCancelResults", deviceResults);
        eventDetailMap.put("devices", deviceResults);
        eventDetailMap.put("cancelledCount", deviceResults.size());

        String eventDetailJson;
        try {
            eventDetailJson = MAPPER.writeValueAsString(eventDetailMap);
        } catch (Exception e) {
            eventDetailJson = "{\"summary\":\"" + cleanReason + "\"}";
        }

        // 记录结构化人工终止事件 MANUAL_TERMINATED 与 TASK_TERMINATED（事件 detail 可被 json.loads 整体解析且同时保留 detailSummary 人类可读摘要）
        taskEventService.append(taskId, "MANUAL_TERMINATED", "OPERATOR", "NORMAL_MANUAL_TERMINATED", eventDetailJson);
        taskEventService.append(taskId, "TASK_TERMINATED", "OPERATOR", "NORMAL_MANUAL_TERMINATED", eventDetailJson);

        // 操作日志必须包含终止原因、前序状态以及每个设备取消响应摘要（包括 cancelCommandId），严禁 detail 为 null！
        Map<String, Object> terminateDetail = new LinkedHashMap<>(eventDetailMap);
        operationLogService.record(operator.getId(), operator.getUsername(), operator.getRole(),
                "TASK_TERMINATE", task.getTaskCode(), "SUCCESS", null, terminateDetail);
        return task;
    }

    private String generateCancelCommandId() {
        return com.airport.ai.device.CommandIds.next();
    }

    /**
     * 对应5.4.1业务规则2/3/4/6/7、异常路径4b/4c。目标理解调用外部规划模型服务
     * （方案A独立端点），60秒超时约束由GoalUnderstandingService实现内部保证。
     * 提交给理解服务的sceneParams不得包含旅客真实身份信息，只保留结构化场景参数
     * （协助类型等），本方法不做额外脱敏处理——业务规则6要求提交入口本身不采集
     * 真实身份字段，前端与SubmitTaskRequest均未开放姓名/证件号等字段。
     */
    private void runGoalUnderstanding(Task task, Map<String, Object> sceneParams,
                                      List<Map<String, Object>> clarificationAnswers) {
        GoalUnderstandingRequest request = new GoalUnderstandingRequest();
        request.setRequestId(UUID.randomUUID().toString());
        request.setTaskGoal(SceneParamsPrivacyGuard.sanitizeGoal(task.getTaskGoal()));
        request.setTaskFamily(task.getTaskFamily());
        request.setSceneParams(SceneParamsPrivacyGuard.sanitize(sceneParams));
        if (clarificationAnswers != null) {
            request.setClarificationAnswers(clarificationAnswers);
        }

        GoalUnderstandingResponse response = goalUnderstandingService.understand(request);

        if (!response.isSuccess()) {
            // 异常路径4b：超时或异常，不进入计划生成，不下发任何设备指令
            taskEventService.append(task.getId(), "GOAL_UNDERSTANDING_FAILED", "SYSTEM",
                    "ERR_GOAL_UNDERSTANDING_TIMEOUT",
                    "目标理解调用规划模型服务失败: " + response.getErrorMessage());
            // DEF-S3-033：超时/异常后不停在PLANNING，进入基线可用性与校验流程，不可用则转待人工
            taskPlanningOrchestrator.downgradeAfterUnderstandingFailure(task.getId(), "目标理解超时或异常: " + response.getErrorMessage());
            throw new BusinessException(ErrorCode.GOAL_UNDERSTANDING_TIMEOUT, response.getErrorMessage());
        }

        if (response.isUnrelatedToAnyFamily()) {
            // 异常路径4c：目标内容与已定义任务族及能力类型完全无关，可支持范围动态取当前已启用任务定义清单
            task.setStatus(TaskStatus.FAILED);
            task.setFailureReason("任务目标与已定义任务族及能力类型完全无关，可支持范围："
                    + String.join("、", taskDefinitionService.listEnabledTaskNames()));
            task.setUpdatedAt(LocalDateTime.now());
            taskMapper.update(task);
            taskEventService.append(task.getId(), "GOAL_CLARIFIED", "SYSTEM", "ERR_GOAL_UNRELATED",
                    task.getFailureReason());
            throw new BusinessException(ErrorCode.GOAL_UNRELATED_TO_ANY_FAMILY, task.getFailureReason());
        }

        Map<String, Object> parsingResult = new HashMap<>();
        parsingResult.put("originalGoal", task.getTaskGoal());
        parsingResult.put("origin", response.getOrigin());
        parsingResult.put("destination", response.getDestination());
        parsingResult.put("constraints", response.getConstraints());
        parsingResult.put("completionCondition", response.getCompletionCondition());
        task.setGoalParsingResult(toJson(parsingResult));

        if (task.getTaskFamily() == null || task.getTaskFamily().isBlank()) {
            task.setTaskFamily(response.getInferredTaskFamily());
        }

        // 必要信息由系统按任务族核对，不直接采信模型的追问清单（DEF-S3-003/004/005）：
        // 已提供的必要信息不再追问，缺失时只问缺的那几项，不问身份、设备、路线等系统自己决定的内容。
        RequiredInfoGuard.Verdict verdict = null;
        if ("FLIGHT_CHANGE_RESPONSE".equals(task.getTaskFamily())) {
            FlightChangeRequiredInfoGuard.Verdict fv = FlightChangeRequiredInfoGuard.check(sceneParams);
            verdict = new RequiredInfoGuard.Verdict(fv.complete(), fv.questions(), fv.missing());
        } else {
            verdict = RequiredInfoGuard.check(
                    RequiredInfoGuard.requirementsFor(task.getTaskFamily(),
                            taskDefinitionService.findByCode(task.getTaskFamily()).orElse(null)),
                    sceneParams, parsingResult);
        }
        boolean infoComplete = response.isInfoComplete();
        List<String> questions = response.getMissingInfoQuestions();
        if (verdict != null) {
            if (verdict.complete() != infoComplete) {
                boolean isFlight = "FLIGHT_CHANGE_RESPONSE".equals(task.getTaskFamily());
                String prefix = isFlight ? "系统按航班变更必需字段核对：" : "系统按任务族核对必要信息：";
                String detail = verdict.complete()
                        ? (isFlight ? "关键信息已齐全，忽略模型追问" : "均已提供，忽略模型的追问")
                        : ("仍缺 " + verdict.missing());
                taskEventService.append(task.getId(), "GOAL_CLARIFIED", "SYSTEM", "INFO_CHECK_OVERRIDE",
                        prefix + detail + "（模型判断" + (infoComplete ? "完整" : "不完整") + "）");
            }
            infoComplete = verdict.complete();
            questions = verdict.questions();
        }

        if (infoComplete) {
            task.setMissingInfoQuestions(null);
            taskMapper.update(task);
            taskEventService.append(task.getId(), "GOAL_CLARIFIED", "SYSTEM", null,
                    "目标理解完成，关键信息已完整，进入规划上下文构建");
            taskPlanningOrchestrator.advance(task.getId());
        } else {
            // 业务规则4：信息补充完成前不得进入计划生成，任务停留在PLANNING
            task.setMissingInfoQuestions(toJson(questions));
            if (clarificationAnswers != null && clarificationAnswers.size() >= 3) {
                task.setStatus(TaskStatus.PENDING_MANUAL);
                task.setFailureReason("三轮信息补充后仍缺少关键信息，需人工处理");
            }
            taskMapper.update(task);
            taskEventService.append(task.getId(), "GOAL_CLARIFIED", "SYSTEM", "INFO_INCOMPLETE",
                    "目标理解发现信息缺失，已补充" + (clarificationAnswers == null ? 0 : clarificationAnswers.size())
                            + "轮，待补充问题: " + questions);
            if (task.getStatus() == TaskStatus.PENDING_MANUAL) {
                taskEventService.append(task.getId(), "TASK_PENDING_MANUAL", "SYSTEM", "INFO_INCOMPLETE",
                        task.getFailureReason());
            }
        }
    }

    /**
     * SRS_F024.R01 / NT-S3-004: 接收模拟行李测量事件，自动触发超规或非超规闭环任务。
     */
    @Transactional(noRollbackFor = BusinessException.class)
    public Task submitMeasurementEvent(com.airport.ai.task.dto.BaggageMeasurementEventRequest request, User user) {
        if (user == null) {
            user = new User();
            user.setId(0L);
            user.setUsername("SYSTEM");
            user.setRole("OPERATOR");
        }

        // 1. 旅客隐私保护检查（SRS_F024.R09 / DEF-S3-032）
        Map<String, Object> privacyCheckMap = new HashMap<>(request.getExtraParams() != null ? request.getExtraParams() : Map.of());
        privacyCheckMap.put("baggageLocation", request.getBaggageLocation());
        if (request.getBaggageId() != null) privacyCheckMap.put("baggageId", request.getBaggageId());
        if (request.getTargetCounter() != null) privacyCheckMap.put("targetCounter", request.getTargetCounter());
        if (request.getHandlingInstructions() != null) privacyCheckMap.put("handlingInstructions", request.getHandlingInstructions());
        if (request.getThresholdSource() != null) privacyCheckMap.put("thresholdSource", request.getThresholdSource());
        if (request.getDeviceCode() != null) privacyCheckMap.put("deviceCode", request.getDeviceCode());
        SceneParamsPrivacyGuard.reject(privacyCheckMap);

        // 2. 测量数据计算与阈值核定（SRS_F024.R02 / DEF-S3-120）
        if (request.getDimensionThresholdCm() != null && request.getDimensionThresholdCm() <= 0) {
            throw new BusinessException(ErrorCode.PARAM_FORMAT_ERROR, "尺寸阈值必须为大于0的正数");
        }
        if (request.getWeightThresholdKg() != null && request.getWeightThresholdKg() <= 0) {
            throw new BusinessException(ErrorCode.PARAM_FORMAT_ERROR, "重量阈值必须为大于0的正数");
        }

        double length = request.getLength();
        double width = request.getWidth();
        double height = request.getHeight();
        double weight = request.getWeight();
        double totalDimension = length + width + height;
        double dimThreshold = request.getDimensionThresholdCm() != null ? request.getDimensionThresholdCm() : 158.0;
        double weightThreshold = request.getWeightThresholdKg() != null ? request.getWeightThresholdKg() : 23.0;
        String thresholdSource = request.getThresholdSource() != null && !request.getThresholdSource().isBlank()
                ? request.getThresholdSource().trim() : "民航旅客行李运输标准（2026版）";

        boolean isOversize = totalDimension > dimThreshold || weight > weightThreshold;

        // 3. 临时业务编号（SRS_F024.R09）
        String baggageId = request.getBaggageId();
        if (baggageId == null || baggageId.isBlank()) {
            baggageId = "BAG-" + System.currentTimeMillis() % 1000000;
        }

        // 4. 构造场景参数（含柜台可选字段，SRS §5.6.3 / DEF-S3-120）
        String targetCounter = request.getTargetCounter() != null && !request.getTargetCounter().isBlank()
                ? request.getTargetCounter().trim() : "F2_TEST_GATE";
        String instructions = request.getHandlingInstructions() != null && !request.getHandlingInstructions().isBlank()
                ? request.getHandlingInstructions().trim()
                : "超规行李办理流程：1. 前往指定柜台办理称重核验；2. 打印并粘贴超规挂牌；3. 办理专属托运；4. 凭凭证通过安检。";

        Map<String, Object> sceneParams = new LinkedHashMap<>();
        if (request.getExtraParams() != null) {
            Set<String> reservedKeys = Set.of(
                    "length", "width", "height", "weight", "totalDimensionCm",
                    "dimensionThresholdCm", "weightThresholdKg", "thresholdSource",
                    "isOversize", "baggageId", "tempBusinessId", "measureMode",
                    "triggerSource", "baggageLocation", "targetCounter", "targetLocation",
                    "contentType", "contentData", "handlingInstructions", "alertLevel",
                    "routePreference", "deviceCode"
            );
            for (Map.Entry<String, Object> entry : request.getExtraParams().entrySet()) {
                if (!reservedKeys.contains(entry.getKey())) {
                    sceneParams.put(entry.getKey(), entry.getValue());
                }
            }
        }
        sceneParams.put("baggageId", baggageId);
        sceneParams.put("tempBusinessId", baggageId);
        sceneParams.put("baggageLocation", request.getBaggageLocation());
        sceneParams.put("targetCounter", targetCounter);
        sceneParams.put("targetLocation", targetCounter);
        sceneParams.put("length", length);
        sceneParams.put("width", width);
        sceneParams.put("height", height);
        sceneParams.put("weight", weight);
        sceneParams.put("totalDimensionCm", totalDimension);
        sceneParams.put("dimensionThresholdCm", dimThreshold);
        sceneParams.put("weightThresholdKg", weightThreshold);
        sceneParams.put("thresholdSource", thresholdSource);
        sceneParams.put("isOversize", isOversize);
        sceneParams.put("measureMode", "EVENT_TRIGGERED");
        sceneParams.put("routePreference", "BARRIER_FREE");
        sceneParams.put("alertLevel", "WARNING");
        sceneParams.put("contentType", "TEXT");
        sceneParams.put("contentData", "超规行李（临时编号" + baggageId + "）请前往" + targetCounter + "办理托运");
        sceneParams.put("handlingInstructions", instructions);
        sceneParams.put("triggerSource", "MEASUREMENT_EVENT");
        if (request.getDeviceCode() != null) sceneParams.put("deviceCode", request.getDeviceCode());

        // 5. 创建任务实例
        String taskGoal = "处理位于 " + request.getBaggageLocation() + " 的行李测量事件（临时业务编号: " + baggageId
                + "，尺寸: " + length + "×" + width + "×" + height + " cm，重量: " + weight + " kg，判定: "
                + (isOversize ? "超规" : "非超规") + "）";

        Task task = new Task();
        task.setTaskCode(taskCodeGenerator.next());
        task.setTaskFamily("OVERSIZE_BAGGAGE_HANDLING");
        task.setTaskGoal(taskGoal);
        task.setCreatedBy(user.getUsername());
        task.setSceneParams(toJson(sceneParams));

        if (!isOversize) {
            // SRS_F024.R03: 非超规时记录测量结果并结束任务，任务置为已完成，不生成引导步骤
            task.setStatus(TaskStatus.COMPLETED);
            task.setUpdatedAt(LocalDateTime.now());
            taskMapper.insert(task);

            taskEventService.append(task.getId(), "GOAL_SUBMITTED", "SYSTEM", "MEASUREMENT_EVENT",
                    "接收模拟行李测量事件，临时业务编号: " + baggageId + "，位置: " + request.getBaggageLocation()
                            + "，尺寸: " + length + "×" + width + "×" + height + "cm，重量: " + weight + "kg，判定: 非超规");
            taskEventService.append(task.getId(), "TASK_COMPLETED", "SYSTEM", "BAGGAGE_WITHIN_LIMIT",
                    "行李未超规，结束处置；三边和" + totalDimension + "cm（阈值" + dimThreshold + "cm），重量" + weight
                            + "kg（阈值" + weightThreshold + "kg）；来源：" + thresholdSource);

            operationLogService.record(user.getId(), user.getUsername(), user.getRole(),
                    "MEASUREMENT_EVENT_NORMAL", task.getTaskCode(), "SUCCESS", null);
            return task;
        }

        // 超规分支（SRS_F024.R04）：进入规划流程
        task.setStatus(TaskStatus.PLANNING);
        taskMapper.insert(task);

        taskEventService.append(task.getId(), "GOAL_SUBMITTED", "SYSTEM", "MEASUREMENT_EVENT",
                "接收模拟超规行李测量事件，临时业务编号: " + baggageId + "，位置: " + request.getBaggageLocation()
                        + "，尺寸: " + length + "×" + width + "×" + height + "cm，重量: " + weight + "kg，超规判定: 超规");

        operationLogService.record(user.getId(), user.getUsername(), user.getRole(),
                "MEASUREMENT_EVENT_OVERSIZE", task.getTaskCode(), "SUCCESS", null);

        runGoalUnderstanding(task, sceneParams, null);
        return taskMapper.findById(task.getId()).orElse(task);
    }

    /**
     * SRS_F026.R01 / TC-080.S1: 仿真体航班变动事件触发入口。
     */
    @Transactional(noRollbackFor = BusinessException.class)
    public Task submitFlightChangeEvent(com.airport.ai.task.dto.FlightChangeEventRequest request, User user) {
        if (user == null) {
            user = new User();
            user.setId(0L);
            user.setUsername("SIMULATOR");
            user.setRole("OPERATOR");
        }
        Map<String, Object> sceneParams = new HashMap<>(request.getExtraParams() != null ? request.getExtraParams() : Map.of());
        sceneParams.put("eventSource", request.getEventSource() != null ? request.getEventSource() : "SIMULATED_EVENT");
        sceneParams.put("flightNumber", request.getFlightNumber().trim());
        sceneParams.put("changeType", request.getChangeType().trim());
        sceneParams.put("originalTime", request.getOriginalTime().trim());
        sceneParams.put("changeDescription", request.getChangeDescription().trim());
        sceneParams.put("updateType", request.getChangeType().trim());
        sceneParams.put("updateContent", request.getChangeDescription().trim());
        sceneParams.put("displayDuration", request.getDisplayDuration() != null ? request.getDisplayDuration() : 60);
        if (request.getNewTime() != null && !request.getNewTime().isBlank()) {
            sceneParams.put("newTime", request.getNewTime().trim());
        }
        if (request.getOriginalGate() != null && !request.getOriginalGate().isBlank()) {
            sceneParams.put("originalGate", request.getOriginalGate().trim());
        }
        if (request.getNewGate() != null && !request.getNewGate().isBlank()) {
            sceneParams.put("newGate", request.getNewGate().trim());
            sceneParams.put("targetLocation", request.getNewGate().trim());
        }

        String changeLabel = switch (request.getChangeType().trim()) {
            case "DELAY" -> "延误";
            case "EARLY" -> "提前";
            case "GATE_CHANGE" -> "登机口变更";
            case "CANCEL" -> "取消";
            default -> request.getChangeType();
        };

        String goal = "请处理虚构航班" + request.getFlightNumber().trim() + "的" + changeLabel + "事件："
                + request.getChangeDescription().trim() + "。原计划时间" + request.getOriginalTime().trim()
                + (request.getNewTime() != null && !request.getNewTime().isBlank() ? "，变更后时间" + request.getNewTime().trim() : "")
                + (request.getOriginalGate() != null && !request.getOriginalGate().isBlank() ? "，原登机口" + request.getOriginalGate().trim() : "")
                + (request.getNewGate() != null && !request.getNewGate().isBlank() ? "，新登机口" + request.getNewGate().trim() : "")
                + "。请由航延屏发布、智慧航显提示，并由机器人现场通知或引导。";

        SubmitTaskRequest submitReq = new SubmitTaskRequest();
        submitReq.setTaskFamily("FLIGHT_CHANGE_RESPONSE");
        submitReq.setTaskGoal(goal.length() > 500 ? goal.substring(0, 500) : goal);
        submitReq.setSceneParams(sceneParams);
        return submit(submitReq, user);
    }

    private String toJson(Object value) {
        if (value == null) return null;
        try {
            return MAPPER.writeValueAsString(value);
        } catch (Exception e) {
            throw new RuntimeException("序列化失败", e);
        }
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> fromJsonMap(String json) {
        if (json == null || json.isBlank()) return new HashMap<>();
        try {
            return MAPPER.readValue(json, Map.class);
        } catch (Exception e) {
            throw new RuntimeException("反序列化失败", e);
        }
    }

    private List<String> fromJsonQuestions(String json) {
        if (json == null || json.isBlank()) return List.of();
        try {
            return MAPPER.readValue(json, new com.fasterxml.jackson.core.type.TypeReference<List<String>>() {});
        } catch (Exception e) {
            throw new RuntimeException("待补充问题反序列化失败", e);
        }
    }

    private void sanitizeSpecialPassengerRound(Map<String, Object> round) {
        Object questions = round.get("questions");
        if (questions instanceof Iterable<?> iterable) {
            List<String> allowedQuestions = new ArrayList<>();
            for (Object question : iterable) {
                if (question instanceof String text && !SceneParamsPrivacyGuard.asksForIdentity(text)) {
                    allowedQuestions.add(text);
                }
            }
            round.put("questions", allowedQuestions);
        }

        Object answers = round.get("answers");
        if (answers instanceof Map<?, ?> answerMap) {
            round.put("answers", sanitizeSpecialPassengerAnswers(answerMap));
        }
    }

    private Map<String, String> sanitizeSpecialPassengerAnswers(Map<?, ?> answers) {
        Map<String, String> safe = new java.util.LinkedHashMap<>();
        answers.forEach((key, value) -> {
            String question = String.valueOf(key);
            if (!SceneParamsPrivacyGuard.asksForIdentity(question) && value != null) {
                safe.put(question, String.valueOf(value));
            }
        });
        return SceneParamsPrivacyGuard.sanitizeFreeTextAnswers(safe);
    }
}
