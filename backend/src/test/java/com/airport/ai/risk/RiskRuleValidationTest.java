package com.airport.ai.risk;

import com.airport.ai.auth.CurrentUser;
import com.airport.ai.auth.OperationLogService;
import com.airport.ai.auth.User;
import com.airport.ai.common.BusinessException;
import com.airport.ai.common.ErrorCode;
import org.junit.jupiter.api.Test;

import java.util.HashMap;
import java.util.Map;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

/** DEF-S3-041：风险规则新增/修改须校验编号与内容，缺失返回明确参数错误且不写入任何数据。 */
class RiskRuleValidationTest {
    private final RiskRuleMapper rules = mock(RiskRuleMapper.class);
    private final OperationLogService audit = mock(OperationLogService.class);
    private final CurrentUser currentUser = mock(CurrentUser.class);
    private final RiskRuleController controller = new RiskRuleController(rules, audit, currentUser);

    RiskRuleValidationTest() {
        User admin = new User();
        admin.setId(2L);
        admin.setUsername("cfg");
        admin.setRole("CONFIG_ADMIN");
        when(currentUser.get()).thenReturn(admin);
    }

    private Map<String, Object> body(Object code, Object content) {
        Map<String, Object> b = new HashMap<>();
        if (code != null) b.put("ruleCode", code);
        if (content != null) b.put("ruleContent", content);
        return b;
    }

    private void assertRejected(ErrorCode expected, Map<String, Object> body) {
        BusinessException ex = assertThrows(BusinessException.class, () -> controller.create(body));
        assertEquals(expected, ex.getErrorCode());
        verify(rules, never()).insert(any());
        verifyNoInteractions(audit);
    }

    @Test
    void missingNullAndBlankCodeOrContentAreRejectedWithoutPersistingAnything() {
        assertRejected(ErrorCode.PARAM_MISSING, body(null, null));
        assertRejected(ErrorCode.PARAM_MISSING, body("R-NEW", null));
        assertRejected(ErrorCode.PARAM_MISSING, body(null, "内容"));
        assertRejected(ErrorCode.PARAM_MISSING, body("", "内容"));
        assertRejected(ErrorCode.PARAM_MISSING, body("   ", "内容"));
        assertRejected(ErrorCode.PARAM_MISSING, body("R-NEW", ""));
        assertRejected(ErrorCode.PARAM_MISSING, body("R-NEW", "   "));
        assertRejected(ErrorCode.PARAM_MISSING, Map.of());
    }

    @Test
    void wrongTypesAndOversizeValuesAreParameterErrorsNotServerErrors() {
        assertRejected(ErrorCode.PARAM_FORMAT_ERROR, body(123, "内容"));
        assertRejected(ErrorCode.PARAM_FORMAT_ERROR, body("x".repeat(65), "内容"));
        assertRejected(ErrorCode.PARAM_FORMAT_ERROR, body("R-NEW", "x".repeat(1001)));
        assertRejected(ErrorCode.PARAM_FORMAT_ERROR, body("R NEW WITH SPACE", "内容"));
        Map<String, Object> badEnabled = body("R-NEW", "内容");
        badEnabled.put("enabled", "yes");
        assertRejected(ErrorCode.PARAM_FORMAT_ERROR, badEnabled);
        Map<String, Object> numericEnabled = body("R-NEW", "内容");
        numericEnabled.put("enabled", 1);
        assertRejected(ErrorCode.PARAM_FORMAT_ERROR, numericEnabled);
    }

    @Test
    void duplicateCodeStillReturnsConflictAfterValidation() {
        when(rules.existsByRuleCode("R-DUP")).thenReturn(true);
        BusinessException ex = assertThrows(BusinessException.class, () -> controller.create(body("R-DUP", "内容")));
        assertEquals(ErrorCode.RISK_RULE_CODE_TAKEN, ex.getErrorCode());
        verify(rules, never()).insert(any());
    }

    @Test
    void validRuleIsTrimmedSavedAndAudited() {
        Map<String, Object> b = body("  R-NEW  ", "  新规则内容  ");
        b.put("enabled", false);
        var response = controller.create(b);
        assertEquals("R-NEW", response.getData().getRuleCode());
        assertEquals("新规则内容", response.getData().getRuleContent());
        assertFalse(response.getData().getEnabled());
        verify(rules).insert(any());
        verify(audit).record(eq(2L), eq("cfg"), eq("CONFIG_ADMIN"), eq("RISK_RULE_CHANGE"), eq("R-NEW"), eq("SUCCESS"), isNull(), any());
    }

    @Test
    void updateRejectsBlankContentAndNonBooleanEnabledWithoutChangingTheRule() {
        RiskRule existing = new RiskRule();
        existing.setRuleCode("R-1");
        existing.setRuleContent("原内容");
        existing.setEnabled(true);
        existing.setRuleVersion("V1.0");
        when(rules.findByRuleCode("R-1")).thenReturn(Optional.of(existing));

        assertEquals(ErrorCode.PARAM_MISSING,
                assertThrows(BusinessException.class, () -> controller.update("R-1", Map.of("ruleContent", "  "))).getErrorCode());
        assertEquals(ErrorCode.PARAM_FORMAT_ERROR,
                assertThrows(BusinessException.class, () -> controller.update("R-1", Map.of("enabled", "maybe"))).getErrorCode());
        verify(rules, never()).update(any());
        assertEquals("原内容", existing.getRuleContent());
        assertEquals("V1.0", existing.getRuleVersion(), "校验失败不能升版本");
    }

    @Test
    void updateNonExistingRuleThrowsNotFound() {
        when(rules.findByRuleCode("NON_EXISTING")).thenReturn(Optional.empty());
        BusinessException ex = assertThrows(BusinessException.class,
                () -> controller.update("NON_EXISTING", Map.of("ruleContent", "新内容")));
        assertEquals(ErrorCode.RISK_RULE_NOT_FOUND, ex.getErrorCode());
        verify(rules, never()).update(any());
    }
}
