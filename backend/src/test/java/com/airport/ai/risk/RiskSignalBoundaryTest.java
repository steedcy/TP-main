package com.airport.ai.risk;

import com.airport.ai.task.PlanVersion;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

/** NT-S3-029 单信号/双信号及 0.8、60 秒边界；NT-S3-028 监督不可判定/不可用注入。 */
class RiskSignalBoundaryTest {

    private final RiskRuleMapper mapper = mock(RiskRuleMapper.class);
    private final RiskAssessmentService service = new RiskAssessmentService(mapper, 0.8, 60, 1);

    private PlanVersion plan(String confidence) {
        PlanVersion p = new PlanVersion();
        p.setStructureCheckResult("PASS");
        p.setCapabilityCheckResult("PASS");
        p.setConstraintCheckResult("PASS");
        p.setPlanSteps("[{\"stepSeq\":1,\"capabilityType\":\"CAP_NAVIGATION\"}]");
        if (confidence != null) p.setConfidence(new BigDecimal(confidence));
        return p;
    }

    private String level(String confidence, boolean diverse, long snapshotAgeSeconds) {
        return service.assess(plan(confidence), "GENERAL_GUIDANCE",
                LocalDateTime.now().minusSeconds(snapshotAgeSeconds), diverse, 5).getRiskLevel();
    }

    @Test
    void singleSignalNeverDowngrades() {
        assertEquals("LOW", level("0.79", false, 0));
        assertEquals("LOW", level("0.95", true, 0));
        assertEquals("LOW", level("0.95", false, 120));
    }

    @Test
    void anyTwoSignalsDowngrade() {
        assertEquals("HIGH", level("0.79", true, 0));
        assertEquals("HIGH", level("0.79", false, 120));
        assertEquals("HIGH", level("0.95", true, 120));
        assertEquals("HIGH", level("0.5", true, 120));
    }

    @Test
    void confidenceBoundaryIsStrictlyBelowPointEight() {
        assertEquals("LOW", level("0.80", true, 0));
        assertEquals("HIGH", level("0.79", true, 0));
    }

    @Test
    void contextBoundaryIsStrictlyOverSixtySeconds() {
        assertEquals("LOW", level("0.50", false, 58));
        assertEquals("HIGH", level("0.50", false, 62));
    }

    @Test
    void injectedUnavailableThrowsAndUndeterminedIsReported() {
        ReflectionTestUtils.setField(service, "faultInjectionMode", "UNAVAILABLE");
        assertThrows(IllegalStateException.class, () -> level("0.95", false, 0));
        ReflectionTestUtils.setField(service, "faultInjectionMode", "UNDETERMINED");
        assertEquals("UNDETERMINED", level("0.95", false, 0));
        ReflectionTestUtils.setField(service, "faultInjectionMode", "");
        assertEquals("LOW", level("0.95", false, 0));
        assertNotNull(List.of());
    }

    @Test
    void def_s3_095_singleSignalListedInBasis() {
        RiskAssessmentResult lowOnly = service.assess(plan("0.79"), "GENERAL_GUIDANCE", LocalDateTime.now(), false, 5);
        assertEquals("LOW", lowOnly.getRiskLevel());
        assertTrue(lowOnly.getJudgmentBasis().contains("模型低置信度(0.79<0.8)"));
        assertTrue(lowOnly.getJudgmentBasis().contains("单一信号不直接阻断"));

        RiskAssessmentResult diverseOnly = service.assess(plan("0.95"), "GENERAL_GUIDANCE", LocalDateTime.now(), true, 5);
        assertEquals("LOW", diverseOnly.getRiskLevel());
        assertTrue(diverseOnly.getJudgmentBasis().contains("候选差异较大"));
        assertTrue(diverseOnly.getJudgmentBasis().contains("单一信号不直接阻断"));

        RiskAssessmentResult staleOnly = service.assess(plan("0.95"), "GENERAL_GUIDANCE", LocalDateTime.now().minusSeconds(120), false, 5);
        assertEquals("LOW", staleOnly.getRiskLevel());
        assertTrue(staleOnly.getJudgmentBasis().contains("上下文快照接近过期(>60秒)"));
        assertTrue(staleOnly.getJudgmentBasis().contains("单一信号不直接阻断"));
    }
}
