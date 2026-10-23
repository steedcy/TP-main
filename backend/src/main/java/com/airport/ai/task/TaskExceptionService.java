package com.airport.ai.task;

import com.airport.ai.device.DeviceAgent;
import com.airport.ai.device.DeviceAgentMapper;
import com.airport.ai.event.TaskEventService;
import com.fasterxml.jackson.databind.ObjectMapper;
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

    @org.springframework.beans.factory.annotation.Autowired
    private com.airport.ai.baseline.BaselineDryRunLifecycle dryRunLifecycle;
    private final TaskMapper taskMapper;
    private final TaskStepAssignmentMapper assignmentMapper;
    private final TaskExceptionMapper taskExceptionMapper;
    private final DeviceAgentMapper deviceAgentMapper;
    private final TaskEventService taskEventService;
    private final TaskExecutionOrchestrator taskExecutionOrchestrator;
    private final ReplanningService replanningService;

    public TaskExceptionService(TaskMapper taskMapper,
                                 TaskStepAssignmentMapper assignmentMapper,
                                 TaskExceptionMapper taskExceptionMapper,
                                 DeviceAgentMapper deviceAgentMapper,
                                 TaskEventService taskEventService,
                                 @Lazy TaskExecutionOrchestrator taskExecutionOrchestrator,
                                 @Lazy ReplanningService replanningService) {
        this.taskMapper = taskMapper;
        this.assignmentMapper = assignmentMapper;
        this.taskExceptionMapper = taskExceptionMapper;
        this.deviceAgentMapper = deviceAgentMapper;
        this.taskEventService = taskEventService;
        this.taskExecutionOrchestrator = taskExecutionOrchestrator;
        this.replanningService = replanningService;
    }

    /**
     * 步骤失败/执行超时的统一入口。对应基本路径：记录异常 -&gt; 冻结未执行步骤 -&gt;
     * 尝试候选设备切换（恢复动作） -&gt; 恢复成功则续跑，失败则判断计划是否可继续。
     */
    @Transactional
    public void handleException(Long taskId, Integer stepSeq, String exceptionType, String detail) {
        Task task = taskMapper.findById(taskId).orElseThrow();
        if (isTerminalOrManual(task.getStatus())) {
            return; // 任务已终止/待人工/终态，异常记录仍写但不再驱动流程
        }

        TaskException exception = new TaskException();
        exception.setTaskId(taskId);
        exception.setStepSeq(stepSeq);
        exception.setExceptionType(exceptionType);
        exception.setReasonCode(detail);
        taskExceptionMapper.insert(exception);
        taskEventService.append(taskId, "EXCEPTION_DETECTED", "SYSTEM", exceptionType,
                "识别到异常: " + exceptionType + "，步骤" + stepSeq + "，详情: " + detail);

        if (Boolean.TRUE.equals(task.getIsDryRun())) {
            dryRunLifecycle.finish(taskId, false, detail);
            return;
        }
        freezeRemainingSteps(task.getId(), stepSeq);

        // 业务规则4/6/7：先尝试一次候选设备切换作为恢复动作（能力缺口无候选可切换时恢复直接失败）
        String excludeAgentCode = findOfflineAgentCode(taskId, stepSeq);
        boolean canRetry = "CAPABILITY_GAP".equals(exceptionType)
                ? false // 无候选场景下"切换候选"本身即恢复动作已在assignStep中尝试过，不重复
                : taskExecutionOrchestrator.hasAvailableCandidate(task.getCurrentPlanVersionId(), stepSeq,
                        excludeAgentCode == null ? List.of() : List.of(excludeAgentCode));

        exception.setRecoveryAction(canRetry ? "候选设备切换" : "无可用候选设备，恢复动作未执行");

        if (canRetry) {
            taskExecutionOrchestrator.retryAssignmentExcluding(task.getId(), task.getCurrentPlanVersionId(),
                    stepSeq, excludeAgentCode);
            exception.setRecoveryResult("SUCCESS");
            exception.setImpactConclusion("已切换候选设备重新分配，计划可继续执行，不触发重新规划");
            exception.setExceptionStatus("RESOLVED");
            exception.setResolvedAt(LocalDateTime.now());
            exception.setResolvedBy("SYSTEM");
            taskExceptionMapper.update(exception);
            taskEventService.append(taskId, "EXCEPTION_RECOVERED", "SYSTEM", null,
                    "恢复动作: 候选设备切换，结果: 成功，步骤" + stepSeq + "已重新分配");
            return;
        }

        exception.setRecoveryResult("FAILED");
        taskExceptionMapper.update(exception);
        taskEventService.append(taskId, "EXCEPTION_RECOVERY_FAILED", "SYSTEM", exceptionType,
                "恢复动作: " + exception.getRecoveryAction() + "，结果: 失败，判断计划是否可继续");

        handleUnrecoverable(task, exception, stepSeq);
    }

    /**
     * 对应业务规则2/5：设备心跳超时离线时调用。仅当离线设备正占用当前任务的步骤才视为
     * "当前任务设备离线"并走完整恢复流程；占用其他任务或未占用任何任务的离线仅记录，不冻结不重规划。
     */
    @Transactional
    public void handleAgentOffline(DeviceAgent agent) {
        if (agent.getCurrentTaskId() == null) {
            return; // 无关设备离线，HeartbeatMonitorTask已记录设备事件，此处不再重复处理
        }
        handleException(agent.getCurrentTaskId(), agent.getCurrentStepSeq(), "AGENT_OFFLINE",
                "设备代理" + agent.getAgentCode() + "心跳超时离线，正占用该任务步骤");
    }

    /**
     * 对应异常路径4a/4b、5.5.3业务规则1a（降级任务基线执行失败不再二次自动降级）：
     * 恢复失败且判定计划不可继续，若重规划额度未用则触发5.5.4局部重新规划；
     * 额度已用或任务本身即为降级执行（DOWNGRADING）则直接转人工处理，不再自动降级。
     */
    private void handleUnrecoverable(Task task, TaskException exception, Integer stepSeq) {
        exception.setImpactConclusion("候选设备切换恢复失败，当前计划不可继续执行");
        exception.setExceptionStatus("PROCESSING");
        taskExceptionMapper.update(exception);

        boolean isDowngradedTask = task.getStatus() == TaskStatus.DOWNGRADING;
        if (Boolean.TRUE.equals(task.getReplanUsed()) || isDowngradedTask) {
            String reason = isDowngradedTask
                    ? "基线降级任务执行异常且恢复失败，按业务规则不再二次自动降级"
                    : "重新规划机会已用，恢复失败，转人工处理";
            markUnresolvable(task, exception, reason);
            return;
        }

        exception.setExceptionStatus("RESOLVED");
        exception.setResolvedAt(LocalDateTime.now());
        exception.setResolvedBy("SYSTEM");
        taskExceptionMapper.update(exception);
        taskEventService.append(task.getId(), "REPLANNING_TRIGGERED", "SYSTEM", null,
                "步骤" + stepSeq + "恢复失败且计划不可继续，重新规划机会未用，触发5.5.4局部重新规划");
        replanningService.replan(task.getId(), stepSeq, exception.getExceptionType() + ": " + exception.getReasonCode());
    }

    private void markUnresolvable(Task task, TaskException exception, String reason) {
        exception.setExceptionStatus("RESOLVED");
        exception.setResolvedAt(LocalDateTime.now());
        exception.setResolvedBy("SYSTEM");
        taskExceptionMapper.update(exception);

        task.setStatus(TaskStatus.PENDING_MANUAL);
        task.setFailureReason(reason);
        task.setUpdatedAt(LocalDateTime.now());
        taskMapper.update(task);
        taskEventService.append(task.getId(), "TASK_PENDING_MANUAL", "SYSTEM", exception.getExceptionType(), reason);
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
        return taskExceptionMapper.countByExceptionStatus("PENDING");
    }
}
