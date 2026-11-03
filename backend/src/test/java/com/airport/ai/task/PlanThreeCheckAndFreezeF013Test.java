package com.airport.ai.task;

import com.airport.ai.auth.OperationLogService;
import com.airport.ai.auth.User;
import com.airport.ai.common.BusinessException;
import com.airport.ai.common.ErrorCode;
import com.airport.ai.device.DeviceAgentMapper;
import com.airport.ai.device.DeviceAgentMessagingService;
import com.airport.ai.device.DeviceCapabilityMapper;
import com.airport.ai.event.TaskEventService;
import com.airport.ai.planning.GoalUnderstandingService;
import com.airport.ai.taskdef.TaskDefinitionService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.*;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * 针对 SRS_F013 计划三类校验与冻结机制（TC-039~TC-042、R01~R09）的完备单测与硬闸门验证：
 * 1. 结构校验：六项必需字段、五步上限、依赖顺序与自依赖、循环与动态代码、无限轮次协商（R01）
 * 2. 能力校验：能力存在性与启用状态、在线候选代理、设备类型能力边界约束（R02）
 * 3. 约束校验：参数合法性、运动安全控制字段拦截、任务定义可用能力限制、核心场景渠道覆盖与顺序（R03）
 * 4. 执行闸门：任一不通过不得进入执行（R04）
 * 5. 顺序执行与错误汇总：三类校验依次执行，前序失败仍收集后续错误并整体拒绝（R05）
 * 6. 处置分支：修改目标重试、转模板降级、置为失败（R06）
 * 7. 硬性拦截：硬性校验失败严禁进入监督判定，严禁人工或监督强行放行，违规放行记录拦截（R07）
 * 8. 冻结机制：三类全部通过后冻结版本，冻结后不可修改，仅局部重规划生成新版本（R08）
 * 9. 事件时间线：校验结果、错误清单与原因码写入任务事件时间线（R09）
 */
class PlanThreeCheckAndFreezeF013Test {

    private DeviceCapabilityMapper capabilities;
    private PlanValidationService validationService;

    @BeforeEach
    void setUp() {
        capabilities = mock(DeviceCapabilityMapper.class);
        when(capabilities.existsByCapabilityTypeAndCapabilityStatus(anyString(), eq("ENABLED"))).thenReturn(true);
        validationService = new PlanValidationService(capabilities);
    }

    private Map<String, Object> standardStep(int seq, String capability) {
        Map<String, Object> step = new LinkedHashMap<>();
        step.put("stepSeq", seq);
        step.put("stepGoal", "执行能力 " + capability);
        step.put("capabilityType", capability);
        step.put("inputParams", new LinkedHashMap<>(Map.of("target", "GATE_A")));
        step.put("precondition", "候选设备在线且空闲");
        step.put("completionCondition", "status=DONE");
        step.put("failureHandling", "重试一次或转人工处理");
        return step;
    }

    private List<Map<String, Object>> standardAgents() {
        return List.of(
                Map.of("agentId", "AGT-DISPLAY", "capabilities", List.of("CAP_INFO_DISPLAY", "CAP_FLIGHT_UPDATE"),
                        "onlineStatus", "ONLINE", "workload", "IDLE", "deviceTypeCode", "SIMULATOR",
                        "simulatedDeviceType", "SMART_DISPLAY", "location", Map.of()),
                Map.of("agentId", "AGT-ROBOT", "capabilities", List.of("CAP_NAVIGATION", "CAP_NOTIFICATION", "CAP_ESCORT"),
                        "onlineStatus", "ONLINE", "workload", "IDLE", "deviceTypeCode", "SIMULATOR",
                        "simulatedDeviceType", "MOBILE_ROBOT", "location", Map.of()),
                Map.of("agentId", "AGT-MEASURE", "capabilities", List.of("CAP_BAGGAGE_MEASURE", "CAP_OVERSIZE_ALERT"),
                        "onlineStatus", "ONLINE", "workload", "IDLE", "deviceTypeCode", "SIMULATOR",
                        "simulatedDeviceType", "BAGGAGE_SCANNER", "location", Map.of())
        );
    }

    // ==========================================
    // R01: 结构校验（完整字段、依赖顺序、循环与无限协商）
    // ==========================================

    @Test
    void r01_validFiveStepPlanPassesStructure() {
        List<Map<String, Object>> steps = List.of(
                standardStep(1, "CAP_INFO_DISPLAY"),
                standardStep(2, "CAP_NAVIGATION"),
                standardStep(3, "CAP_NOTIFICATION"),
                standardStep(4, "CAP_INFO_DISPLAY"),
                standardStep(5, "CAP_NAVIGATION")
        );
        PlanValidationResult result = validationService.validate(steps, standardAgents());
        assertTrue(result.isAllPassed());
        assertEquals("PASS", result.getStructureCheckResult());
    }

