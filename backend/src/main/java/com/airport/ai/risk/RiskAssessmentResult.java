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
}
