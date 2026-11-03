package com.airport.ai.risk;

import com.airport.ai.common.BusinessException;
import com.airport.ai.common.ErrorCode;
import com.airport.ai.task.PlanVersion;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

/**
 * 针对 SRS_F014 特殊旅客服务规划与监督判定（TC-043 ~ TC-046, R01 ~ R10）专项单测集。
 */
class SpecialPassengerSupervisionF014Test {

    private RiskRuleMapper mapper;
    private RiskAssessmentService service;

    private RiskRule rEscort;
    private RiskRule rCrossZone;
    private RiskRule rResourceCritical;

    @BeforeEach
    void setUp() {
        mapper = mock(RiskRuleMapper.class);
        service = new RiskAssessmentService(mapper, 0.8, 60, 1);

        rEscort = new RiskRule();
        rEscort.setRuleCode("RULE_ESCORT_SPECIAL_PASSENGER");
        rEscort.setRuleVersion("V1.0");
        rEscort.setEnabled(true);

        rCrossZone = new RiskRule();
        rCrossZone.setRuleCode("RULE_CROSS_ZONE");
        rCrossZone.setRuleVersion("V1.0");
        rCrossZone.setEnabled(true);

        rResourceCritical = new RiskRule();
        rResourceCritical.setRuleCode("RULE_RESOURCE_CRITICAL");
        rResourceCritical.setRuleVersion("V1.0");
        rResourceCritical.setEnabled(true);

        List<RiskRule> seeded = List.of(rEscort, rCrossZone, rResourceCritical);
        when(mapper.findAll()).thenReturn(seeded);
        when(mapper.findByEnabled(true)).thenReturn(seeded);
    }

    private PlanVersion validatedPlan(String stepsJson, String confidence) {
        PlanVersion p = new PlanVersion();
        p.setStructureCheckResult("PASS");
        p.setCapabilityCheckResult("PASS");
        p.setConstraintCheckResult("PASS");
        p.setPlanSteps(stepsJson);
        if (confidence != null) p.setConfidence(new BigDecimal(confidence));
        return p;
    }

    @Test
    @DisplayName("R01 & R10: 监督判定完整输出风险等级、原因码、判定依据、置信度、推荐处置及规则集版本")
    void r01_r10_assessmentOutputsAllRequiredFieldsAndTimeline() {
        // 普通引导任务，两台备用候选设备，正常快照，高置信度 -> LOW
        String steps = "[{\"stepSeq\":1,\"capabilityType\":\"CAP_NAVIGATION\",\"inputParams\":{\"targetLocation\":\"F2_TEST_GATE\"}}]";
        PlanVersion plan = validatedPlan(steps, "0.95");

        RiskAssessmentResult result = service.assess(plan, "GENERAL_GUIDANCE", LocalDateTime.now(), false, 3);
        assertEquals("LOW", result.getRiskLevel());
        assertNull(result.getRiskReasonCode());
        assertNotNull(result.getJudgmentBasis());
        assertEquals(new BigDecimal("0.95"), result.getConfidence());
        assertEquals("AUTO_EXECUTE", result.getRecommendedAction());
        assertEquals("V1.0", result.getRuleSetVersion());

        String timeline = result.timelineDetail("监督判定");
        assertTrue(timeline.contains("风险等级=LOW"));
        assertTrue(timeline.contains("置信度=0.95"));
        assertTrue(timeline.contains("规则集版本=V1.0"));
        assertTrue(timeline.contains("推荐处置=AUTO_EXECUTE"));
        assertTrue(timeline.contains("自动执行"));
    }

