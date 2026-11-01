package com.airport.ai.task;

import com.airport.ai.device.ParameterValues;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 基线降级时把任务信息绑定到模板输入（SRS_F008.R03、TC-025.S2，DEF-S3-085）。
 *
 * 每个模板输入按这个优先级取值：
 * 1. 提交时显式给出的场景参数（同名）；
 * 2. 目标理解解析出的值（目的地/起点按名称映射）；
 * 3. 模板默认值。
 *
 * 第 3 项只有在前两项都没有时才用。对“指向地点”的输入，用默认值会改写任务想去的地方，
 * 所以结果里会列出这类输入，调用方据此写一条可追溯的事件，而不是悄悄套用默认值。
 */
public final class TemplateInputBinder {
    private static final ObjectMapper JSON = new ObjectMapper();

    /** 模板输入名 → 目标理解结果里的字段。只映射语义明确的两个地点字段。 */
    private static final Map<String, String> PARSED_FIELD_BY_INPUT = Map.of(
            "targetLocation", "destination",
            "destination", "destination",
            "targetPlace", "destination",
            "originLocation", "origin",
            "origin", "origin",
            "startLocation", "origin");

    private TemplateInputBinder() {}

    public record Result(Map<String, Object> values, List<String> fromParsedGoal, List<String> defaultedLocations) {}

    @SuppressWarnings("unchecked")
    public static Result bind(String templateInputParamsJson, Map<String, Object> scene, Map<String, Object> parsedGoal)
            throws Exception {
        List<Map<String, Object>> fields = templateInputParamsJson == null ? List.of()
                : JSON.readValue(templateInputParamsJson, List.class);
        Map<String, Object> supplied = new LinkedHashMap<>();
        List<String> fromParsed = new ArrayList<>();
        List<String> defaultedLocations = new ArrayList<>();
        for (Map<String, Object> field : fields) {
            String name = String.valueOf(field.get("name"));
            Object explicit = scene == null ? null : scene.get(name);
            if (!isBlank(explicit)) {
                supplied.put(name, explicit);
                continue;
            }
            String parsedKey = PARSED_FIELD_BY_INPUT.get(name);
            Object parsed = parsedKey == null || parsedGoal == null ? null : parsedGoal.get(parsedKey);
            if (!isBlank(parsed)) {
                supplied.put(name, String.valueOf(parsed).trim());
                fromParsed.add(name);
            } else if (parsedKey != null && !isBlank(field.get("defaultValue"))) {
                defaultedLocations.add(name);
            }
        }
        // 类型转换、范围与必填由 ParameterValues 统一处理；这里只决定“用谁的值”
        Map<String, Object> values = ParameterValues.materialize(templateInputParamsJson, supplied);
        return new Result(values, fromParsed, defaultedLocations);
    }

    private static boolean isBlank(Object v) {
        return v == null || (v instanceof String s && s.isBlank());
    }
}
