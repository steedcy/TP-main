package com.airport.ai.task;

import com.airport.ai.common.BusinessException;
import com.airport.ai.common.ErrorCode;
import com.airport.ai.device.Device;
import com.airport.ai.device.DeviceAgent;
import com.airport.ai.device.DeviceAgentMapper;
import com.airport.ai.device.DeviceCapabilityMapper;
import com.airport.ai.device.DeviceMapper;
import com.airport.ai.event.TaskEventService;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.*;
import java.util.stream.Collectors;

/**
 * 对应5.5.1步骤设备匹配与任务接受、5.5.2业务指令下发与执行反馈。
 * 通过统一设备代理消息网关向设备运行时发送命令，接受/拒绝和执行结果由设备侧报告入口推进状态机。
 */
@Service
public class TaskExecutionOrchestrator {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private final com.airport.ai.baseline.BaselineDryRunLifecycle dryRunLifecycle;
    private final com.airport.ai.baseline.DryRunDeviceSelectionMapper selections;
    private final StepParameterResolver parameterResolver;
    private final TaskMapper taskMapper;
    private final PlanVersionMapper planVersionMapper;
    private final TaskStepAssignmentMapper assignmentMapper;
    private final DeviceAgentMapper deviceAgentMapper;
    private final DeviceMapper deviceMapper;
    private final DeviceCapabilityMapper deviceCapabilityMapper;
    private final TaskEventService taskEventService;
    private final TaskExceptionService taskExceptionService;
    private final com.airport.ai.device.DeviceAgentMessagingService deviceAgentMessagingService;

    public TaskExecutionOrchestrator(TaskMapper taskMapper,
                                      PlanVersionMapper planVersionMapper,
                                      TaskStepAssignmentMapper assignmentMapper,
                                      DeviceAgentMapper deviceAgentMapper,
                                      DeviceMapper deviceMapper,
                                      DeviceCapabilityMapper deviceCapabilityMapper,
                                      TaskEventService taskEventService,
                                      TaskExceptionService taskExceptionService,
                                      com.airport.ai.device.DeviceAgentMessagingService deviceAgentMessagingService,
                                      com.airport.ai.baseline.BaselineDryRunLifecycle dryRunLifecycle,
                                      com.airport.ai.baseline.DryRunDeviceSelectionMapper selections,
                                      StepParameterResolver parameterResolver) {
        this.dryRunLifecycle=dryRunLifecycle; this.selections=selections; this.parameterResolver=parameterResolver;
        this.taskMapper = taskMapper;
        this.planVersionMapper = planVersionMapper;
        this.assignmentMapper = assignmentMapper;
        this.deviceAgentMapper = deviceAgentMapper;
        this.deviceMapper = deviceMapper;
        this.deviceCapabilityMapper = deviceCapabilityMapper;
        this.taskEventService = taskEventService;
        this.taskExceptionService = taskExceptionService;
        this.deviceAgentMessagingService = deviceAgentMessagingService;
    }

    /**
     * 对应5.5.1前置条件：任务处于PENDING_ASSIGNMENT或DOWNGRADING时，计划版本冻结后调用本方法
     * 启动执行监督链路。为计划的每个步骤插入待分配记录，并从第一个步骤开始分配设备。
     */
    @Transactional
    public void startExecution(Long taskId, Long planVersionId) {
        startExecution(taskId, planVersionId, null);
    }

