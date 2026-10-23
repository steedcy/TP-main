package com.airport.ai.planning;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

/**
 * 对应附录B 5.1节规划模型服务调用接口响应体
 */
public class PlanningResponse {

    private String resultCode; // "0"=成功，非0=失败
    private String errorMessage;
    private List<Map<String, Object>> planSteps;
    private String planRationale;
    private BigDecimal confidence;
    /** 候选差异信号标签，由模型输出，平台层直接采信不做二次量化（对应TBD-04拍板结论） */
    private Boolean candidateDiverse;

    public boolean isSuccess() {
        return "0".equals(resultCode);
    }

    public String getResultCode() { return resultCode; }
    public void setResultCode(String resultCode) { this.resultCode = resultCode; }
    public String getErrorMessage() { return errorMessage; }
    public void setErrorMessage(String errorMessage) { this.errorMessage = errorMessage; }
    public List<Map<String, Object>> getPlanSteps() { return planSteps; }
    public void setPlanSteps(List<Map<String, Object>> planSteps) { this.planSteps = planSteps; }
    public String getPlanRationale() { return planRationale; }
    public void setPlanRationale(String planRationale) { this.planRationale = planRationale; }
    public BigDecimal getConfidence() { return confidence; }
    public void setConfidence(BigDecimal confidence) { this.confidence = confidence; }
    public Boolean getCandidateDiverse() { return candidateDiverse; }
    public void setCandidateDiverse(Boolean candidateDiverse) { this.candidateDiverse = candidateDiverse; }
}
