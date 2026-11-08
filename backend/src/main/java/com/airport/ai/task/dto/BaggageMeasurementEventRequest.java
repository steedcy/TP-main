package com.airport.ai.task.dto;

import com.fasterxml.jackson.annotation.JsonAnySetter;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;

import java.util.HashMap;
import java.util.Map;

/**
 * SRS_F024.R01 / NT-S3-004: 模拟行李测量事件请求 DTO。
 * 支持两种触发方式之一：系统接收模拟测量事件；
 * 测量设备返回长宽高尺寸、重量与超规结果三项数据；
 * 行李所在位置必填，目标柜台可选（不填由规划依据场景参数与约束确定）；
 * 临时业务编号关联，不保存旅客真实身份信息。
 */
public class BaggageMeasurementEventRequest {

    @NotBlank(message = "行李位置不能为空")
    private String baggageLocation;

    /** 可选目标柜台，不填由规划依据场景参数/约束确定（SRS §5.6.3） */
    private String targetCounter;

    /** 可选临时业务编号（如 BAG-001），不填自动生成，不保存真实身份（SRS_F024.R09） */
    private String baggageId;

    @NotNull(message = "长度不能为空")
    @Positive(message = "长度必须大于0")
    private Double length;

    @NotNull(message = "宽度不能为空")
    @Positive(message = "宽度必须大于0")
    private Double width;

    @NotNull(message = "高度不能为空")
    @Positive(message = "高度必须大于0")
    private Double height;

    @NotNull(message = "重量不能为空")
    @Positive(message = "重量必须大于0")
    private Double weight;

    /** 超规判定三边和阈值，默认 158.0 cm */
    private Double dimensionThresholdCm;

    /** 超规判定重量阈值，默认 23.0 kg */
    private Double weightThresholdKg;

    /** 超规判定阈值来源，默认“民航旅客行李运输标准（2026版）” */
    private String thresholdSource;

    /** 自定义超规办理说明文本（可选） */
    private String handlingInstructions;

    /** 测量设备编码（可选） */
    private String deviceCode;

    private Map<String, Object> extraParams = new HashMap<>();

    public BaggageMeasurementEventRequest() {}

    public String getBaggageLocation() { return baggageLocation; }
    public void setBaggageLocation(String baggageLocation) { this.baggageLocation = baggageLocation; }

    public String getTargetCounter() { return targetCounter; }
    public void setTargetCounter(String targetCounter) { this.targetCounter = targetCounter; }

    public String getBaggageId() { return baggageId; }
    public void setBaggageId(String baggageId) { this.baggageId = baggageId; }

    public Double getLength() { return length; }
    public void setLength(Double length) { this.length = length; }

    public Double getWidth() { return width; }
    public void setWidth(Double width) { this.width = width; }

    public Double getHeight() { return height; }
    public void setHeight(Double height) { this.height = height; }

    public Double getWeight() { return weight; }
    public void setWeight(Double weight) { this.weight = weight; }

    public Double getDimensionThresholdCm() { return dimensionThresholdCm; }
    public void setDimensionThresholdCm(Double dimensionThresholdCm) { this.dimensionThresholdCm = dimensionThresholdCm; }

    public Double getWeightThresholdKg() { return weightThresholdKg; }
    public void setWeightThresholdKg(Double weightThresholdKg) { this.weightThresholdKg = weightThresholdKg; }

    public String getThresholdSource() { return thresholdSource; }
    public void setThresholdSource(String thresholdSource) { this.thresholdSource = thresholdSource; }

    public String getHandlingInstructions() { return handlingInstructions; }
    public void setHandlingInstructions(String handlingInstructions) { this.handlingInstructions = handlingInstructions; }

    public String getDeviceCode() { return deviceCode; }
    public void setDeviceCode(String deviceCode) { this.deviceCode = deviceCode; }

    @JsonAnySetter
    public void setExtraParam(String key, Object value) {
        if (extraParams == null) extraParams = new HashMap<>();
        extraParams.put(key, value);
    }

    public Map<String, Object> getExtraParams() { return extraParams; }
    public void setExtraParams(Map<String, Object> extraParams) { this.extraParams = extraParams; }
}
