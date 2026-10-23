package com.airport.ai.baseline.dto;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotEmpty;

import java.util.List;
import java.util.Map;

/**
 * 对应5.3.2界面元素、附录B 6.6节dry-run请求体
 */
public class DryRunRequest {

    private Map<String, Object> inputParams;

    @NotEmpty(message = "请为每个步骤选择模拟设备")
    @Valid
    private List<StepDeviceSelection> simulatedDevices;

    public Map<String, Object> getInputParams() { return inputParams; }
    public void setInputParams(Map<String, Object> inputParams) { this.inputParams = inputParams; }
    public List<StepDeviceSelection> getSimulatedDevices() { return simulatedDevices; }
    public void setSimulatedDevices(List<StepDeviceSelection> simulatedDevices) { this.simulatedDevices = simulatedDevices; }

    public static class StepDeviceSelection {
        private Integer stepSeq;
        private String agentId;

        public Integer getStepSeq() { return stepSeq; }
        public void setStepSeq(Integer stepSeq) { this.stepSeq = stepSeq; }
        public String getAgentId() { return agentId; }
        public void setAgentId(String agentId) { this.agentId = agentId; }
    }
}
