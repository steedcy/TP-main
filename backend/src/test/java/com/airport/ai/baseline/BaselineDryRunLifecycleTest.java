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
