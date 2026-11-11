package com.airport.ai.task;

import com.airport.ai.device.DeviceCommandMapper;
import com.airport.ai.event.TaskEventService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.lang.Nullable;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;

/**
 * 对应5.5.2业务3异常路径3c：指令下发EXECUTING状态后，超过计划中
 * app.task.step-timeout-default-seconds（默认60秒）仍未收到执行反馈，判定为执行超时。
 * 与HeartbeatMonitorTask设备超时机制同理，采用定时扫描+阈值判断同一模式。
 */
@Component
public class StepTimeoutMonitorTask {

    private final TaskStepAssignmentMapper assignmentMapper;
    private final com.airport.ai.device.DeviceAgentMapper deviceAgentMapper;
    private final TaskEventService taskEventService;
    private final TaskExceptionService taskExceptionService;
    private final int stepTimeoutSeconds;
    private final PlanVersionMapper plans;
    private final DeviceCommandMapper deviceCommandMapper;

    public StepTimeoutMonitorTask(TaskStepAssignmentMapper assignmentMapper,
                                   com.airport.ai.device.DeviceAgentMapper deviceAgentMapper,
                                   TaskEventService taskEventService,
                                   TaskExceptionService taskExceptionService,
                                   int stepTimeoutSeconds) {
        this(assignmentMapper, deviceAgentMapper, taskEventService, taskExceptionService, stepTimeoutSeconds, null, null);
    }

    @Autowired
    public StepTimeoutMonitorTask(TaskStepAssignmentMapper assignmentMapper,
                                   com.airport.ai.device.DeviceAgentMapper deviceAgentMapper,
                                   TaskEventService taskEventService,
                                   TaskExceptionService taskExceptionService,
                                   @Value("${app.task.step-timeout-default-seconds:60}") int stepTimeoutSeconds,
                                   @Nullable PlanVersionMapper plans,
                                   @Nullable DeviceCommandMapper deviceCommandMapper) {
        this.assignmentMapper = assignmentMapper;
        this.deviceAgentMapper = deviceAgentMapper;
        this.taskEventService = taskEventService;
        this.taskExceptionService = taskExceptionService;
        this.stepTimeoutSeconds = stepTimeoutSeconds;
        this.plans = plans;
        this.deviceCommandMapper = deviceCommandMapper;
    }

    @Scheduled(fixedRate = 10000)
    @Transactional
    public void checkStepTimeout() {
        LocalDateTime threshold = LocalDateTime.now();
        List<TaskStepAssignment> timedOut = assignmentMapper.findByStepStatusAndDispatchedAtBefore("EXECUTING", threshold);
        for (TaskStepAssignment assignment : timedOut) {
            try {
                int timeout = stepTimeoutSeconds;
                if (plans != null && assignment.getPlanVersionId() != null) {
                    try {
                        var plan = plans.findById(assignment.getPlanVersionId()).orElseThrow();
                        java.util.List<java.util.Map<String, Object>> steps = new com.fasterxml.jackson.databind.ObjectMapper().readValue(plan.getPlanSteps(), java.util.List.class);
                        timeout = steps.stream().filter(step -> assignment.getStepSeq().equals(((Number) step.get("stepSeq")).intValue()))
                                .map(step -> ((Number) step.getOrDefault("stepTimeout", stepTimeoutSeconds)).intValue()).findFirst().orElse(stepTimeoutSeconds);
                    } catch (Exception ignored) { /* Use the documented default for legacy plans. */ }
                }
                if (assignment.getDispatchedAt() == null || assignment.getDispatchedAt().plusSeconds(timeout).isAfter(LocalDateTime.now())) continue;
                assignment.setStepStatus("FAILED");
                assignment.setExecutionResult("TIMEOUT");
                assignment.setReasonCode("ERR_EXECUTION_TIMEOUT");
                assignment.setUpdatedAt(LocalDateTime.now());
                assignmentMapper.update(assignment);

                taskEventService.append(assignment.getTaskId(), "STEP_TIMEOUT_DETECTED", "SYSTEM",
                        "ERR_EXECUTION_TIMEOUT",
                        "第" + assignment.getStepSeq() + "步指令" + executeId(assignment) + "下发后超过"
                                + timeout + "秒未收到执行反馈，判定执行超时");

                if (assignment.getDeviceAgentId() != null) {
                    deviceAgentMapper.findById(assignment.getDeviceAgentId()).ifPresent(agent -> {
                        if (agent.getCurrentTaskId() != null && !assignment.getTaskId().equals(agent.getCurrentTaskId())) {
                            return;
                        }
                        agent.setWorkStatus("IDLE");
                        agent.setCurrentTaskId(null);
                        agent.setCurrentStepSeq(null);
                        deviceAgentMapper.update(agent);
                        if (deviceCommandMapper != null) {
                            deviceCommandMapper.updateStatus(agent.getAgentCode(), executeId(assignment),
                                    "EXECUTE_CAPABILITY", assignment.getRetryCount(), "TIMED_OUT",
                                    "{\"message\":\"STEP_TIMEOUT_DETECTED\"}");
                        }
                    });
                }

                taskExceptionService.handleException(assignment.getTaskId(), assignment.getStepSeq(),
                        "EXECUTION_TIMEOUT", "指令" + executeId(assignment) + "执行超时未收到");
            } catch (RuntimeException ignored) {
                // SRS_NF005：单个步骤超时处置异常隔离，不阻断同批次其余超时步骤的巡检与自愈
            }
        }
    }

    /** 执行消息引入独立指令号，迁移前遗留行没有时回退到集中指令号 */
    private static String executeId(com.airport.ai.task.TaskStepAssignment a) {
        return a.getExecuteCommandId() != null ? a.getExecuteCommandId() : a.getCommandId();
    }
}