    /**
     * 对应5.5.4局部重新规划后续跑：新计划版本步骤序号小于resumeFromStepSeq的是原计划已完成
     * 步骤原样保留（ReplanningService.replan已将其合并入新版本plan_steps，本身不再重新执行），
     * 只为resumeFromStepSeq及其后续步骤插入待分配记录并从resumeFromStepSeq开始分配设备；
     * 保留步骤直接落一行COMPLETED记录，保证按plan_version_id查询步骤分配情况时序列完整。
     */
    @Transactional
    public void startExecution(Long taskId, Long planVersionId, Integer resumeFromStepSeq) {
        PlanVersion planVersion = planVersionMapper.findById(planVersionId).orElseThrow();
        List<Map<String, Object>> steps = parseSteps(planVersion.getPlanSteps());
        for (Map<String, Object> step : steps) {
            Integer stepSeq = asInteger(step.get("stepSeq"));
            TaskStepAssignment assignment = new TaskStepAssignment();
            assignment.setTaskId(taskId);
            assignment.setPlanVersionId(planVersionId);
            assignment.setStepSeq(stepSeq);
            if (resumeFromStepSeq != null && stepSeq < resumeFromStepSeq) {
                assignment.setStepStatus("COMPLETED");
                assignment.setExecutionResult(String.valueOf(step.getOrDefault("executionResult", "SUCCESS")));
                if (step.get("outputParams") instanceof Map<?, ?> output) assignment.setOutputParams(toJson(output));
            }
            assignmentMapper.insert(assignment);
        }
        Integer firstStepSeq = resumeFromStepSeq != null ? resumeFromStepSeq : asInteger(steps.get(0).get("stepSeq"));
        assignStep(taskId, planVersionId, firstStepSeq);
    }

    /**
     * 对应5.5.3恢复动作"候选设备切换"：将指定代理排除后重新走一次5.5.1分配流程，
     * 供TaskExceptionService在步骤失败/执行超时/相关设备离线时调用。excludeAgentCode
     * 为本次失败/离线的设备代理编码，不加入exclude会导致重新分配时选回同一设备。
     * 找不到候选时assignStep内部会走异常路径2a生成能力缺口异常，交由调用方读取步骤最新状态判定。
     */
    @Transactional
    public void retryAssignmentExcluding(Long taskId, Long planVersionId, Integer stepSeq, String excludeAgentCode) {
        TaskStepAssignment assignment = assignmentMapper.findByPlanVersionIdAndStepSeq(planVersionId, stepSeq)
                .orElseThrow(() -> new BusinessException(ErrorCode.STEP_ASSIGNMENT_NOT_FOUND));
        List<String> rejected = parseRejectedIds(assignment.getRejectedAgentIds());
        if (excludeAgentCode != null && !rejected.contains(excludeAgentCode)) {
            rejected.add(excludeAgentCode);
        }
        assignment.setRejectedAgentIds(toJson(rejected));
        assignment.setCommandId(null);
        assignment.setRetryCount(0);
        assignment.setStepStatus("PENDING_ASSIGNMENT");
        assignment.setDeviceAgentId(null);
        assignment.setUpdatedAt(LocalDateTime.now());
        assignmentMapper.update(assignment);
        assignStep(taskId, planVersionId, stepSeq);
    }

    /** 供TaskExceptionService判断"当前步骤是否还有候选可用"（计划是否可继续的判断依据之一） */
    public boolean hasAvailableCandidate(Long planVersionId, Integer stepSeq, List<String> excludeAgentCodes) {
        Map<String, Object> step = findStep(planVersionId, stepSeq);
        String capabilityType = String.valueOf(step.get("capabilityType"));
        return !findRankedCandidates(capabilityType, step, excludeAgentCodes).isEmpty();
    }