    @Test
    void r01_exceedingFiveStepsRejectsWithoutTruncating() {
        List<Map<String, Object>> steps = List.of(
                standardStep(1, "CAP_INFO_DISPLAY"),
                standardStep(2, "CAP_NAVIGATION"),
                standardStep(3, "CAP_NOTIFICATION"),
                standardStep(4, "CAP_INFO_DISPLAY"),
                standardStep(5, "CAP_NAVIGATION"),
                standardStep(6, "CAP_NOTIFICATION")
        );
        PlanValidationResult result = validationService.validate(steps, standardAgents());
        assertFalse(result.isAllPassed());
        assertEquals("FAIL", result.getStructureCheckResult());
        assertTrue(result.getErrors().stream().anyMatch(e -> "ERR_STEP_LIMIT_EXCEEDED".equals(e.getReasonCode())));
    }

    @Test
    void r01_missingAnyOfSixFieldsRejects() {
        for (String field : List.of("stepGoal", "capabilityType", "precondition", "completionCondition", "failureHandling")) {
            Map<String, Object> bad = standardStep(1, "CAP_INFO_DISPLAY");
            bad.remove(field);
            PlanValidationResult result = validationService.validate(List.of(bad), standardAgents());
            assertFalse(result.isAllPassed());
            assertEquals("FAIL", result.getStructureCheckResult());
            assertTrue(result.getErrors().stream().anyMatch(e -> "ERR_STEP_FIELD_MISSING".equals(e.getReasonCode())));
        }
    }

    @Test
    void r01_forwardAndSelfDependenciesInPreconditionAreRejected() {
        // 自依赖：步骤1依赖步骤1
        Map<String, Object> step1Self = standardStep(1, "CAP_INFO_DISPLAY");
        step1Self.put("precondition", "依赖步骤1完成后方可执行");
        PlanValidationResult r1 = validationService.validate(List.of(step1Self), standardAgents());
        assertFalse(r1.isAllPassed());
        assertTrue(r1.getErrors().stream().anyMatch(e -> "ERR_STEP_DEPENDENCY_ORDER".equals(e.getReasonCode())));

        // 前向依赖：步骤1依赖步骤2
        Map<String, Object> step1Forward = standardStep(1, "CAP_INFO_DISPLAY");
        step1Forward.put("precondition", "前置步骤 2 完成后执行");
        Map<String, Object> step2 = standardStep(2, "CAP_NAVIGATION");
        PlanValidationResult r2 = validationService.validate(List.of(step1Forward, step2), standardAgents());
        assertFalse(r2.isAllPassed());
        assertTrue(r2.getErrors().stream().anyMatch(e -> "ERR_STEP_DEPENDENCY_ORDER".equals(e.getReasonCode())));

        // 依赖不存在的步骤
        Map<String, Object> step2NonExistent = standardStep(2, "CAP_NAVIGATION");
        step2NonExistent.put("precondition", "依赖步骤 99 完成");
        PlanValidationResult r3 = validationService.validate(List.of(standardStep(1, "CAP_INFO_DISPLAY"), step2NonExistent), standardAgents());
        assertFalse(r3.isAllPassed());
        assertTrue(r3.getErrors().stream().anyMatch(e -> "ERR_STEP_DEPENDENCY_ORDER".equals(e.getReasonCode())));

        // 合法前置依赖：步骤2依赖步骤1
        Map<String, Object> step2Valid = standardStep(2, "CAP_NAVIGATION");
        step2Valid.put("precondition", "步骤1完成后才可执行");
        PlanValidationResult r4 = validationService.validate(List.of(standardStep(1, "CAP_INFO_DISPLAY"), step2Valid), standardAgents());
        assertTrue(r4.isAllPassed());
    }

    @Test
    void r01_loopAndDynamicCodeAndInfiniteNegotiationAreRejected() {
        List<String> badTexts = List.of(
                "while(true) { repeat this display; }",
                "for(int i=0; ; i++) { display(); }",
                "do { update(); } while(flag);",
                "eval(dynamic_code)",
                "exec(script)",
                "repeat forever",
                "repeat indefinitely",
                "死循环直到成功为止",
                "无限轮次协商设备占用",
                "无限协商直至满意",
                "unlimited negotiation with agent",
                "动态生成代码并执行"
        );

        for (String bad : badTexts) {
            Map<String, Object> step = standardStep(1, "CAP_INFO_DISPLAY");
            step.put("stepGoal", bad);
            PlanValidationResult r = validationService.validate(List.of(step), standardAgents());
            assertFalse(r.isAllPassed(), "应拦截: " + bad);
            assertTrue(r.getErrors().stream().anyMatch(e -> "ERR_STEP_LOOP_DETECTED".equals(e.getReasonCode())),
                    "未命中 ERR_STEP_LOOP_DETECTED: " + bad);
        }

        // inputParams 内部递归检测
        Map<String, Object> stepWithParamLoop = standardStep(1, "CAP_INFO_DISPLAY");
        stepWithParamLoop.put("inputParams", Map.of("loopConfig", Map.of("mode", "while(true)")));
        PlanValidationResult rParam = validationService.validate(List.of(stepWithParamLoop), standardAgents());
        assertFalse(rParam.isAllPassed());
        assertTrue(rParam.getErrors().stream().anyMatch(e -> "ERR_STEP_LOOP_DETECTED".equals(e.getReasonCode())));

        // 正常有限业务重试文字不被误伤
        Map<String, Object> normalStep = standardStep(1, "CAP_INFO_DISPLAY");
        normalStep.put("failureHandling", "最多重试2次或转人工处理");
        normalStep.put("precondition", "等待设备就绪后展示，展示直到完成条件满足");
        PlanValidationResult rNormal = validationService.validate(List.of(normalStep), standardAgents());
        assertTrue(rNormal.isAllPassed(), "正常有限业务描述不应误伤");
    }

