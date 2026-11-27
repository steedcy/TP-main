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
    @org.springframework.beans.factory.annotation.Autowired(required = false)
    private com.airport.ai.device.DeviceEventService deviceEventService;
    @org.springframework.beans.factory.annotation.Autowired(required = false)
    private TerminalMapMapper terminalMapMapper;
    @org.springframework.beans.factory.annotation.Autowired(required = false)
    private SpatialRuleConfig spatialRuleConfig;
    @org.springframework.beans.factory.annotation.Value("${app.device.fixed-device-strict-zone:true}")
    private boolean fixedDeviceStrictZone = true;
    @org.springframework.beans.factory.annotation.Value("${app.device.fixed-max-service-distance:650}")
    private double fixedMaxServiceDistance = 650.0;
    @org.springframework.beans.factory.annotation.Value("${app.device.robot-max-service-distance:1600}")
    private double robotMaxServiceDistance = 1600.0;

    private boolean strictZoneEnabled() {
        return spatialRuleConfig != null ? spatialRuleConfig.isFixedDeviceStrictZone() : fixedDeviceStrictZone;
    }

    private double fixedMaxDist() {
        return spatialRuleConfig != null ? spatialRuleConfig.getFixedMaxServiceDistance() : fixedMaxServiceDistance;
    }

    private double robotMaxDist() {
        return spatialRuleConfig != null ? spatialRuleConfig.getRobotMaxServiceDistance() : robotMaxServiceDistance;
    }

    public void setTerminalMapMapper(TerminalMapMapper terminalMapMapper) {
        this.terminalMapMapper = terminalMapMapper;
    }

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
        // DEF-S3-111: 当局部重规划尾部首步为条件节点时，折叠后只保留可执行动作（序号大于等于resumeFromStepSeq）；
        // 必须从步骤列表中寻找首个 stepSeq >= resumeFromStepSeq 的可执行步骤，严禁直接使用可能不存在的 resumeFromStepSeq
        Integer firstStepSeq = null;
        for (Map<String, Object> step : steps) {
            Integer sSeq = asInteger(step.get("stepSeq"));
            if (sSeq == null) continue;
            if (resumeFromStepSeq == null || sSeq >= resumeFromStepSeq) {
                firstStepSeq = sSeq;
                break;
            }
        }
        if (firstStepSeq != null) {
            assignStep(taskId, planVersionId, firstStepSeq);
        } else {
            List<TaskStepAssignment> all = assignmentMapper.findByPlanVersionIdOrderByStepSeqAsc(planVersionId);
            completeAvailableChannels(taskId, planVersionId, all);
        }
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
        assignment.setExecuteCommandId(null);
        assignment.setRetryCount(0);
        assignment.setStepStatus("PENDING_ASSIGNMENT");
        assignment.setDeviceAgentId(null);
        assignment.setUpdatedAt(LocalDateTime.now());
        assignmentMapper.update(assignment);
        assignStep(taskId, planVersionId, stepSeq);
    }

    /** 计划步骤要求的能力类型，供设备能力停用时判断是否影响进行中步骤（SRS_F006.R06） */
    public String stepCapabilityType(Long planVersionId, Integer stepSeq) {
        return String.valueOf(findStep(planVersionId, stepSeq).get("capabilityType"));
    }

    /** 供TaskExceptionService判断"当前步骤是否还有候选可用"（计划是否可继续的判断依据之一） */
    public boolean hasAvailableCandidate(Long planVersionId, Integer stepSeq, List<String> excludeAgentCodes) {
        Map<String, Object> step = findStep(planVersionId, stepSeq);
        String capabilityType = String.valueOf(step.get("capabilityType"));
        String family = taskMapper.findById(planVersionMapper.findById(planVersionId).orElseThrow().getTaskId())
                .orElseThrow().getTaskFamily();
        TaskStepAssignment assignment = assignmentMapper.findByPlanVersionIdAndStepSeq(planVersionId, stepSeq).orElse(null);
        List<String> allExcludes = new ArrayList<>();
        if (assignment != null && assignment.getRejectedAgentIds() != null) {
            allExcludes.addAll(parseRejectedIds(assignment.getRejectedAgentIds()));
        }
        if (excludeAgentCodes != null) {
            for (String code : excludeAgentCodes) {
                if (code != null && !allExcludes.contains(code)) {
                    allExcludes.add(code);
                }
            }
        }
        return !findRankedCandidates(capabilityType, step, allExcludes, family, planVersionId, stepSeq).isEmpty();
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
        Task currentTask = taskMapper.findById(taskId).orElseThrow();
        // 终态硬拦截（SRS_F021.R07）：任务处于 MANUAL_TERMINATED 或步骤已被冻结时，严禁继续分派或下发指令
        if (currentTask.getStatus() == TaskStatus.MANUAL_TERMINATED || "FROZEN".equals(assignment.getStepStatus())) {
            return;
        }
        if ("CAP_BAGGAGE_MEASURE".equals(capabilityType)
                && "OVERSIZE_BAGGAGE_HANDLING".equals(currentTask.getTaskFamily())
                && !Boolean.TRUE.equals(currentTask.getIsDryRun())
                && reuseMeasurementEvent(currentTask, assignment, step)) return;
        List<CandidateScore> candidates = findRankedCandidates(capabilityType, step, rejected, currentTask.getTaskFamily(), planVersionId, stepSeq);
        if (Boolean.TRUE.equals(currentTask.getIsDryRun())) {
            Long selected = selections.findByTaskId(taskId).stream().filter(s -> stepSeq.equals(s.getStepSeq()))
                    .map(com.airport.ai.baseline.DryRunDeviceSelection::getDeviceAgentId).findFirst().orElseThrow();
            candidates = candidates.stream().filter(c -> selected.equals(c.agent.getId())).toList();
        }
        assignment.setStepStatus("PENDING_ASSIGNMENT");
        assignment.setRetryCount(0);

        if (candidates.isEmpty()) {
            if (!Boolean.TRUE.equals(currentTask.getIsDryRun()) && rejected.isEmpty()
                    && CoreScenarioChannelPolicy.isFlightChannel(currentTask.getTaskFamily(), capabilityType)) {
                skipUnavailableFlightChannel(currentTask, assignment, capabilityType);
                return;
            }
            if (!Boolean.TRUE.equals(currentTask.getIsDryRun()) && rejected.isEmpty()
                    && "OVERSIZE_BAGGAGE_HANDLING".equals(currentTask.getTaskFamily())
                    && "CAP_NAVIGATION".equals(capabilityType)) {
                skipUnavailableNavigationChannel(currentTask, assignment, capabilityType);
                return;
            }
            if (!Boolean.TRUE.equals(currentTask.getIsDryRun()) && rejected.isEmpty()
                    && "SPECIAL_PASSENGER_SERVICE".equals(currentTask.getTaskFamily())
                    && ("CAP_NOTIFICATION".equals(capabilityType) || "CAP_ESCORT".equals(capabilityType) || "CAP_NAVIGATION".equals(capabilityType))) {
                skipUnavailableSpecialPassengerChannel(currentTask, assignment, capabilityType);
                return;
            }
            // 异常路径2a/4b：无候选(CAPABILITY_GAP)或全部候选已拒绝(ASSIGNMENT_FAILED)，进入5.5.3异常识别与恢复
            boolean hasRejected = !rejected.isEmpty();
            String errReasonCode = hasRejected ? "ERR_ALL_CANDIDATES_REJECTED" : "ERR_NO_CANDIDATE_AVAILABLE";
            String exceptionType = hasRejected ? "ASSIGNMENT_FAILED" : "CAPABILITY_GAP";
            String eventDetail = hasRejected
                    ? "步骤" + stepSeq + "所有候选设备均已拒绝承接（已尝试" + rejected.size() + "个候选）"
                    : "步骤" + stepSeq + "无可用候选设备（已尝试0个候选均拒绝或无候选）";
            String exceptionDetail = hasRejected
                    ? "步骤" + stepSeq + "全部候选设备均已拒绝承接"
                    : "步骤" + stepSeq + "无可用候选设备";
            taskEventService.append(taskId, "STEP_ASSIGNMENT_FAILED", "SYSTEM", errReasonCode, eventDetail);
            taskExceptionService.handleException(taskId, stepSeq, exceptionType, exceptionDetail);
            return;
        }

        CandidateScore chosen = candidates.get(0);
        String candidateOrder = candidates.stream()
                .map(c -> c.agent.getAgentCode() + "(匹配度" + c.matchScore + ",距离" + c.distance + ",负载" + c.workloadScore + ")")
                .collect(Collectors.joining("；"));
        taskEventService.append(taskId, "AGENT_ASSIGNMENT_REQUESTED", "SYSTEM", null,
                "步骤" + stepSeq + "候选排序（能力匹配->距离->负载）: " + candidateOrder
                        + "，向候选" + chosen.agent.getAgentCode() + "发起承接请求");

        String commandId = assignment.getCommandId() != null ? assignment.getCommandId() : generateCommandId();
        assignment.setCommandId(commandId);
        assignment.setDeviceAgentId(chosen.agent.getId());
        assignment.setAcceptanceRequestedAt(LocalDateTime.now());
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
        if (!"PENDING_ASSIGNMENT".equals(assignment.getStepStatus())) {
            // Device-side retries may replay an already accepted response. A matching replay is a no-op.
            if ("EXECUTING".equals(assignment.getStepStatus()) || "COMPLETED".equals(assignment.getStepStatus())) return;
            if ("FROZEN".equals(assignment.getStepStatus())) {
                taskEventService.append(assignment.getTaskId(), "LATE_TASK_RESPONSE_IGNORED", "SYSTEM", null,
                        "任务已终止，忽略设备代理" + agentCode + "对承接请求的迟到响应");
                return;
            }
            throw new BusinessException(ErrorCode.STEP_STATUS_NOT_ALLOWED, "步骤当前状态不是待分配，不接受任务响应");
        }

        LocalDateTime now = LocalDateTime.now();
        assignment.setAcceptedAt(now);
        if (assignment.getAcceptanceRequestedAt() != null) {
            long duration = java.time.Duration.between(assignment.getAcceptanceRequestedAt(), now).toMillis();
            assignment.setAcceptanceDurationMs(Math.max(0, duration));
        }

        if (accepted) {
            // DEF-S3-100: 使用数据库行锁获取代理最新原子状态，彻底杜绝并发抢占时的竞态窗口
            DeviceAgent agent = (assignment.getDeviceAgentId() != null
                    ? deviceAgentMapper.findByIdForUpdate(assignment.getDeviceAgentId()).or(() -> deviceAgentMapper.findById(assignment.getDeviceAgentId()))
                    : deviceAgentMapper.findByAgentCodeForUpdate(agentCode).or(() -> deviceAgentMapper.findByAgentCode(agentCode)))
                    .orElseThrow(() -> new BusinessException(ErrorCode.DEVICE_AGENT_NOT_FOUND));

            if (assignment.getDeviceAgentId() == null || !assignment.getDeviceAgentId().equals(agent.getId())
                    || !agent.getAgentCode().equals(agentCode)) {
                throw new BusinessException(ErrorCode.STEP_STATUS_NOT_ALLOWED, "响应代理与当前步骤分配不匹配");
            }

            if ("BUSY".equals(agent.getWorkStatus()) || (agent.getCurrentTaskId() != null && !agent.getCurrentTaskId().equals(assignment.getTaskId()))) {
                handleAssignmentConflict(assignment, agentCode, agent.getCurrentTaskId());
                return;
            }

            // DEF-S3-100: 数据库原子比较更新抢占代理所有权
            int claimed = deviceAgentMapper.claimAgent(agent.getId(), assignment.getTaskId(), assignment.getStepSeq());
            if (claimed == 0) {
                // 重新查证代理当前最新占用状态
                Optional<DeviceAgent> recheck = deviceAgentMapper.findById(agent.getId());
                if (recheck.isPresent() && ("BUSY".equals(recheck.get().getWorkStatus())
                        || (recheck.get().getCurrentTaskId() != null && !recheck.get().getCurrentTaskId().equals(assignment.getTaskId())))) {
                    handleAssignmentConflict(assignment, agentCode, recheck.get().getCurrentTaskId());
                    return;
                }
            }

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
            DeviceAgent agent = deviceAgentMapper.findByAgentCode(agentCode)
                    .orElseThrow(() -> new BusinessException(ErrorCode.DEVICE_AGENT_NOT_FOUND));
            if (assignment.getDeviceAgentId() == null || !assignment.getDeviceAgentId().equals(agent.getId())) {
                throw new BusinessException(ErrorCode.STEP_STATUS_NOT_ALLOWED, "响应代理与当前步骤分配不匹配");
            }

            List<String> rejected = parseRejectedIds(assignment.getRejectedAgentIds());
            rejected.add(agentCode);
            assignment.setRejectedAgentIds(toJson(rejected));
            assignment.setDeviceAgentId(null);
            assignment.setCommandId(null);
            assignment.setExecuteCommandId(null);
            assignment.setUpdatedAt(LocalDateTime.now());
            assignmentMapper.update(assignment);

            taskEventService.append(assignment.getTaskId(), "AGENT_REJECTED", "SYSTEM", null,
                    "设备代理" + agentCode + "拒绝步骤" + assignment.getStepSeq() + "承接请求，原因: " + rejectReason);

            assignStep(assignment.getTaskId(), assignment.getPlanVersionId(), assignment.getStepSeq());
        }
    }

    private void handleAssignmentConflict(TaskStepAssignment assignment, String agentCode, Long occupiedTaskId) {
        String detail = occupiedTaskId != null
                ? "设备代理" + agentCode + "已被任务" + occupiedTaskId + "占用，拒绝该冲突承接响应，顺位切换候选设备"
                : "设备代理" + agentCode + "已被并发任务占用，拒绝该冲突承接响应，顺位切换候选设备";
        taskEventService.append(assignment.getTaskId(), "AGENT_ASSIGNMENT_CONFLICTED", "SYSTEM", "ERR_AGENT_ALREADY_BUSY", detail);

        List<String> rejected = parseRejectedIds(assignment.getRejectedAgentIds());
        if (!rejected.contains(agentCode)) {
            rejected.add(agentCode);
        }
        assignment.setRejectedAgentIds(toJson(rejected));
        assignment.setDeviceAgentId(null);
        assignment.setCommandId(null);
        assignment.setExecuteCommandId(null);
        assignment.setUpdatedAt(LocalDateTime.now());
        assignmentMapper.update(assignment);

        assignStep(assignment.getTaskId(), assignment.getPlanVersionId(), assignment.getStepSeq());
    }

    /** A measurement event supplies the sample. It has no dispatch or device acknowledgement. */
    private boolean reuseMeasurementEvent(Task task, TaskStepAssignment assignment, Map<String, Object> step) {
        Map<String, Object> scene = fromJsonMap(task.getSceneParams());
        if (!"MEASUREMENT_EVENT".equals(scene.get("triggerSource"))) return false;
        var events = taskEventService.listByTask(task.getId());
        var receipt = events.stream()
                .filter(e -> "GOAL_SUBMITTED".equals(e.getEventType()) && "SYSTEM".equals(e.getTrigger())
                        && "MEASUREMENT_EVENT".equals(e.getReasonCode())).findFirst();
        if (receipt.isEmpty()) return false;
        // Older events retained their numeric sample in the task scene only.
        var source = events.stream().filter(e -> "MEASUREMENT_RECORDED".equals(e.getEventType())
                && "SYSTEM".equals(e.getTrigger()) && "MEASUREMENT_EVENT".equals(e.getReasonCode())).findFirst();
        Map<String, Object> sample = source.map(e -> fromJsonMap(e.getDetailSummary())).orElse(scene);
        Map<String, Object> measurement = new LinkedHashMap<>();
        for (String key : List.of("length", "width", "height", "weight", "isOversize", "totalDimensionCm",
                "dimensionThresholdCm", "weightThresholdKg", "thresholdSource", "baggageId")) {
            measurement.put(key, sample.get(key));
        }
        measurement.put("measureStatus", "SUCCESS");
        measurement.put("measurementSource", "MEASUREMENT_EVENT");
        measurement.put("baggageInfo", toJson(measurement));
        if (!Boolean.TRUE.equals(measurement.get("isOversize"))
                || List.of("length", "width", "height", "weight").stream().anyMatch(k -> !(measurement.get(k) instanceof Number))
                || !CompletionConditionEvaluator.satisfied(step, measurement)) {
            task.setStatus(TaskStatus.PENDING_MANUAL);
            task.setFailureReason("已登记的超规测量结果不满足当前步骤条件，请核对原始事件");
            task.setUpdatedAt(LocalDateTime.now());
            taskMapper.update(task);
            taskEventService.append(task.getId(), "TASK_PENDING_MANUAL", "SYSTEM", "ERR_MEASUREMENT_EVENT_INVALID", task.getFailureReason());
            return true;
        }
        if (assignmentMapper.completeFromMeasurementEvent(assignment.getId(), toJson(measurement),
                source.orElse(receipt.get()).getOccurredAt()) == 1) {
            taskEventService.append(task.getId(), "STEP_COMPLETED", "SYSTEM", "MEASUREMENT_EVENT_REUSED",
                    "步骤" + assignment.getStepSeq() + "使用已登记的测量结果，来源事件 " + source.orElse(receipt.get()).getId());
            advanceAfterStepCompleted(task.getId(), assignment.getPlanVersionId(), assignment.getStepSeq());
        }
        return true;
    }

    /**
     * 对应5.5.2基本路径1~2、业务规则3/5：生成全局唯一指令编号，指令下发前对拼装后的
     * inputParams再次做运动安全控制字段拦截（异常路径2a）——5.4.4三类校验只检查计划模板本身，
     * 分配阶段可能对inputParams做二次拼装，故须在真正下发动作发生前再拦截一次。
     */
    private void dispatchCommand(TaskStepAssignment assignment) {
        // 终态硬拦截（SRS_F021.R07）：任务处于 MANUAL_TERMINATED 或步骤已被冻结时，严禁下发新指令
        Task task = taskMapper.findById(assignment.getTaskId()).orElse(null);
        if (task != null && task.getStatus() == TaskStatus.MANUAL_TERMINATED) {
            return;
        }
        if ("FROZEN".equals(assignment.getStepStatus())) {
            return;
        }

        Map<String, Object> step = findStep(assignment.getPlanVersionId(), assignment.getStepSeq());
        Map<String, Object> resolvedParams = parameterResolver.resolve(assignment.getTaskId(), assignment.getPlanVersionId(), step);
        List<String> motionSafetyHits = MotionSafetyGuard.detect(step);
        if (motionSafetyHits.isEmpty() && resolvedParams != null) {
            motionSafetyHits = MotionSafetyGuard.detect(Map.of("inputParams", resolvedParams));
        }
        if (!motionSafetyHits.isEmpty()) {
            String blockDetail = "步骤" + assignment.getStepSeq() + "指令内容检出运动安全控制字段: " + motionSafetyHits + "，已拦截下发";
            taskEventService.append(assignment.getTaskId(), "COMMAND_DISPATCH_BLOCKED", "SYSTEM",
                    "ERR_MOTION_SAFETY_FIELD", blockDetail);
            if (deviceEventService != null && assignment.getDeviceAgentId() != null) {
                deviceEventService.appendBlockedMessage(assignment.getDeviceAgentId(), "COMMAND_DISPATCH_BLOCKED",
                        assignment.getExecuteCommandId() != null ? assignment.getExecuteCommandId() : assignment.getCommandId(),
                        "ERR_MOTION_SAFETY_FIELD", blockDetail);
            }
            releaseAgent(assignment.getDeviceAgentId(), assignment.getTaskId());
            markStepFailed(assignment, "ERR_MOTION_SAFETY_FIELD", "指令内容检出运动安全控制字段，已拦截");
            return;
        }

        if (assignment.getExecuteCommandId() == null) assignment.setExecuteCommandId(generateCommandId());
        assignment.setStepStatus("EXECUTING");
        assignment.setDispatchedAt(LocalDateTime.now());
        assignment.setUpdatedAt(LocalDateTime.now());
        assignmentMapper.update(assignment);

        DeviceAgent agent = deviceAgentMapper.findById(assignment.getDeviceAgentId()).orElseThrow();
        taskEventService.append(assignment.getTaskId(), "STEP_DISPATCHED", "SYSTEM", null,
                "指令" + assignment.getExecuteCommandId() + "已下发至设备代理" + agent.getAgentCode()
                        + "，业务意图: " + step.get("stepGoal"));

        try {
            deviceAgentMessagingService.executeCapability(agent.getAgentCode(), assignment.getExecuteCommandId(),
                    assignment.getTaskId(), assignment.getStepSeq(), String.valueOf(step.get("capabilityType")),
                    assignment.getRetryCount(), resolvedParams);
        } catch (RuntimeException ex) {
            onExecutionFeedback(agent.getAgentCode(), assignment.getExecuteCommandId(), assignment.getRetryCount(),
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
        TaskStepAssignment assignment = assignmentMapper.findByExecuteCommandId(commandId)
                .or(() -> assignmentMapper.findByCommandId(commandId).filter(a -> a.getExecuteCommandId() == null))
                .orElseThrow(() -> new BusinessException(ErrorCode.STEP_ASSIGNMENT_NOT_FOUND));
        DeviceAgent reportingAgent = deviceAgentMapper.findByAgentCode(agentCode)
                .orElseThrow(() -> new BusinessException(ErrorCode.DEVICE_AGENT_NOT_FOUND));
        if (assignment.getDeviceAgentId() == null || !assignment.getDeviceAgentId().equals(reportingAgent.getId())) {
            throw new BusinessException(ErrorCode.STEP_STATUS_NOT_ALLOWED, "反馈代理与当前步骤分配不匹配");
        }
        if (attemptNo != assignment.getRetryCount()) {
            taskEventService.append(assignment.getTaskId(), "STALE_EXECUTION_FEEDBACK_IGNORED", "SYSTEM",
                    "STALE_ATTEMPT", "忽略指令" + commandId + "第" + attemptNo + "次尝试的迟到反馈");
            return;
        }
        if (!"EXECUTING".equals(assignment.getStepStatus())) {
            if ("COMPLETED".equals(assignment.getStepStatus()) || "FAILED".equals(assignment.getStepStatus())) return;
            if ("FROZEN".equals(assignment.getStepStatus())) {
                taskEventService.append(assignment.getTaskId(), "LATE_EXECUTION_FEEDBACK_IGNORED", "SYSTEM",
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
                && CompletionConditionEvaluator.satisfied(step, outputParams);

        // DEF-S3-125: 行李测量步骤必须包含长宽高尺寸、重量、超规结果三项必要数据，缺项不得完成
        if (completionSatisfied && "CAP_BAGGAGE_MEASURE".equals(step.get("capabilityType"))) {
            boolean hasDimensions = outputParams != null
                    && outputParams.get("length") instanceof Number
                    && outputParams.get("width") instanceof Number
                    && outputParams.get("height") instanceof Number;
            boolean hasWeight = outputParams != null && outputParams.get("weight") instanceof Number;
            boolean hasOversize = outputParams != null && outputParams.get("isOversize") != null;
            if (!hasDimensions || !hasWeight || !hasOversize) {
                completionSatisfied = false;
                reasonCode = "ERR_MEASUREMENT_DATA_INCOMPLETE";
            }
        }

        if (completionSatisfied) {
            assignment.setStepStatus("COMPLETED");
            assignmentMapper.update(assignment);
            releaseAgent(assignment.getDeviceAgentId(), assignment.getTaskId());
            taskEventService.append(assignment.getTaskId(), "STEP_COMPLETED", "SYSTEM", null,
                    "步骤" + assignment.getStepSeq() + "完成条件已满足: " + step.get("completionCondition"));
            taskExceptionService.onStepRecovered(assignment.getTaskId(), assignment.getStepSeq());
            Task currentTask = taskMapper.findById(assignment.getTaskId()).orElseThrow();
            if ("OVERSIZE_BAGGAGE_HANDLING".equals(currentTask.getTaskFamily())
                    && "CAP_BAGGAGE_MEASURE".equals(step.get("capabilityType"))) {
                Map<String, Object> scene = fromJsonMap(currentTask.getSceneParams());
                outputParams.putIfAbsent("dimensionThresholdCm", scene.getOrDefault("dimensionThresholdCm", 158.0));
                outputParams.putIfAbsent("weightThresholdKg", scene.getOrDefault("weightThresholdKg", 32.0));
                outputParams.putIfAbsent("thresholdSource", scene.getOrDefault("thresholdSource", "附录F-五类设备能力边界清单 2.2 智能行李测量设备能力约束"));
                if (outputParams.get("totalDimensionCm") == null && outputParams.get("length") != null && outputParams.get("width") != null && outputParams.get("height") != null) {
                    try {
                        double l = ((Number) outputParams.get("length")).doubleValue();
                        double w = ((Number) outputParams.get("width")).doubleValue();
                        double h = ((Number) outputParams.get("height")).doubleValue();
                        outputParams.put("totalDimensionCm", l + w + h);
                    } catch (Exception ignored) {}
                }
                assignment.setOutputParams(toJson(outputParams));
                assignmentMapper.update(assignment);
            }
            if (!Boolean.TRUE.equals(currentTask.getIsDryRun())
                    && "OVERSIZE_BAGGAGE_HANDLING".equals(currentTask.getTaskFamily())
                    && "CAP_BAGGAGE_MEASURE".equals(step.get("capabilityType"))
                    && Boolean.FALSE.equals(outputParams.get("isOversize"))) {
                completeNormalBaggageBranch(currentTask, assignment.getPlanVersionId(), assignment.getStepSeq(), outputParams);
                return;
            }
            advanceAfterStepCompleted(assignment.getTaskId(), assignment.getPlanVersionId(), assignment.getStepSeq());
            return;
        }

        // 异常路径4a：设备返回SUCCESS但完成条件未满足，按步骤失败处理，不视为完成
        String failureDetail = "SUCCESS".equals(executionResult) && !completionSatisfied
                ? ("ERR_MEASUREMENT_DATA_INCOMPLETE".equals(reasonCode)
                        ? "测量反馈缺少尺寸、重量或超规结果必要数据"
                        : "设备返回执行成功，但完成条件未满足")
                : "执行结果: " + executionResult + "，原因: " + reasonCode;

        if (Boolean.TRUE.equals(taskMapper.findById(assignment.getTaskId()).orElseThrow().getIsDryRun())) {
            assignment.setStepStatus("FAILED"); assignmentMapper.update(assignment);
            releaseAgent(assignment.getDeviceAgentId(), assignment.getTaskId());
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
                    "步骤" + assignment.getStepSeq() + "自动重试1次，沿用执行指令编号" + commandId + "，尝试序号" + assignment.getRetryCount() + "，原因: " + failureDetail);
            taskExceptionService.onStepFirstFailure(assignment.getTaskId(), assignment.getStepSeq(),
                    "TIMEOUT".equalsIgnoreCase(executionResult) || "ERR_EXECUTION_TIMEOUT".equals(reasonCode) || (reasonCode != null && reasonCode.contains("TIMEOUT")) ? "EXECUTION_TIMEOUT" : "STEP_FAILED",
                    reasonCode, failureDetail);

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
        releaseAgent(assignment.getDeviceAgentId(), assignment.getTaskId());
        boolean isTimeout = "TIMEOUT".equalsIgnoreCase(executionResult)
                || "ERR_EXECUTION_TIMEOUT".equals(reasonCode)
                || (reasonCode != null && reasonCode.contains("TIMEOUT"));
        String exceptionType = isTimeout ? "EXECUTION_TIMEOUT" : "STEP_FAILED";
        String eventType = isTimeout ? "STEP_TIMEOUT_DETECTED" : "STEP_FAILED";
        taskEventService.append(assignment.getTaskId(), eventType, "SYSTEM", reasonCode,
                "步骤" + assignment.getStepSeq() + "重试后仍失败: " + failureDetail);
        taskExceptionService.handleException(assignment.getTaskId(), assignment.getStepSeq(), exceptionType, failureDetail);
    }

    private void completeNormalBaggageBranch(Task task, Long planVersionId, Integer measuredStepSeq,
                                             Map<String, Object> outputParams) {
        Map<String, Object> scene = fromJsonMap(task.getSceneParams());
        outputParams.putIfAbsent("dimensionThresholdCm", scene.getOrDefault("dimensionThresholdCm", 158.0));
        outputParams.putIfAbsent("weightThresholdKg", scene.getOrDefault("weightThresholdKg", 32.0));
        outputParams.putIfAbsent("thresholdSource", scene.getOrDefault("thresholdSource", "附录F-五类设备能力边界清单 2.2 智能行李测量设备能力约束"));
        if (outputParams.get("totalDimensionCm") == null && outputParams.get("length") != null && outputParams.get("width") != null && outputParams.get("height") != null) {
            try {
                double l = ((Number) outputParams.get("length")).doubleValue();
                double w = ((Number) outputParams.get("width")).doubleValue();
                double h = ((Number) outputParams.get("height")).doubleValue();
                outputParams.put("totalDimensionCm", l + w + h);
            } catch (Exception ignored) {}
        }
        for (TaskStepAssignment later : assignmentMapper.findByPlanVersionIdOrderByStepSeqAsc(planVersionId)) {
            if (later.getStepSeq().equals(measuredStepSeq)) {
                later.setOutputParams(toJson(outputParams));
                assignmentMapper.update(later);
            }
        }
        // DEF-S3-119: 非超规分支删除后续未执行引导步骤，严格遵守R03“不生成引导步骤”
        assignmentMapper.deleteByPlanVersionIdAndStepSeqGreaterThan(planVersionId, measuredStepSeq);
        planVersionMapper.findById(planVersionId).ifPresent(pv -> {
            try {
                List<Map<String, Object>> steps = parseSteps(pv.getPlanSteps());
                List<Map<String, Object>> remainingSteps = steps.stream()
                        .filter(s -> {
                            Integer seq = asInteger(s.get("stepSeq"));
                            return seq != null && seq <= measuredStepSeq;
                        })
                        .toList();
                String newPlanStepsJson = toJson(remainingSteps);
                pv.setPlanSteps(newPlanStepsJson);
                planVersionMapper.update(pv);
                planVersionMapper.updatePlanSteps(planVersionId, newPlanStepsJson);
            } catch (Exception ignored) {}
        });
        task.setStatus(TaskStatus.COMPLETED);
        task.setUpdatedAt(LocalDateTime.now());
        taskMapper.update(task);
        taskExceptionService.archiveAllUnresolvedOnTaskComplete(task.getId());
        taskEventService.append(task.getId(), "TASK_COMPLETED", "SYSTEM", "BAGGAGE_WITHIN_LIMIT",
                "行李未超规，结束处置；三边和" + outputParams.get("totalDimensionCm") + "cm（阈值"
                        + outputParams.get("dimensionThresholdCm") + "cm），重量" + outputParams.get("weight")
                        + "kg（阈值" + outputParams.get("weightThresholdKg") + "kg）；来源："
                        + outputParams.get("thresholdSource"));
    }

    /** 对应5.5.2业务规则8/9：全部步骤完成条件满足后置任务完成，否则按顺序取下一步骤分配设备 */
    public void advanceAfterStepCompleted(Long taskId, Long planVersionId, Integer completedStepSeq) {
        List<TaskStepAssignment> all = assignmentMapper.findByPlanVersionIdOrderByStepSeqAsc(planVersionId);
        Optional<TaskStepAssignment> next = all.stream()
                .filter(a -> a.getStepSeq() > completedStepSeq)
                .min(Comparator.comparing(TaskStepAssignment::getStepSeq));

        if (next.isPresent()) {
            TaskStepAssignment nextAssignment = next.get();
            if ("FROZEN".equals(nextAssignment.getStepStatus())) {
                nextAssignment.setStepStatus("PENDING_ASSIGNMENT");
                nextAssignment.setUpdatedAt(LocalDateTime.now());
                assignmentMapper.update(nextAssignment);
            }
            assignStep(taskId, planVersionId, nextAssignment.getStepSeq());
            return;
        }

        completeAvailableChannels(taskId, planVersionId, all);
    }

    /** 5.6.5备选路径5a：只跳过确实无在线空闲候选的航班渠道，不把拒绝或执行失败当作覆盖成功。 */
    private void skipUnavailableFlightChannel(Task task, TaskStepAssignment assignment, String capabilityType) {
        String channel = CoreScenarioChannelPolicy.requiredType(task.getTaskFamily(), capabilityType);
        assignment.setStepStatus("SKIPPED");
        assignment.setReasonCode("FLIGHT_CHANNEL_UNAVAILABLE");
        assignment.setOutputParams(toJson(Map.of("channelResult", "UNCOVERED", "capabilityType", capabilityType,
                "requiredDeviceType", channel, "reason", "NO_ONLINE_IDLE_CANDIDATE")));
        assignment.setUpdatedAt(LocalDateTime.now());
        assignmentMapper.update(assignment);
        taskEventService.append(task.getId(), "FLIGHT_CHANNEL_UNCOVERED", "SYSTEM", "FLIGHT_CHANNEL_UNAVAILABLE",
                "步骤" + assignment.getStepSeq() + "所需" + channel + "渠道无在线空闲候选，未下发设备命令");

        List<TaskStepAssignment> all = assignmentMapper.findByPlanVersionIdOrderByStepSeqAsc(assignment.getPlanVersionId());
        Optional<TaskStepAssignment> next = all.stream()
                .filter(a -> a.getStepSeq() > assignment.getStepSeq() && "PENDING_ASSIGNMENT".equals(a.getStepStatus()))
                .min(Comparator.comparing(TaskStepAssignment::getStepSeq));
        if (next.isPresent()) assignStep(task.getId(), assignment.getPlanVersionId(), next.get().getStepSeq());
        else completeAvailableChannels(task.getId(), assignment.getPlanVersionId(), all);
    }

    /** SRS §5.6.3 / DEF-S3-124: 超规行李无移动机器人时跳过导航步骤，降级为仅信息提示与测量。 */
    private void skipUnavailableNavigationChannel(Task task, TaskStepAssignment assignment, String capabilityType) {
        String channel = CoreScenarioChannelPolicy.requiredType(task.getTaskFamily(), capabilityType);
        assignment.setStepStatus("SKIPPED");
        assignment.setReasonCode("NAVIGATION_CHANNEL_UNAVAILABLE");
        assignment.setOutputParams(toJson(Map.of(
                "channelResult", "UNCOVERED",
                "capabilityType", capabilityType,
                "requiredDeviceType", channel != null ? channel : "MOBILE_ROBOT",
                "guidanceStatus", "UNCOMPLETED",
                "reason", "NO_ONLINE_IDLE_CANDIDATE")));
        assignment.setUpdatedAt(LocalDateTime.now());
        assignmentMapper.update(assignment);
        taskEventService.append(task.getId(), "GUIDANCE_UNCOVERED", "SYSTEM", "NAVIGATION_CHANNEL_UNAVAILABLE",
                "步骤" + assignment.getStepSeq() + "所需" + channel + "移动机器人无在线候选，未完成现场引导，降级保留信息提示与测量");

        List<TaskStepAssignment> all = assignmentMapper.findByPlanVersionIdOrderByStepSeqAsc(assignment.getPlanVersionId());
        Optional<TaskStepAssignment> next = all.stream()
                .filter(a -> a.getStepSeq() > assignment.getStepSeq() && "PENDING_ASSIGNMENT".equals(a.getStepStatus()))
                .min(Comparator.comparing(TaskStepAssignment::getStepSeq));
        if (next.isPresent()) assignStep(task.getId(), assignment.getPlanVersionId(), next.get().getStepSeq());
        else completeAvailableChannels(task.getId(), assignment.getPlanVersionId(), all);
    }

    /** SRS §5.6.4 / SRS_F025.R04: 特殊旅客服务在无移动机器人时跳过现场通知与陪同步骤，降级为仅信息提示并转人工协助。 */
    private void skipUnavailableSpecialPassengerChannel(Task task, TaskStepAssignment assignment, String capabilityType) {
        String channel = CoreScenarioChannelPolicy.requiredType(task.getTaskFamily(), capabilityType);
        assignment.setStepStatus("SKIPPED");
        assignment.setReasonCode("ESCORT_CHANNEL_UNAVAILABLE");
        assignment.setOutputParams(toJson(Map.of(
                "channelResult", "UNCOVERED",
                "capabilityType", capabilityType,
                "requiredDeviceType", channel != null ? channel : "MOBILE_ROBOT",
                "escortStatus", "UNCOMPLETED",
                "reason", "NO_ONLINE_IDLE_CANDIDATE")));
        assignment.setUpdatedAt(LocalDateTime.now());
        assignmentMapper.update(assignment);
        taskEventService.append(task.getId(), "ESCORT_UNCOVERED", "SYSTEM", "ESCORT_CHANNEL_UNAVAILABLE",
                "步骤" + assignment.getStepSeq() + "所需" + channel + "移动机器人无在线候选，未完成现场陪同/通知，降级保留信息提示并转人工协助");

        List<TaskStepAssignment> all = assignmentMapper.findByPlanVersionIdOrderByStepSeqAsc(assignment.getPlanVersionId());
        Optional<TaskStepAssignment> next = all.stream()
                .filter(a -> a.getStepSeq() > assignment.getStepSeq() && "PENDING_ASSIGNMENT".equals(a.getStepStatus()))
                .min(Comparator.comparing(TaskStepAssignment::getStepSeq));
        if (next.isPresent()) assignStep(task.getId(), assignment.getPlanVersionId(), next.get().getStepSeq());
        else completeAvailableChannels(task.getId(), assignment.getPlanVersionId(), all);
    }

    private void completeAvailableChannels(Long taskId, Long planVersionId, List<TaskStepAssignment> all) {
        Task task = taskMapper.findById(taskId).orElseThrow();
        if ("FLIGHT_CHANGE_RESPONSE".equals(task.getTaskFamily()) && !Boolean.TRUE.equals(task.getIsDryRun())) {
            List<Map<String, Object>> steps = parseSteps(planVersionMapper.findById(planVersionId).orElseThrow().getPlanSteps());
            Map<Integer, String> capabilities = steps.stream().collect(Collectors.toMap(
                    step -> asInteger(step.get("stepSeq")), step -> String.valueOf(step.get("capabilityType"))));
            List<String> covered = all.stream().filter(a -> "COMPLETED".equals(a.getStepStatus()))
                    .map(a -> capabilities.get(a.getStepSeq())).toList();
            List<String> uncovered = all.stream().filter(a -> "FLIGHT_CHANNEL_UNAVAILABLE".equals(a.getReasonCode()))
                    .map(a -> capabilities.get(a.getStepSeq())).toList();
            if (covered.stream().noneMatch(CoreScenarioChannelPolicy::isFlightPublication)) {
                task.setStatus(TaskStatus.PENDING_MANUAL);
                task.setFailureReason("无任何已完成的航班信息发布渠道；未覆盖渠道: " + uncovered);
                task.setUpdatedAt(LocalDateTime.now());
                taskMapper.update(task);
                taskEventService.append(taskId, "TASK_PENDING_MANUAL", "SYSTEM", "FLIGHT_PUBLICATION_UNAVAILABLE",
                        task.getFailureReason());
                return;
            }
            task.setStatus(TaskStatus.COMPLETED);
            task.setUpdatedAt(LocalDateTime.now());
            taskMapper.update(task);
            taskExceptionService.archiveAllUnresolvedOnTaskComplete(taskId);

            // 统计各渠道发布结果与响应时长（SRS_F026.R09 / TC-081.S3 / TC-082.S1）
            List<Map<String, Object>> channelMetrics = new ArrayList<>();
            for (TaskStepAssignment a : all) {
                String cap = capabilities.get(a.getStepSeq());
                long durationMs = 0L;
                if (a.getDispatchedAt() != null && a.getFeedbackAt() != null) {
                    durationMs = java.time.Duration.between(a.getDispatchedAt(), a.getFeedbackAt()).toMillis();
                } else if (a.getAcceptanceDurationMs() != null) {
                    durationMs = a.getAcceptanceDurationMs();
                }
                Map<String, Object> metric = new LinkedHashMap<>();
                metric.put("stepSeq", a.getStepSeq());
                metric.put("capabilityType", cap);
                metric.put("deviceAgentId", a.getDeviceAgentId());
                metric.put("stepStatus", a.getStepStatus());
                metric.put("executionResult", a.getExecutionResult());
                metric.put("durationMs", durationMs);
                channelMetrics.add(metric);
            }

            Map<String, Object> completedDetail = new LinkedHashMap<>();
            completedDetail.put("summary", "航班变更可用渠道执行完成；已覆盖: " + covered + "；未覆盖: " + uncovered);
            completedDetail.put("coveredChannels", covered);
            completedDetail.put("uncoveredChannels", uncovered);
            completedDetail.put("channelMetrics", channelMetrics);

            taskEventService.append(taskId, "TASK_COMPLETED", "SYSTEM", "FLIGHT_CHANGE_RESPONSE_COMPLETED",
                    toJson(completedDetail));
            return;
        }

        if ("OVERSIZE_BAGGAGE_HANDLING".equals(task.getTaskFamily()) && !Boolean.TRUE.equals(task.getIsDryRun())) {
            boolean guidanceUncovered = all.stream().anyMatch(a -> "NAVIGATION_CHANNEL_UNAVAILABLE".equals(a.getReasonCode()));
            task.setStatus(TaskStatus.COMPLETED);
            task.setUpdatedAt(LocalDateTime.now());
            taskMapper.update(task);
            taskExceptionService.archiveAllUnresolvedOnTaskComplete(taskId);

            Map<String, Object> scene = fromJsonMap(task.getSceneParams());
            String baggageId = String.valueOf(scene.getOrDefault("baggageId", "临时业务编号"));
            String targetLoc = String.valueOf(scene.getOrDefault("targetCounter", scene.getOrDefault("targetLocation", "CHECKIN_WEST")));
            if (guidanceUncovered) {
                String detail = "超规行李信息提示与测量完成（临时业务编号: " + baggageId + "）：已完成行李测量、超规告警上报、航显办理说明发布；移动机器人未完成引导（无可用移动机器人候选）";
                taskEventService.append(taskId, "TASK_COMPLETED", "SYSTEM", "OVERSIZE_HANDLING_INFO_ONLY", detail);
            } else {
                String detail = "超规行李处置闭环完成（临时业务编号: " + baggageId + "）：已完成行李测量、超规告警上报、航显办理说明发布，以及移动机器人至" + targetLoc + "的空间引导；全部步骤均已执行完成。";
                taskEventService.append(taskId, "TASK_COMPLETED", "SYSTEM", "OVERSIZE_HANDLING_CLOSED_LOOP", detail);
            }
            return;
        }

        if ("SPECIAL_PASSENGER_SERVICE".equals(task.getTaskFamily()) && !Boolean.TRUE.equals(task.getIsDryRun())) {
            boolean escortUncovered = all.stream().anyMatch(a -> "ESCORT_CHANNEL_UNAVAILABLE".equals(a.getReasonCode()));
            taskExceptionService.archiveAllUnresolvedOnTaskComplete(taskId);

            Map<String, Object> scene = fromJsonMap(task.getSceneParams());
            String assistanceType = String.valueOf(scene.getOrDefault("assistanceType", "特殊协助"));
            String origin = String.valueOf(scene.getOrDefault("origin", scene.getOrDefault("startLocation", "服务起点")));
            String destination = String.valueOf(scene.getOrDefault("destination", scene.getOrDefault("targetLocation", "服务目的地")));

            if (escortUncovered) {
                // TC-078.S1 / SRS_F025.R04: 无可用移动服务设备时降级为信息提示并转人工协助，记录降级原因
                task.setStatus(TaskStatus.PENDING_MANUAL);
                task.setFailureReason("无可用移动服务设备（机器人离线或无候选），已完成航显会合信息提示发布，转人工协助接续");
                task.setDowngradeReason("无可用移动服务设备，降级为信息提示并转人工协助");
                task.setUpdatedAt(LocalDateTime.now());
                taskMapper.update(task);

                String detail = "特殊旅客服务（" + assistanceType + "，" + origin + "->" + destination
                        + "）：已发布智慧航显会合信息提示；移动服务设备无可用候选，已记录未完成陪同并转人工协助接续。";
                taskEventService.append(taskId, "TASK_PENDING_MANUAL", "SYSTEM", "MOBILE_ROBOT_UNAVAILABLE", detail);
            } else {
                // TC-077.S3 / SRS_F025.R09: 完成后记录服务处理结果与完整事件时间线
                task.setStatus(TaskStatus.COMPLETED);
                task.setUpdatedAt(LocalDateTime.now());
                taskMapper.update(task);

                String detail = "特殊旅客服务闭环完成（" + assistanceType + "，" + origin + "->" + destination
                        + "）：已完成智慧航显会合提示发布、移动机器人现场通知与全程陪同引导服务；全部步骤均已执行完成。";
                taskEventService.append(taskId, "TASK_COMPLETED", "SYSTEM", "SPECIAL_PASSENGER_SERVICE_COMPLETED", detail);
            }
            return;
        }

        task.setStatus(TaskStatus.COMPLETED);
        task.setUpdatedAt(LocalDateTime.now());
        taskMapper.update(task);
        taskExceptionService.archiveAllUnresolvedOnTaskComplete(taskId);
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

    public void releaseAgent(Long deviceAgentId) {
        releaseAgent(deviceAgentId, null);
    }

    public void releaseAgent(Long deviceAgentId, Long expectedTaskId) {
        if (deviceAgentId == null) return;
        deviceAgentMapper.findById(deviceAgentId).ifPresent(agent -> {
            if (expectedTaskId != null && agent.getCurrentTaskId() != null && !expectedTaskId.equals(agent.getCurrentTaskId())) {
                // DEF-S3-103: 代理当前归属于其他任务，严禁清空其他任务的占用与工作状态
                return;
            }
            if (expectedTaskId == null && agent.getCurrentTaskId() != null) {
                Task current = taskMapper.findById(agent.getCurrentTaskId()).orElse(null);
                if (current != null && current.getStatus() == TaskStatus.EXECUTING) {
                    // DEF-S3-103: 未指定expectedTaskId时，若代理正在为执行中任务工作，拒绝清空其占用
                    return;
                }
            }
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
                                                        List<String> excludeAgentCodes, String taskFamily,
                                                        Long planVersionId, Integer stepSeq) {
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

        // 同任务/同组绑定同一台移动服务机器人，并追踪前序移动机器人步骤到达的锚点位置（与 PlanValidationService 保持一致）
        Long preferredSameRobotAgentId = null;
        Map<String, Object> prevRobotPoi = null;
        if (planVersionId != null && stepSeq != null && stepSeq > 1) {
            PlanVersion pv = planVersionMapper.findById(planVersionId).orElse(null);
            if (pv != null) {
                List<Map<String, Object>> allSteps = parseSteps(pv.getPlanSteps());
                Object bindGroup = step.get("bindSameAgentGroup");
                boolean isCurrentRobotStep = "CAP_NAVIGATION".equals(capabilityType)
                        || "CAP_ESCORT".equals(capabilityType)
                        || ("CAP_NOTIFICATION".equals(capabilityType)
                                && "MOBILE_ROBOT".equals(CoreScenarioChannelPolicy.requiredType(taskFamily, capabilityType)));
                for (Map<String, Object> prev : allSteps) {
                    if (PlanStepRules.isConditionNode(prev)) continue;
                    Integer pSeq = asInteger(prev.get("stepSeq"));
                    if (pSeq == null || pSeq >= stepSeq) continue;
                    String pCap = String.valueOf(prev.get("capabilityType"));
                    String reqCh = CoreScenarioChannelPolicy.requiredType(taskFamily, pCap);
                    boolean prevIsRobot = ("CAP_NAVIGATION".equals(pCap) || "CAP_ESCORT".equals(pCap) || "CAP_NOTIFICATION".equals(pCap))
                            && (reqCh == null || "MOBILE_ROBOT".equals(reqCh));
                    if (!prevIsRobot) continue;
                    var prevAssign = assignmentMapper.findByPlanVersionIdAndStepSeq(planVersionId, pSeq).orElse(null);
                    if (prevAssign != null && "COMPLETED".equals(prevAssign.getStepStatus()) && prevAssign.getDeviceAgentId() != null) {
                        boolean sameGroup = bindGroup != null && bindGroup.equals(prev.get("bindSameAgentGroup"));
                        if (sameGroup || isCurrentRobotStep) {
                            preferredSameRobotAgentId = prevAssign.getDeviceAgentId();
                        }
                        if (("CAP_NAVIGATION".equals(pCap) || "CAP_ESCORT".equals(pCap)) && terminalMapMapper != null) {
                            Map<String, Object> movedTo = resolveTargetPoiForStep(prev, stepInputParams(prev), planVersionId, pSeq, taskFamily);
                            if (movedTo != null) prevRobotPoi = movedTo;
                        }
                    }
                }
            }
        }
        if (preferredSameRobotAgentId != null) {
            final Long boundAgentId = preferredSameRobotAgentId;
            List<DeviceAgent> boundOnly = onlineIdle.stream().filter(a -> boundAgentId.equals(a.getId())).toList();
            if (!boundOnly.isEmpty()) {
                onlineIdle = boundOnly;
            }
        }

        if ("SPECIAL_PASSENGER_SERVICE".equals(taskFamily) && "CAP_ESCORT".equals(capabilityType) && stepSeq > 1) {
            var previous = parseSteps(planVersionMapper.findById(planVersionId).orElseThrow().getPlanSteps()).stream()
                    .filter(s -> Objects.equals(asInteger(s.get("stepSeq")), stepSeq - 1)).findFirst().orElse(Map.of());
            if ("CAP_NAVIGATION".equals(previous.get("capabilityType"))
                    && ("arrivalStatus=ARRIVED".equals(previous.get("completionCondition"))
                    || "routeGenerated=true".equals(previous.get("completionCondition")))) {
                var meeting = assignmentMapper.findByPlanVersionIdAndStepSeq(planVersionId, stepSeq - 1);
                if (meeting.isEmpty() || !"COMPLETED".equals(meeting.get().getStepStatus())) return List.of();
                var feedback = fromJsonMap(meeting.get().getOutputParams());
                Long metBy = meeting.get().getDeviceAgentId();
                onlineIdle = onlineIdle.stream().filter(agent -> metBy != null ? metBy.equals(agent.getId())
                        : deviceById.get(agent.getDeviceId()) != null && deviceById.get(agent.getDeviceId()).getDeviceCode()
                                .equals(feedback.get("arrivalDeviceCode"))).toList();
            }
        }

        Map<String, Object> inputParams = stepInputParams(step);
        BigDecimal targetX = asBigDecimal(step.get("targetX"));
        if (targetX == null && inputParams != null) {
            targetX = asBigDecimal(inputParams.get("targetX"));
        }
        BigDecimal targetY = asBigDecimal(step.get("targetY"));
        if (targetY == null && inputParams != null) {
            targetY = asBigDecimal(inputParams.get("targetY"));
        }
        String targetIsolationZone = null;
        if ((targetX == null || targetY == null) && terminalMapMapper != null) {
            Map<String, Object> poi = resolveTargetPoiForStep(step, inputParams, planVersionId, stepSeq, taskFamily);
            if (poi != null) {
                if (poi.get("x") instanceof Number nx) targetX = BigDecimal.valueOf(nx.doubleValue());
                if (poi.get("y") instanceof Number ny) targetY = BigDecimal.valueOf(ny.doubleValue());
                targetIsolationZone = SpatialRuleConfig.resolveIsolationZone(poi);
            }
        } else if (targetY != null) {
            double py = targetY.doubleValue();
            targetIsolationZone = py < SpatialRuleConfig.HOLDING_ZONE_MAX_Y ? "隔离区内"
                    : (py > SpatialRuleConfig.CHECKIN_HALL_MIN_Y ? "隔离区外" : null);
        }

        boolean enforceSpatialRules = terminalMapMapper != null && targetX != null && targetY != null && targetY.doubleValue() <= 600.0;
        boolean globalFlightBroadcast = "FLIGHT_CHANGE_RESPONSE".equals(taskFamily)
                && CoreScenarioChannelPolicy.isFlightPublication(capabilityType)
                && !hasExplicitPassengerOrigin(planVersionId);
        boolean strictZone = strictZoneEnabled();
        double fixedLimit = fixedMaxDist();
        double robotLimit = robotMaxDist();

        List<CandidateScore> scored = new ArrayList<>();
        for (DeviceAgent agent : onlineIdle) {
            Device device = deviceById.get(agent.getDeviceId());
            if (device == null || !"ACTIVE".equals(device.getDeviceStatus())
                    || !CoreScenarioChannelPolicy.matches(taskFamily, capabilityType, device)) continue;
            boolean hasCapability = deviceHasCapability(device.getId(), capabilityType);
            if (!hasCapability) continue;

            String actualDeviceType = "SIMULATOR".equals(device.getDeviceTypeCode())
                    ? device.getSimulatedDeviceType() : device.getDeviceTypeCode();
            boolean isMobileRobot = "MOBILE_ROBOT".equals(actualDeviceType);

            double rawDistance = 0.0;
            if (targetX != null && targetY != null) {
                if (isMobileRobot && preferredSameRobotAgentId != null && preferredSameRobotAgentId.equals(agent.getId())
                        && prevRobotPoi != null && prevRobotPoi.get("x") instanceof Number rx && prevRobotPoi.get("y") instanceof Number ry) {
                    rawDistance = Math.hypot(rx.doubleValue() - targetX.doubleValue(), ry.doubleValue() - targetY.doubleValue());
                } else if (device.getPositionX() != null && device.getPositionY() != null) {
                    rawDistance = Math.hypot(device.getPositionX().doubleValue() - targetX.doubleValue(),
                                             device.getPositionY().doubleValue() - targetY.doubleValue());
                }
            }

            if (enforceSpatialRules) {
                // 规则1：区域硬隔离——除移动服务机器人及无特定旅客起点的航班变更全局广播外，固定设备必须与目标同处一隔离区
                if (!isMobileRobot && strictZone && targetIsolationZone != null
                        && !globalFlightBroadcast && device.getAreaCode() != null
                        && ("隔离区内".equals(device.getAreaCode()) || "隔离区外".equals(device.getAreaCode()))
                        && !targetIsolationZone.equals(device.getAreaCode())) {
                    continue;
                }
                // 规则2：最大服务距离限制——统一读取 SpatialRuleConfig（固定设备默认650像素，移动服务机器人默认1600像素）
                double maxAllowedDistance = isMobileRobot ? robotLimit : fixedLimit;
                if (maxAllowedDistance > 0 && device.getPositionX() != null && device.getPositionY() != null
                        && rawDistance > maxAllowedDistance) {
                    continue;
                }
            }

            double matchScore = 1.0;
            if (agent.getBusinessStatus() != null) {
                try {
                    com.fasterxml.jackson.databind.JsonNode node = MAPPER.readTree(agent.getBusinessStatus());
                    if (node.has("capabilityMatch")) {
                        matchScore = node.get("capabilityMatch").asDouble();
                    } else if (node.has("matchDegree")) {
                        matchScore = node.get("matchDegree").asDouble();
                    }
                } catch (Exception ignored) {}
            }
            String preferredType = CoreScenarioChannelPolicy.requiredType(taskFamily, capabilityType);
            if (preferredType != null) {
                if (!preferredType.equals(actualDeviceType)) {
                    matchScore = Math.min(matchScore, 0.8);
                }
            }

            double distance = rawDistance;
            if (targetIsolationZone != null && device.getAreaCode() != null
                    && ("隔离区内".equals(device.getAreaCode()) || "隔离区外".equals(device.getAreaCode()))
                    && !targetIsolationZone.equals(device.getAreaCode())) {
                // 移动服务机器人允许跨隔离区，但同区域空闲机器人优先派单，跨隔离区附加绕行距离权重
                distance += 2000.0;
            }

            int workloadScore = "IDLE".equals(agent.getWorkStatus()) ? 0 : 1;
            if (agent.getBusinessStatus() != null) {
                try {
                    com.fasterxml.jackson.databind.JsonNode node = MAPPER.readTree(agent.getBusinessStatus());
                    if (node.has("workloadScore")) {
                        workloadScore = node.get("workloadScore").asInt();
                    } else if (node.has("workload")) {
                        workloadScore = node.get("workload").asInt();
                    }
                } catch (Exception ignored) {}
            }

            scored.add(new CandidateScore(agent, matchScore, distance, workloadScore));
        }
        scored.sort(Comparator.comparingDouble((CandidateScore c) -> -c.matchScore)
                .thenComparingDouble(c -> c.distance)
                .thenComparingInt(c -> c.workloadScore)
                .thenComparing(c -> c.agent.getAgentCode()));
        return scored;
    }

    private boolean deviceHasCapability(Long deviceId, String capabilityType) {
        return deviceCapabilityMapper.existsByDeviceIdAndCapabilityTypeAndCapabilityStatus(
                deviceId, capabilityType, "ENABLED");
    }

    private boolean hasExplicitPassengerOrigin(Long planVersionId) {
        if (planVersionId == null || planVersionMapper == null || taskMapper == null) return false;
        try {
            return planVersionMapper.findById(planVersionId)
                    .flatMap(pv -> pv.getTaskId() == null ? Optional.empty() : taskMapper.findById(pv.getTaskId()))
                    .map(t -> {
                        Map<String, Object> scene = fromJsonMap(t.getSceneParams());
                        for (String k : List.of("origin", "startLocation", "originLocation")) {
                            Object v = scene.get(k);
                            if (v != null && !String.valueOf(v).isBlank()) return true;
                        }
                        return false;
                    }).orElse(false);
        } catch (Exception ignored) {
            return false;
        }
    }

    private Map<String, Object> resolveTargetPoiForStep(Map<String, Object> step, Map<String, Object> inputParams,
                                                        Long planVersionId, Integer stepSeq, String taskFamily) {
        try {
            List<Map<String, Object>> pois = terminalMapMapper.findAllPois();
            if (pois == null || pois.isEmpty()) return null;
            Map<String, Map<String, Object>> index = new java.util.HashMap<>();
            for (Map<String, Object> p : pois) {
                if (p.get("poiCode") != null) index.put(String.valueOf(p.get("poiCode")).trim().toUpperCase(), p);
                if (p.get("poiName") != null) index.putIfAbsent(String.valueOf(p.get("poiName")).trim().toUpperCase(), p);
            }
            // 1. 当前步骤显式指定的地点参数优先
            if (inputParams != null) {
                for (String key : List.of("targetLocation", "targetCounter", "origin", "destination")) {
                    Map<String, Object> matched = lookupPoiText(inputParams.get(key), index);
                    if (matched != null) return matched;
                }
            }
            // 2. 追踪前序移动机器人陪同/引导后的旅客实时位置
            if (planVersionId != null) {
                Optional<PlanVersion> pvOpt = planVersionMapper.findById(planVersionId);
                if (pvOpt.isPresent()) {
                    PlanVersion pv = pvOpt.get();
                    Map<String, Object> scene = pv.getTaskId() == null ? Map.of()
                            : taskMapper.findById(pv.getTaskId()).map(t -> fromJsonMap(t.getSceneParams())).orElse(Map.of());
                    Map<String, Object> initialOrigin = null;
                    for (String k : List.of("origin", "startLocation", "originLocation", "baggageLocation")) {
                        initialOrigin = lookupPoiText(scene.get(k), index);
                        if (initialOrigin != null) break;
                    }
                    Map<String, Object> currentPassengerPoi = initialOrigin;
                    if (stepSeq != null && stepSeq > 1) {
                        for (Map<String, Object> prev : parseSteps(pv.getPlanSteps())) {
                            if (PlanStepRules.isConditionNode(prev)) continue;
                            Integer pSeq = asInteger(prev.get("stepSeq"));
                            if (pSeq == null || pSeq >= stepSeq) continue;
                            String pCap = String.valueOf(prev.get("capabilityType"));
                            String reqCh = CoreScenarioChannelPolicy.requiredType(taskFamily, pCap);
                            boolean robotMove = ("CAP_NAVIGATION".equals(pCap) || "CAP_ESCORT".equals(pCap))
                                    && (reqCh == null || "MOBILE_ROBOT".equals(reqCh));
                            if (!robotMove) continue;
                            Map<String, Object> pIn = stepInputParams(prev);
                            Map<String, Object> movedTo = lookupPoiText(pIn.get("targetLocation"), index);
                            if (movedTo == null) movedTo = lookupPoiText(pIn.get("destination"), index);
                            if (movedTo != null) {
                                boolean rendezvousOnly = "CAP_NAVIGATION".equals(pCap) && initialOrigin != null
                                        && Objects.equals(initialOrigin.get("poiCode"), movedTo.get("poiCode"));
                                if (!rendezvousOnly) {
                                    currentPassengerPoi = movedTo;
                                }
                            }
                        }
                    }
                    if (currentPassengerPoi != null) return currentPassengerPoi;
                    for (String k : List.of("targetLocation", "targetCounter")) {
                        Map<String, Object> fallback = lookupPoiText(scene.get(k), index);
                        if (fallback != null) return fallback;
                    }
                }
            }
        } catch (Exception ignored) {}
        return null;
    }

    private static Map<String, Object> lookupPoiText(Object raw, Map<String, Map<String, Object>> index) {
        if (raw == null) return null;
        String text = String.valueOf(raw).trim();
        if (text.isEmpty() || text.startsWith("TEMPLATE_INPUT.")) return null;
        String normalized = TerminalLocationNormalizer.normalize(text);
        if (normalized != null) {
            Map<String, Object> byNorm = index.get(normalized.toUpperCase());
            if (byNorm != null) return byNorm;
        }
        Map<String, Object> direct = index.get(text.toUpperCase());
        if (direct != null) return direct;
        int open = text.indexOf('('), close = text.indexOf(')', open + 1);
        if (open < 0) { open = text.indexOf('（'); close = text.indexOf('）', open + 1); }
        if (open >= 0 && close > open + 1) {
            return index.get(text.substring(open + 1, close).trim().toUpperCase());
        }
        return null;
    }

    private record CandidateScore(DeviceAgent agent, double matchScore, double distance, int workloadScore) {}

    private Map<String, Object> findStep(Long planVersionId, Integer stepSeq) {
        PlanVersion planVersion = planVersionMapper.findById(planVersionId).orElseThrow();
        return parseSteps(planVersion.getPlanSteps()).stream()
                .filter(s -> stepSeq.equals(asInteger(s.get("stepSeq"))))
                .findFirst().orElseThrow();
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
        return com.airport.ai.device.CommandIds.next();
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

    @SuppressWarnings("unchecked")
    private Map<String, Object> fromJsonMap(String json) {
        if (json == null || json.isBlank()) return new HashMap<>();
        try {
            return MAPPER.readValue(json, Map.class);
        } catch (Exception e) {
            return new HashMap<>();
        }
    }
}