    @Test
    @DisplayName("R02: 判定为低风险时推荐AUTO_EXECUTE，判定为高风险时推荐BASELINE_DOWNGRADE")
    void r02_recommendedActionAlignsWithRiskLevel() {
        // 低风险 -> AUTO_EXECUTE
        String normalStep = "[{\"stepSeq\":1,\"capabilityType\":\"CAP_INFO_DISPLAY\"}]";
        PlanVersion lowPlan = validatedPlan(normalStep, "0.92");
        RiskAssessmentResult lowResult = service.assess(lowPlan, "FLIGHT_CHANGE_RESPONSE", LocalDateTime.now(), false, 3);
        assertEquals("LOW", lowResult.getRiskLevel());
        assertEquals("AUTO_EXECUTE", lowResult.getRecommendedAction());
        lowPlan.setRiskLevel(lowResult.getRiskLevel());
        assertEquals("AUTO_EXECUTE", lowPlan.getRecommendedAction());

        // 高风险（特殊旅客+机器人陪同） -> BASELINE_DOWNGRADE
        String escortStep = "[{\"stepSeq\":1,\"capabilityType\":\"CAP_ESCORT\"}]";
        PlanVersion highPlan = validatedPlan(escortStep, "0.98");
        RiskAssessmentResult highResult = service.assess(highPlan, "SPECIAL_PASSENGER_SERVICE", LocalDateTime.now(), false, 3);
        assertEquals("HIGH", highResult.getRiskLevel());
        assertEquals("BASELINE_DOWNGRADE", highResult.getRecommendedAction());
        highPlan.setRiskLevel(highResult.getRiskLevel());
        assertEquals("BASELINE_DOWNGRADE", highPlan.getRecommendedAction());
    }

    @Test
    @DisplayName("R03: 监督智能体输出无法确定时推荐MANUAL_HANDLING，不可用时抛出异常由上层转待人工")
    void r03_undeterminedAndUnavailableFaults() {
        String steps = "[{\"stepSeq\":1,\"capabilityType\":\"CAP_INFO_DISPLAY\"}]";
        PlanVersion plan = validatedPlan(steps, "0.90");

        ReflectionTestUtils.setField(service, "faultInjectionMode", "UNDETERMINED");
        RiskAssessmentResult undetermined = service.assess(plan, "GENERAL_GUIDANCE", LocalDateTime.now(), false, 3);
        assertEquals("UNDETERMINED", undetermined.getRiskLevel());
        assertEquals("INJECTED_UNDETERMINED", undetermined.getRiskReasonCode());
        assertEquals("MANUAL_HANDLING", undetermined.getRecommendedAction());
        plan.setRiskLevel(undetermined.getRiskLevel());
        assertEquals("MANUAL_HANDLING", plan.getRecommendedAction());

        ReflectionTestUtils.setField(service, "faultInjectionMode", "UNAVAILABLE");
        assertThrows(IllegalStateException.class,
                () -> service.assess(plan, "GENERAL_GUIDANCE", LocalDateTime.now(), false, 3));
    }

