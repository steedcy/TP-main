package com.airport.ai.device;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.*;

/** Applies the configured parameter names, defaults and primitive types at the business boundary. */
public final class ParameterValues {
    private static final ObjectMapper JSON = new ObjectMapper();
    private ParameterValues() {}

    @SuppressWarnings("unchecked")
    public static Map<String, Object> materialize(String schemaJson, Map<String, Object> supplied) {
        try {
            List<Map<String, Object>> schema = JSON.readValue(schemaJson, List.class);
            Map<String, Object> result = new LinkedHashMap<>();
            Set<String> names = new HashSet<>();
            for (Map<String, Object> field : schema) {
                String name = String.valueOf(field.get("name"));
                names.add(name);
                Object value = supplied == null ? null : supplied.get(name);
                if (value == null || value instanceof String s && s.isBlank()) value = field.get("defaultValue");
                if (value == null || value instanceof String s && s.isBlank()) {
                    if (Boolean.TRUE.equals(field.get("required"))) throw new IllegalArgumentException("缺少必填参数: " + name);
                    continue;
                }
                value = convert(value, String.valueOf(field.get("type")), name);
                String range = String.valueOf(field.getOrDefault("range", ""));
                if (range.matches("-?\\d+(\\.\\d+)?[~～]-?\\d+(\\.\\d+)?") && value instanceof Number n) {
                    String[] ends = range.split("[~～]");
                    if (n.doubleValue() < Double.parseDouble(ends[0]) || n.doubleValue() > Double.parseDouble(ends[1]))
                        throw new IllegalArgumentException("参数超出范围: " + name);
                } else if (range.matches("[A-Z_]+(/[A-Z_]+)+") && !List.of(range.split("/")).contains(String.valueOf(value))) {
                    throw new IllegalArgumentException("参数枚举值不合法: " + name);
                }
                result.put(name, value);
            }
            if (supplied != null && !names.containsAll(supplied.keySet())) {
                Set<String> extra = new HashSet<>(supplied.keySet()); extra.removeAll(names);
                throw new IllegalArgumentException("未声明的参数: " + extra);
            }
            return result;
        } catch (IllegalArgumentException ex) { throw ex; }
        catch (Exception ex) { throw new IllegalArgumentException("参数定义无法解析", ex); }
    }

    private static Object convert(Object value, String type, String name) {
        try {
            return switch (type) {
                case "String" -> { if (!(value instanceof String)) throw new IllegalArgumentException(); yield value; }
                case "Integer" -> {
                    double number = Double.parseDouble(String.valueOf(value));
                    if (!Double.isFinite(number) || number != (int)number) throw new IllegalArgumentException();
                    yield (int)number;
                }
                case "Double" -> {
                    double number = Double.parseDouble(String.valueOf(value));
                    if (!Double.isFinite(number)) throw new IllegalArgumentException(); yield number;
                }
                case "Boolean" -> {
                    if (!Set.of("true", "false").contains(String.valueOf(value))) throw new IllegalArgumentException();
                    yield Boolean.parseBoolean(String.valueOf(value));
                }
                default -> throw new IllegalArgumentException();
            };
        } catch (IllegalArgumentException ex) { throw new IllegalArgumentException("参数类型不合法: " + name + " 应为 " + type); }
    }
}