    // ==========================================
    // R02: 能力校验（存在性、已启用、在线候选代理、边界约束）
    // ==========================================

    @Test
    void r02_unknownOrDisabledCapabilityRejectsWithGap() {
        when(capabilities.existsByCapabilityTypeAndCapabilityStatus("CAP_UNKNOWN_TEST", "ENABLED")).thenReturn(false);
        Map<String, Object> step = standardStep(1, "CAP_UNKNOWN_TEST");
        PlanValidationResult result = validationService.validate(List.of(step), standardAgents());
        assertFalse(result.isAllPassed());
        assertEquals("FAIL", result.getCapabilityCheckResult());
        assertTrue(result.getErrors().stream().anyMatch(e -> "ERR_CAPABILITY_GAP".equals(e.getReasonCode())));
    }

    @Test
    void r02_noOnlineCandidateAgentRejects() {
        // AGT-DISPLAY 离线
        List<Map<String, Object>> offlineAgents = List.of(
                Map.of("agentId", "AGT-DISPLAY", "capabilities", List.of("CAP_INFO_DISPLAY"),
                        "onlineStatus", "OFFLINE", "workload", "IDLE", "deviceTypeCode", "SIMULATOR",
                        "simulatedDeviceType", "SMART_DISPLAY", "location", Map.of())
        );
        Map<String, Object> step = standardStep(1, "CAP_INFO_DISPLAY");
        PlanValidationResult result = validationService.validate(List.of(step), offlineAgents);
        assertFalse(result.isAllPassed());
        assertEquals("FAIL", result.getCapabilityCheckResult());
        assertTrue(result.getErrors().stream().anyMatch(e -> "ERR_NO_ONLINE_CANDIDATE".equals(e.getReasonCode())));
    }

    @Test
    void r02_channelMismatchFilteredOutLeadingToNoCandidate() {
        // 代理虽声明 CAP_INFO_DISPLAY，但设备类型为 MOBILE_ROBOT，不符合 SMART_DISPLAY 渠道
        List<Map<String, Object>> mismatchedAgents = List.of(
                Map.of("agentId", "AGT-ROBOT", "capabilities", List.of("CAP_INFO_DISPLAY"),
                        "onlineStatus", "ONLINE", "workload", "IDLE", "deviceTypeCode", "SIMULATOR",
                        "simulatedDeviceType", "MOBILE_ROBOT", "location", Map.of())
        );
        Map<String, Object> step = standardStep(1, "CAP_INFO_DISPLAY");
        PlanValidationResult result = validationService.validate(List.of(step), mismatchedAgents, null, "OVERSIZE_BAGGAGE_HANDLING");
        assertFalse(result.isAllPassed());
        assertTrue(result.getErrors().stream().anyMatch(e -> "ERR_NO_ONLINE_CANDIDATE".equals(e.getReasonCode())));
    }

    // ==========================================
    // R03: 约束校验（运动安全、任务定义范围、核心场景渠道与顺序）
    // ==========================================

    @Test
    void r03_motionSafetyFieldsAreStrictlyRejected() {
        List<String> motionKeywords = List.of("速度", "加速度", "姿态", "路径点", "避障", "急停", "限速", "失联停靠",
                "speed", "velocity", "acceleration", "waypoint", "emergency stop", "estop");
        for (String kw : motionKeywords) {
            Map<String, Object> step = standardStep(1, "CAP_NAVIGATION");
            step.put("inputParams", Map.of("command", "navigate", "safetyControl", kw));
            PlanValidationResult result = validationService.validate(List.of(step), standardAgents());
            assertFalse(result.isAllPassed());
            assertEquals("FAIL", result.getConstraintCheckResult());
            assertTrue(result.getErrors().stream().anyMatch(e -> "ERR_MOTION_SAFETY_FIELD".equals(e.getReasonCode())),
                    "未拦截运动安全关键词: " + kw);
        }
    }

    @Test
    void r03_capabilityNotInTaskDefinitionRejects() {
        Map<String, Object> step = standardStep(1, "CAP_ESCORT");
        List<String> allowedTypes = List.of("CAP_INFO_DISPLAY", "CAP_NAVIGATION");
        PlanValidationResult result = validationService.validate(List.of(step), standardAgents(), allowedTypes);
        assertFalse(result.isAllPassed());
        assertEquals("FAIL", result.getConstraintCheckResult());
        assertTrue(result.getErrors().stream().anyMatch(e -> "ERR_CAPABILITY_NOT_IN_TASK_DEFINITION".equals(e.getReasonCode())));
    }