    @Test
    @DisplayName("R04 & R05: 特殊旅客服务场景中移动机器人会合(CAP_NAVIGATION)或陪同(CAP_ESCORT)命中确定性高风险规则")
    void r05_specialPassengerServiceEscortAndRendezvousRobotStepHitsDeterministicRule() {
        // 1. 特殊旅客任务 + CAP_ESCORT (机器人陪同) -> 命中 RULE_ESCORT_SPECIAL_PASSENGER
        String escortSteps = "[{\"stepSeq\":1,\"capabilityType\":\"CAP_ESCORT\",\"inputParams\":{\"escortMode\":\"LEAD\"}}]";
        PlanVersion p1 = validatedPlan(escortSteps, "0.99");
        RiskAssessmentResult r1 = service.assess(p1, "SPECIAL_PASSENGER_SERVICE", LocalDateTime.now(), false, 3);
        assertEquals("HIGH", r1.getRiskLevel());
        assertEquals("RULE_ESCORT_SPECIAL_PASSENGER", r1.getRiskReasonCode());
        assertTrue(r1.getJudgmentBasis().contains("移动机器人会合或陪同对象为特殊旅客"));
        assertTrue(r1.getJudgmentBasis().contains("CAP_ESCORT"));

        // 2. 特殊旅客任务 + CAP_NAVIGATION (机器人前往会合引导) -> 命中 RULE_ESCORT_SPECIAL_PASSENGER
        String navSteps = "[{\"stepSeq\":1,\"capabilityType\":\"CAP_NAVIGATION\",\"inputParams\":{\"targetLocation\":\"F2_TEST_GATE\"}}]";
        PlanVersion p2 = validatedPlan(navSteps, "0.99");
        RiskAssessmentResult r2 = service.assess(p2, "SPECIAL_PASSENGER_SERVICE", LocalDateTime.now(), false, 3);
        assertEquals("HIGH", r2.getRiskLevel());
        assertEquals("RULE_ESCORT_SPECIAL_PASSENGER", r2.getRiskReasonCode());
        assertTrue(r2.getJudgmentBasis().contains("CAP_NAVIGATION"));
        assertTrue(r2.getJudgmentBasis().contains("会合"));

        // 3. 特殊旅客任务 + CAP_INFO_DISPLAY (仅航显发布会合提示，非移动服务机器人步骤) -> 不命中 RULE_ESCORT_SPECIAL_PASSENGER
        String displaySteps = "[{\"stepSeq\":1,\"capabilityType\":\"CAP_INFO_DISPLAY\",\"inputParams\":{\"contentType\":\"TEXT\"}}]";
        PlanVersion p3 = validatedPlan(displaySteps, "0.99");
        RiskAssessmentResult r3 = service.assess(p3, "SPECIAL_PASSENGER_SERVICE", LocalDateTime.now(), false, 3);
        assertEquals("LOW", r3.getRiskLevel());
        assertNull(r3.getRiskReasonCode());

        // 4. 普通航班信息发布或引导 (FLIGHT_CHANGE_RESPONSE) 即使包含 CAP_NAVIGATION 或 CAP_ESCORT，也不命中 RULE_ESCORT_SPECIAL_PASSENGER
        RiskAssessmentResult r4 = service.assess(p2, "FLIGHT_CHANGE_RESPONSE", LocalDateTime.now(), false, 3);
        assertEquals("LOW", r4.getRiskLevel());
        assertNull(r4.getRiskReasonCode());

        // 5. 大件行李任务 (OVERSIZE_BAGGAGE_HANDLING) 包含 CAP_NAVIGATION，不命中特殊旅客规则
        RiskAssessmentResult r5 = service.assess(p2, "OVERSIZE_BAGGAGE_HANDLING", LocalDateTime.now(), false, 3);
        assertEquals("LOW", r5.getRiskLevel());
        assertNull(r5.getRiskReasonCode());
    }

    @Test
    @DisplayName("R05: 跨区域连续服务(RULE_CROSS_ZONE)与资源冲突临界(RULE_RESOURCE_CRITICAL)命中判定")
    void r05_crossZoneAndResourceCriticalRules() {
        // 跨区域：移动服务机器人步骤涉及2个不同区域 -> HIGH
        String crossZoneSteps = "["
                + "{\"stepSeq\":1,\"capabilityType\":\"CAP_NAVIGATION\",\"inputParams\":{\"targetLocation\":\"F2_GATE_01\",\"targetZone\":\"ZONE_A\"}},"
                + "{\"stepSeq\":2,\"capabilityType\":\"CAP_NAVIGATION\",\"inputParams\":{\"targetLocation\":\"F2_GATE_20\",\"targetZone\":\"ZONE_B\"}}"
                + "]";
        PlanVersion pCross = validatedPlan(crossZoneSteps, "0.95");
        RiskAssessmentResult rCross = service.assess(pCross, "GENERAL_GUIDANCE", LocalDateTime.now(), false, 3);
        assertEquals("HIGH", rCross.getRiskLevel());
        assertEquals("RULE_CROSS_ZONE", rCross.getRiskReasonCode());

        // 同一区域内的多步 -> 不命中跨区域
        String singleZoneSteps = "["
                + "{\"stepSeq\":1,\"capabilityType\":\"CAP_NAVIGATION\",\"inputParams\":{\"targetZone\":\"ZONE_A\"}},"
                + "{\"stepSeq\":2,\"capabilityType\":\"CAP_NAVIGATION\",\"inputParams\":{\"targetZone\":\"ZONE_A\"}}"
                + "]";
        PlanVersion pSame = validatedPlan(singleZoneSteps, "0.95");
        RiskAssessmentResult rSame = service.assess(pSame, "GENERAL_GUIDANCE", LocalDateTime.now(), false, 3);
        assertEquals("LOW", rSame.getRiskLevel());

        // 资源临界：可用候选设备数=1（消费1台后备用设备=0 < 阈值1） -> HIGH
        PlanVersion pRes = validatedPlan(singleZoneSteps, "0.95");
        RiskAssessmentResult rRes = service.assess(pRes, "GENERAL_GUIDANCE", LocalDateTime.now(), false, 1);
        assertEquals("HIGH", rRes.getRiskLevel());
        assertEquals("RULE_RESOURCE_CRITICAL", rRes.getRiskReasonCode());
    }