    /**
     * 对应5.5.1基本路径2~4、备选路径4a：查候选并按能力匹配度/距离/负载排序，向排序首位且
     * 未被拒绝过的候选发起TASK_ACCEPT请求。异常路径2a：无候选时不下发任何请求，直接生成异常。
     */
    @Transactional
    @SuppressWarnings("unchecked")
    public void assignStep(Long taskId, Long planVersionId, Integer stepSeq) {
        TaskStepAssignment assignment = assignmentMapper.findByPlanVersionIdAndStepSeq(planVersionId, stepSeq)
                .orElseThrow(() -> new BusinessException(ErrorCode.STEP_ASSIGNMENT_NOT_FOUND));
        Map<String, Object> step = findStep(planVersionId, stepSeq);
        String capabilityType = String.valueOf(step.get("capabilityType"));

        List<String> rejected = parseRejectedIds(assignment.getRejectedAgentIds());
        List<CandidateScore> candidates = findRankedCandidates(capabilityType, step, rejected);
        Task currentTask = taskMapper.findById(taskId).orElseThrow();
        if (Boolean.TRUE.equals(currentTask.getIsDryRun())) {
            Long selected = selections.findByTaskId(taskId).stream().filter(s -> stepSeq.equals(s.getStepSeq()))
                    .map(com.airport.ai.baseline.DryRunDeviceSelection::getDeviceAgentId).findFirst().orElseThrow();
            candidates = candidates.stream().filter(c -> selected.equals(c.agent.getId())).toList();
        }
        assignment.setStepStatus("PENDING_ASSIGNMENT");
        assignment.setRetryCount(0);

        if (candidates.isEmpty()) {
            // 异常路径2a/4b：无候选或全部候选已拒绝，进入5.5.3异常识别与恢复
            taskEventService.append(taskId, "STEP_ASSIGNMENT_FAILED", "SYSTEM", "ERR_NO_CANDIDATE_AVAILABLE",
                    "步骤" + stepSeq + "无可用候选设备（已尝试" + rejected.size() + "个候选均拒绝或无候选）");
            taskExceptionService.handleException(taskId, stepSeq, "CAPABILITY_GAP",
                    "步骤" + stepSeq + "无可用候选设备");
            return;
        }

        CandidateScore chosen = candidates.get(0);
        String candidateOrder = candidates.stream()
                .map(c -> c.agent.getAgentCode() + "(距离" + c.distance + ",负载" + c.workloadScore + ")")
                .collect(Collectors.joining("；"));
        taskEventService.append(taskId, "AGENT_ASSIGNMENT_REQUESTED", "SYSTEM", null,
                "步骤" + stepSeq + "候选排序（能力匹配->距离->负载）: " + candidateOrder
                        + "，向候选" + chosen.agent.getAgentCode() + "发起承接请求");

        String commandId = assignment.getCommandId() != null ? assignment.getCommandId() : generateCommandId();
        assignment.setCommandId(commandId);
        assignment.setDeviceAgentId(chosen.agent.getId());
        assignment.setUpdatedAt(LocalDateTime.now());
        assignmentMapper.update(assignment);

        try {
            deviceAgentMessagingService.requestTaskAcceptance(chosen.agent.getAgentCode(), commandId, taskId, stepSeq,
                    capabilityType, parameterResolver.resolve(taskId, planVersionId, step));
        } catch (RuntimeException ex) {
            taskEventService.append(taskId, "DEVICE_COMMAND_SEND_FAILED", "SYSTEM", "DEVICE_API_ERROR",
                    "向设备代理" + chosen.agent.getAgentCode() + "发送承接请求失败: " + ex.getMessage());
            onTaskResponse(chosen.agent.getAgentCode(), commandId, false, "DEVICE_API_ERROR");
        }
    }

