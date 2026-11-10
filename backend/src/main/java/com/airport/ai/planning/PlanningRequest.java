package com.airport.ai.planning;

import java.util.List;
import java.util.Map;

/**
 * 对应附录B 5.1节规划模型服务调用接口请求体
 */
public class PlanningRequest {

    private String requestId;
    private String taskGoal;
    private String taskFamily;
    private Map<String, Object> sceneParams;
    private List<String> constraints;
    private List<Map<String, Object>> capabilityContext;
    private int remainingStepQuota;
    private List<Map<String, Object>> completedSteps;

    public String getRequestId() { return requestId; }
    public void setRequestId(String requestId) { this.requestId = requestId; }
    public String getTaskGoal() { return taskGoal; }
    public void setTaskGoal(String taskGoal) {
        this.taskGoal = com.airport.ai.task.SceneParamsPrivacyGuard.sanitizeGoal(taskGoal);
    }
    public String getTaskFamily() { return taskFamily; }
    public void setTaskFamily(String taskFamily) { this.taskFamily = taskFamily; }
    public Map<String, Object> getSceneParams() { return sceneParams; }
    public void setSceneParams(Map<String, Object> sceneParams) {
        this.sceneParams = com.airport.ai.task.SceneParamsPrivacyGuard.sanitize(sceneParams);
    }
    public List<String> getConstraints() { return constraints; }
    public void setConstraints(List<String> constraints) {
        this.constraints = constraints != null
                ? constraints.stream().map(com.airport.ai.task.SceneParamsPrivacyGuard::sanitizeGoal).toList()
                : null;
    }
    public List<Map<String, Object>> getCapabilityContext() { return capabilityContext; }
    public void setCapabilityContext(List<Map<String, Object>> capabilityContext) { this.capabilityContext = capabilityContext; }
    public int getRemainingStepQuota() { return remainingStepQuota; }
    public void setRemainingStepQuota(int remainingStepQuota) { this.remainingStepQuota = remainingStepQuota; }
    public List<Map<String, Object>> getCompletedSteps() { return completedSteps; }
    public void setCompletedSteps(List<Map<String, Object>> completedSteps) {
        if (completedSteps == null) {
            this.completedSteps = null;
        } else {
            java.util.List<Map<String, Object>> cleaned = new java.util.ArrayList<>();
            for (Map<String, Object> step : completedSteps) {
                cleaned.add(com.airport.ai.task.SceneParamsPrivacyGuard.sanitize(step));
            }
            this.completedSteps = cleaned;
        }
    }
}
