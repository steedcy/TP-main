package com.airport.ai.task;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * SRS_F012.R01/R02/R10 步骤计数口径：每个候选计划版本最多5个可执行步骤。
 * <ul>
 *   <li>条件节点（nodeType/stepType/type=CONDITION，或conditionNode=true）只表达分支判断，不下发设备、不计数；</li>
 *   <li>条件分支里的业务动作是普通可执行步骤，通过branchOf指向条件节点序号，照常计数；</li>
 *   <li>计划按顺序执行且分支动作同样计入上限，所以实际执行路径步骤数不会超过版本可执行步骤数；</li>
 *   <li>重试、失败事件不产生新步骤，不影响计数。</li>
 * </ul>
 * 通过校验后条件节点被折叠进分支动作的branchCondition字段，冻结版本中只保留可执行步骤，
 * 执行链路（设备分配、完成判定）因此不需要认识条件节点。
 */
public final class PlanStepRules {

    /** 每个候选计划版本可执行步骤数上限，初始剩余额度即该值。 */
    public static final int MAX_EXECUTABLE_STEPS = 5;

    private static final Set<String> CONDITION_TYPES = Set.of("CONDITION", "CONDITIONAL", "CONDITION_NODE", "BRANCH_CONDITION");

    private PlanStepRules() {}

    public static boolean isConditionNode(Map<String, Object> step) {
        if (step == null) return false;
        if (Boolean.TRUE.equals(step.get("conditionNode"))) return true;
        for (String key : List.of("nodeType", "stepType", "type")) {
            Object value = step.get(key);
            if (value instanceof String s && CONDITION_TYPES.contains(s.trim().toUpperCase())) return true;
        }
        return false;
    }

    /** 条件节点的判断表达式：优先condition，其次stepGoal。 */
    public static String conditionText(Map<String, Object> step) {
        for (String key : List.of("condition", "stepGoal")) {
            Object value = step.get(key);
            if (value instanceof String s && !s.isBlank()) return s.trim();
        }
        return null;
    }

    /** 可执行步骤数：条件节点不计，其余（含分支动作）全部计数。 */
    public static int executableCount(List<Map<String, Object>> steps) {
        if (steps == null) return 0;
        int count = 0;
        for (Map<String, Object> step : steps) {
            if (step != null && !isConditionNode(step)) count++;
        }
        return count;
    }

    /** 分支动作所属条件节点的序号；无branchOf返回null。 */
    public static Integer branchOf(Map<String, Object> step) {
        Object value = step.get("branchOf");
        if (value == null) return null;
        if (value instanceof Number n) return n.intValue();
        try {
            return Integer.parseInt(String.valueOf(value).trim());
        } catch (NumberFormatException ex) {
            return -1;
        }
    }

    /**
     * 仅当map中完全不包含指定key时放入默认值；
     * 如果已包含key（即使value是null、空串、空白），不覆盖，保留原值供校验器检测（SRS_F012.R04）。
     */
    public static void defaultIfAbsent(Map<String, Object> map, String key, Object defaultValue) {
        if (map != null && !map.containsKey(key)) {
            map.put(key, defaultValue);
        }
    }

    /**
     * 去掉条件节点，只保留可执行步骤；分支动作带上branchCondition（所属条件节点的判断文字）。
     * 没有条件节点时原样返回同一个列表，不改变步骤序号（执行链路按序号大小而不是连续性推进）。
     */
    public static List<Map<String, Object>> foldConditionNodes(List<Map<String, Object>> steps) {
        if (steps == null || steps.stream().noneMatch(PlanStepRules::isConditionNode)) return steps;
        Map<Integer, String> conditions = new LinkedHashMap<>();
        for (int i = 0; i < steps.size(); i++) {
            Map<String, Object> step = steps.get(i);
            if (!isConditionNode(step)) continue;
            Object seq = step.get("stepSeq");
            Integer key = seq instanceof Number n ? Integer.valueOf(n.intValue()) : Integer.valueOf(i + 1);
            conditions.put(key, conditionText(step));
        }
        List<Map<String, Object>> folded = new ArrayList<>();
        for (Map<String, Object> step : steps) {
            if (isConditionNode(step)) continue;
            Map<String, Object> copy = new LinkedHashMap<>(step);
            Integer owner = branchOf(step);
            if (owner != null && conditions.get(owner) != null) {
                copy.put("branchCondition", conditions.get(owner));
            }
            folded.add(copy);
        }
        return folded;
    }
}