    @Test
    void r03_oversizeBaggageScenarioRequiresMeasureBeforeAlert() {
        // 超规场景：报警早于测量 -> 违反步骤时序约束
        List<Map<String, Object>> invertedSteps = List.of(
                standardStep(1, "CAP_OVERSIZE_ALERT"),
                standardStep(2, "CAP_BAGGAGE_MEASURE"),
                standardStep(3, "CAP_INFO_DISPLAY"),
                standardStep(4, "CAP_NAVIGATION")
        );
        PlanValidationResult result = validationService.validate(invertedSteps, standardAgents(),
                List.of("CAP_BAGGAGE_MEASURE", "CAP_OVERSIZE_ALERT", "CAP_INFO_DISPLAY", "CAP_NAVIGATION"),
                "OVERSIZE_BAGGAGE_HANDLING");
        validationService.requireCoreScenarioCoverage(invertedSteps, "OVERSIZE_BAGGAGE_HANDLING", result);
        assertFalse(result.isAllPassed());
        assertTrue(result.getErrors().stream().anyMatch(e -> "ERR_BAGGAGE_BRANCH_ORDER".equals(e.getReasonCode())));
    }

    @Test
    void r03_resourceConflictWhenCandidateIsOccupied_rejectsWithErrResourceConflict() {
        // DEF-S3-092 / TC-039.S2 / TC-041.S2：唯一候选机器人在线但已被任务143占用（BUSY）
        List<Map<String, Object>> busyAgents = List.of(
                Map.of("agentId", "AGT-803437A3", "capabilities", List.of("CAP_NAVIGATION"),
                        "onlineStatus", "ONLINE", "workload", "BUSY", "currentTaskId", 143L,
                        "deviceTypeCode", "SIMULATOR", "simulatedDeviceType", "MOBILE_ROBOT",
                        "location", Map.of())
        );
        Map<String, Object> step = standardStep(1, "CAP_NAVIGATION");
        // 竞争任务 144
        PlanValidationResult result = validationService.validate(List.of(step), busyAgents, null,
                "EXT_2AD8B934", 0, 144L);
        assertFalse(result.isAllPassed());
        assertEquals("PASS", result.getStructureCheckResult());
        assertEquals("PASS", result.getCapabilityCheckResult());
        assertEquals("FAIL", result.getConstraintCheckResult());
        assertTrue(result.getErrors().stream().anyMatch(e -> "ERR_RESOURCE_CONFLICT".equals(e.getReasonCode())),
                "必须拦截资源冲突 ERR_RESOURCE_CONFLICT: " + result.getErrors());
    }

    @Test
    void r03_resourceConflictPassesWhenIdleCandidateExists() {
        // 一台被占用，但存在另一台空闲候选设备 -> 校验放行给软风险规则
        List<Map<String, Object>> mixedAgents = List.of(
                Map.of("agentId", "AGT-BUSY", "capabilities", List.of("CAP_NAVIGATION"),
                        "onlineStatus", "ONLINE", "workload", "BUSY", "currentTaskId", 143L,
                        "deviceTypeCode", "SIMULATOR", "simulatedDeviceType", "MOBILE_ROBOT",
                        "location", Map.of()),
                Map.of("agentId", "AGT-IDLE", "capabilities", List.of("CAP_NAVIGATION"),
                        "onlineStatus", "ONLINE", "workload", "IDLE",
                        "deviceTypeCode", "SIMULATOR", "simulatedDeviceType", "MOBILE_ROBOT",
                        "location", Map.of())
        );
        Map<String, Object> step = standardStep(1, "CAP_NAVIGATION");
        PlanValidationResult result = validationService.validate(List.of(step), mixedAgents, null,
                "EXT_2AD8B934", 0, 144L);
        assertTrue(result.isAllPassed());
        assertEquals("PASS", result.getConstraintCheckResult());
    }

    // ----------------------------------------------------
    // DEF-S3-094: 步骤完成条件与任务期望完成条件一致性与反向矛盾硬校验
    // ----------------------------------------------------

    @Test
    void r03_completionConditionContradictionRejectsWithErrCompletionConditionConflict() {
        // DEF-S3-094 / TC-039.S2 / TC-041.S2 / R03:
        // 任务目标/定义明确要求 routeGenerated=true，候选唯一导航步骤完成条件却为 routeGenerated=false
        Map<String, Object> step = standardStep(1, "CAP_NAVIGATION");
        step.put("completionCondition", "routeGenerated=false");

        PlanValidationResult result = validationService.validate(List.of(step), standardAgents(),
                List.of("CAP_NAVIGATION"), "EXT_FAMILY", 155L, "routeGenerated=true");

        assertFalse(result.isAllPassed(), "完成条件直接反向矛盾必须判定三类校验未通过");
        assertEquals("PASS", result.getStructureCheckResult(), "结构校验应PASS");
        assertEquals("PASS", result.getCapabilityCheckResult(), "能力校验应PASS");
        assertEquals("FAIL", result.getConstraintCheckResult(), "约束校验必须FAIL");
        assertTrue(result.getErrors().stream().anyMatch(e -> "ERR_COMPLETION_CONDITION_CONFLICT".equals(e.getReasonCode())),
                "必须包含 ERR_COMPLETION_CONDITION_CONFLICT 原因码: " + result.getErrors());
        assertTrue(result.getErrors().stream().anyMatch(e -> e.getDescription().contains("routegenerated")),
                "错误描述应指明冲突的字段: " + result.getErrors());
    }

