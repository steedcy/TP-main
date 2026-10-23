package com.airport.ai.baseline.dto;

import com.airport.ai.baseline.BaselineTemplate;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

public class BaselineTemplateView {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private Long id;
    private String templateName;
    private String templateIntent;
    private Boolean isPreset;
    private List<Map<String, Object>> inputParams;
    private List<Map<String, Object>> steps;
    private String templateVersion;
    private String templateStatus;
    private LocalDateTime updatedAt;
    private String updatedBy;

    public static BaselineTemplateView from(BaselineTemplate t) {
        BaselineTemplateView v = new BaselineTemplateView();
        v.id = t.getId();
        v.templateName = t.getTemplateName();
        v.templateIntent = t.getTaskFamily();
        v.isPreset = t.getIsPreset();
        v.inputParams = parseListOfMap(t.getInputParams());
        v.steps = parseListOfMap(t.getSteps());
        v.templateVersion = t.getTemplateVersion();
        v.templateStatus = t.getTemplateStatus();
        v.updatedAt = t.getUpdatedAt();
        v.updatedBy = t.getUpdatedBy();
        return v;
    }

    private static List<Map<String, Object>> parseListOfMap(String json) {
        try {
            return MAPPER.readValue(json, MAPPER.getTypeFactory().constructCollectionType(List.class, Map.class));
        } catch (Exception e) {
            throw new RuntimeException("解析失败: " + json, e);
        }
    }

    public Long getId() { return id; }
    public String getTemplateName() { return templateName; }
    public String getTemplateIntent() { return templateIntent; }
    public Boolean getIsPreset() { return isPreset; }
    public List<Map<String, Object>> getInputParams() { return inputParams; }
    public List<Map<String, Object>> getSteps() { return steps; }
    public String getTemplateVersion() { return templateVersion; }
    public String getTemplateStatus() { return templateStatus; }
    public LocalDateTime getUpdatedAt() { return updatedAt; }
    public String getUpdatedBy() { return updatedBy; }
}
