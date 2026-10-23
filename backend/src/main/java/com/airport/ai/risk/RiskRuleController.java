package com.airport.ai.risk;

import com.airport.ai.auth.CurrentUser;
import com.airport.ai.auth.OperationLogService;
import com.airport.ai.auth.User;
import com.airport.ai.common.ApiResponse;
import com.airport.ai.common.BusinessException;
import com.airport.ai.common.ErrorCode;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/**
 * 对应附录B 6.11节确定性高风险规则配置，仅配置管理员可操作（对应5.4.5业务规则5）。
 * 规则新增/修改均写入操作记录（对应5.7.2业务规则2"确定性高风险规则变更"）。
 */
@RestController
@RequestMapping("/api/v1/risk-rules")
@PreAuthorize("hasRole('CONFIG_ADMIN')")
public class RiskRuleController {

    private final RiskRuleMapper riskRuleMapper;
    private final OperationLogService operationLogService;
    private final CurrentUser currentUser;

    public RiskRuleController(RiskRuleMapper riskRuleMapper, OperationLogService operationLogService, CurrentUser currentUser) {
        this.riskRuleMapper = riskRuleMapper;
        this.operationLogService = operationLogService;
        this.currentUser = currentUser;
    }

    @GetMapping
    public ApiResponse<List<RiskRule>> list(@RequestParam(required = false) Boolean enabled) {
        if (enabled != null) {
            return ApiResponse.ok(riskRuleMapper.findByEnabled(enabled));
        }
        return ApiResponse.ok(riskRuleMapper.findAll());
    }

    @PostMapping
    public ApiResponse<RiskRule> create(@RequestBody Map<String, Object> body) {
        String ruleCode = (String) body.get("ruleCode");
        if (riskRuleMapper.existsByRuleCode(ruleCode)) {
            throw new BusinessException(ErrorCode.RISK_RULE_CODE_TAKEN);
        }
        RiskRule rule = new RiskRule();
        rule.setRuleCode(ruleCode);
        rule.setRuleContent((String) body.get("ruleContent"));
        rule.setEnabled((Boolean) body.getOrDefault("enabled", true));
        riskRuleMapper.insert(rule);

        User operator = currentUser.get();
        Map<String, Object> detail = new java.util.HashMap<>();
        detail.put("action", "CREATE");
        detail.put("ruleContent", rule.getRuleContent());
        detail.put("enabled", rule.getEnabled());
        operationLogService.record(operator.getId(), operator.getUsername(), operator.getRole(),
                "RISK_RULE_CHANGE", ruleCode, "SUCCESS", null, detail);
        return ApiResponse.ok(rule);
    }

    /** 修改规则内容/启用状态即生成新版本号（对应5.4.5业务规则10） */
    @PostMapping("/{ruleCode}/update")
    public ApiResponse<RiskRule> update(@PathVariable String ruleCode, @RequestBody Map<String, Object> body) {
        RiskRule rule = riskRuleMapper.findByRuleCode(ruleCode)
                .orElseThrow(() -> new BusinessException(ErrorCode.SYSTEM_ERROR, "规则不存在"));
        String beforeContent = rule.getRuleContent();
        Boolean beforeEnabled = rule.getEnabled();
        if (body.containsKey("ruleContent")) {
            rule.setRuleContent((String) body.get("ruleContent"));
            rule.setRuleVersion(bumpVersion(rule.getRuleVersion()));
        }
        if (body.containsKey("enabled")) {
            rule.setEnabled((Boolean) body.get("enabled"));
        }
        rule.setUpdatedAt(java.time.LocalDateTime.now());
        riskRuleMapper.update(rule);

        User operator = currentUser.get();
        Map<String, Object> before = new java.util.HashMap<>();
        before.put("ruleContent", beforeContent);
        before.put("enabled", beforeEnabled);
        Map<String, Object> after = new java.util.HashMap<>();
        after.put("ruleContent", rule.getRuleContent());
        after.put("enabled", rule.getEnabled());
        Map<String, Object> detail = new java.util.HashMap<>();
        detail.put("action", "UPDATE");
        detail.put("before", before);
        detail.put("after", after);
        operationLogService.record(operator.getId(), operator.getUsername(), operator.getRole(),
                "RISK_RULE_CHANGE", ruleCode, "SUCCESS", null, detail);
        return ApiResponse.ok(rule);
    }

    /**
     * double加法在多次修改后会产生浮点误差（如1.1+0.1=1.2000000000000002），超出
     * rule_version varchar(16)导致写库失败，改用BigDecimal精确计算，这是此前从未
     * 被触发过的既有缺陷（此前从未有人对同一规则连续修改验证过版本号递增）。
     */
    private String bumpVersion(String current) {
        try {
            String numPart = current.replace("V", "");
            java.math.BigDecimal v = new java.math.BigDecimal(numPart);
            return "V" + v.add(new java.math.BigDecimal("0.1")).stripTrailingZeros().toPlainString();
        } catch (NumberFormatException e) {
            return "V1.1";
        }
    }
}
