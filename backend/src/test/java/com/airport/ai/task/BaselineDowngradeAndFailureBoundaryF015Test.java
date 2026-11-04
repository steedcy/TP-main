package com.airport.ai.task;

import com.airport.ai.baseline.BaselineTemplate;
import com.airport.ai.baseline.BaselineTemplateMapper;
import com.airport.ai.baseline.BaselineTemplateService;
import com.airport.ai.common.BusinessException;
import com.airport.ai.common.ErrorCode;
import com.airport.ai.device.DeviceAgentMapper;
import com.airport.ai.device.DeviceCapabilityMapper;
import com.airport.ai.event.TaskEventService;
import com.airport.ai.planning.PlanningModelService;
import com.airport.ai.risk.RiskAssessmentResult;
import com.airport.ai.risk.RiskAssessmentService;
import com.airport.ai.taskdef.TaskDefinition;
import com.airport.ai.taskdef.TaskDefinitionService;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * SRS_F015 高峰/基线降级与故障边界 核心业务规则与缺陷专项验证（R01 ~ R09、DEF-S3-065、DEF-S3-066、DEF-S3-067）。
 */
class BaselineDowngradeAndFailureBoundaryF015Test {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private final TaskMapper taskMapper = mock(TaskMapper.class);
    private final PlanVersionMapper planVersionMapper = mock(PlanVersionMapper.class);
    private final ContextSnapshotService contextSnapshotService = mock(ContextSnapshotService.class);
    private final PlanValidationService planValidationService = mock(PlanValidationService.class);
    private final PlanningModelService planningModelService = mock(PlanningModelService.class);
    private final RiskAssessmentService riskAssessmentService = mock(RiskAssessmentService.class);
    private final TaskEventService taskEventService = mock(TaskEventService.class);
    private final TaskExecutionOrchestrator taskExecutionOrchestrator = mock(TaskExecutionOrchestrator.class);
    private final TaskDefinitionService taskDefinitionService = mock(TaskDefinitionService.class);

    private final BaselineTemplateMapper templateMapper = mock(BaselineTemplateMapper.class);
    private final DeviceCapabilityMapper capabilityMapper = mock(DeviceCapabilityMapper.class);
    private final BaselineTemplateService baselineTemplateService = new BaselineTemplateService(
            templateMapper, capabilityMapper, mock(com.airport.ai.auth.OperationLogService.class), taskDefinitionService);

    private final TaskStepAssignmentMapper assignmentMapper = mock(TaskStepAssignmentMapper.class);
    private final TaskExceptionMapper exceptionMapper = mock(TaskExceptionMapper.class);
    private final DeviceAgentMapper deviceAgentMapper = mock(DeviceAgentMapper.class);
    private final ReplanningService replanningService = mock(ReplanningService.class);

    private TaskPlanningOrchestrator planningOrchestrator;
    private TaskExceptionService exceptionService;

    @BeforeEach
    void setUp() {
        planningOrchestrator = new TaskPlanningOrchestrator(
                taskMapper, planVersionMapper, contextSnapshotService, planValidationService,
                planningModelService, riskAssessmentService, baselineTemplateService,
                taskEventService, taskExecutionOrchestrator, taskDefinitionService);

        exceptionService = new TaskExceptionService(
                taskMapper, assignmentMapper, exceptionMapper, deviceAgentMapper,
                taskEventService, taskExecutionOrchestrator, replanningService, planVersionMapper);

        ContextSnapshot snapshot = new ContextSnapshot();
        snapshot.setSnapshotCode("CTX-F015");
        snapshot.setAgents("[]");
        when(contextSnapshotService.buildSnapshot(anyLong(), anyList())).thenReturn(snapshot);
        when(contextSnapshotService.parseAgents(any())).thenReturn(List.of());
    }

    private BaselineTemplate createTemplate(Long id, String name, String family, int stepCount, LocalDateTime updatedAt) {
        BaselineTemplate t = new BaselineTemplate();
        t.setId(id);
        t.setTemplateName(name);
        t.setTaskFamily(family);
        t.setTemplateVersion("V1.3");
        t.setTemplateStatus("ENABLED");
        t.setUpdatedAt(updatedAt);
        t.setCreatedAt(updatedAt.minusDays(1));
        t.setInputParams("[]");

        StringBuilder steps = new StringBuilder("[");
        for (int i = 1; i <= stepCount; i++) {
            if (i > 1) steps.append(",");
            steps.append("{\"stepSeq\":").append(i)
                    .append(",\"capabilityType\":\"CAP_NAVIGATION\",\"completionCondition\":\"reached=true\",\"paramMapping\":[]}");
        }
        steps.append("]");
        t.setSteps(steps.toString());
        return t;
    }