    @Test
    @DisplayName("R05 & DEF-S3-043: 规则停用后不再命中高风险，且规则集版本递增并记录在判定结果中")
    void r05_disablingRuleBumpsRuleSetVersionAndAllowsLowRisk() {
        String steps = "[{\"stepSeq\":1,\"capabilityType\":\"CAP_ESCORT\"}]";
        PlanVersion p = validatedPlan(steps, "0.95");

        // 启用时：HIGH，规则集版本 V1.0
        RiskAssessmentResult before = service.assess(p, "SPECIAL_PASSENGER_SERVICE", LocalDateTime.now(), false, 3);
        assertEquals("HIGH", before.getRiskLevel());
        assertEquals("V1.0", before.getRuleSetVersion());

        // 停用 RULE_ESCORT_SPECIAL_PASSENGER，版本升为 V1.1
        rEscort.setEnabled(false);
        rEscort.setRuleVersion("V1.1");
        when(mapper.findByEnabled(true)).thenReturn(List.of(rCrossZone, rResourceCritical));

        // 停用后：LOW，规则集版本 V1.1
        RiskAssessmentResult after = service.assess(p, "SPECIAL_PASSENGER_SERVICE", LocalDateTime.now(), false, 3);
        assertEquals("LOW", after.getRiskLevel());
        assertEquals("V1.1", after.getRuleSetVersion());
    }

    @Test
    @DisplayName("R06: 风险信号双信号降级规则及严格边界（<0.80，>60s）")
    void r06_riskSignalsCombinationAndStrictBoundaries() {
        String steps = "[{\"stepSeq\":1,\"capabilityType\":\"CAP_INFO_DISPLAY\"}]";

        // 单信号均不降级（LOW）
        assertEquals("LOW", service.assess(validatedPlan(steps, "0.79"), "GENERAL_GUIDANCE", LocalDateTime.now(), false, 3).getRiskLevel());
        assertEquals("LOW", service.assess(validatedPlan(steps, "0.95"), "GENERAL_GUIDANCE", LocalDateTime.now(), true, 3).getRiskLevel());
        assertEquals("LOW", service.assess(validatedPlan(steps, "0.95"), "GENERAL_GUIDANCE", LocalDateTime.now().minusSeconds(65), false, 3).getRiskLevel());

        // 任意两个信号组合触发降级（HIGH / RISK_SIGNAL_COMBINATION）
        RiskAssessmentResult rComb = service.assess(validatedPlan(steps, "0.79"), "GENERAL_GUIDANCE", LocalDateTime.now(), true, 3);
        assertEquals("HIGH", rComb.getRiskLevel());
        assertEquals("RISK_SIGNAL_COMBINATION", rComb.getRiskReasonCode());
        assertTrue(rComb.getJudgmentBasis().contains("模型低置信度"));
        assertTrue(rComb.getJudgmentBasis().contains("候选差异较大"));

        // 边界：0.80 不算低置信度，与差异标签组合仍为 LOW
        assertEquals("LOW", service.assess(validatedPlan(steps, "0.80"), "GENERAL_GUIDANCE", LocalDateTime.now(), true, 3).getRiskLevel());
        // 边界：0.79 为低置信度，与差异标签组合为 HIGH
        assertEquals("HIGH", service.assess(validatedPlan(steps, "0.79"), "GENERAL_GUIDANCE", LocalDateTime.now(), true, 3).getRiskLevel());

        // 边界：59秒快照未过期，与低置信度组合仍为 LOW
        assertEquals("LOW", service.assess(validatedPlan(steps, "0.79"), "GENERAL_GUIDANCE", LocalDateTime.now().minusSeconds(59), false, 3).getRiskLevel());
        // 边界：61秒快照已过期，与低置信度组合为 HIGH
        assertEquals("HIGH", service.assess(validatedPlan(steps, "0.79"), "GENERAL_GUIDANCE", LocalDateTime.now().minusSeconds(61), false, 3).getRiskLevel());
    }

