package com.airport.ai.taskdef.dto;

import com.airport.ai.taskdef.TaskDefinition;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

public class TaskDefinitionView {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private Long id;
    private String definitionCode;
    private String taskName;
    private String goalTemplate;
    private List<Map<String, Object>> sceneParams;
    private List<String> availableCapabilityTypes;
    private String constraintDescription;
    private String completionCondition;
    private Boolean isPreset;
    private String definitionStatus;
    private LocalDateTime updatedAt;
    private String updatedBy;

    public static TaskDefinitionView from(TaskDefinition d) {
        TaskDefinitionView v = new TaskDefinitionView();
        v.id = d.getId();
        v.definitionCode = d.getDefinitionCode();
        v.taskName = d.getTaskName();
        v.goalTemplate = d.getGoalTemplate();
        v.sceneParams = parseListOfMap(d.getSceneParams());
        v.availableCapabilityTypes = parseListOfString(d.getAvailableCapabilityTypes());
        v.constraintDescription = d.getConstraintDescription();
        v.completionCondition = d.getCompletionCondition();
        v.isPreset = d.getIsPreset();
        v.definitionStatus = d.getDefinitionStatus();
        v.updatedAt = d.getUpdatedAt();
        v.updatedBy = d.getUpdatedBy();
        return v;
    }

    private static List<Map<String, Object>> parseListOfMap(String json) {
        try {
            return MAPPER.readValue(json, MAPPER.getTypeFactory().constructCollectionType(List.class, Map.class));
        } catch (Exception e) {
            throw new RuntimeException("解析失败: " + json, e);
        }
    }

    private static List<String> parseListOfString(String json) {
        try {
            return MAPPER.readValue(json, MAPPER.getTypeFactory().constructCollectionType(List.class, String.class));
        } catch (Exception e) {
            throw new RuntimeException("解析失败: " + json, e);
        }
    }

    public Long getId() { return id; }
    public String getDefinitionCode() { return definitionCode; }
    public String getTaskName() { return taskName; }
    public String getGoalTemplate() { return goalTemplate; }
    public List<Map<String, Object>> getSceneParams() { return sceneParams; }
    public List<String> getAvailableCapabilityTypes() { return availableCapabilityTypes; }
    public String getConstraintDescription() { return constraintDescription; }
    public String getCompletionCondition() { return completionCondition; }
    public Boolean getIsPreset() { return isPreset; }
    public String getDefinitionStatus() { return definitionStatus; }
    public LocalDateTime getUpdatedAt() { return updatedAt; }
    public String getUpdatedBy() { return updatedBy; }
}
