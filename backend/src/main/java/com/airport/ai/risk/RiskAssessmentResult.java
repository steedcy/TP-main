package com.airport.ai.risk;

import java.math.BigDecimal;

/**
 * 对应附录B 4.4节监督判定接口响应
 */
public class RiskAssessmentResult {

    private String riskLevel;       // LOW / HIGH / UNDETERMINED
    private String riskReasonCode;
    private String judgmentBasis;
    private BigDecimal confidence;
    private String recommendedAction; // AUTO_EXECUTE / BASELINE_DOWNGRADE / MANUAL_HANDLING
    private String ruleSetVersion;

    public RiskAssessmentResult(String riskLevel, String riskReasonCode, String judgmentBasis,
                                 BigDecimal confidence, String recommendedAction, String ruleSetVersion) {
        this.riskLevel = riskLevel;
        this.riskReasonCode = riskReasonCode;
        this.judgmentBasis = judgmentBasis;
        this.confidence = confidence;
        this.recommendedAction = recommendedAction;
        this.ruleSetVersion = ruleSetVersion;
    }

    public String getRiskLevel() { return riskLevel; }
    public String getRiskReasonCode() { return riskReasonCode; }
    public String getJudgmentBasis() { return judgmentBasis; }
    public BigDecimal getConfidence() { return confidence; }
    public String getRecommendedAction() { return recommendedAction; }
    public String getRuleSetVersion() { return ruleSetVersion; }

    /** 推荐处置的中文名称，供时间线与界面展示。 */
    public static String actionLabel(String recommendedAction) {
        if (recommendedAction == null) return "未给出";
        return switch (recommendedAction) {
            case "AUTO_EXECUTE" -> "自动执行";
            case "BASELINE_DOWNGRADE" -> "基线降级";
            case "MANUAL_HANDLING" -> "转人工处理";
            default -> recommendedAction;
        };
    }

    /**
     * SRS_F014.R10：判定结果、原因码、判定依据、置信度、所用规则集版本和处置策略写入任务事件时间线。
     * 每一项都固定输出（缺失时显式写"无"），使时间线可逐项核对，不依赖计划版本表。
     */
    public String timelineDetail(String prefix) {
        return (prefix == null ? "监督判定" : prefix)
                + ": 风险等级=" + riskLevel
                + "；原因码=" + (riskReasonCode == null ? "无" : riskReasonCode)
                + "；判定依据=" + (judgmentBasis == null ? "无" : judgmentBasis)
                + "；置信度=" + (confidence == null ? "无" : confidence.toPlainString())
                + "（仅作参考，不覆盖三类校验结果）"
                + "；规则集版本=" + (ruleSetVersion == null ? "无" : ruleSetVersion)
                + "；推荐处置=" + (recommendedAction == null ? "无" : recommendedAction)
                + "（" + actionLabel(recommendedAction) + "）";
    }
}
