package com.airport.ai.devicetype;

import com.airport.ai.devicetype.dto.ParamDefinition;

import java.util.List;
import java.util.Map;

/**
 * 各标准能力类型调用所需的全部必填输入参数名（SRS_F006A.R10）与完成条件判定所需的输出参数名（R11）。
 * 取自标准能力的参数契约（与V18种子模板、F2演示夹具一致）。能力模板的输入必须覆盖必填输入，
 * 输出必须定义，缺失时保存被拒绝并提示缺失的参数名。仿真状态生成无调用输入。
 */
public final class CapabilityContract {

    private static final Map<String, List<String>> REQUIRED_INPUTS = Map.of(
            "CAP_INFO_DISPLAY", List.of("contentType", "contentData", "displayDuration"),
            "CAP_FLIGHT_UPDATE", List.of("flightNumber", "updateType", "updateContent", "displayDuration"),
            "CAP_NAVIGATION", List.of("targetLocation", "routePreference"),
            "CAP_BAGGAGE_MEASURE", List.of("measureMode", "timeout"),
            "CAP_OVERSIZE_ALERT", List.of("baggageInfo", "alertLevel"),
            "CAP_ESCORT", List.of("targetLocation", "escortMode", "maxDuration"),
            "CAP_NOTIFICATION", List.of("notificationType", "notificationContent", "repeatCount"),
            "CAP_SIM_STATUS", List.of());

    private CapabilityContract() {}

    public static List<String> requiredInputs(String capabilityType) {
        return REQUIRED_INPUTS.getOrDefault(capabilityType, List.of());
    }

    /** 返回缺失的必填输入参数名，全部齐备则为空。 */
    public static List<String> missingInputs(String capabilityType, List<ParamDefinition> inputs) {
        List<String> defined = inputs == null ? List.of()
                : inputs.stream().map(ParamDefinition::getName).toList();
        return requiredInputs(capabilityType).stream().filter(n -> !defined.contains(n)).toList();
    }
}