    @Test
    void r03_completionConditionConsistentPasses() {
        // 正例：任务目标要求 routeGenerated=true，候选唯一步骤完成条件 routeGenerated=true
        Map<String, Object> step = standardStep(1, "CAP_NAVIGATION");
        step.put("completionCondition", "routeGenerated=true");

        PlanValidationResult result = validationService.validate(List.of(step), standardAgents(),
                List.of("CAP_NAVIGATION"), "EXT_FAMILY", 155L, "routeGenerated=true");

        assertTrue(result.isAllPassed());
        assertEquals("PASS", result.getConstraintCheckResult());
        assertTrue(result.getErrors().isEmpty());
    }

    @Test
    void r03_multiStepIntermediateConditionsPasses() {
        // 多步合法时序：中间步骤完成条件不冲突，最终步骤达成任务期望条件
        Map<String, Object> step1 = standardStep(1, "CAP_INFO_DISPLAY");
        step1.put("completionCondition", "infoDisplayed=true");
        Map<String, Object> step2 = standardStep(2, "CAP_NAVIGATION");
        step2.put("completionCondition", "routeGenerated=true");

        PlanValidationResult result = validationService.validate(List.of(step1, step2), standardAgents(),
                List.of("CAP_INFO_DISPLAY", "CAP_NAVIGATION"), "EXT_FAMILY", 155L, "routeGenerated=true");

        assertTrue(result.isAllPassed(), "多步合法时序且中间步骤不冲突应正常通过校验");
        assertEquals("PASS", result.getConstraintCheckResult());
    }

    @Test
    void r03_multiStepContradictionInAnyStepRejects() {
        // 多步计划中任一步骤显式声明了与任务目标相反的反向矛盾断言，必须硬拦截
        Map<String, Object> step1 = standardStep(1, "CAP_INFO_DISPLAY");
        step1.put("completionCondition", "routeGenerated=false"); // 显式反向矛盾
        Map<String, Object> step2 = standardStep(2, "CAP_NAVIGATION");
        step2.put("completionCondition", "routeGenerated=true");

        PlanValidationResult result = validationService.validate(List.of(step1, step2), standardAgents(),
                List.of("CAP_INFO_DISPLAY", "CAP_NAVIGATION"), "EXT_FAMILY", 155L, "routeGenerated=true");

        assertFalse(result.isAllPassed());
        assertEquals("FAIL", result.getConstraintCheckResult());
        assertTrue(result.getErrors().stream().anyMatch(e -> "ERR_COMPLETION_CONDITION_CONFLICT".equals(e.getReasonCode())));
    }

    @Test
    void r03_naturalLanguageUnderstandingDoesNotOverrideStructuredTaskDefinition() {
        // DEF-S3-094 (V1.146实机绕过反例):
        // 任务定义要求 routeGenerated=true，目标理解模型返回自然语言 "The navigation route has been generated."
        // 两者合并保留为 "routeGenerated=true; The navigation route has been generated."
        // 唯一步骤若声明 routeGenerated=false，仍必须硬拦截拒绝！
        String combinedCondition = "routeGenerated=true; The navigation route has been generated.";
        Map<String, Object> stepContradict = standardStep(1, "CAP_NAVIGATION");
        stepContradict.put("completionCondition", "routeGenerated=false");

        PlanValidationResult resultFail = validationService.validate(List.of(stepContradict), standardAgents(),
                List.of("CAP_NAVIGATION"), "EXT_FAMILY", 162L, combinedCondition);

        assertFalse(resultFail.isAllPassed(), "自然语言理解绝不能覆盖结构化任务定义硬约束");
        assertEquals("FAIL", resultFail.getConstraintCheckResult());
        assertTrue(resultFail.getErrors().stream().anyMatch(e -> "ERR_COMPLETION_CONDITION_CONFLICT".equals(e.getReasonCode())));

        // 正例：候选步骤声明 routeGenerated=true，正常放行
        Map<String, Object> stepPass = standardStep(1, "CAP_NAVIGATION");
        stepPass.put("completionCondition", "routeGenerated=true");

        PlanValidationResult resultPass = validationService.validate(List.of(stepPass), standardAgents(),
                List.of("CAP_NAVIGATION"), "EXT_FAMILY", 162L, combinedCondition);

        assertTrue(resultPass.isAllPassed(), "候选步骤满足结构化任务定义与自然语言理解时应正常通过");
        assertEquals("PASS", resultPass.getConstraintCheckResult());
    }