    /**
     * 对应5.5.1业务规则3/4/8：设备侧对TASK_ACCEPT的响应。接受则置BUSY并进入5.5.2指令下发；
     * 拒绝则记录拒绝原因并轮询下一候选，全部候选拒绝转5.5.3异常识别（异常路径4b）。
     */
    @Transactional
    public void onTaskResponse(String agentCode, String commandId, boolean accepted, String rejectReason) {
        TaskStepAssignment assignment = assignmentMapper.findByCommandId(commandId)
                .orElseThrow(() -> new BusinessException(ErrorCode.STEP_ASSIGNMENT_NOT_FOUND));
        DeviceAgent agent = deviceAgentMapper.findByAgentCode(agentCode)
                .orElseThrow(() -> new BusinessException(ErrorCode.DEVICE_AGENT_NOT_FOUND));
        if (assignment.getDeviceAgentId() == null || !assignment.getDeviceAgentId().equals(agent.getId())) {
            throw new BusinessException(ErrorCode.STEP_STATUS_NOT_ALLOWED, "响应代理与当前步骤分配不匹配");
        }
        if (!"PENDING_ASSIGNMENT".equals(assignment.getStepStatus())) {
            // Device-side retries may replay an already accepted response. A matching replay is a no-op.
            if ("EXECUTING".equals(assignment.getStepStatus()) || "COMPLETED".equals(assignment.getStepStatus())) return;
            if ("FROZEN".equals(assignment.getStepStatus())) {
                taskEventService.append(assignment.getTaskId(), "LATE_TASK_RESPONSE_IGNORED", "DEVICE", null,
                        "任务已终止，忽略设备代理" + agentCode + "对承接请求的迟到响应");
                return;
            }
            throw new BusinessException(ErrorCode.STEP_STATUS_NOT_ALLOWED, "步骤当前状态不是待分配，不接受任务响应");
        }

        if (accepted) {
            agent.setWorkStatus("BUSY");
            agent.setCurrentTaskId(assignment.getTaskId());
            agent.setCurrentStepSeq(assignment.getStepSeq());
            deviceAgentMapper.update(agent);

            taskEventService.append(assignment.getTaskId(), "AGENT_ASSIGNED", "SYSTEM", null,
                    "设备代理" + agentCode + "接受步骤" + assignment.getStepSeq() + "承接请求");

            Task task = taskMapper.findById(assignment.getTaskId()).orElseThrow();
            if (task.getStatus() == TaskStatus.PENDING_ASSIGNMENT || task.getStatus() == TaskStatus.DOWNGRADING) {
                task.setStatus(TaskStatus.EXECUTING);
                task.setUpdatedAt(LocalDateTime.now());
                taskMapper.update(task);
            }

            dispatchCommand(assignment);
        } else {
            List<String> rejected = parseRejectedIds(assignment.getRejectedAgentIds());
            rejected.add(agentCode);
            assignment.setRejectedAgentIds(toJson(rejected));
            assignment.setDeviceAgentId(null);
            assignment.setCommandId(null);
            assignment.setUpdatedAt(LocalDateTime.now());
            assignmentMapper.update(assignment);

            taskEventService.append(assignment.getTaskId(), "AGENT_REJECTED", "SYSTEM", null,
                    "设备代理" + agentCode + "拒绝步骤" + assignment.getStepSeq() + "承接请求，原因: " + rejectReason);

            assignStep(assignment.getTaskId(), assignment.getPlanVersionId(), assignment.getStepSeq());
        }
    }

    /**
     * 对应5.5.2基本路径1~2、业务规则3/5：生成全局唯一指令编号，指令下发前对拼装后的
     * inputParams再次做运动安全控制字段拦截（异常路径2a）——5.4.4三类校验只检查计划模板本身，
     * 分配阶段可能对inputParams做二次拼装，故须在真正下发动作发生前再拦截一次。
     */
    private void dispatchCommand(TaskStepAssignment assignment) {
        Map<String, Object> step = findStep(assignment.getPlanVersionId(), assignment.getStepSeq());
        List<String> motionSafetyHits = MotionSafetyGuard.detect(step);
        if (!motionSafetyHits.isEmpty()) {
            taskEventService.append(assignment.getTaskId(), "COMMAND_DISPATCH_BLOCKED", "SYSTEM",
                    "ERR_MOTION_SAFETY_FIELD",
                    "步骤" + assignment.getStepSeq() + "指令内容检出运动安全控制字段: " + motionSafetyHits + "，已拦截下发");
            releaseAgent(assignment.getDeviceAgentId());
            markStepFailed(assignment, "ERR_MOTION_SAFETY_FIELD", "指令内容检出运动安全控制字段，已拦截");
            return;
        }

        assignment.setStepStatus("EXECUTING");
        assignment.setDispatchedAt(LocalDateTime.now());
        assignment.setUpdatedAt(LocalDateTime.now());
        assignmentMapper.update(assignment);

        DeviceAgent agent = deviceAgentMapper.findById(assignment.getDeviceAgentId()).orElseThrow();
        taskEventService.append(assignment.getTaskId(), "STEP_DISPATCHED", "SYSTEM", null,
                "指令" + assignment.getCommandId() + "已下发至设备代理" + agent.getAgentCode()
                        + "，业务意图: " + step.get("stepGoal"));

        try {
            deviceAgentMessagingService.executeCapability(agent.getAgentCode(), assignment.getCommandId(),
                    assignment.getTaskId(), assignment.getStepSeq(), String.valueOf(step.get("capabilityType")),
                    assignment.getRetryCount(), parameterResolver.resolve(assignment.getTaskId(), assignment.getPlanVersionId(), step));
        } catch (RuntimeException ex) {
            onExecutionFeedback(agent.getAgentCode(), assignment.getCommandId(), assignment.getRetryCount(),
                    "FAILED", "DEVICE_API_ERROR", Map.of("message", ex.getMessage() == null ? "device call failed" : ex.getMessage()));
        }
    }

