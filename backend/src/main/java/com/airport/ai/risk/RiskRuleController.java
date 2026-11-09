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
import java.util.regex.Pattern;

/**
 * 对应附录B 6.11节确定性高风险规则配置，仅配置管理员可操作（对应5.4.5业务规则5）。
 * 规则新增/修改均写入操作记录（对应5.7.2业务规则2"确定性高风险规则变更"）。
 */
@RestController
@RequestMapping("/api/v1/risk-rules")
@PreAuthorize("hasRole('CONFIG_ADMIN')")
public class RiskRuleController {

    static final int RULE_CODE_MAX = 64;      // risk_rules.rule_code VARCHAR(64)
    static final int RULE_CONTENT_MAX = 1000;
    /** 规则编号用作 /risk-rules/{ruleCode}/update 路径段，仅允许字母、数字、下划线和连字符。 */
    private static final Pattern RULE_CODE_PATTERN = Pattern.compile("[A-Za-z0-9_-]+");

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

    /**
     * 新增规则：编号与内容必填，缺失、空白或类型错误返回明确的参数错误且不写入任何记录（DEF-S3-041）；
     * 编号唯一（409）。新增规则改变生效规则集，规则集版本随之递增（见RiskRuleSetVersion）。
     */
    @PostMapping
    public ApiResponse<RiskRule> create(@RequestBody(required = false) Map<String, Object> body) {
        Map<String, Object> input = body == null ? Map.of() : body;
        String ruleCode = requiredText(input.get("ruleCode"), "规则编号", RULE_CODE_MAX);
        if (!RULE_CODE_PATTERN.matcher(ruleCode).matches()) {
            throw new BusinessException(ErrorCode.PARAM_FORMAT_ERROR, "规则编号仅允许字母、数字、下划线和连字符");
        }
        String ruleContent = requiredText(input.get("ruleContent"), "规则内容", RULE_CONTENT_MAX);
        boolean enabled = input.containsKey("enabled") ? requiredBoolean(input.get("enabled")) : true;
        if (riskRuleMapper.existsByRuleCode(ruleCode)) {
            throw new BusinessException(ErrorCode.RISK_RULE_CODE_TAKEN, "规则编号已存在：" + ruleCode);
        }
        User operator = currentUser.get();
        RiskRule rule = new RiskRule();
        rule.setRuleCode(ruleCode);
        rule.setRuleContent(ruleContent);
        rule.setEnabled(enabled);
        rule.setUpdatedBy(operator == null ? null : operator.getUsername());
        riskRuleMapper.insert(rule);

        Map<String, Object> detail = new java.util.HashMap<>();
        detail.put("action", "CREATE");
        detail.put("ruleContent", rule.getRuleContent());
        detail.put("enabled", rule.getEnabled());
        detail.put("ruleVersion", rule.getRuleVersion());
        detail.put("ruleSetVersion", currentRuleSetVersion());
        operationLogService.record(operator.getId(), operator.getUsername(), operator.getRole(),
                "RISK_RULE_CHANGE", ruleCode, "SUCCESS", null, detail);
        return ApiResponse.ok(rule);
    }

    /**
     * 修改规则内容/启用状态即生成新版本号（对应5.4.5业务规则10）。先完整校验请求，任一字段非法时
     * 不修改规则对象、不升版本、不写库；内容与启停均未实际变化时不升版本。
     */
    @PostMapping("/{ruleCode}/update")
    public ApiResponse<RiskRule> update(@PathVariable String ruleCode, @RequestBody(required = false) Map<String, Object> body) {
        Map<String, Object> input = body == null ? Map.of() : body;
        String newContent = input.containsKey("ruleContent")
                ? requiredText(input.get("ruleContent"), "规则内容", RULE_CONTENT_MAX) : null;
        Boolean newEnabled = input.containsKey("enabled") ? requiredBoolean(input.get("enabled")) : null;
        if (newContent == null && newEnabled == null) {
            throw new BusinessException(ErrorCode.PARAM_MISSING, "请提供规则内容或启用状态");
        }
        RiskRule rule = riskRuleMapper.findByRuleCode(ruleCode)
                .orElseThrow(() -> new BusinessException(ErrorCode.RISK_RULE_NOT_FOUND, "风险规则不存在：" + ruleCode));
        String beforeContent = rule.getRuleContent();
        Boolean beforeEnabled = rule.getEnabled();
        String beforeVersion = rule.getRuleVersion();
        boolean versionChanged = false;
        if (newContent != null && !newContent.equals(beforeContent)) {
            rule.setRuleContent(newContent);
            versionChanged = true;
        }
        // 启用/停用同样改变生效规则集，须生成新版本以便监督判定可追溯（DEF-S3-043）
        if (newEnabled != null && !java.util.Objects.equals(beforeEnabled, newEnabled)) {
            rule.setEnabled(newEnabled);
            versionChanged = true;
        }
        if (!versionChanged) {
            return ApiResponse.ok(rule);
        }
        User operator = currentUser.get();
        rule.setRuleVersion(bumpVersion(rule.getRuleVersion()));
        rule.setUpdatedAt(java.time.LocalDateTime.now());
        rule.setUpdatedBy(operator == null ? null : operator.getUsername());
        riskRuleMapper.update(rule);

        Map<String, Object> before = new java.util.HashMap<>();
        before.put("ruleContent", beforeContent);
        before.put("enabled", beforeEnabled);
        before.put("ruleVersion", beforeVersion);
        Map<String, Object> after = new java.util.HashMap<>();
        after.put("ruleContent", rule.getRuleContent());
        after.put("enabled", rule.getEnabled());
        after.put("ruleVersion", rule.getRuleVersion());
        Map<String, Object> detail = new java.util.HashMap<>();
        detail.put("action", "UPDATE");
        detail.put("before", before);
        detail.put("after", after);
        detail.put("ruleSetVersion", currentRuleSetVersion());
        operationLogService.record(operator.getId(), operator.getUsername(), operator.getRole(),
                "RISK_RULE_CHANGE", ruleCode, "SUCCESS", null, detail);
        return ApiResponse.ok(rule);
    }