    @Test
    @DisplayName("R07 & R08: 试图对三类校验未通过计划执行监督判定直接抛异常(4109)，置信度不可覆盖校验结果")
    void r07_r08_unvalidatedPlanCannotBeAssessedRegardlessOfConfidence() {
        String steps = "[{\"stepSeq\":1,\"capabilityType\":\"CAP_INFO_DISPLAY\"}]";

        PlanVersion badStructure = validatedPlan(steps, "1.00");
        badStructure.setStructureCheckResult("FAIL");
        BusinessException ex1 = assertThrows(BusinessException.class,
                () -> service.assess(badStructure, "GENERAL_GUIDANCE", LocalDateTime.now(), false, 3));
        assertEquals(ErrorCode.SUPERVISION_ON_UNVALIDATED_PLAN, ex1.getErrorCode());

        PlanVersion badCapability = validatedPlan(steps, "1.00");
        badCapability.setCapabilityCheckResult("FAIL");
        BusinessException ex2 = assertThrows(BusinessException.class,
                () -> service.assess(badCapability, "GENERAL_GUIDANCE", LocalDateTime.now(), false, 3));
        assertEquals(ErrorCode.SUPERVISION_ON_UNVALIDATED_PLAN, ex2.getErrorCode());

        PlanVersion badConstraint = validatedPlan(steps, "1.00");
        badConstraint.setConstraintCheckResult("FAIL");
        BusinessException ex3 = assertThrows(BusinessException.class,
                () -> service.assess(badConstraint, "GENERAL_GUIDANCE", LocalDateTime.now(), false, 3));
        assertEquals(ErrorCode.SUPERVISION_ON_UNVALIDATED_PLAN, ex3.getErrorCode());
    }

    @Test
    @DisplayName("DEF-S3-043: 动态新增自定义规则计入规则集版本，保证监督判定生效版本单调递增")
    void def_s3_043_dynamicRuleAdditionBumpsRuleSetVersion() {
        List<RiskRule> rules = new ArrayList<>(List.of(rEscort, rCrossZone, rResourceCritical));
        assertEquals("V1.0", RiskRuleSetVersion.of(rules));

        // 新增一条规则
        RiskRule custom = new RiskRule();
        custom.setRuleCode("RULE_NIGHT_SHIFT_ESCORT");
        custom.setRuleVersion("V1.0");
        custom.setEnabled(true);
        rules.add(custom);
        assertEquals("V1.1", RiskRuleSetVersion.of(rules));

        // 再次修改已有规则
        rResourceCritical.setRuleVersion("V1.1");
        assertEquals("V1.2", RiskRuleSetVersion.of(rules));
    }
}
