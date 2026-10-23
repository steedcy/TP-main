package com.airport.ai.task;

import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * 运动安全控制字段检测，对应5.4.4业务规则3、5.2.5业务规则3、附录B多处"计划只允许包含
 * 业务意图，不得包含速度、加速度、姿态、路径点、避障、急停、限速和失联停靠等运动安全
 * 控制指令"约束。需求全篇反复强调此规则但此前代码库没有任何黑名单实现，本类是首次落地。
 * 扫描范围：步骤的capabilityType/stepGoal/precondition/completionCondition/failureHandling
 * 等文本字段，以及inputParams的全部key和字符串value，命中任一关键词即判定为违规。
 */
public final class MotionSafetyGuard {

    /** 中文关键词直接取自需求原文；英文同义词覆盖常见的运动控制参数命名习惯 */
    private static final Set<String> BLOCKED_KEYWORDS = Set.of(
            "速度", "加速度", "姿态", "路径点", "避障", "急停", "限速", "失联停靠",
            "speed", "velocity", "acceleration", "attitude", "orientation", "waypoint",
            "obstacle", "avoidance", "emergency stop", "e-stop", "estop",
            "speed limit", "speed_limit", "failsafe", "fail-safe", "dock on disconnect"
    );

    private MotionSafetyGuard() {}

    /** 返回命中的关键词清单（用于生成4106错误的详细原因），为空表示未命中，即通过 */
    public static List<String> detect(Map<String, Object> step) {
        List<String> hits = new java.util.ArrayList<>();
        checkText(hits, asString(step.get("capabilityType")));
        checkText(hits, asString(step.get("stepGoal")));
        checkText(hits, asString(step.get("precondition")));
        checkText(hits, asString(step.get("completionCondition")));
        checkText(hits, asString(step.get("failureHandling")));

        Object inputParams = step.get("inputParams");
        if (inputParams instanceof Map<?, ?> map) {
            for (Map.Entry<?, ?> entry : map.entrySet()) {
                checkText(hits, asString(entry.getKey()));
                checkText(hits, asString(entry.getValue()));
            }
        }
        return hits;
    }

    private static void checkText(List<String> hits, String text) {
        if (text == null || text.isBlank()) {
            return;
        }
        String lower = text.toLowerCase();
        for (String keyword : BLOCKED_KEYWORDS) {
            if (lower.contains(keyword.toLowerCase())) {
                hits.add(keyword);
            }
        }
    }

    private static String asString(Object value) {
        return value == null ? null : String.valueOf(value);
    }
}