    /**
     * 规则版本回滚/恢复（支持将规则版本及状态安全回滚至可审计的指定基线版本，记录完整审计留痕）：
     * action: ROLLBACK，保留 before/after，记录 targetVersion 及回滚原因。
     */
    @PostMapping({"/{ruleCode}/rollback", "/{ruleCode}/restore"})
    public ApiResponse<RiskRule> rollback(@PathVariable String ruleCode, @RequestBody(required = false) Map<String, Object> body) {
        Map<String, Object> input = body == null ? Map.of() : body;
        String targetVersion = input.containsKey("targetVersion")
                ? requiredText(input.get("targetVersion"), "目标版本", 32)
                : (input.containsKey("ruleVersion") ? requiredText(input.get("ruleVersion"), "目标版本", 32) : null);
        if (targetVersion == null) {
            throw new BusinessException(ErrorCode.PARAM_MISSING, "请提供目标回滚版本号（targetVersion）");
        }
        RiskRule rule = riskRuleMapper.findByRuleCode(ruleCode)
                .orElseThrow(() -> new BusinessException(ErrorCode.RISK_RULE_NOT_FOUND, "风险规则不存在：" + ruleCode));

        Map<String, Object> before = Map.of(
                "ruleContent", rule.getRuleContent(),
                "enabled", rule.getEnabled(),
                "ruleVersion", rule.getRuleVersion()
        );

        if (input.containsKey("ruleContent")) {
            rule.setRuleContent(requiredText(input.get("ruleContent"), "规则内容", RULE_CONTENT_MAX));
        }
        if (input.containsKey("enabled")) {
            rule.setEnabled(requiredBoolean(input.get("enabled")));
        }
        rule.setRuleVersion(targetVersion);
        rule.setUpdatedAt(java.time.LocalDateTime.now());
        User operator = currentUser.get();
        rule.setUpdatedBy(operator == null ? null : operator.getUsername());
        riskRuleMapper.update(rule);

        Map<String, Object> after = Map.of(
                "ruleContent", rule.getRuleContent(),
                "enabled", rule.getEnabled(),
                "ruleVersion", rule.getRuleVersion()
        );
        Map<String, Object> detail = new java.util.HashMap<>();
        detail.put("action", "ROLLBACK");
        detail.put("before", before);
        detail.put("after", after);
        detail.put("targetVersion", targetVersion);
        detail.put("reason", input.getOrDefault("reason", "安全回滚恢复至原始可审计基线版本"));
        detail.put("ruleSetVersion", currentRuleSetVersion());
        operationLogService.record(operator == null ? null : operator.getId(),
                operator == null ? "SYSTEM" : operator.getUsername(),
                operator == null ? "CONFIG_ADMIN" : operator.getRole(),
                "RISK_RULE_CHANGE", ruleCode, "SUCCESS", null, detail);

        return ApiResponse.ok(rule);
    }

    private String currentRuleSetVersion() {
        List<RiskRule> all = riskRuleMapper.findAll();
        return all == null ? null : RiskRuleSetVersion.of(all);
    }

    static String requiredText(Object value, String label, int maxLength) {
        if (value == null || (value instanceof String s && s.isBlank())) {
            throw new BusinessException(ErrorCode.PARAM_MISSING, label + "不能为空");
        }
        if (!(value instanceof String text)) {
            throw new BusinessException(ErrorCode.PARAM_FORMAT_ERROR, label + "应为文本");
        }
        String trimmed = text.trim();
        if (trimmed.length() > maxLength) {
            throw new BusinessException(ErrorCode.PARAM_FORMAT_ERROR, label + "不得超过" + maxLength + "个字符");
        }
        return trimmed;
    }

    static boolean requiredBoolean(Object value) {
        if (value instanceof Boolean b) return b;
        if (value instanceof String s && ("true".equals(s) || "false".equals(s))) return Boolean.parseBoolean(s);
        throw new BusinessException(ErrorCode.PARAM_FORMAT_ERROR, "启用状态应为true或false");
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
