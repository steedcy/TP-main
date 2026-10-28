package com.airport.ai.risk;

import java.math.BigDecimal;
import java.util.List;

/**
 * 规则集版本：每条规则每次内容或启停变更使其版本+0.1，规则集版本为全部规则累计变更次数，
 * 形如V1.N（初始V1.0）。单调递增，任一规则的内容或启停变化都会得到新的可追溯版本（DEF-S3-043）。
 */
public final class RiskRuleSetVersion {
    private RiskRuleSetVersion() {}

    public static String of(List<RiskRule> rules) {
        BigDecimal changes = BigDecimal.ZERO;
        for (RiskRule r : rules) {
            changes = changes.add(minorChanges(r.getRuleVersion()));
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
