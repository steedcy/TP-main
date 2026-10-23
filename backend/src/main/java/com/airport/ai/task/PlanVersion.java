package com.airport.ai.task;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * 对应数据库设计说明书V2.0 4.5.2节 plan_versions表。纯POJO，持久化映射见 mapper/PlanVersionMapper.xml。
 * 冻结后不可变，修改需通过局部重新规划生成新版本（不提供UPDATE plan_steps接口）。
 * planSteps为JSON列，Java侧统一用String承载。
 */
public class PlanVersion {

    private Long id;
    private Long taskId;
    private Integer versionNo;
    /** AUTONOMOUS / BASELINE_TEMPLATE */
    private String source;
    private Long baselineTemplateId;
    private String snapshotId;
    private String planSteps;
    private String structureCheckResult;
    private String capabilityCheckResult;
    private String constraintCheckResult;
    /** 对应5.4.4界面元素"错误清单"，JSON数组，每项含errorType/description/stepSeq/reasonCode */
    private String validationErrors;
    /** LOW / HIGH / UNDETERMINED */
    private String riskLevel;
    private String riskReasonCode;
    private String judgmentBasis;
    private BigDecimal confidence;
    private String ruleSetVersion;
    private LocalDateTime frozenAt;
    private LocalDateTime createdAt = LocalDateTime.now();

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public Long getTaskId() { return taskId; }
    public void setTaskId(Long taskId) { this.taskId = taskId; }
    public Integer getVersionNo() { return versionNo; }
    public void setVersionNo(Integer versionNo) { this.versionNo = versionNo; }
    public String getSource() { return source; }
    public void setSource(String source) { this.source = source; }
    public Long getBaselineTemplateId() { return baselineTemplateId; }
    public void setBaselineTemplateId(Long baselineTemplateId) { this.baselineTemplateId = baselineTemplateId; }
    public String getSnapshotId() { return snapshotId; }
    public void setSnapshotId(String snapshotId) { this.snapshotId = snapshotId; }
    public String getPlanSteps() { return planSteps; }
    public void setPlanSteps(String planSteps) { this.planSteps = planSteps; }
    public String getStructureCheckResult() { return structureCheckResult; }
    public void setStructureCheckResult(String structureCheckResult) { this.structureCheckResult = structureCheckResult; }
    public String getCapabilityCheckResult() { return capabilityCheckResult; }
    public void setCapabilityCheckResult(String capabilityCheckResult) { this.capabilityCheckResult = capabilityCheckResult; }
    public String getConstraintCheckResult() { return constraintCheckResult; }
    public void setConstraintCheckResult(String constraintCheckResult) { this.constraintCheckResult = constraintCheckResult; }
    public String getValidationErrors() { return validationErrors; }
    public void setValidationErrors(String validationErrors) { this.validationErrors = validationErrors; }
    public String getRiskLevel() { return riskLevel; }
    public void setRiskLevel(String riskLevel) { this.riskLevel = riskLevel; }
    public String getRiskReasonCode() { return riskReasonCode; }
    public void setRiskReasonCode(String riskReasonCode) { this.riskReasonCode = riskReasonCode; }
    public String getJudgmentBasis() { return judgmentBasis; }
    public void setJudgmentBasis(String judgmentBasis) { this.judgmentBasis = judgmentBasis; }
    public BigDecimal getConfidence() { return confidence; }
    public void setConfidence(BigDecimal confidence) { this.confidence = confidence; }
    public String getRuleSetVersion() { return ruleSetVersion; }
    public void setRuleSetVersion(String ruleSetVersion) { this.ruleSetVersion = ruleSetVersion; }
    public LocalDateTime getFrozenAt() { return frozenAt; }
    public void setFrozenAt(LocalDateTime frozenAt) { this.frozenAt = frozenAt; }
    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }
}
