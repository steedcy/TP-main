package com.airport.ai.planning;

import java.util.List;

/**
 * 对应5.4.1界面元素"解析结果""待补充问题"、附录B 5.2节目标理解服务响应体
 */
public class GoalUnderstandingResponse {

    private String resultCode; // "0"=成功，非0=失败
    private String errorMessage;
    /** 提取出的原始目标（原文回显，不做改写），起点、目的地、约束条件、完成条件 */
    private String origin;
    private String destination;
    private List<String> constraints;
    private String completionCondition;
    /** 关键信息是否完整；为false时missingInfoQuestions不得为空，且不得进入计划生成 */
    private boolean infoComplete;
    private List<String> missingInfoQuestions;
    /** 目标内容与已定义任务族及能力类型完全无关时为true（对应5.4.1异常路径4c） */
    private boolean unrelatedToAnyFamily;
    /** 系统按目标内容判定出的任务族（运行操作员未指定任务族时使用） */
    private String inferredTaskFamily;

    public boolean isSuccess() {
        return "0".equals(resultCode);
    }

    public String getResultCode() { return resultCode; }
    public void setResultCode(String resultCode) { this.resultCode = resultCode; }
    public String getErrorMessage() { return errorMessage; }
    public void setErrorMessage(String errorMessage) { this.errorMessage = errorMessage; }
    public String getOrigin() { return origin; }
    public void setOrigin(String origin) { this.origin = origin; }
    public String getDestination() { return destination; }
    public void setDestination(String destination) { this.destination = destination; }
    public List<String> getConstraints() { return constraints; }
    public void setConstraints(List<String> constraints) { this.constraints = constraints; }
    public String getCompletionCondition() { return completionCondition; }
    public void setCompletionCondition(String completionCondition) { this.completionCondition = completionCondition; }
    public boolean isInfoComplete() { return infoComplete; }
    public void setInfoComplete(boolean infoComplete) { this.infoComplete = infoComplete; }
    public List<String> getMissingInfoQuestions() { return missingInfoQuestions; }
    public void setMissingInfoQuestions(List<String> missingInfoQuestions) { this.missingInfoQuestions = missingInfoQuestions; }
    public boolean isUnrelatedToAnyFamily() { return unrelatedToAnyFamily; }
    public void setUnrelatedToAnyFamily(boolean unrelatedToAnyFamily) { this.unrelatedToAnyFamily = unrelatedToAnyFamily; }
    public String getInferredTaskFamily() { return inferredTaskFamily; }
    public void setInferredTaskFamily(String inferredTaskFamily) { this.inferredTaskFamily = inferredTaskFamily; }
}
