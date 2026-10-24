package com.airport.ai.task;

import com.airport.ai.common.BusinessException;
import com.airport.ai.common.ErrorCode;
import java.time.LocalDateTime;
import java.time.format.DateTimeParseException;
import java.util.Map;
import java.util.Set;

/** Validate the structured manual flight-event entry before creating a task. */
public final class FlightChangeSceneValidator {
    private FlightChangeSceneValidator() {}

    public static void validate(String taskFamily, Map<String, Object> scene) {
        if (!"FLIGHT_CHANGE_RESPONSE".equals(taskFamily) || scene == null
                || !"MANUAL_FORM".equals(scene.get("eventSource"))) return;
        String flight = required(scene, "flightNumber");
        if (flight.length() < 2 || flight.length() > 10) invalid("航班号长度须为2~10位");
        String change = required(scene, "changeType");
        if (!Set.of("DELAY", "EARLY", "GATE_CHANGE", "CANCEL").contains(change)) invalid("变更类型无效");
        timestamp(required(scene, "originalTime"), "原计划时间");
        if (Set.of("DELAY", "EARLY").contains(change)) timestamp(required(scene, "newTime"), "变更后时间");
        else if (scene.get("newTime") != null && !scene.get("newTime").toString().isBlank())
            timestamp(scene.get("newTime").toString(), "变更后时间");
        if ("GATE_CHANGE".equals(change)) required(scene, "newGate");
        String description = required(scene, "changeDescription");
        if (description.length() > 200) invalid("变更内容说明不得超过200位");
    }

    private static String required(Map<String, Object> scene, String key) {
        Object value = scene.get(key);
        if (!(value instanceof String text) || text.isBlank()) {
            throw new BusinessException(ErrorCode.PARAM_MISSING, key + "不能为空");
        }
        return text.trim();
    }

    private static void timestamp(String value, String name) {
        try { LocalDateTime.parse(value); }
        catch (DateTimeParseException ex) { invalid(name + "须为ISO本地日期时间"); }
    }

    private static void invalid(String message) {
        throw new BusinessException(ErrorCode.PARAM_FORMAT_ERROR, message);
    }
}