    /**
     * 对应5.5.2基本路径3~5、备选路径3a、异常路径3b/4a：接收设备侧执行反馈。SUCCESS且完成条件
     * 满足则释放占用并推进下一步骤/整体完成；FAILED首次自动重试一次（沿用同一command_id，
     * 不重新分配设备）；重试后仍失败或反馈判定完成条件未满足，转5.5.3异常识别与恢复。
     */
    @Transactional
    public void onExecutionFeedback(String agentCode, String commandId, String executionResult,
                                     String reasonCode, Map<String, Object> outputParams) {
        onExecutionFeedback(agentCode, commandId, 0, executionResult, reasonCode, outputParams);
    }

    @Transactional
    public void onExecutionFeedback(String agentCode, String commandId, int attemptNo, String executionResult,
                                     String reasonCode, Map<String, Object> outputParams) {
        TaskStepAssignment assignment = assignmentMapper.findByCommandId(commandId)
                .orElseThrow(() -> new BusinessException(ErrorCode.STEP_ASSIGNMENT_NOT_FOUND));
        DeviceAgent reportingAgent = deviceAgentMapper.findByAgentCode(agentCode)
                .orElseThrow(() -> new BusinessException(ErrorCode.DEVICE_AGENT_NOT_FOUND));
        if (assignment.getDeviceAgentId() == null || !assignment.getDeviceAgentId().equals(reportingAgent.getId())) {
            throw new BusinessException(ErrorCode.STEP_STATUS_NOT_ALLOWED, "反馈代理与当前步骤分配不匹配");
        }
        if (attemptNo != assignment.getRetryCount()) {
            taskEventService.append(assignment.getTaskId(), "STALE_EXECUTION_FEEDBACK_IGNORED", "DEVICE",
                    "STALE_ATTEMPT", "忽略指令" + commandId + "第" + attemptNo + "次尝试的迟到反馈");
            return;
        }
        if (!"EXECUTING".equals(assignment.getStepStatus())) {
            if ("COMPLETED".equals(assignment.getStepStatus()) || "FAILED".equals(assignment.getStepStatus())) return;
            if ("FROZEN".equals(assignment.getStepStatus())) {
                taskEventService.append(assignment.getTaskId(), "LATE_EXECUTION_FEEDBACK_IGNORED", "DEVICE",
                        "TASK_TERMINATED", "任务已终止，忽略指令" + commandId + "的迟到执行反馈");
                return;
            }
            throw new BusinessException(ErrorCode.STEP_STATUS_NOT_ALLOWED, "步骤当前状态不是执行中，不接受执行反馈");
        }

        assignment.setExecutionResult(executionResult);
        assignment.setReasonCode(reasonCode);
        assignment.setOutputParams(toJson(outputParams));
        assignment.setFeedbackAt(LocalDateTime.now());
        assignment.setUpdatedAt(LocalDateTime.now());

        taskEventService.append(assignment.getTaskId(), "EXECUTION_FEEDBACK_RECEIVED", "SYSTEM", reasonCode,
                "指令" + commandId + "收到设备代理" + agentCode + "执行反馈: " + executionResult);

        // 对应5.5.2业务规则7：完成判定以计划中定义的完成条件为依据，不以"已收到SUCCESS反馈"为完成
        Map<String, Object> step = findStep(assignment.getPlanVersionId(), assignment.getStepSeq());
        boolean completionSatisfied = "SUCCESS".equals(executionResult)
                && isCompletionConditionSatisfied(step, outputParams);

        if (completionSatisfied) {
            assignment.setStepStatus("COMPLETED");
            assignmentMapper.update(assignment);
            releaseAgent(assignment.getDeviceAgentId());
            taskEventService.append(assignment.getTaskId(), "STEP_COMPLETED", "SYSTEM", null,
                    "步骤" + assignment.getStepSeq() + "完成条件已满足: " + step.get("completionCondition"));
            advanceAfterStepCompleted(assignment.getTaskId(), assignment.getPlanVersionId(), assignment.getStepSeq());
            return;
        }

        // 异常路径4a：设备返回SUCCESS但完成条件未满足，按步骤失败处理，不视为完成
        String failureDetail = "SUCCESS".equals(executionResult) && !completionSatisfied
                ? "设备返回执行成功，但完成条件未满足" : "执行结果: " + executionResult + "，原因: " + reasonCode;

        if (Boolean.TRUE.equals(taskMapper.findById(assignment.getTaskId()).orElseThrow().getIsDryRun())) {
            assignment.setStepStatus("FAILED"); assignmentMapper.update(assignment);
            releaseAgent(assignment.getDeviceAgentId());
            dryRunLifecycle.finish(assignment.getTaskId(), false, failureDetail);
            return;
        }
        if (assignment.getRetryCount() < 1) {
            // 备选路径3a：失败只自动重试一次，沿用同一command_id（对应5.5.2业务规则2）
            assignment.setRetryCount(assignment.getRetryCount() + 1);
            assignment.setStepStatus("EXECUTING");
            assignment.setDispatchedAt(LocalDateTime.now());
            assignment.setFeedbackAt(null);
            assignmentMapper.update(assignment);
            taskEventService.append(assignment.getTaskId(), "STEP_RETRY_DISPATCHED", "SYSTEM", reasonCode,
                    "步骤" + assignment.getStepSeq() + "自动重试1次，沿用指令编号" + commandId + "，原因: " + failureDetail);

            try {
                deviceAgentMessagingService.executeCapability(agentCode, commandId, assignment.getTaskId(),
                        assignment.getStepSeq(), String.valueOf(step.get("capabilityType")),
                        assignment.getRetryCount(), parameterResolver.resolve(assignment.getTaskId(), assignment.getPlanVersionId(), step));
            } catch (RuntimeException ex) {
                onExecutionFeedback(agentCode, commandId, assignment.getRetryCount(), "FAILED", "DEVICE_API_ERROR",
                        Map.of("message", ex.getMessage() == null ? "device call failed" : ex.getMessage()));
            }
            return;
        }

        // 异常路径3b：重试后仍失败，释放占用并转5.5.3异常识别与恢复
        assignment.setStepStatus("FAILED");
        assignmentMapper.update(assignment);
        releaseAgent(assignment.getDeviceAgentId());
        taskEventService.append(assignment.getTaskId(), "STEP_FAILED", "SYSTEM", reasonCode,
                "步骤" + assignment.getStepSeq() + "重试后仍失败: " + failureDetail);
        taskExceptionService.handleException(assignment.getTaskId(), assignment.getStepSeq(), "STEP_FAILED", failureDetail);
    }

