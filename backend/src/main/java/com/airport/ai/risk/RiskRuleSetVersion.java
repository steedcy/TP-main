package com.airport.ai.risk;

import java.math.BigDecimal;
import java.util.List;
import java.util.Set;

/**
 * 规则集版本：每条规则每次内容或启停变更使其版本+0.1，规则集版本为全部规则累计变更次数，
 * 形如V1.N（初始V1.0）。单调递增，任一规则的内容或启停变化都会得到新的可追溯版本（DEF-S3-043）。
 *
 * <p>SRS_F014.R05/备选路径2a：配置管理员新增规则同样改变生效规则集，须发布新的规则集版本。
 * 预置三条规则（V3初始数据）属于初始版本V1.0；此外每新增一条规则计一次变更。规则不提供删除入口，
 * 因此该计数单调递增，不会因数据变化回退。
 */
public final class RiskRuleSetVersion {
    /** V3__init_data.sql预置的三条确定性高风险规则，属于规则集初始版本。 */
    static final Set<String> SEEDED_RULE_CODES = Set.of(
            "RULE_ESCORT_SPECIAL_PASSENGER", "RULE_CROSS_ZONE", "RULE_RESOURCE_CRITICAL");

    private RiskRuleSetVersion() {}

    public static String of(List<RiskRule> rules) {
        BigDecimal changes = BigDecimal.ZERO;
        for (RiskRule r : rules) {
            changes = changes.add(minorChanges(r.getRuleVersion()));
            if (r.getRuleCode() != null && !SEEDED_RULE_CODES.contains(r.getRuleCode())) {
                changes = changes.add(BigDecimal.ONE);
            }
        }
        return "V1." + changes.toBigInteger();
    }

    private static BigDecimal minorChanges(String version) {
        try {
            BigDecimal v = new BigDecimal(version.replace("V", ""));
            return v.subtract(BigDecimal.ONE).multiply(BigDecimal.TEN).max(BigDecimal.ZERO);
        } catch (RuntimeException e) {
            return BigDecimal.ZERO;
        }
    }
}
