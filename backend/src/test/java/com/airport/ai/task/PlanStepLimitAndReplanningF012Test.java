package com.airport.ai.task;

import com.airport.ai.baseline.BaselineTemplateService;
import com.airport.ai.event.TaskEventService;
import com.airport.ai.planning.PlanningModelService;
import com.airport.ai.planning.PlanningRequest;
import com.airport.ai.planning.PlanningResponse;
import com.airport.ai.risk.RiskAssessmentResult;
import com.airport.ai.risk.RiskAssessmentService;
import com.airport.ai.taskdef.TaskDefinitionMapper;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

import java.math.BigDecimal;
import java.util.*;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * SRS_F012.R01/R02/R10：五步限制、条件节点计数、实际执行路径与重规划剩余额度计算。
 */
class PlanStepLimitAndReplanningF012Test {

    private Map<String, Object> step(int seq, String capability) {
        Map<String, Object> s = new LinkedHashMap<>();
        s.put("stepSeq", seq);
        s.put("stepGoal", "执行步骤" + seq);
        s.put("capabilityType", capability);
        s.put("inputParams", Map.of("key", "val" + seq));
        s.put("precondition", "设备空闲");
        s.put("completionCondition", "status=DONE");
        s.put("failureHandling", "重试一次或转人工");
        return s;
    }

    private Map<String, Object> conditionNode(int seq, String cond) {
        Map<String, Object> s = new LinkedHashMap<>();
        s.put("stepSeq", seq);
        s.put("conditionNode", true);
        s.put("nodeType", "CONDITION");
        s.put("condition", cond);
        s.put("stepGoal", "判断: " + cond);
        return s;
    }

    @Test
    void replanningCalculatesRemainingQuotaFromActuallyCompletedPrefix() {
        var tasks = mock(TaskMapper.class);
        var plans = mock(PlanVersionMapper.class);
        var assignments = mock(TaskStepAssignmentMapper.class);
        var context = mock(ContextSnapshotService.class);
        var model = mock(PlanningModelService.class);
        var events = mock(TaskEventService.class);
        var definitions = mock(TaskDefinitionMapper.class);

        var task = new Task();
        task.setId(10L);
        task.setCurrentPlanVersionId(1L);
        task.setTaskGoal("航班保障原目标");
        task.setTaskFamily("FLIGHT_CHANGE_RESPONSE");
        when(tasks.findById(10L)).thenReturn(Optional.of(task));
        when(tasks.claimReplan(eq(10L), anyString())).thenReturn(1);

        var planV1 = new PlanVersion();
        planV1.setId(1L);
        planV1.setPlanSteps("[{\"stepSeq\":1,\"capabilityType\":\"CAP_FLIGHT_UPDATE\"}," +
                "{\"stepSeq\":2,\"capabilityType\":\"CAP_INFO_DISPLAY\"}," +
                "{\"stepSeq\":3,\"capabilityType\":\"CAP_NOTIFICATION\"}]");
        when(plans.findById(1L)).thenReturn(Optional.of(planV1));

        // 步骤1已完成，步骤2失败触发重规划 -> 已完成数=1，剩余额度=5-1=4
        var a1 = new TaskStepAssignment();
        a1.setStepSeq(1); a1.setStepStatus("COMPLETED"); a1.setExecutionResult("SUCCESS");
        a1.setOutputParams("{\"status\":\"OK\"}"); a1.setCommandId("CMD-1");

        var a2 = new TaskStepAssignment();
        a2.setStepSeq(2); a2.setStepStatus("FAILED"); a2.setRetryCount(1);

        when(assignments.findByPlanVersionIdOrderByStepSeqAsc(1L)).thenReturn(List.of(a1, a2));

        var snapshot = new ContextSnapshot();
        snapshot.setSnapshotCode("SNAP-REPLAN-1");
        when(context.buildSnapshot(eq(10L), anyList())).thenReturn(snapshot);
        when(context.capabilityContext(eq(snapshot), anyList())).thenReturn(List.of());

        // 模型在重规划时收到 remainingStepQuota = 4
        var response = new PlanningResponse();
        response.setResultCode("0");
        response.setConfidence(BigDecimal.valueOf(0.95));
        // 返回2个可执行步骤 + 1个条件节点 = 2可执行 <= 4 额度 -> 通过
        response.setPlanSteps(List.of(
                conditionNode(1, "是否有大屏可用"),
                step(2, "CAP_INFO_DISPLAY"),
                step(3, "CAP_NOTIFICATION")
        ));
        when(model.generatePlan(any())).thenReturn(response);

        var validationService = mock(PlanValidationService.class);
        var validResult = new PlanValidationResult();
        when(validationService.validate(anyList(), any(), any(), any(), anyInt())).thenReturn(validResult);
        when(validationService.validate(anyList(), any(), any(), any(), anyInt(), any())).thenReturn(validResult);

        var riskService = mock(RiskAssessmentService.class);
        var riskResult = new RiskAssessmentResult("LOW", "RULE_LOW_RISK", "符合低风险要求",
                BigDecimal.valueOf(0.95), "AUTO_EXECUTE", "V1.0");
        when(riskService.assess(any(), any(), any(), anyBoolean(), anyInt())).thenReturn(riskResult);

        var orchestrator = mock(TaskExecutionOrchestrator.class);
        var baselineService = mock(BaselineTemplateService.class);

        var replanningService = new ReplanningService(tasks, plans, assignments, context, validationService,
                model, riskService, orchestrator, events, baselineService);
        org.springframework.test.util.ReflectionTestUtils.setField(replanningService, "definitions", definitions);

        replanningService.replan(10L, 2, "STEP_FAILED");

        var captor = ArgumentCaptor.forClass(PlanningRequest.class);
        verify(model).generatePlan(captor.capture());
        PlanningRequest sentRequest = captor.getValue();

        // 核对送模的剩余额度与已完成步骤
        assertEquals(4, sentRequest.getRemainingStepQuota(), "5 - 1个已完成步骤 = 4剩余额度");
        assertEquals(1, sentRequest.getCompletedSteps().size());
        assertEquals("航班保障原目标", sentRequest.getTaskGoal());

        // 核对保存的PlanVersion为新版本，折叠条件节点后只有 1已完成 + 2替换 = 3个步骤 <= 5
        var planCaptor = ArgumentCaptor.forClass(PlanVersion.class);
        verify(plans).insert(planCaptor.capture());
        PlanVersion inserted = planCaptor.getValue();
        assertNotNull(inserted.getFrozenAt(), "校验通过应冻结");
        assertTrue(inserted.getPlanSteps().contains("CAP_INFO_DISPLAY"));
    }