    /** 对应5.5.2业务规则8/9：全部步骤完成条件满足后置任务完成，否则按顺序取下一步骤分配设备 */
    private void advanceAfterStepCompleted(Long taskId, Long planVersionId, Integer completedStepSeq) {
        List<TaskStepAssignment> all = assignmentMapper.findByPlanVersionIdOrderByStepSeqAsc(planVersionId);
        Optional<TaskStepAssignment> next = all.stream()
                .filter(a -> a.getStepSeq() > completedStepSeq)
                .min(Comparator.comparing(TaskStepAssignment::getStepSeq));

        if (next.isPresent()) {
            assignStep(taskId, planVersionId, next.get().getStepSeq());
            return;
        }

        Task task = taskMapper.findById(taskId).orElseThrow();
        task.setStatus(TaskStatus.COMPLETED);
        task.setUpdatedAt(LocalDateTime.now());
        taskMapper.update(task);
        taskEventService.append(taskId, "TASK_COMPLETED", "SYSTEM", null, "全部步骤完成条件均已满足，任务完成");
        if (Boolean.TRUE.equals(task.getIsDryRun())) dryRunLifecycle.finish(taskId, true, "所有步骤均收到实际设备成功反馈");
    }

    /** 对应5.5.2异常路径2a/3b场景下的步骤失败标记，复用于运动安全拦截场景 */
    private void markStepFailed(TaskStepAssignment assignment, String reasonCode, String detail) {
        assignment.setStepStatus("FAILED");
        assignment.setReasonCode(reasonCode);
        assignment.setUpdatedAt(LocalDateTime.now());
        assignmentMapper.update(assignment);
        taskExceptionService.handleException(assignment.getTaskId(), assignment.getStepSeq(), "STEP_FAILED", detail);
    }

