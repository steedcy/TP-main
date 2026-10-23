package com.airport.ai.task;

import com.airport.ai.planning.*;
import com.airport.ai.risk.RiskAssessmentService;
import com.airport.ai.event.TaskEventService;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import java.util.*;
import static org.mockito.Mockito.*;
import static org.mockito.ArgumentMatchers.*;
import static org.junit.jupiter.api.Assertions.*;

class ReplanningContextTest {
    @Test void timeoutKeepsActualContextAndConsumesOnlyOpportunity() {
        var tasks=mock(TaskMapper.class); var plans=mock(PlanVersionMapper.class);
        var assignments=mock(TaskStepAssignmentMapper.class); var context=mock(ContextSnapshotService.class);
        var model=mock(PlanningModelService.class);
        var task=new Task(); task.setId(1L); task.setCurrentPlanVersionId(2L);
        task.setTaskGoal("保留原目标"); task.setTaskFamily("FLIGHT_CHANGE_RESPONSE");
        task.setSceneParams("{\"flightNumber\":\"TEST123\"}");
        task.setGoalParsingResult("{\"constraints\":[\"信息发布必须先于旅客引导\"]}");
        when(tasks.findById(1L)).thenReturn(Optional.of(task));
        when(tasks.claimReplan(1L,"STEP_FAILED")).thenReturn(1);
        var plan=new PlanVersion(); plan.setPlanSteps("[{\"stepSeq\":1,\"capabilityType\":\"CAP_INFO_DISPLAY\"},{\"stepSeq\":2,\"capabilityType\":\"CAP_FLIGHT_UPDATE\"}]");
        when(plans.findById(2L)).thenReturn(Optional.of(plan));
        var completed=new TaskStepAssignment(); completed.setStepSeq(1); completed.setStepStatus("COMPLETED");
        completed.setExecutionResult("SUCCESS"); completed.setOutputParams("{\"displayStatus\":\"SUCCESS\"}"); completed.setCommandId("CMD-REAL");
        when(assignments.findByPlanVersionIdOrderByStepSeqAsc(2L)).thenReturn(List.of(completed));
        var snapshot=new ContextSnapshot(); snapshot.setSnapshotCode("CTX-NEW");
        when(context.buildSnapshot(eq(1L),anyList())).thenReturn(snapshot);
        var capabilities=List.<Map<String,Object>>of(Map.of("capabilityType","CAP_FLIGHT_UPDATE","candidateCount",2));
        when(context.capabilityContext(eq(snapshot),anyList())).thenReturn(capabilities);
        when(model.generatePlan(any())).thenThrow(new RuntimeException("controlled timeout"));
        var service=new ReplanningService(tasks,plans,assignments,context,mock(PlanValidationService.class),model,
                mock(RiskAssessmentService.class),mock(TaskExecutionOrchestrator.class),mock(TaskEventService.class));
        var definitions=mock(com.airport.ai.taskdef.TaskDefinitionMapper.class);
        var definition=new com.airport.ai.taskdef.TaskDefinition();
        definition.setAvailableCapabilityTypes("[\"CAP_FLIGHT_UPDATE\",\"CAP_NOTIFICATION\"]");
        definition.setConstraintDescription("保留任务定义约束");
        when(definitions.findByDefinitionCode("FLIGHT_CHANGE_RESPONSE")).thenReturn(Optional.of(definition));
        org.springframework.test.util.ReflectionTestUtils.setField(service,"definitions",definitions);
        service.replan(1L,2,"STEP_FAILED");
        var capture=ArgumentCaptor.forClass(PlanningRequest.class); verify(model).generatePlan(capture.capture());
        var request=capture.getValue();
        assertEquals("TEST123",request.getSceneParams().get("flightNumber"));
        assertTrue(request.getConstraints().contains("信息发布必须先于旅客引导"));
        assertTrue(request.getConstraints().contains("本次异常: STEP_FAILED"));
        verify(context).buildSnapshot(1L,List.of("CAP_FLIGHT_UPDATE","CAP_NOTIFICATION"));
        assertTrue(request.getConstraints().contains("保留任务定义约束"));
        assertEquals(capabilities,request.getCapabilityContext()); assertEquals(4,request.getRemainingStepQuota());
        assertEquals(Map.of("displayStatus","SUCCESS"),request.getCompletedSteps().get(0).get("outputParams"));
        assertEquals("CMD-REAL",request.getCompletedSteps().get(0).get("originalCommandId"));
        assertTrue(task.getReplanUsed()); assertEquals(TaskStatus.PENDING_MANUAL,task.getStatus());
        service.replan(1L,2,"SECOND"); verify(model,times(1)).generatePlan(any());
    }
}
