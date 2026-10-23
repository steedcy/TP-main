package com.airport.ai.task.dto;

import com.airport.ai.task.PlanVersion;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

/**
 * 对应5.4.3~5.4.6任务详情内的候选计划展示、校验结果与错误清单、监督判定结果、降级信息
 */
public class PlanVersionView {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private Long id;
    private Integer versionNo;
    private String source;
    private Long baselineTemplateId;
    private String snapshotId;
    private List<Map<String, Object>> planSteps;
    private String structureCheckResult;
    private String capabilityCheckResult;
    private String constraintCheckResult;
    private List<Map<String, Object>> validationErrors;
    private String riskLevel;
    private String riskReasonCode;
    private String judgmentBasis;
    private BigDecimal confidence;
    private String ruleSetVersion;
    private LocalDateTime frozenAt;
    private LocalDateTime createdAt;

    public static PlanVersionView from(PlanVersion pv) {
        PlanVersionView v = new PlanVersionView();
        v.id = pv.getId();
        v.versionNo = pv.getVersionNo();
        v.source = pv.getSource();
        v.baselineTemplateId = pv.getBaselineTemplateId();
        v.snapshotId = pv.getSnapshotId();
        v.planSteps = parseList(pv.getPlanSteps());
        v.structureCheckResult = pv.getStructureCheckResult();
        v.capabilityCheckResult = pv.getCapabilityCheckResult();
        v.constraintCheckResult = pv.getConstraintCheckResult();
        v.validationErrors = parseList(pv.getValidationErrors());
        v.riskLevel = pv.getRiskLevel();
        v.riskReasonCode = pv.getRiskReasonCode();
        v.judgmentBasis = pv.getJudgmentBasis();
        v.confidence = pv.getConfidence();
        v.ruleSetVersion = pv.getRuleSetVersion();
        v.frozenAt = pv.getFrozenAt();
        v.createdAt = pv.getCreatedAt();
        return v;
    }

    private static List<Map<String, Object>> parseList(String json) {
        if (json == null || json.isBlank()) return null;
        try {
            return MAPPER.readValue(json, List.class);
        } catch (Exception e) {
            throw new RuntimeException("解析失败: " + json, e);
        }
    }

    public Long getId() { return id; }
    public Integer getVersionNo() { return versionNo; }
    public String getSource() { return source; }
    public Long getBaselineTemplateId() { return baselineTemplateId; }
    public String getSnapshotId() { return snapshotId; }
    public List<Map<String, Object>> getPlanSteps() { return planSteps; }
    public String getStructureCheckResult() { return structureCheckResult; }
    public String getCapabilityCheckResult() { return capabilityCheckResult; }
    public String getConstraintCheckResult() { return constraintCheckResult; }
    public List<Map<String, Object>> getValidationErrors() { return validationErrors; }
    public String getRiskLevel() { return riskLevel; }
    public String getRiskReasonCode() { return riskReasonCode; }
    public String getJudgmentBasis() { return judgmentBasis; }
    public BigDecimal getConfidence() { return confidence; }
    public String getRuleSetVersion() { return ruleSetVersion; }
    public LocalDateTime getFrozenAt() { return frozenAt; }
    public LocalDateTime getCreatedAt() { return createdAt; }
}
