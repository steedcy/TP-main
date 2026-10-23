package com.airport.ai.devicetype.dto;

import com.airport.ai.devicetype.CapabilityTemplate;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.time.LocalDateTime;
import java.util.List;

public class CapabilityTemplateView {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private Long id;
    private String deviceTypeCode;
    private String templateCode;
    private String templateName;
    private String capabilityType;
    private List<ParamDefinition> inputParams;
    private List<ParamDefinition> outputParams;
    private String templateVersion;
    private String templateStatus;
    private String templateDescription;
    private Integer usageCount;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;

    public static CapabilityTemplateView from(CapabilityTemplate t) {
        CapabilityTemplateView v = new CapabilityTemplateView();
        v.id = t.getId();
        v.deviceTypeCode = t.getDeviceTypeCode();
        v.templateCode = t.getTemplateCode();
        v.templateName = t.getTemplateName();
        v.capabilityType = t.getCapabilityType();
        v.inputParams = parseParams(t.getInputParams());
        v.outputParams = parseParams(t.getOutputParams());
        v.templateVersion = t.getTemplateVersion();
        v.templateStatus = t.getTemplateStatus();
        v.templateDescription = t.getTemplateDescription();
        v.usageCount = t.getUsageCount();
        v.createdAt = t.getCreatedAt();
        v.updatedAt = t.getUpdatedAt();
        return v;
    }

    private static List<ParamDefinition> parseParams(String json) {
        try {
            return MAPPER.readValue(json, MAPPER.getTypeFactory().constructCollectionType(List.class, ParamDefinition.class));
        } catch (Exception e) {
            throw new RuntimeException("解析参数定义失败: " + json, e);
        }
    }

    public Long getId() { return id; }
    public String getDeviceTypeCode() { return deviceTypeCode; }
    public String getTemplateCode() { return templateCode; }
    public String getTemplateName() { return templateName; }
    public String getCapabilityType() { return capabilityType; }
    public List<ParamDefinition> getInputParams() { return inputParams; }
    public List<ParamDefinition> getOutputParams() { return outputParams; }
    public String getTemplateVersion() { return templateVersion; }
    public String getTemplateStatus() { return templateStatus; }
    public String getTemplateDescription() { return templateDescription; }
    public Integer getUsageCount() { return usageCount; }
    public LocalDateTime getCreatedAt() { return createdAt; }
    public LocalDateTime getUpdatedAt() { return updatedAt; }
}
