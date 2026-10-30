package com.airport.ai.device.dto;

import com.airport.ai.device.DeviceCapability;
import com.airport.ai.devicetype.dto.ParamDefinition;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.time.LocalDateTime;
import java.util.List;

public class DeviceCapabilityView {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private Long id;
    private String capabilityCode;
    private String capabilityName;
    private String capabilityType;
    private List<ParamDefinition> inputParams;
    private List<ParamDefinition> outputParams;
    private String applicableConditions;
    private String capabilityStatus;
    private String testResult;
    private LocalDateTime lastTestAt;
    private String testRequest;
    private String testResponse;
    private Long testDurationMs;
    private String capabilityDescription;

    public static DeviceCapabilityView from(DeviceCapability c) {
        DeviceCapabilityView v = new DeviceCapabilityView();
        v.id = c.getId();
        v.capabilityCode = c.getCapabilityCode();
        v.capabilityName = c.getCapabilityName();
        v.capabilityType = c.getCapabilityType();
        v.inputParams = parseParams(c.getInputParams());
        v.outputParams = parseParams(c.getOutputParams());
        v.applicableConditions = c.getApplicableConditions();
        v.capabilityStatus = c.getCapabilityStatus();
        v.testResult = c.getTestResult();
        v.lastTestAt = c.getLastTestAt();
        v.testRequest = c.getTestRequest();
        v.testResponse = c.getTestResponse();
        v.testDurationMs = c.getTestDurationMs();
        v.capabilityDescription = c.getCapabilityDescription();
        return v;
    }

    private static List<ParamDefinition> parseParams(String json) {
        try {
            return MAPPER.readValue(json, MAPPER.getTypeFactory().constructCollectionType(List.class, ParamDefinition.class));
        } catch (Exception e) {
            throw new RuntimeException("解析参数定义失败: " + json, e);
        }
    }

    public String getTestRequest() { return testRequest; }
    public String getTestResponse() { return testResponse; }
    public Long getTestDurationMs() { return testDurationMs; }
    public Long getId() { return id; }
    public String getCapabilityCode() { return capabilityCode; }
    public String getCapabilityName() { return capabilityName; }
    public String getCapabilityType() { return capabilityType; }
    public List<ParamDefinition> getInputParams() { return inputParams; }
    public List<ParamDefinition> getOutputParams() { return outputParams; }
    public String getApplicableConditions() { return applicableConditions; }
    public String getCapabilityStatus() { return capabilityStatus; }
    public String getTestResult() { return testResult; }
    public LocalDateTime getLastTestAt() { return lastTestAt; }
    public String getCapabilityDescription() { return capabilityDescription; }
}