    @Test
    void r03_modelConflictingAssertionDoesNotOverwriteTaskDefinition() {
        // DEF-S3-094 (V1.147任务172实机复现):
        // 任务定义要求 routeGenerated=true，模型理解返回相反的结构化断言 routeGenerated=false。
        // 即使模型企图反转同名字段，任务定义硬条件依然权威锁定并生效，
        // 唯一候选步骤声明 routeGenerated=false 必须在约束校验硬拒绝，绝不得因同名键覆盖而放行！
        String multiSourceConditions = "routeGenerated=true; routeGenerated=false";
        Map<String, Object> stepContradict = standardStep(1, "CAP_NAVIGATION");
        stepContradict.put("completionCondition", "routeGenerated=false");

        PlanValidationResult resultFail = validationService.validate(List.of(stepContradict), standardAgents(),
                List.of("CAP_NAVIGATION"), "EXT_FAMILY", 172L, multiSourceConditions);

        assertFalse(resultFail.isAllPassed(), "模型返回相反断言绝不能覆盖任务定义中的权威true");
        assertEquals("FAIL", resultFail.getConstraintCheckResult());
        assertTrue(resultFail.getErrors().stream().anyMatch(e -> "ERR_COMPLETION_CONDITION_CONFLICT".equals(e.getReasonCode())));

        // 正例：候选步骤满足任务定义的 routeGenerated=true，正常放行
        Map<String, Object> stepPass = standardStep(1, "CAP_NAVIGATION");
        stepPass.put("completionCondition", "routeGenerated=true");

        PlanValidationResult resultPass = validationService.validate(List.of(stepPass), standardAgents(),
                List.of("CAP_NAVIGATION"), "EXT_FAMILY", 172L, multiSourceConditions);

        assertTrue(resultPass.isAllPassed(), "候选步骤满足任务定义期望条件应正常通过");
        assertEquals("PASS", resultPass.getConstraintCheckResult());
    }

    @Test
    void r03_candidateStepInternalContradictoryConditionRejects() {
        // DEF-S3-094 (V1.148任务183实机复现):
        // 候选唯一步骤声明 routeGenerated=true and routeGenerated=false，
        // 同一候选步骤内部直接相反的合取条件必须在约束校验硬拦截，绝不能因首值优先而忽略后面的反向断言！
        Map<String, Object> stepContradict1 = standardStep(1, "CAP_NAVIGATION");
        stepContradict1.put("completionCondition", "routeGenerated=true and routeGenerated=false");

        PlanValidationResult resultFail1 = validationService.validate(List.of(stepContradict1), standardAgents(),
                List.of("CAP_NAVIGATION"), "EXT_FAMILY", 183L, "routeGenerated=true");

        assertFalse(resultFail1.isAllPassed(), "候选步骤自身布尔合取自相矛盾必须硬拒绝");
        assertEquals("FAIL", resultFail1.getConstraintCheckResult());
        assertTrue(resultFail1.getErrors().stream().anyMatch(e -> "ERR_COMPLETION_CONDITION_CONFLICT".equals(e.getReasonCode())),
                "必须包含 ERR_COMPLETION_CONDITION_CONFLICT 原因码: " + resultFail1.getErrors());

        // 反向顺序同样必须硬拒绝：routeGenerated=false and routeGenerated=true
        Map<String, Object> stepContradict2 = standardStep(1, "CAP_NAVIGATION");
        stepContradict2.put("completionCondition", "routeGenerated=false and routeGenerated=true");

        PlanValidationResult resultFail2 = validationService.validate(List.of(stepContradict2), standardAgents(),
                List.of("CAP_NAVIGATION"), "EXT_FAMILY", 183L, "routeGenerated=true");

        assertFalse(resultFail2.isAllPassed(), "反向顺序的自相矛盾条件同样必须硬拒绝");
        assertEquals("FAIL", resultFail2.getConstraintCheckResult());
        assertTrue(resultFail2.getErrors().stream().anyMatch(e -> "ERR_COMPLETION_CONDITION_CONFLICT".equals(e.getReasonCode())));

        // 无显式期望条件时，候选步骤内部自相矛盾同样必须硬拒绝
        Map<String, Object> stepContradict3 = standardStep(1, "CAP_NAVIGATION");
        stepContradict3.put("completionCondition", "routeGenerated=true and routeGenerated=false");
        PlanValidationResult resultFail3 = validationService.validate(List.of(stepContradict3), standardAgents(),
                List.of("CAP_NAVIGATION"), "EXT_FAMILY", 183L, null);
        assertFalse(resultFail3.isAllPassed(), "即使任务无期望条件，步骤自身自相矛盾也必须硬拦截");
        assertEquals("FAIL", resultFail3.getConstraintCheckResult());

        // 正例 1：合法同值重复 routeGenerated=true and routeGenerated=true 应正常放行
        Map<String, Object> stepRepeatPass = standardStep(1, "CAP_NAVIGATION");
        stepRepeatPass.put("completionCondition", "routeGenerated=true and routeGenerated=true");

        PlanValidationResult resultPass1 = validationService.validate(List.of(stepRepeatPass), standardAgents(),
                List.of("CAP_NAVIGATION"), "EXT_FAMILY", 183L, "routeGenerated=true");
        assertTrue(resultPass1.isAllPassed(), "合法重复相同布尔断言应正常放行");
        assertEquals("PASS", resultPass1.getConstraintCheckResult());

        // 正例 2：合法合取 routeGenerated=true and waypointCount>0（任务176场景）应正常放行
        Map<String, Object> stepConjunctivePass = standardStep(1, "CAP_NAVIGATION");
        stepConjunctivePass.put("completionCondition", "routeGenerated=true and waypointCount>0");

        PlanValidationResult resultPass2 = validationService.validate(List.of(stepConjunctivePass), standardAgents(),
                List.of("CAP_NAVIGATION"), "EXT_FAMILY", 183L, "routeGenerated=true");
        assertTrue(resultPass2.isAllPassed(), "合法合取断言应正常放行");
        assertEquals("PASS", resultPass2.getConstraintCheckResult());
    }