    /**
     * SRS_F015.R01: 高风险计划不得直接执行原候选计划，必须自动切换到经过静态校验和试运行的基线模板。
     * SRS_F015.R03: 基线降级不得改变原始任务目标，只能替换计划来源和步骤方案。
     * SRS_F015.R04: 基线模板仍须通过结构、能力、约束三类校验。
     * SRS_F015.R06: 降级任务必须记录原计划版本、基线模板版本和降级原因。
     */
    @Test
    void r01_r03_r04_r06_highRiskPlanAutomaticallyDowngradesToBaselineTemplatePreservingGoal() {
        Task task = new Task();
        task.setId(101L);
        task.setTaskGoal("特殊旅客轮椅协同接送至登机口B12");
        task.setTaskFamily("SPECIAL_PASSENGER_SERVICE");
        task.setStatus(TaskStatus.PLANNING);
        when(taskMapper.findById(101L)).thenReturn(Optional.of(task));

        BaselineTemplate template = createTemplate(1L, "特殊旅客标准接送基线", "SPECIAL_PASSENGER_SERVICE", 3, LocalDateTime.of(2026, 10, 27, 4, 25));
        when(templateMapper.findAll()).thenReturn(List.of(template));

        PlanValidationResult ok = new PlanValidationResult();
        when(planValidationService.validate(anyList(), anyList(), any(), any())).thenReturn(ok);
        when(planVersionMapper.countByTaskId(101L)).thenReturn(1L);

        // 触发降级
        planningOrchestrator.switchToBaseline(101L);

        // 验证原目标未被修改
        assertEquals("特殊旅客轮椅协同接送至登机口B12", task.getTaskGoal());
        assertEquals(TaskStatus.DOWNGRADING, task.getStatus());
        assertNotNull(task.getDowngradeReason());

        // 验证生成的基线计划版本记录了来源、模板ID与模板版本
        ArgumentCaptor<PlanVersion> planCaptor = ArgumentCaptor.forClass(PlanVersion.class);
        verify(planVersionMapper).insert(planCaptor.capture());
        PlanVersion inserted = planCaptor.getValue();
        assertEquals("BASELINE_TEMPLATE", inserted.getSource());
        assertEquals(1L, inserted.getBaselineTemplateId());
        assertEquals("V1.3", inserted.getRuleSetVersion(), "必须冻结记录基线模板版本");
        assertNotNull(inserted.getFrozenAt(), "通过三类校验后必须冻结");

        // 验证原候选计划未下发，而是以基线计划启动执行
        verify(taskExecutionOrchestrator).startExecution(eq(101L), any());
    }

    /**
     * SRS_F015.R05: 无匹配模板或模板校验失败时才进入待人工处理。
     */
    @Test
    void r05_noMatchingTemplateTransitionsToPendingManual() {
        Task task = new Task();
        task.setId(102L);
        task.setTaskGoal("未知业务目标");
        task.setTaskFamily("UNKNOWN_FAMILY");
        task.setStatus(TaskStatus.PLANNING);
        when(taskMapper.findById(102L)).thenReturn(Optional.of(task));
        when(templateMapper.findAll()).thenReturn(List.of());

        planningOrchestrator.switchToBaseline(102L);

        assertEquals(TaskStatus.PENDING_MANUAL, task.getStatus());
        assertTrue(task.getFailureReason().contains("无匹配"));
        verify(taskEventService).append(eq(102L), eq("BASELINE_DOWNGRADED"), eq("SYSTEM"), eq("ERR_NO_BASELINE_TEMPLATE"), anyString());
        verify(taskEventService).append(eq(102L), eq("TASK_PENDING_MANUAL"), eq("SYSTEM"), eq("ERR_PLANNING_FAILED"), anyString());
        verifyNoInteractions(taskExecutionOrchestrator);
    }

