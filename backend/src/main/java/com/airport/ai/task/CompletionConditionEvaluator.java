package com.airport.ai.task;

import java.math.BigDecimal;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/** Compares explicit plan predicates with device business output before advancing a step. */
final class CompletionConditionEvaluator {
    private static final Pattern EQUALITY = Pattern.compile(
            "(?<![A-Za-z0-9_])([A-Za-z][A-Za-z0-9_]*)\\s*=(?!=)\\s*(true|false|[A-Za-z_][A-Za-z0-9_]*|-?\\d+(?:\\.\\d+)?)",
            Pattern.CASE_INSENSITIVE);

    private CompletionConditionEvaluator() {}

    static boolean satisfied(Map<String, Object> step, Map<String, Object> output) {
        if (step == null || output == null || output.isEmpty() || Boolean.FALSE.equals(output.get("completed"))) {
            return false;
        }
        String condition = String.valueOf(step.getOrDefault("completionCondition", ""));
        Matcher predicates = EQUALITY.matcher(condition);
        boolean hasPredicate = false;
        while (predicates.find()) {
            hasPredicate = true;
            if (!equalsExpected(output.get(predicates.group(1)), predicates.group(2))) return false;
        }
        if (hasPredicate) return true;

        // Older model responses describe completion in prose. Require the physical
        // device's business result for that capability; an HTTP/receipt flag alone
        // cannot finish the step.
        String marker = switch (String.valueOf(step.get("capabilityType"))) {
            case "CAP_INFO_DISPLAY" -> "displayStatus";
            case "CAP_FLIGHT_UPDATE" -> "publishStatus";
            case "CAP_BAGGAGE_MEASURE" -> "measureStatus";
            case "CAP_OVERSIZE_ALERT" -> "reportStatus";
            case "CAP_ESCORT" -> "arrivalStatus";
            case "CAP_NOTIFICATION" -> "notificationStatus";
            case "CAP_NAVIGATION" -> "routeGenerated";
            default -> "completed";
        };
        Object value = output.get(marker);
        return switch (marker) {
            case "arrivalStatus" -> equalsExpected(value, "ARRIVED");
            case "routeGenerated", "completed" -> equalsExpected(value, "true");
            default -> equalsExpected(value, "SUCCESS");
        };
    }

    private static boolean equalsExpected(Object actual, String expected) {
        if (actual == null) return false;
        if ("true".equalsIgnoreCase(expected) || "false".equalsIgnoreCase(expected)) {
            return actual instanceof Boolean b ? b == Boolean.parseBoolean(expected)
                    : expected.equalsIgnoreCase(String.valueOf(actual));
        }
        if (actual instanceof Number number) {
            try {
                return new BigDecimal(number.toString()).compareTo(new BigDecimal(expected)) == 0;
            } catch (NumberFormatException ignored) {
                return false;
            }
        }
        return expected.equalsIgnoreCase(String.valueOf(actual));
    }
}
