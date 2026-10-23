package com.airport.ai.devicetype.dto;

import com.airport.ai.devicetype.CapabilityTemplate;
import com.airport.ai.devicetype.DeviceTypeCapability;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.time.LocalDateTime;
import java.util.List;

/**
 * 对应附录B 4.7/6.4.1节响应结构，及5.2.4A列表/详情界面元素
 */
public class CapabilityBoundaryView {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private String deviceTypeCode;
    private String deviceTypeName;
    private List<String> supportedCapabilityTypes;
    private List<String> unsupportedCapabilityTypes;
    private String typeDescription;
    private String constraintRules;
    private String typicalScenarios;
    private Integer templateCount;
    private Integer instanceCount;
    private LocalDateTime updatedAt;
    private String updatedBy;
    private List<TemplateSummary> templates;

    public static class TemplateSummary {
        private String templateCode;
        private String capabilityType;
        private String templateVersion;
        private String templateStatus;

        public static TemplateSummary from(CapabilityTemplate t) {
            TemplateSummary s = new TemplateSummary();
            s.templateCode = t.getTemplateCode();
            s.capabilityType = t.getCapabilityType();
            s.templateVersion = t.getTemplateVersion();
            s.templateStatus = t.getTemplateStatus();
            return s;
        }

        public String getTemplateCode() { return templateCode; }
        public String getCapabilityType() { return capabilityType; }
        public String getTemplateVersion() { return templateVersion; }
        public String getTemplateStatus() { return templateStatus; }
    }

    public static CapabilityBoundaryView from(DeviceTypeCapability entity, List<CapabilityTemplate> templates, int instanceCount) {
        CapabilityBoundaryView v = new CapabilityBoundaryView();
        v.deviceTypeCode = entity.getDeviceTypeCode();
        v.deviceTypeName = entity.getDeviceTypeName();
        v.supportedCapabilityTypes = parseArray(entity.getSupportedCapabilityTypes());
        v.unsupportedCapabilityTypes = com.airport.ai.devicetype.CapabilityCatalog.ALL_CODES.stream()
                .filter(c -> !v.supportedCapabilityTypes.contains(c))
                .toList();
        v.typeDescription = entity.getTypeDescription();
        v.constraintRules = entity.getConstraintRules();
        v.typicalScenarios = entity.getTypicalScenarios();
        v.templateCount = templates.size();
        v.instanceCount = instanceCount;
        v.updatedAt = entity.getUpdatedAt();
        v.updatedBy = entity.getUpdatedBy();
        v.templates = templates.stream().map(TemplateSummary::from).toList();
        return v;
    }

    private static List<String> parseArray(String json) {
        try {
            return MAPPER.readValue(json, MAPPER.getTypeFactory().constructCollectionType(List.class, String.class));
        } catch (Exception e) {
            throw new RuntimeException("解析supportedCapabilityTypes失败: " + json, e);
        }
    }

    public String getDeviceTypeCode() { return deviceTypeCode; }
    public String getDeviceTypeName() { return deviceTypeName; }
    public List<String> getSupportedCapabilityTypes() { return supportedCapabilityTypes; }
    public List<String> getUnsupportedCapabilityTypes() { return unsupportedCapabilityTypes; }
    public String getTypeDescription() { return typeDescription; }
    public String getConstraintRules() { return constraintRules; }
    public String getTypicalScenarios() { return typicalScenarios; }
    public Integer getTemplateCount() { return templateCount; }
    public Integer getInstanceCount() { return instanceCount; }
    public LocalDateTime getUpdatedAt() { return updatedAt; }
    public String getUpdatedBy() { return updatedBy; }
    public List<TemplateSummary> getTemplates() { return templates; }
}
