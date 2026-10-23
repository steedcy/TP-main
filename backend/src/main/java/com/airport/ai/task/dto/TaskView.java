package com.airport.ai.task.dto;

import com.airport.ai.task.Task;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

public class TaskView {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private Long id;
    private String taskCode;
    private String taskGoal;
    private String taskFamily;
    private Map<String, Object> sceneParams;
    private Map<String, Object> goalParsingResult;
    private String status;
    private Long currentPlanVersionId;
    private Boolean replanUsed;
    private String replanningReason;
    private String manualTerminateReason;
    private String failureReason;
    private List<String> missingInfoQuestions;
    private String downgradeReason;
    private Boolean isDryRun;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
    private String createdBy;

    public static TaskView from(Task t) {
        TaskView v = new TaskView();
        v.id = t.getId();
        v.taskCode = t.getTaskCode();
        v.taskGoal = t.getTaskGoal();
        v.taskFamily = t.getTaskFamily();
        v.sceneParams = parseMap(t.getSceneParams());
        v.goalParsingResult = parseMap(t.getGoalParsingResult());
        v.status = t.getStatus() == null ? null : t.getStatus().name();
        v.currentPlanVersionId = t.getCurrentPlanVersionId();
        v.replanUsed = t.getReplanUsed();
        v.replanningReason = t.getReplanningReason();
        v.manualTerminateReason = t.getManualTerminateReason();
        v.failureReason = t.getFailureReason();
        v.missingInfoQuestions = parseList(t.getMissingInfoQuestions());
        v.downgradeReason = t.getDowngradeReason();
        v.isDryRun = t.getIsDryRun();
        v.createdAt = t.getCreatedAt();
        v.updatedAt = t.getUpdatedAt();
        v.createdBy = t.getCreatedBy();
        return v;
    }

    private static Map<String, Object> parseMap(String json) {
        if (json == null || json.isBlank()) return null;
        try {
            return MAPPER.readValue(json, Map.class);
        } catch (Exception e) {
            throw new RuntimeException("解析失败: " + json, e);
        }
    }

    private static List<String> parseList(String json) {
        if (json == null || json.isBlank()) return null;
        try {
            return MAPPER.readValue(json, List.class);
        } catch (Exception e) {
            throw new RuntimeException("解析失败: " + json, e);
        }
    }

    public Long getId() { return id; }
    public String getTaskCode() { return taskCode; }
    public String getTaskGoal() { return taskGoal; }
    public String getTaskFamily() { return taskFamily; }
    public Map<String, Object> getSceneParams() { return sceneParams; }
    public Map<String, Object> getGoalParsingResult() { return goalParsingResult; }
    public String getStatus() { return status; }
    public Long getCurrentPlanVersionId() { return currentPlanVersionId; }
    public Boolean getReplanUsed() { return replanUsed; }
    public String getReplanningReason() { return replanningReason; }
    public String getManualTerminateReason() { return manualTerminateReason; }
    public String getFailureReason() { return failureReason; }
    public List<String> getMissingInfoQuestions() { return missingInfoQuestions; }
    public String getDowngradeReason() { return downgradeReason; }
    public Boolean getIsDryRun() { return isDryRun; }
    public LocalDateTime getCreatedAt() { return createdAt; }
    public LocalDateTime getUpdatedAt() { return updatedAt; }
    public String getCreatedBy() { return createdBy; }
}