    @Test
    void r03_sameTaskCanReuseItsOwnOccupiedAgentDuringReplanning() {
        // 当前任务自身（taskId=143）占用的代理，在重规划时不属于外部资源冲突
        List<Map<String, Object>> selfOccupiedAgents = List.of(
                Map.of("agentId", "AGT-803437A3", "capabilities", List.of("CAP_NAVIGATION"),
                        "onlineStatus", "ONLINE", "workload", "BUSY", "currentTaskId", 143L,
                        "deviceTypeCode", "SIMULATOR", "simulatedDeviceType", "MOBILE_ROBOT",
                        "location", Map.of())
        );
        Map<String, Object> step = standardStep(1, "CAP_NAVIGATION");
        PlanValidationResult result = validationService.validate(List.of(step), selfOccupiedAgents, null,
                "EXT_2AD8B934", 0, 143L);
        assertTrue(result.isAllPassed());
        assertEquals("PASS", result.getConstraintCheckResult());
    }

    // ==========================================
    // R05: 三类校验顺序执行并汇总错误
    // ==========================================

    @Test
    void r05_allThreeCategoriesExecuteAndAggregateErrors() {
        when(capabilities.existsByCapabilityTypeAndCapabilityStatus("CAP_UNKNOWN_TEST", "ENABLED")).thenReturn(false);

        // 构造同时包含三类错误的步骤：
        // 结构错误：while(true) 无限循环
        // 能力错误：未定义能力 CAP_UNKNOWN_TEST
        // 约束错误：含运动安全字段 speed=1.5
        Map<String, Object> badStep = standardStep(1, "CAP_UNKNOWN_TEST");
        badStep.put("stepGoal", "while(true) { navigate(); }");
        badStep.put("inputParams", Map.of("speed", 1.5));

        PlanValidationResult result = validationService.validate(List.of(badStep), standardAgents());
        assertFalse(result.isAllPassed());
        assertEquals("FAIL", result.getStructureCheckResult());
        assertEquals("FAIL", result.getCapabilityCheckResult());
        assertEquals("FAIL", result.getConstraintCheckResult());

        // 错误清单聚合
        List<String> reasonCodes = result.getErrors().stream().map(PlanValidationResult.ValidationError::getReasonCode).toList();
        assertTrue(reasonCodes.contains("ERR_STEP_LOOP_DETECTED"));
        assertTrue(reasonCodes.contains("ERR_CAPABILITY_GAP"));
        assertTrue(reasonCodes.contains("ERR_MOTION_SAFETY_FIELD"));
    }

    // ==========================================
    // R07 & R06: 严禁强行放行，违规放行被硬性拦截并留痕
    // ==========================================

