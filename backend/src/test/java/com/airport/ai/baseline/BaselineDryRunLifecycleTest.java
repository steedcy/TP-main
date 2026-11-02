package com.airport.ai.baseline;
import com.airport.ai.task.*;
import com.airport.ai.device.*;
import com.airport.ai.event.TaskEventService;
import org.junit.jupiter.api.Test;
import java.util.Optional;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;
class BaselineDryRunLifecycleTest {
    @Test void onlySuccessfulTrialOfCurrentVersionCanPassTemplate() { verifyVersion("V1.2",true); }
    @Test void completingOldTrialCannotPassAnEditedDraft() { verifyVersion("V1.3",false); }
    // DEF-S3-027：试运行成功/失败都写带模板版本与任务编号的结果操作日志
    @Test void successAndFailureBothWriteAResultAuditRecord() {
        for (boolean success : new boolean[]{true, false}) {
            var tasks=mock(TaskMapper.class);var plans=mock(PlanVersionMapper.class);var templates=mock(BaselineTemplateMapper.class);
            var task=new Task();task.setIsDryRun(true);task.setCurrentPlanVersionId(2L);when(tasks.findById(1L)).thenReturn(Optional.of(task));
            var plan=new PlanVersion();plan.setBaselineTemplateId(3L);plan.setSnapshotId("V1.2");when(plans.findById(2L)).thenReturn(Optional.of(plan));
            var template=new BaselineTemplate();template.setTemplateName("tpl-A");template.setTemplateVersion("V1.2");template.setTemplateStatus("DRAFT");
            when(templates.findById(3L)).thenReturn(Optional.of(template));
            var audit=mock(com.airport.ai.auth.OperationLogService.class);
            var lifecycle=new BaselineDryRunLifecycle(tasks,plans,templates,mock(TaskStepAssignmentMapper.class),mock(DeviceAgentMapper.class),mock(DeviceAgentMessagingService.class),mock(TaskEventService.class));
            org.springframework.test.util.ReflectionTestUtils.setField(lifecycle,"operationLogService",audit);
            lifecycle.finish(1L,success,"step 2 failed");
            var target=org.mockito.ArgumentCaptor.forClass(String.class);
            @SuppressWarnings("unchecked") var detail=org.mockito.ArgumentCaptor.forClass(java.util.Map.class);
            verify(audit).record(isNull(),eq("SYSTEM"),isNull(),eq("BASELINE_TEMPLATE_DRY_RUN_RESULT"),target.capture(),
                    eq(success ? "SUCCESS":"FAILED"),isNull(),detail.capture());
            assertTrue(target.getValue().contains("tpl-A") && target.getValue().contains("V1.2") && target.getValue().contains("任务1"));
            assertEquals(success ? "DRY_RUN_PASSED":"DRY_RUN_FAILED", target.getValue().substring(target.getValue().lastIndexOf("-> ")+3));
            assertEquals(1L,detail.getValue().get("taskId"));
            assertEquals("V1.2",detail.getValue().get("templateVersion"));
        }
    }
    // DEF-S3-086：人工取消试运行，结果事件与操作日志均为CANCELLED，任务保持MANUAL_TERMINATED，模板不通过
    @Test void cancelledTrialIsAuditedAsCancelledNotFailed() {
        var tasks=mock(TaskMapper.class);var plans=mock(PlanVersionMapper.class);var templates=mock(BaselineTemplateMapper.class);
        var task=new Task();task.setIsDryRun(true);task.setCurrentPlanVersionId(2L);when(tasks.findById(1L)).thenReturn(Optional.of(task));
        var plan=new PlanVersion();plan.setBaselineTemplateId(3L);plan.setSnapshotId("V1.2");when(plans.findById(2L)).thenReturn(Optional.of(plan));
        var template=new BaselineTemplate();template.setTemplateName("tpl-A");template.setTemplateVersion("V1.2");template.setTemplateStatus("DRY_RUN_PASSED");
        when(templates.findById(3L)).thenReturn(Optional.of(template));
        var audit=mock(com.airport.ai.auth.OperationLogService.class);var events=mock(TaskEventService.class);
        var lifecycle=new BaselineDryRunLifecycle(tasks,plans,templates,mock(TaskStepAssignmentMapper.class),mock(DeviceAgentMapper.class),mock(DeviceAgentMessagingService.class),events);
        org.springframework.test.util.ReflectionTestUtils.setField(lifecycle,"operationLogService",audit);
        lifecycle.finish(1L,false,"cancelled by admin",true);
        assertEquals(TaskStatus.MANUAL_TERMINATED,task.getStatus());
        assertEquals("DRAFT",template.getTemplateStatus());
        verify(events).append(eq(1L),eq("DRY_RUN_CANCELLED"),eq("SYSTEM"),eq("ERR_DRY_RUN_CANCELLED"),eq("cancelled by admin"));
        var target=org.mockito.ArgumentCaptor.forClass(String.class);
        @SuppressWarnings("unchecked") var detail=org.mockito.ArgumentCaptor.forClass(java.util.Map.class);
        verify(audit).record(isNull(),eq("SYSTEM"),isNull(),eq("BASELINE_TEMPLATE_DRY_RUN_RESULT"),target.capture(),eq("CANCELLED"),isNull(),detail.capture());
        assertTrue(target.getValue().endsWith("DRY_RUN_CANCELLED"));
        assertEquals("CANCELLED",detail.getValue().get("result"));
    }
    @Test void auditIsOptionalSoExistingWiringStillWorks() { verifyVersion("V1.2",true); }
    private void verifyVersion(String version, boolean shouldPass) {
        var tasks=mock(TaskMapper.class);var plans=mock(PlanVersionMapper.class);var templates=mock(BaselineTemplateMapper.class);
        var task=new Task();task.setIsDryRun(true);task.setCurrentPlanVersionId(2L);when(tasks.findById(1L)).thenReturn(Optional.of(task));
        var plan=new PlanVersion();plan.setBaselineTemplateId(3L);plan.setSnapshotId("V1.2");when(plans.findById(2L)).thenReturn(Optional.of(plan));
        var template=new BaselineTemplate();template.setTemplateStatus("DRAFT");template.setTemplateVersion(version);when(templates.findById(3L)).thenReturn(Optional.of(template));
        var lifecycle=new BaselineDryRunLifecycle(tasks,plans,templates,mock(TaskStepAssignmentMapper.class),mock(DeviceAgentMapper.class),mock(DeviceAgentMessagingService.class),mock(TaskEventService.class));
        lifecycle.finish(1L,true,"actual feedback");
        assertEquals(shouldPass ? "DRY_RUN_PASSED":"DRAFT",template.getTemplateStatus());
        verify(templates,times(shouldPass ? 1:0)).update(template);
    }
}