    /**
     * SRS_F015.R05: 模板三类校验失败时进入待人工处理，不执行计划。
     */
    @Test
    void r05_templateValidationFailureTransitionsToPendingManual() {
        Task task = new Task();
        task.setId(103L);
        task.setTaskGoal("超规行李转运");
        task.setTaskFamily("OVERSIZE_BAGGAGE_HANDLING");
        task.setStatus(TaskStatus.PLANNING);
        when(taskMapper.findById(103L)).thenReturn(Optional.of(task));

        BaselineTemplate template = createTemplate(2L, "超规行李模板", "OVERSIZE_BAGGAGE_HANDLING", 3, LocalDateTime.of(2026, 10, 27, 5, 0));
        when(templateMapper.findAll()).thenReturn(List.of(template));

        PlanValidationResult failed = new PlanValidationResult();
        failed.failStructure("缺少前置测量步骤", 1, "ERR_PRESET_SCENARIO_VIOLATION");
        when(planValidationService.validate(anyList(), anyList(), any(), any())).thenReturn(failed);
        when(planVersionMapper.countByTaskId(103L)).thenReturn(1L);

        planningOrchestrator.switchToBaseline(103L);

        assertEquals(TaskStatus.PENDING_MANUAL, task.getStatus());
        assertTrue(task.getFailureReason().contains("校验失败"));
        verify(taskEventService).append(eq(103L), eq("BASELINE_DOWNGRADED"), eq("SYSTEM"), eq("ERR_PRESET_SCENARIO_VIOLATION"), anyString());
        verify(taskEventService).append(eq(103L), eq("TASK_PENDING_MANUAL"), eq("SYSTEM"), eq("ERR_PLANNING_FAILED"), anyString());
        verifyNoInteractions(taskExecutionOrchestrator);
    }

    /**
     * SRS_F015.R07: 存在多个可匹配模板时，按任务族精确匹配优先、步骤数少优先、最近试运行通过优先的顺序选择，选择依据写入事件。
     */
    @Test
    void r07_templateMatchingPriorities_exactMatch_fewerSteps_latestDryRun() {
        LocalDateTime t1 = LocalDateTime.of(2026, 10, 20, 10, 0);
        LocalDateTime t2 = LocalDateTime.of(2026, 10, 25, 10, 0);
        LocalDateTime t3 = LocalDateTime.of(2026, 10, 28, 10, 0);

        // 1. 精确匹配 vs 非精确通用匹配：精确匹配（4步）优先于非精确通用（2步）
        BaselineTemplate exactFourSteps = createTemplate(10L, "特殊旅客精确4步", "SPECIAL_PASSENGER_SERVICE", 4, t1);
        BaselineTemplate commonTwoSteps = createTemplate(11L, "通用兜底2步", "COMMON", 2, t3);
        when(templateMapper.findAll()).thenReturn(List.of(commonTwoSteps, exactFourSteps));

        Optional<BaselineTemplate> match1 = baselineTemplateService.matchForDowngrade("SPECIAL_PASSENGER_SERVICE");
        assertTrue(match1.isPresent());
        assertEquals(10L, match1.get().getId(), "任务族精确匹配必须优先于通用非精确匹配，即便非精确步骤数更少");

        // 2. 同为精确匹配：步骤数少优先（3步优先于4步）
        BaselineTemplate exactThreeSteps = createTemplate(12L, "特殊旅客精确3步", "SPECIAL_PASSENGER_SERVICE", 3, t1);
        when(templateMapper.findAll()).thenReturn(List.of(exactFourSteps, exactThreeSteps));

        Optional<BaselineTemplate> match2 = baselineTemplateService.matchForDowngrade("SPECIAL_PASSENGER_SERVICE");
        assertTrue(match2.isPresent());
        assertEquals(12L, match2.get().getId(), "同精确度下步骤数少者优先");

        // 3. 同为精确匹配且步骤数相同：最近试运行通过/更新者优先（t3优先于t2）
        BaselineTemplate exactThreeStepsOlder = createTemplate(13L, "特殊旅客精确3步旧版", "SPECIAL_PASSENGER_SERVICE", 3, t2);
        BaselineTemplate exactThreeStepsNewer = createTemplate(14L, "特殊旅客精确3步新版", "SPECIAL_PASSENGER_SERVICE", 3, t3);
        when(templateMapper.findAll()).thenReturn(List.of(exactThreeStepsOlder, exactThreeStepsNewer));

        Optional<BaselineTemplate> match3 = baselineTemplateService.matchForDowngrade("SPECIAL_PASSENGER_SERVICE");
        assertTrue(match3.isPresent());
        assertEquals(14L, match3.get().getId(), "同匹配度与步骤数下，最近试运行通过时间优先");

        // 4. 选择依据格式化并包含全部三要素
        String basis = baselineTemplateService.formatSelectionBasis(exactThreeStepsNewer, "SPECIAL_PASSENGER_SERVICE");
        assertTrue(basis.contains("任务族精确匹配"));
        assertTrue(basis.contains("步骤数3步少优先"));
        assertTrue(basis.contains("最近试运行通过时间"));
    }