    private void releaseAgent(Long deviceAgentId) {
        if (deviceAgentId == null) return;
        deviceAgentMapper.findById(deviceAgentId).ifPresent(agent -> {
            agent.setWorkStatus("IDLE");
            agent.setCurrentTaskId(null);
            agent.setCurrentStepSeq(null);
            deviceAgentMapper.update(agent);
        });
    }

    /**
     * 对应5.5.1业务规则1/2/5：候选须同时满足具备所需能力、在线、空闲；候选排序依据
     * 能力匹配度（硬性前提，已满足）->与步骤目标位置的距离->当前负载依次排序。
     * 步骤inputParams若提供数值坐标targetX/targetY则参与距离计算，否则距离项视为并列，
     * 距离数据的结构化来源（如网格坐标到区域编码的映射服务）超出本期范围。
     */
    @SuppressWarnings("unchecked")
    private List<CandidateScore> findRankedCandidates(String capabilityType, Map<String, Object> step,
                                                        List<String> excludeAgentCodes) {
        List<DeviceAgent> onlineIdle = deviceAgentMapper.findByAgentStatusAndOnlineStatus("ENABLED", "ONLINE")
                .stream()
                .filter(a -> "IDLE".equals(a.getWorkStatus()))
                .filter(a -> !excludeAgentCodes.contains(a.getAgentCode()))
                .toList();
        if (onlineIdle.isEmpty()) {
            return List.of();
        }

        List<Long> deviceIds = onlineIdle.stream().map(DeviceAgent::getDeviceId).distinct().toList();
        Map<Long, Device> deviceById = deviceMapper.findByIds(deviceIds).stream()
                .collect(Collectors.toMap(Device::getId, d -> d));

        BigDecimal targetX = asBigDecimal(step.get("targetX"));
        BigDecimal targetY = asBigDecimal(step.get("targetY"));

        List<CandidateScore> scored = new ArrayList<>();
        for (DeviceAgent agent : onlineIdle) {
            Device device = deviceById.get(agent.getDeviceId());
            if (device == null) continue;
            boolean hasCapability = deviceHasCapability(device.getId(), capabilityType);
            if (!hasCapability) continue;

            double distance = (targetX != null && targetY != null
                    && device.getPositionX() != null && device.getPositionY() != null)
                    ? Math.hypot(device.getPositionX().doubleValue() - targetX.doubleValue(),
                                 device.getPositionY().doubleValue() - targetY.doubleValue())
                    : 0.0;
            int workloadScore = "IDLE".equals(agent.getWorkStatus()) ? 0 : 1;
            scored.add(new CandidateScore(agent, distance, workloadScore));
        }
        scored.sort(Comparator.comparingDouble((CandidateScore c) -> c.distance)
                .thenComparingInt(c -> c.workloadScore)
                .thenComparing(c -> c.agent.getAgentCode()));
        return scored;
    }

