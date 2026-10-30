package com.airport.ai.task;

import com.airport.ai.event.TaskEventService;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;

/**
 * 对应5.5.2业务规则3、异常路径3c：指令下发后步骤持续处于EXECUTING状态超过
 * app.task.step-timeout-default-seconds（默认60秒）仍未收到执行反馈，判定为执行超时，
 * 与HeartbeatMonitorTask检测设备心跳超时是同类机制（定期扫描+阈值判断），复用相同模式。
 */
@Component
public class StepTimeoutMonitorTask {

    @org.springframework.beans.factory.annotation.Autowired private PlanVersionMapper plans;
    private final TaskStepAssignmentMapper assignmentMapper;
    private final com.airport.ai.device.DeviceAgentMapper deviceAgentMapper;
    private final TaskEventService taskEventService;
    private final TaskExceptionService taskExceptionService;
    private final int stepTimeoutSeconds;

    public StepTimeoutMonitorTask(TaskStepAssignmentMapper assignmentMapper,
                                   com.airport.ai.device.DeviceAgentMapper deviceAgentMapper,
                                   TaskEventService taskEventService,
                                   TaskExceptionService taskExceptionService,
                                   @Value("${app.task.step-timeout-default-seconds:60}") int stepTimeoutSeconds) {
        this.assignmentMapper = assignmentMapper;
        this.deviceAgentMapper = deviceAgentMapper;
        this.taskEventService = taskEventService;
        this.taskExceptionService = taskExceptionService;
        this.stepTimeoutSeconds = stepTimeoutSeconds;
    }

    @Scheduled(fixedRate = 10000)
    @Transactional
    public void checkStepTimeout() {
        LocalDateTime threshold = LocalDateTime.now().minusSeconds(10);
        List<TaskStepAssignment> timedOut = assignmentMapper.findByStepStatusAndDispatchedAtBefore("EXECUTING", threshold);
        for (TaskStepAssignment assignment : timedOut) {
            int timeout=stepTimeoutSeconds;
            try {
                var plan=plans.findById(assignment.getPlanVersionId()).orElseThrow();
                java.util.List<java.util.Map<String,Object>> steps=new com.fasterxml.jackson.databind.ObjectMapper().readValue(plan.getPlanSteps(),java.util.List.class);
                timeout=steps.stream().filter(step -> assignment.getStepSeq().equals(((Number)step.get("stepSeq")).intValue()))
                        .map(step -> ((Number)step.getOrDefault("stepTimeout",stepTimeoutSeconds)).intValue()).findFirst().orElse(stepTimeoutSeconds);
            } catch (Exception ignored) { /* Use the documented default for legacy plans. */ }
            if (assignment.getDispatchedAt().plusSeconds(timeout).isAfter(LocalDateTime.now())) continue;
            assignment.setStepStatus("FAILED");
            assignment.setExecutionResult("TIMEOUT");
            assignment.setReasonCode("ERR_EXECUTION_TIMEOUT");
            assignment.setUpdatedAt(LocalDateTime.now());
            assignmentMapper.update(assignment);

            taskEventService.append(assignment.getTaskId(), "STEP_TIMEOUT_DETECTED", "SYSTEM",
                    "ERR_EXECUTION_TIMEOUT",
                    "步骤" + assignment.getStepSeq() + "指令" + executeId(assignment) + "下发后超过"
                            + timeout + "秒未收到执行反馈，判定执行超时");

            if (assignment.getDeviceAgentId() != null) {
                deviceAgentMapper.findById(assignment.getDeviceAgentId()).ifPresent(agent -> {
                    agent.setWorkStatus("IDLE");
                    agent.setCurrentTaskId(null);
                    agent.setCurrentStepSeq(null);
                    deviceAgentMapper.update(agent);
                });
            }

            taskExceptionService.handleException(assignment.getTaskId(), assignment.getStepSeq(),
                    "EXECUTION_TIMEOUT", "指令" + executeId(assignment) + "执行超时未收到反馈");
        }
    }

    /** 执行消息自己的指令号；迁移前遗留行没有时回退到承接指令号 */
    private static String executeId(com.airport.ai.task.TaskStepAssignment a) {
        return a.getExecuteCommandId() != null ? a.getExecuteCommandId() : a.getCommandId();
    }
}
