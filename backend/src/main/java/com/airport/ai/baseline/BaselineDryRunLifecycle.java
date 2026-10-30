package com.airport.ai.baseline;

import com.airport.ai.task.*;
import com.airport.ai.device.*;
import com.airport.ai.event.TaskEventService;
import org.springframework.stereotype.Service;
import java.time.LocalDateTime;

/** Finalizes only the exact template version actually exercised by device feedback. */
@Service
public class BaselineDryRunLifecycle {
    private final TaskMapper tasks;
    private final PlanVersionMapper plans;
    private final BaselineTemplateMapper templates;
    private final TaskStepAssignmentMapper assignments;
    private final DeviceAgentMapper agents;
    private final DeviceAgentMessagingService gateway;
    private final TaskEventService events;
    public BaselineDryRunLifecycle(TaskMapper tasks, PlanVersionMapper plans, BaselineTemplateMapper templates,
            TaskStepAssignmentMapper assignments, DeviceAgentMapper agents, DeviceAgentMessagingService gateway,
            TaskEventService events) {
        this.tasks=tasks; this.plans=plans; this.templates=templates; this.assignments=assignments;
        this.agents=agents; this.gateway=gateway; this.events=events;
    }
    public void finish(Long taskId, boolean success, String reason) {
        Task task=tasks.findById(taskId).orElseThrow();
        if (!Boolean.TRUE.equals(task.getIsDryRun())) return;
        if (!success) {
            task.setStatus(TaskStatus.FAILED); task.setFailureReason(reason);
            task.setUpdatedAt(LocalDateTime.now()); tasks.update(task);
            for (var assignment:assignments.findByPlanVersionIdOrderByStepSeqAsc(task.getCurrentPlanVersionId())) {
                if ("COMPLETED".equals(assignment.getStepStatus())) continue;
                if (assignment.getDeviceAgentId()!=null && assignment.getCommandId()!=null) {
                    agents.findById(assignment.getDeviceAgentId()).ifPresent(agent -> {
                        try { gateway.cancelTask(agent.getAgentCode(), com.airport.ai.device.CommandIds.next(), taskId, assignment.getStepSeq()); }
                        catch (RuntimeException ignored) { /* Failure remains visible; do not fabricate a successful run. */ }
                        if (taskId.equals(agent.getCurrentTaskId())) {
                            agent.setWorkStatus("IDLE"); agent.setCurrentTaskId(null); agent.setCurrentStepSeq(null); agents.update(agent);
                        }
                    });
                }
                if (!"FAILED".equals(assignment.getStepStatus())) assignment.setStepStatus("FROZEN");
                assignment.setUpdatedAt(LocalDateTime.now()); assignments.update(assignment);
            }
        }
        PlanVersion plan=plans.findById(task.getCurrentPlanVersionId()).orElseThrow();
        templates.findById(plan.getBaselineTemplateId()).ifPresent(template -> {
            if (java.util.Objects.equals(template.getTemplateVersion(), plan.getSnapshotId())) {
                template.setTemplateStatus(success ? "DRY_RUN_PASSED" : "DRAFT");
                template.setUpdatedAt(LocalDateTime.now()); templates.update(template);
            }
        });
        events.append(taskId, success ? "DRY_RUN_SUCCEEDED" : "DRY_RUN_FAILED", "SYSTEM",
                success ? null : "ERR_DRY_RUN_STEP_FAILED", reason);
    }
}
