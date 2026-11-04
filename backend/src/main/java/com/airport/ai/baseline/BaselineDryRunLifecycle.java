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
    public void finish(Long taskId, boolean success, String reason) { finish(taskId, success, reason, false); }

    /** cancelled=true：人工取消试运行，结果为CANCELLED而非FAILED（DEF-S3-086），任务状态保持MANUAL_TERMINATED。 */
    public void finish(Long taskId, boolean success, String reason, boolean cancelled) {
        Task task=tasks.findById(taskId).orElseThrow();
        if (!Boolean.TRUE.equals(task.getIsDryRun())) return;
        if (!success) {
            task.setStatus(cancelled ? TaskStatus.MANUAL_TERMINATED : TaskStatus.FAILED); task.setFailureReason(reason);
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
                template.setUpdatedAt(LocalDateTime.now());
                if (success) {
                    template.setLastDryRunPassedAt(LocalDateTime.now());
                }
                templates.update(template);
            }
        });
        events.append(taskId, success ? "DRY_RUN_SUCCEEDED" : cancelled ? "DRY_RUN_CANCELLED" : "DRY_RUN_FAILED", "SYSTEM",
                success ? null : cancelled ? "ERR_DRY_RUN_CANCELLED" : "ERR_DRY_RUN_STEP_FAILED", reason);
        recordResult(taskId, plan, success, cancelled, reason);
    }

    @org.springframework.beans.factory.annotation.Autowired(required = false)
    private com.airport.ai.auth.OperationLogService operationLogService;

    /**
     * 试运行结果也写操作日志（SRS_F009.R08、DEF-S3-027）：发起时只记了RUNNING，完成或失败须有结果记录，
     * 带模板名称、模板版本与任务编号；失败原因只写简短文本，不带设备载荷。
     */
    private void recordResult(Long taskId, PlanVersion plan, boolean success, boolean cancelled, String reason) {
        if (operationLogService == null) return;
        String templateName = templates.findById(plan.getBaselineTemplateId())
                .map(BaselineTemplate::getTemplateName).orElse("template-" + plan.getBaselineTemplateId());
        String target = templateName + "(" + plan.getSnapshotId() + ") 任务" + taskId + " -> "
                + (success ? "DRY_RUN_PASSED" : cancelled ? "DRY_RUN_CANCELLED" : "DRY_RUN_FAILED");
        java.util.Map<String, Object> detail = new java.util.LinkedHashMap<>();
        detail.put("taskId", taskId);
        detail.put("templateVersion", plan.getSnapshotId());
        detail.put("result", success ? "SUCCESS" : cancelled ? "CANCELLED" : "FAILED");
        if (reason != null) detail.put("reason", reason.length() > 200 ? reason.substring(0, 200) + "…" : reason);
        operationLogService.record(null, "SYSTEM", null, "BASELINE_TEMPLATE_DRY_RUN_RESULT", target,
                success ? "SUCCESS" : cancelled ? "CANCELLED" : "FAILED", null, detail);
    }
}