    private boolean deviceHasCapability(Long deviceId, String capabilityType) {
        return deviceCapabilityMapper.existsByDeviceIdAndCapabilityTypeAndCapabilityStatus(
                deviceId, capabilityType, "ENABLED");
    }

    private record CandidateScore(DeviceAgent agent, double distance, int workloadScore) {}

    private Map<String, Object> findStep(Long planVersionId, Integer stepSeq) {
        PlanVersion planVersion = planVersionMapper.findById(planVersionId).orElseThrow();
        return parseSteps(planVersion.getPlanSteps()).stream()
                .filter(s -> stepSeq.equals(asInteger(s.get("stepSeq"))))
                .findFirst().orElseThrow();
    }

    /**
     * 完成条件判定为业务语义描述（如"旅客到达登机口"），本期以outputParams中约定的
     * arrivalStatus/completed等标记做通用判定；未提供标记时以executionResult=SUCCESS为准
     * （保留对业务规则7"不以已收到为完成"的语义区分，为后续接入更精细的条件解析预留扩展点）。
     */
    private boolean isCompletionConditionSatisfied(Map<String, Object> step, Map<String, Object> outputParams) {
        if (outputParams == null || outputParams.isEmpty()) return false;
        Object explicit = outputParams.get("completed");
        if (explicit != null) return Boolean.TRUE.equals(explicit);
        String marker = switch (String.valueOf(step.get("capabilityType"))) {
            case "CAP_INFO_DISPLAY" -> "displayStatus";
            case "CAP_FLIGHT_UPDATE" -> "publishStatus";
            case "CAP_BAGGAGE_MEASURE" -> "measureStatus";
            case "CAP_OVERSIZE_ALERT" -> "reportStatus";
            case "CAP_ESCORT" -> "arrivalStatus";
            case "CAP_NOTIFICATION" -> "notificationStatus";
            case "CAP_NAVIGATION" -> "routeGenerated";
            default -> "completed";
        };
        Object value=outputParams.get(marker);
        return "arrivalStatus".equals(marker) ? "ARRIVED".equals(value)
                : "routeGenerated".equals(marker) ? Boolean.TRUE.equals(value) : "SUCCESS".equals(value);
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> stepInputParams(Map<String, Object> step) {
        Object input = step.get("inputParams");
        if (input instanceof Map<?, ?> map) return (Map<String, Object>) map;
        return Map.of();
    }

    private List<String> parseRejectedIds(String json) {
        if (json == null || json.isBlank()) return new ArrayList<>();
        try {
            return new ArrayList<>((List<String>) MAPPER.readValue(json, List.class));
        } catch (Exception e) {
            return new ArrayList<>();
        }
    }

    /** 列宽32（V2迁移），CMD-yyyyMMddHHmmss(14)-8位大写十六进制共27字符，留有余量 */
    private String generateCommandId() {
        String datePart = LocalDateTime.now().format(java.time.format.DateTimeFormatter.ofPattern("yyyyMMddHHmmss"));
        return "CMD-" + datePart + "-" + UUID.randomUUID().toString().replace("-", "").substring(0, 8).toUpperCase();
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

    private BigDecimal asBigDecimal(Object value) {
        if (value == null) return null;
        if (value instanceof BigDecimal b) return b;
        if (value instanceof Number n) return BigDecimal.valueOf(n.doubleValue());
        try { return new BigDecimal(value.toString()); } catch (NumberFormatException e) { return null; }
    }

    private String toJson(Object value) {
        try {
            return MAPPER.writeValueAsString(value);
        } catch (Exception e) {
            throw new RuntimeException("序列化失败", e);
        }
    }
}