    @Test
    void r07_forceBypassAttemptsAreStrictlyIntercepted() {
        TaskMapper taskMapper = mock(TaskMapper.class);
        TaskEventService taskEventService = mock(TaskEventService.class);
        OperationLogService operationLogService = mock(OperationLogService.class);
        TaskPlanningOrchestrator orchestrator = mock(TaskPlanningOrchestrator.class);

        Task task = new Task();
        task.setId(100L);
        task.setTaskCode("TASK-F013-100");
        task.setStatus(TaskStatus.PENDING_MANUAL);
        when(taskMapper.findById(100L)).thenReturn(Optional.of(task));

        TaskService taskService = new TaskService(taskMapper, mock(PlanVersionMapper.class),
                mock(ContextSnapshotMapper.class), mock(DeviceAgentMapper.class),
                mock(GoalUnderstandingService.class), mock(TaskCodeGenerator.class),
                taskEventService, operationLogService, orchestrator,
                mock(TaskStepAssignmentMapper.class), mock(TaskDefinitionService.class),
                mock(DeviceAgentMessagingService.class));

        User operator = new User();
        operator.setId(10L);
        operator.setUsername("operator_zhang");
        operator.setRole("OPERATOR");

        List<String> bypassAttempts = List.of(
                "FORCE_RELEASE", "BYPASS_VALIDATION", "FORCE_BYPASS", "RELEASE",
                "OVERRIDE", "APPROVE", "FORCE_PASS", "FORCE_EXECUTE",
                "REQUEST_SUPERVISION", "FORCE_SUPERVISION"
        );

        for (String action : bypassAttempts) {
            BusinessException ex = assertThrows(BusinessException.class,
                    () -> taskService.manualAction(100L, action, "尝试放行", null, operator));
            assertEquals(ErrorCode.FORCE_BYPASS_HARD_CHECK, ex.getErrorCode());
            assertEquals(TaskStatus.PENDING_MANUAL, task.getStatus(), "状态绝不可被修改为执行或监督");
        }

        // 校验拦截事件与审计记录已生成
        verify(taskEventService, atLeast(bypassAttempts.size())).append(eq(100L),
                eq("FORCE_BYPASS_INTERCEPTED"), eq("OPERATOR"), eq("ERR_FORCE_BYPASS_REJECTED"), anyString());
        verify(operationLogService, atLeast(bypassAttempts.size())).record(eq(10L), eq("operator_zhang"),
                eq("OPERATOR"), eq("FORCE_BYPASS_ATTEMPT"), anyString(), eq("INTERCEPTED"), any());

        // 绝无推进或下发
        verifyNoInteractions(orchestrator);
    }

    @Test
    void def_s3_089_forceBypassAuditRecorderPersistsInterceptionAndAudit() {
        TaskEventService taskEventService = mock(TaskEventService.class);
        OperationLogService operationLogService = mock(OperationLogService.class);
        ForceBypassAuditRecorder recorder = new ForceBypassAuditRecorder(taskEventService, operationLogService);

        User operator = new User();
        operator.setId(88L);
        operator.setUsername("audit_op");
        operator.setRole("OPERATOR");

        recorder.recordInterception(118L, "TASK-F013-118", "FORCE_RELEASE", operator);
        verify(taskEventService).append(eq(118L), eq("FORCE_BYPASS_INTERCEPTED"), eq("OPERATOR"),
                eq("ERR_FORCE_BYPASS_REJECTED"), contains("FORCE_RELEASE"));
        verify(operationLogService).record(eq(88L), eq("audit_op"), eq("OPERATOR"),
                eq("FORCE_BYPASS_ATTEMPT"), eq("TASK-F013-118 -> FORCE_RELEASE"), eq("INTERCEPTED"), isNull());

        // Null operator fallback check
        recorder.recordInterception(119L, "TASK-F013-119", "REQUEST_SUPERVISION", null);
        verify(operationLogService).record(isNull(), eq("OPERATOR"), eq("OPERATOR"),
                eq("FORCE_BYPASS_ATTEMPT"), eq("TASK-F013-119 -> REQUEST_SUPERVISION"), eq("INTERCEPTED"), isNull());
    }

    @Test
    void r06_retryPlanningSupportsUpdatedGoal() {
        TaskMapper taskMapper = mock(TaskMapper.class);
        TaskEventService taskEventService = mock(TaskEventService.class);
        OperationLogService operationLogService = mock(OperationLogService.class);
        TaskPlanningOrchestrator orchestrator = mock(TaskPlanningOrchestrator.class);
        GoalUnderstandingService goalService = mock(GoalUnderstandingService.class);

        Task task = new Task();
        task.setId(101L);
        task.setTaskCode("TASK-F013-101");
        task.setStatus(TaskStatus.PENDING_MANUAL);
        task.setTaskGoal("原目标：无限循环测试");
        when(taskMapper.findById(101L)).thenReturn(Optional.of(task));

        var goalResponse = mock(com.airport.ai.planning.GoalUnderstandingResponse.class);
        when(goalResponse.isSuccess()).thenReturn(true);
        when(goalResponse.isInfoComplete()).thenReturn(true);
        when(goalService.understand(any())).thenReturn(goalResponse);

        TaskService taskService = new TaskService(taskMapper, mock(PlanVersionMapper.class),
                mock(ContextSnapshotMapper.class), mock(DeviceAgentMapper.class),
                goalService, mock(TaskCodeGenerator.class),
                taskEventService, operationLogService, orchestrator,
                mock(TaskStepAssignmentMapper.class), mock(TaskDefinitionService.class),
                mock(DeviceAgentMessagingService.class));

        User operator = new User();
        operator.setId(10L);
        operator.setUsername("operator_zhang");
        operator.setRole("OPERATOR");

        Task result = taskService.manualAction(101L, "RETRY_PLANNING", "修改目标重试", "新目标：引导旅客至登机口A1", operator);
        assertEquals(TaskStatus.PLANNING, result.getStatus());
        assertEquals("新目标：引导旅客至登机口A1", task.getTaskGoal());

        verify(taskEventService).append(eq(101L), eq("TASK_GOAL_UPDATED"), eq("OPERATOR"), isNull(), contains("引导旅客至登机口A1"));
        verify(orchestrator).advance(101L);
    }
}
