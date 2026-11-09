package com.airport.ai.task;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Set;

/** System-side required-field check for F026 flight-change events. */
public final class FlightChangeRequiredInfoGuard {
    private static final Set<String> CHANGE_TYPES = Set.of("DELAY", "EARLY", "GATE_CHANGE", "CANCEL");

    public record Verdict(boolean complete, List<String> questions, List<String> missing) {}

    private record Field(String key, String question) {}

    private static final List<Field> BASE_FIELDS = List.of(
            new Field("flightNumber", "请补充航班号"),
            new Field("changeType", "请补充有效的航班变更类型"),
            new Field("originalTime", "请补充原计划时间"),
            new Field("changeDescription", "请补充航班变更内容"));

    private FlightChangeRequiredInfoGuard() {}

    /**
     * Checks the F026 baseline fields and the conditional fields for delay/early and gate changes.
     * Physical device and route choices are intentionally outside the operator's required inputs.
     */
    public static Verdict check(Map<String, Object> scene) {
        List<Field> required = new ArrayList<>(BASE_FIELDS);
        Object rawType = scene == null ? null : scene.get("changeType");
        if (rawType == null && scene != null) {
            rawType = extractFromClarification(scene.get("clarificationAnswers"), "请补充有效的航班变更类型");
        }
        String changeType = rawType == null ? null : rawType.toString().trim();
        if ("DELAY".equals(changeType) || "EARLY".equals(changeType)) {
            required.add(new Field("newTime", "请补充变更后的航班时间"));
        } else if ("GATE_CHANGE".equals(changeType)) {
            required.add(new Field("newGate", "请补充变更后的登机口"));
        }

        List<String> missing = new ArrayList<>();
        List<String> questions = new ArrayList<>();
        for (Field field : required) {
            if (!isProvided(field, scene)) {
                missing.add(field.key());
                questions.add(field.question());
            }
        }
        if (hasValue(rawType) && !CHANGE_TYPES.contains(changeType)) {
            missing.add("changeType");
            questions.remove("请补充有效的航班变更类型");
            questions.add("请补充有效的航班变更类型");
        }
        return new Verdict(missing.isEmpty(), List.copyOf(questions), List.copyOf(missing));
    }

    private static boolean isProvided(Field field, Map<String, Object> scene) {
        if (scene == null) return false;
        if (hasValue(scene.get(field.key()))) return true;
        return hasValue(extractFromClarification(scene.get("clarificationAnswers"), field.question()));
    }

    private static Object extractFromClarification(Object rounds, String question) {
        if (rounds instanceof Iterable<?> list) {
            for (Object round : list) {
                if (round instanceof Map<?, ?> roundMap) {
                    Object answers = roundMap.get("answers");
                    if (answers instanceof Map<?, ?> byQuestion && hasValue(byQuestion.get(question))) {
                        return byQuestion.get(question);
                    }
                }
            }
        }
        return null;
    }

    private static boolean hasValue(Object value) {
        if (value == null) return false;
        if (value instanceof String text) {
            String stripped = text.replaceAll("\\[PROTECTED_[A-Z]+\\]|[;；,，\\s]", "");
            return !stripped.isBlank();
        }
        if (value instanceof Iterable<?> values) return values.iterator().hasNext();
        if (value instanceof Map<?, ?> values) return !values.isEmpty();
        return true;
    }
}
