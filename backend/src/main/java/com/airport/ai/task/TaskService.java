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
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.HashMap;
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
        PageHelper.startPage(page, size);
        return PageResult.of(new PageInfo<>(taskMapper.searchPaged(
                blankToNull(taskCode), status, blankToNull(taskFamily), createdFrom, createdTo)));
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
        FlightChangeSceneValidator.validate(request.getTaskFamily(), request.getSceneParams());

        Task task = new Task();
        task.setTaskCode(taskCodeGenerator.next());
        task.setTaskGoal(request.getTaskGoal());
        task.setTaskFamily(request.getTaskFamily());
        task.setSceneParams(toJson(request.getSceneParams()));
        task.setStatus(TaskStatus.PLANNING);
        task.setCreatedBy(operator.getUsername());
        taskMapper.insert(task);

        taskEventService.append(task.getId(), "GOAL_SUBMITTED", "OPERATOR", null,
                "运行操作员" + operator.getUsername() + "提交任务目标: " + request.getTaskGoal());
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

        Map<String, Object> mergedSceneParams = new HashMap<>(fromJsonMap(task.getSceneParams()));
        mergedSceneParams.put("clarificationAnswers", request.getAnswers());

        task.setSceneParams(toJson(mergedSceneParams));
        taskMapper.update(task);

        taskEventService.append(task.getId(), "GOAL_CLARIFIED", "OPERATOR", null,
                "运行操作员" + operator.getUsername() + "补充信息: " + request.getAnswers());

        runGoalUnderstanding(task, mergedSceneParams, request.getAnswers());
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
    @Transactional
    public Task manualAction(Long taskId, String action, User operator) {
        Task task = get(taskId);
        if (task.getStatus() != TaskStatus.PENDING_MANUAL) {
            throw new BusinessException(ErrorCode.TASK_STATUS_NOT_ALLOWED, "任务当前状态不是待人工处理，不可执行该操作");
        }

        switch (action) {
            case "SWITCH_TO_BASELINE", "RETRY_PLANNING" -> {
                task.setStatus(TaskStatus.PLANNING);
                task.setUpdatedAt(LocalDateTime.now());
                taskMapper.update(task);
                taskEventService.append(taskId, "SWITCH_TO_BASELINE".equals(action)
                                ? "BASELINE_SWITCH_REQUESTED" : "REPLANNING_TRIGGERED", "OPERATOR", null,
                        "运行操作员" + operator.getUsername() + "选择" + action);
                if ("SWITCH_TO_BASELINE".equals(action)) taskPlanningOrchestrator.switchToBaseline(taskId);
                else taskPlanningOrchestrator.advance(taskId);
            }
            case "MARK_FAILED" -> {
                task.setStatus(TaskStatus.FAILED);
                task.setFailureReason("运行操作员" + operator.getUsername() + "在待人工处理阶段手动置为失败");
                task.setUpdatedAt(LocalDateTime.now());
                taskMapper.update(task);
                taskEventService.append(taskId, "TASK_FAILED", "OPERATOR", null, task.getFailureReason());
            }
            default -> throw new BusinessException(ErrorCode.PARAM_FORMAT_ERROR, "未知的人工处理动作: " + action);
        }

        Task result = get(taskId);
        boolean failed = result.getStatus() == TaskStatus.PENDING_MANUAL;
        if (failed) taskEventService.append(taskId, "TASK_MANUAL_ACTION_FAILED", "SYSTEM",
                "ERR_MANUAL_ACTION_FAILED", result.getFailureReason());
        operationLogService.record(operator.getId(), operator.getUsername(), operator.getRole(),
                "TASK_MANUAL_ACTION", task.getTaskCode() + " -> " + action, failed ? "FAILED" : "SUCCESS", null);
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

        taskEventService.append(task.getId(), "MANUAL_TERMINATED", "OPERATOR", null,
                "运行操作员" + operator.getUsername() + "在计划生成前取消任务: " + reason);
        operationLogService.record(operator.getId(), operator.getUsername(), operator.getRole(),
                "TASK_CANCEL", task.getTaskCode(), "SUCCESS", null);
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
        Task task = get(taskId);
        Set<TaskStatus> terminable = Set.of(TaskStatus.PLANNING, TaskStatus.SUPERVISING,
                TaskStatus.PENDING_ASSIGNMENT, TaskStatus.DOWNGRADING, TaskStatus.EXECUTING, TaskStatus.PENDING_MANUAL);
        if (!terminable.contains(task.getStatus())) {
            throw new BusinessException(ErrorCode.TASK_TERMINATE_NOT_ALLOWED,
                    "任务当前状态为" + task.getStatus() + "，已处于终态，不可终止");
        }

        List<Map<String, String>> deviceResults = new ArrayList<>();
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
        for (var agent : affectedAgents) {
            String agentCode = agent.getAgentCode();
            TaskStepAssignment assignment = activeAssignmentsByAgent.get(agent.getId());
            String cancelCommandId = assignment != null && assignment.getCommandId() != null
                    ? assignment.getCommandId() : generateCancelCommandId();
            try {
                deviceAgentMessagingService.cancelTask(agentCode, cancelCommandId, taskId,
                        assignment == null ? agent.getCurrentStepSeq() : assignment.getStepSeq());
                taskEventService.append(taskId, "TASK_CANCEL_REQUESTED", "OPERATOR", null,
                        "已向设备代理" + agentCode + "发送业务任务取消请求");
                deviceResults.add(Map.of("agentId", agentCode, "result", "CANCEL_QUEUED"));
            } catch (RuntimeException ex) {
                taskEventService.append(taskId, "TASK_CANCEL_DELIVERY_FAILED", "OPERATOR", "DEVICE_API_ERROR",
                        "向设备代理" + agentCode + "发送业务任务取消请求失败: " + ex.getMessage());
                deviceResults.add(Map.of("agentId", agentCode, "result", "CANCEL_FAILED"));
            }
            // A queued cancellation does not prove the device stopped. Keep it unavailable
            // until an IDLE status report confirms release (or an operator resolves it).
            agent.setWorkStatus("BUSY");
            agent.setCurrentTaskId(taskId);
            deviceAgentMapper.update(agent);
        }

        task.setStatus(TaskStatus.MANUAL_TERMINATED);
        task.setManualTerminateReason(reason);
        task.setUpdatedAt(LocalDateTime.now());
        taskMapper.update(task);

        taskEventService.append(taskId, "MANUAL_TERMINATED", "OPERATOR", null,
                "运行操作员" + operator.getUsername() + "人工终止任务，原因: " + reason
                        + "，涉及设备: " + deviceResults.stream().map(m -> m.get("agentId")).toList());
        operationLogService.record(operator.getId(), operator.getUsername(), operator.getRole(),
                "TASK_TERMINATE", task.getTaskCode(), "SUCCESS", null);
        return task;
    }

    private String generateCancelCommandId() {
        String datePart = LocalDateTime.now().format(java.time.format.DateTimeFormatter.ofPattern("yyyyMMddHHmmss"));
        return "CMD-" + datePart + "-" + UUID.randomUUID().toString().replace("-", "").substring(0, 8).toUpperCase();
    }

    /**
     * 对应5.4.1业务规则2/3/4/6/7、异常路径4b/4c。目标理解调用外部规划模型服务
     * （方案A独立端点），60秒超时约束由GoalUnderstandingService实现内部保证。
     * 提交给理解服务的sceneParams不得包含旅客真实身份信息，只保留结构化场景参数
     * （协助类型等），本方法不做额外脱敏处理——业务规则6要求提交入口本身不采集
     * 真实身份字段，前端与SubmitTaskRequest均未开放姓名/证件号等字段。
     */
    private void runGoalUnderstanding(Task task, Map<String, Object> sceneParams, Map<String, String> clarificationAnswers) {
        GoalUnderstandingRequest request = new GoalUnderstandingRequest();
        request.setRequestId(UUID.randomUUID().toString());
        request.setTaskGoal(task.getTaskGoal());
        request.setTaskFamily(task.getTaskFamily());
        request.setSceneParams(sceneParams);
        if (clarificationAnswers != null) {
            request.setClarificationAnswers(List.of(Map.of("answers", clarificationAnswers)));
        }

        GoalUnderstandingResponse response = goalUnderstandingService.understand(request);

        if (!response.isSuccess()) {
            // 异常路径4b：超时或异常，不进入计划生成，不下发任何设备指令
            taskEventService.append(task.getId(), "GOAL_UNDERSTANDING_FAILED", "SYSTEM",
                    "ERR_GOAL_UNDERSTANDING_TIMEOUT",
                    "目标理解调用规划模型服务失败: " + response.getErrorMessage());
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

        if (response.isInfoComplete()) {
            task.setMissingInfoQuestions(null);
            taskMapper.update(task);
            taskEventService.append(task.getId(), "GOAL_CLARIFIED", "SYSTEM", null,
                    "目标理解完成，关键信息已完整，进入规划上下文构建");
            taskPlanningOrchestrator.advance(task.getId());
        } else {
            // 业务规则4：信息补充完成前不得进入计划生成，任务停留在PLANNING
            task.setMissingInfoQuestions(toJson(response.getMissingInfoQuestions()));
            taskMapper.update(task);
            taskEventService.append(task.getId(), "GOAL_CLARIFIED", "SYSTEM", "INFO_INCOMPLETE",
                    "目标理解发现信息缺失，待补充问题: " + response.getMissingInfoQuestions());
        }
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
}