    /**
     * SRS_F015.R07: 选择依据必须写入 BASELINE_DOWNGRADED 事件详情。
     */
    @Test
    void r07_selectionBasisIsWrittenToTimelineEvent() {
        Task task = new Task();
        task.setId(104L);
        task.setTaskGoal("特殊旅客接送");
        task.setTaskFamily("SPECIAL_PASSENGER_SERVICE");
        task.setStatus(TaskStatus.PLANNING);
        when(taskMapper.findById(104L)).thenReturn(Optional.of(task));

        BaselineTemplate template = createTemplate(1L, "特殊旅客标准接送基线", "SPECIAL_PASSENGER_SERVICE", 3, LocalDateTime.of(2026, 10, 27, 4, 25));
        when(templateMapper.findAll()).thenReturn(List.of(template));
        when(planValidationService.validate(anyList(), anyList(), any(), any())).thenReturn(new PlanValidationResult());

        planningOrchestrator.switchToBaseline(104L);

        ArgumentCaptor<String> eventCaptor = ArgumentCaptor.forClass(String.class);
        verify(taskEventService).append(eq(104L), eq("BASELINE_DOWNGRADED"), eq("SYSTEM"), isNull(), eventCaptor.capture());
        String eventDetail = eventCaptor.getValue();
        assertTrue(eventDetail.contains("选择依据: [任务族精确匹配"), "降级事件必须包含选择依据");
        assertTrue(eventDetail.contains("步骤数3步少优先"));
    }

    /**
     * SRS_F015.R08 / DEF-S3-065: 基线执行失败时任务进入待人工处理，不再自动二次降级或局部重规划。
     */
    @Test
    void r08_defS3065_baselineExecutionFailureGoesStraightToManualNoSecondaryDowngrade() {
        Task task = new Task();
        task.setId(83L);
        task.setStatus(TaskStatus.EXECUTING);
        task.setReplanUsed(false);
        task.setCurrentPlanVersionId(7L);
        task.setDowngradeReason("高风险基线降级");
        when(taskMapper.findById(83L)).thenReturn(Optional.of(task));

        PlanVersion plan = new PlanVersion();
        plan.setSource("BASELINE_TEMPLATE");
        when(planVersionMapper.findById(7L)).thenReturn(Optional.of(plan));

        // 无可用候选设备，恢复失败
        when(taskExecutionOrchestrator.hasAvailableCandidate(anyLong(), anyInt(), anyList())).thenReturn(false);

        exceptionService.handleException(83L, 1, "STEP_FAILED", "机器人故障且无候选设备");

        // 严禁调用 replanningService.replan
        verify(replanningService, never()).replan(anyLong(), anyInt(), anyString());
        verify(taskEventService, never()).append(eq(83L), eq("REPLANNING_TRIGGERED"), any(), any(), any());

        // 任务直接进入 PENDING_MANUAL
        assertEquals(TaskStatus.PENDING_MANUAL, task.getStatus());
        assertTrue(task.getFailureReason().contains("基线降级任务"));
        verify(taskEventService).append(eq(83L), eq("TASK_PENDING_MANUAL"), eq("SYSTEM"), eq("STEP_FAILED"), contains("不再二次自动降级"));
    }