    @Test
    void replanningExceedingQuotaIsRejectedWithLimitExceeded() {
        var tasks = mock(TaskMapper.class);
        var plans = mock(PlanVersionMapper.class);
        var assignments = mock(TaskStepAssignmentMapper.class);
        var context = mock(ContextSnapshotService.class);
        var model = mock(PlanningModelService.class);
        var events = mock(TaskEventService.class);

        var task = new Task();
        task.setId(20L);
        task.setCurrentPlanVersionId(1L);
        task.setTaskGoal("航班保障原目标");
        task.setTaskFamily("FLIGHT_CHANGE_RESPONSE");
        when(tasks.findById(20L)).thenReturn(Optional.of(task));
        when(tasks.claimReplan(eq(20L), anyString())).thenReturn(1);

        var planV1 = new PlanVersion();
        planV1.setId(1L);
        planV1.setPlanSteps("[]");
        when(plans.findById(1L)).thenReturn(Optional.of(planV1));

        // 已完成3步，步骤4失败 -> 剩余额度 = 5 - 3 = 2
        var a1 = new TaskStepAssignment(); a1.setStepSeq(1); a1.setStepStatus("COMPLETED"); a1.setExecutionResult("SUCCESS");
        var a2 = new TaskStepAssignment(); a2.setStepSeq(2); a2.setStepStatus("COMPLETED"); a2.setExecutionResult("SUCCESS");
        var a3 = new TaskStepAssignment(); a3.setStepSeq(3); a3.setStepStatus("COMPLETED"); a3.setExecutionResult("SUCCESS");
        var a4 = new TaskStepAssignment(); a4.setStepSeq(4); a4.setStepStatus("FAILED");

        when(assignments.findByPlanVersionIdOrderByStepSeqAsc(1L)).thenReturn(List.of(a1, a2, a3, a4));

        var snapshot = new ContextSnapshot();
        snapshot.setSnapshotCode("SNAP-REPLAN-2");
        when(context.buildSnapshot(eq(20L), anyList())).thenReturn(snapshot);

        // 模型返回3个可执行步骤 > 剩余额度2 -> 必须拒绝
        var response = new PlanningResponse();
        response.setResultCode("0");
        response.setPlanSteps(List.of(
                step(1, "CAP_INFO_DISPLAY"),
                step(2, "CAP_NOTIFICATION"),
                step(3, "CAP_FLIGHT_UPDATE")
        ));
        when(model.generatePlan(any())).thenReturn(response);

        var replanningService = new ReplanningService(tasks, plans, assignments, context, mock(PlanValidationService.class),
                model, mock(RiskAssessmentService.class), mock(TaskExecutionOrchestrator.class), events, mock(BaselineTemplateService.class));

        replanningService.replan(20L, 4, "STEP_FAILED");

        verify(events).append(eq(20L), eq("REPLAN_FAILED"), eq("SYSTEM"), eq("ERR_STEP_LIMIT_EXCEEDED"), contains("超过剩余额度2"));
        assertEquals(TaskStatus.PENDING_MANUAL, task.getStatus());
    }

    @Test
    void replanningWhenAllFiveStepsCompletedHasZeroQuotaAndFailsImmediately() {
        var tasks = mock(TaskMapper.class);
        var plans = mock(PlanVersionMapper.class);
        var assignments = mock(TaskStepAssignmentMapper.class);
        var events = mock(TaskEventService.class);

        var task = new Task();
        task.setId(30L);
        task.setCurrentPlanVersionId(1L);
        when(tasks.findById(30L)).thenReturn(Optional.of(task));

        // 5步均已完成
        List<TaskStepAssignment> allCompleted = new ArrayList<>();
        for (int i = 1; i <= 5; i++) {
            var a = new TaskStepAssignment();
            a.setStepSeq(i); a.setStepStatus("COMPLETED"); a.setExecutionResult("SUCCESS");
            allCompleted.add(a);
        }
        when(assignments.findByPlanVersionIdOrderByStepSeqAsc(1L)).thenReturn(allCompleted);

        var model = mock(PlanningModelService.class);
        var replanningService = new ReplanningService(tasks, plans, assignments, mock(ContextSnapshotService.class),
                mock(PlanValidationService.class), model, mock(RiskAssessmentService.class),
                mock(TaskExecutionOrchestrator.class), events, mock(BaselineTemplateService.class));

        replanningService.replan(30L, 6, "STEP_FAILED");

        verify(events).append(eq(30L), eq("REPLAN_FAILED"), eq("SYSTEM"), eq("ERR_STEP_QUOTA_EXHAUSTED"), contains("无剩余步骤额度"));
        verifyNoInteractions(model);
        assertEquals(TaskStatus.PENDING_MANUAL, task.getStatus());
    }
}
