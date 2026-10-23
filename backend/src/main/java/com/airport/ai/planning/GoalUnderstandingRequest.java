package com.airport.ai.planning;

import java.util.List;
import java.util.Map;

/**
 * 对应5.4.1开放式任务目标提交与理解，采用方案A：目标理解与候选计划生成
 * 是外部规划模型服务的两个独立端点（/v1/goal/understand 与 /v1/planning/generate），
 * 契约见附录B 5.2节。目标理解阶段不下发任何设备指令，也不生成计划步骤。
 */
public class GoalUnderstandingRequest {

    private String requestId;
    private String taskGoal;
    private String taskFamily;
    private Map<String, Object> sceneParams;
    /** 补充信息轮次：运行操作员对missingInfoQuestions的逐条回答，首次提交为空 */
    private List<Map<String, Object>> clarificationAnswers;

    public String getRequestId() { return requestId; }
    public void setRequestId(String requestId) { this.requestId = requestId; }
    public String getTaskGoal() { return taskGoal; }
    public void setTaskGoal(String taskGoal) { this.taskGoal = taskGoal; }
    public String getTaskFamily() { return taskFamily; }
    public void setTaskFamily(String taskFamily) { this.taskFamily = taskFamily; }
    public Map<String, Object> getSceneParams() { return sceneParams; }
    public void setSceneParams(Map<String, Object> sceneParams) { this.sceneParams = sceneParams; }
    public List<Map<String, Object>> getClarificationAnswers() { return clarificationAnswers; }
    public void setClarificationAnswers(List<Map<String, Object>> clarificationAnswers) { this.clarificationAnswers = clarificationAnswers; }
}
