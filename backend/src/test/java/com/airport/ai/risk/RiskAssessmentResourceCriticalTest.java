package com.airport.ai.risk;

import com.airport.ai.task.PlanVersion;
import org.junit.jupiter.api.Test;

import java.time.LocalDateTime;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.Mockito.*;

class RiskAssessmentResourceCriticalTest {
    @Test
    void oneEligibleDeviceHasNoBackupAndMustDowngrade() {
        RiskRuleMapper mapper = mock(RiskRuleMapper.class);
        RiskRule rule = new RiskRule();
        rule.setRuleCode("RULE_RESOURCE_CRITICAL");
        when(mapper.findByEnabled(true)).thenReturn(List.of(rule));
        RiskAssessmentService service = new RiskAssessmentService(mapper, 0.8, 60, 1);
        PlanVersion plan = new PlanVersion();
        plan.setStructureCheckResult("PASS");
        plan.setCapabilityCheckResult("PASS");
        plan.setConstraintCheckResult("PASS");
        plan.setPlanSteps("[{\"stepSeq\":1,\"capabilityType\":\"CAP_NAVIGATION\"}]");

        RiskAssessmentResult one = service.assess(plan, "GENERAL_GUIDANCE", LocalDateTime.now(), false, 1);
        assertEquals("HIGH", one.getRiskLevel());
        assertEquals("RULE_RESOURCE_CRITICAL", one.getRiskReasonCode());
        assertEquals("LOW", service.assess(plan, "GENERAL_GUIDANCE", LocalDateTime.now(), false, 2).getRiskLevel());
    }
}