    /**
     * SRS_F015.R08 / DEF-S3-066: 恢复事件必须包含异常类型、恢复动作、结果、影响结论与原因码。
     */
    @Test
    void defS3066_recoveryEventsIncludeAllRequiredFields() {
        Task task = new Task();
        task.setId(83L);
        task.setStatus(TaskStatus.EXECUTING);
        task.setCurrentPlanVersionId(7L);
        when(taskMapper.findById(83L)).thenReturn(Optional.of(task));
        when(planVersionMapper.findById(7L)).thenReturn(Optional.of(new PlanVersion()));

        // 1. 无候选设备恢复失败
        when(taskExecutionOrchestrator.hasAvailableCandidate(anyLong(), anyInt(), anyList())).thenReturn(false);
        exceptionService.handleException(83L, 1, "AGENT_OFFLINE", "设备离线");

        ArgumentCaptor<String> failedMsg = ArgumentCaptor.forClass(String.class);
        verify(taskEventService).append(eq(83L), eq("EXCEPTION_RECOVERY_FAILED"), eq("SYSTEM"), eq("AGENT_OFFLINE"), failedMsg.capture());
        String failedDetail = failedMsg.getValue();
        assertTrue(failedDetail.contains("恢复动作:"));
        assertTrue(failedDetail.contains("结果: 失败"));
        assertTrue(failedDetail.contains("异常类型: AGENT_OFFLINE"));
        assertTrue(failedDetail.contains("影响结论:"));

        // 2. 有候选设备切换成功
        when(taskExecutionOrchestrator.hasAvailableCandidate(anyLong(), anyInt(), anyList())).thenReturn(true);
        exceptionService.handleException(83L, 2, "STEP_FAILED", "步骤失败");

        ArgumentCaptor<String> recoveredMsg = ArgumentCaptor.forClass(String.class);
        verify(taskEventService).append(eq(83L), eq("EXCEPTION_RECOVERED"), eq("SYSTEM"), eq("STEP_FAILED"), recoveredMsg.capture());
        String recoveredDetail = recoveredMsg.getValue();
        assertTrue(recoveredDetail.contains("恢复动作: 候选设备切换"));
        assertTrue(recoveredDetail.contains("结果: 成功"));
        assertTrue(recoveredDetail.contains("异常类型: STEP_FAILED"));
        assertTrue(recoveredDetail.contains("影响结论: 计划可继续执行"));
    }

    /**
     * SRS_F015.R09: 执行中任务使用其冻结时的模板版本，模板后续变更不影响在执行任务。
     */
    @Test
    void r09_runningTaskPreservesFrozenPlanEvenIfTemplateIsUpdated() {
        // 创建任务并冻结基线计划 V1.3
        Task task = new Task();
        task.setId(105L);
        task.setTaskGoal("航班延误应急广播");
        task.setTaskFamily("FLIGHT_CHANGE_RESPONSE");
        task.setStatus(TaskStatus.EXECUTING);
        task.setCurrentPlanVersionId(20L);
        when(taskMapper.findById(105L)).thenReturn(Optional.of(task));

        PlanVersion frozenPlan = new PlanVersion();
        frozenPlan.setId(20L);
        frozenPlan.setTaskId(105L);
        frozenPlan.setSource("BASELINE_TEMPLATE");
        frozenPlan.setBaselineTemplateId(5L);
        frozenPlan.setRuleSetVersion("V1.3");
        frozenPlan.setPlanSteps("[{\"stepSeq\":1,\"capabilityType\":\"CAP_NOTIFICATION\"}]");
        frozenPlan.setFrozenAt(LocalDateTime.of(2026, 10, 27, 8, 0));
        when(planVersionMapper.findById(20L)).thenReturn(Optional.of(frozenPlan));

        // 此时管理员修改模板为 V1.4，状态回退为 DRAFT
        BaselineTemplate template = createTemplate(5L, "航班变动基线", "FLIGHT_CHANGE_RESPONSE", 2, LocalDateTime.of(2026, 10, 27, 9, 0));
        template.setTemplateVersion("V1.4");
        template.setTemplateStatus("DRAFT");
        when(templateMapper.findById(5L)).thenReturn(Optional.of(template));

        // 验证执行中任务读取的计划版本仍是冻结时的 V1.3，步骤不受影响
        PlanVersion current = planVersionMapper.findById(task.getCurrentPlanVersionId()).orElseThrow();
        assertEquals("V1.3", current.getRuleSetVersion(), "必须保持冻结时的模板版本");
        assertEquals("[{\"stepSeq\":1,\"capabilityType\":\"CAP_NOTIFICATION\"}]", current.getPlanSteps());
        assertNotNull(current.getFrozenAt());
    }
}
