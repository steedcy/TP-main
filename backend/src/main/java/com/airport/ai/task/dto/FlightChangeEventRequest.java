package com.airport.ai.task.dto;

import com.fasterxml.jackson.annotation.JsonAnySetter;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

import java.util.HashMap;
import java.util.Map;

/**
 * SRS_F026.R01 / TC-080.S1: 仿真体航班变动事件请求 DTO。
 * 支持双触发入口之一：仿真体事件触发（与运行操作员手工录入对应）；
 * 航班号2~10位必填；变动类型必填（DELAY/EARLY/GATE_CHANGE/CANCEL）；原计划时间必填；
 * 变更内容说明1~200位必填；延误/提前变动新时间必填；登机口变更时新登机口必填。
 */
public class FlightChangeEventRequest {

    @NotBlank(message = "航班号不能为空")
    @Size(min = 2, max = 10, message = "航班号长度须为2~10位")
    private String flightNumber;

    @NotBlank(message = "变更类型不能为空")
    private String changeType;

    @NotBlank(message = "原计划时间不能为空")
    private String originalTime;

    private String newTime;

    private String originalGate;

    private String newGate;

    @NotBlank(message = "变更内容说明不能为空")
    @Size(min = 1, max = 200, message = "变更内容说明不得超过200位")
    private String changeDescription;

    private String eventSource = "SIMULATED_EVENT";

    private Integer displayDuration = 60;

    private Map<String, Object> extraParams = new HashMap<>();

    public String getFlightNumber() { return flightNumber; }
    public void setFlightNumber(String flightNumber) { this.flightNumber = flightNumber; }

    public String getChangeType() { return changeType; }
    public void setChangeType(String changeType) { this.changeType = changeType; }

    public String getOriginalTime() { return originalTime; }
    public void setOriginalTime(String originalTime) { this.originalTime = originalTime; }

    public String getNewTime() { return newTime; }
    public void setNewTime(String newTime) { this.newTime = newTime; }

    public String getOriginalGate() { return originalGate; }
    public void setOriginalGate(String originalGate) { this.originalGate = originalGate; }

    public String getNewGate() { return newGate; }
    public void setNewGate(String newGate) { this.newGate = newGate; }

    public String getChangeDescription() { return changeDescription; }
    public void setChangeDescription(String changeDescription) { this.changeDescription = changeDescription; }

    public String getEventSource() { return eventSource; }
    public void setEventSource(String eventSource) { this.eventSource = eventSource; }

    public Integer getDisplayDuration() { return displayDuration; }
    public void setDisplayDuration(Integer displayDuration) { this.displayDuration = displayDuration; }

    public Map<String, Object> getExtraParams() { return extraParams; }
    public void setExtraParams(Map<String, Object> extraParams) { this.extraParams = extraParams; }

    @JsonAnySetter
    public void setExtraParam(String key, Object value) {
        if (this.extraParams == null) {
            this.extraParams = new HashMap<>();
        }
        this.extraParams.put(key, value);
    }
}
