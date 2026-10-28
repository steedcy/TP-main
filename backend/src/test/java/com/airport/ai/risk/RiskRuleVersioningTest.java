package com.airport.ai.risk;

import com.airport.ai.auth.CurrentUser;
import com.airport.ai.auth.OperationLogService;
import com.airport.ai.auth.User;
import org.junit.jupiter.api.Test;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

/** DEF-S3-043 / SRS_F002.R05：规则内容修改与启停都生成新版本，规则集版本随之变化并可在判定结果中追溯。 */
class RiskRuleVersioningTest {

    private final RiskRuleMapper mapper = mock(RiskRuleMapper.class);
    private final CurrentUser currentUser = mock(CurrentUser.class);
    private final RiskRuleController controller =
            new RiskRuleController(mapper, mock(OperationLogService.class), currentUser);

    private RiskRule rule(String version, boolean enabled) {
        RiskRule r = new RiskRule();
        r.setRuleCode("RULE_CROSS_ZONE");
        r.setRuleContent("content");
        r.setRuleVersion(version);
        r.setEnabled(enabled);
        when(mapper.findByRuleCode("RULE_CROSS_ZONE")).thenReturn(Optional.of(r));
        User u = new User();
        u.setId(1L);
        u.setUsername("cfg");
        u.setRole("CONFIG_ADMIN");
        when(currentUser.get()).thenReturn(u);
        return r;
    }

    private Map<String, Object> body(String k, Object v) {
        Map<String, Object> m = new HashMap<>();
        m.put(k, v);
        return m;
    }

    @Test
    void disablingBumpsVersion() {
        RiskRule r = rule("V1.1", true);
        controller.update("RULE_CROSS_ZONE", body("enabled", false));
        assertEquals("V1.2", r.getRuleVersion());
        assertFalse(r.getEnabled());
    }

    @Test
    void enablingBumpsVersion() {
        RiskRule r = rule("V1.2", false);
        controller.update("RULE_CROSS_ZONE", body("enabled", true));
        assertEquals("V1.3", r.getRuleVersion());
    }

    @Test
    void contentChangeStillBumpsVersionOnce() {
        RiskRule r = rule("V1.0", true);
        Map<String, Object> b = body("ruleContent", "new");
        b.put("enabled", false);
        controller.update("RULE_CROSS_ZONE", b);
        assertEquals("V1.1", r.getRuleVersion());
    }

    @Test
    void unchangedEnabledFlagDoesNotBump() {
        RiskRule r = rule("V1.0", true);
        controller.update("RULE_CROSS_ZONE", body("enabled", true));
        assertEquals("V1.0", r.getRuleVersion());
    }

    @Test
    void ruleSetVersionChangesWithEveryRuleChange() {
        RiskRule a = rule("V1.0", true);
        RiskRule b = new RiskRule();
        b.setRuleVersion("V1.0");
        assertEquals("V1.0", RiskRuleSetVersion.of(List.of(a, b)));
        a.setRuleVersion("V1.1");
        assertEquals("V1.1", RiskRuleSetVersion.of(List.of(a, b)));
        b.setRuleVersion("V1.2");
        assertEquals("V1.3", RiskRuleSetVersion.of(List.of(a, b)));
    }

    @Test
    void assessmentRecordsRuleSetVersionAfterDisable() {
        RiskRule on = new RiskRule();
        on.setRuleCode("RULE_RESOURCE_CRITICAL");
        on.setRuleVersion("V1.0");
        on.setEnabled(true);
        RiskRuleMapper m = mock(RiskRuleMapper.class);
        when(m.findAll()).thenReturn(List.of(on));
        when(m.findByEnabled(true)).thenReturn(List.of(on));
        RiskAssessmentService service = new RiskAssessmentService(m, 0.8, 60, 1);
        com.airport.ai.task.PlanVersion plan = new com.airport.ai.task.PlanVersion();
        plan.setStructureCheckResult("PASS");
        plan.setCapabilityCheckResult("PASS");
        plan.setConstraintCheckResult("PASS");
        plan.setPlanSteps("[{\"stepSeq\":1,\"capabilityType\":\"CAP_NAVIGATION\"}]");
        String before = service.assess(plan, "GENERAL_GUIDANCE", java.time.LocalDateTime.now(), false, 1).getRuleSetVersion();

        on.setEnabled(false);
        on.setRuleVersion("V1.1");
        when(m.findByEnabled(true)).thenReturn(List.of());
        RiskAssessmentResult after = service.assess(plan, "GENERAL_GUIDANCE", java.time.LocalDateTime.now(), false, 1);

        assertEquals("V1.0", before);
        assertEquals("V1.1", after.getRuleSetVersion());
        assertEquals("LOW", after.getRiskLevel());
    }
}
