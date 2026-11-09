package com.airport.ai.event;

import java.util.Map;

/**
 * 任务事件的默认原因码（SRS_F027.R02，DEF-S3-057）：每条事件都要有原因码。
 *
 * 调用方显式给出的原因码一律保留，只有在调用方没给（null或空白）时才按事件类型补一个稳定的码。
 * 正常流转（提交、规划、分配、完成等）没有“错误原因”，这里用 <code>NORMAL_*</code> 前缀的流程码标明
 * 是哪一步，避免和 <code>ERR_*</code>/<code>WARN_*</code> 的异常原因码混淆。
 * 没有登记的事件类型用 <code>NORMAL_EVENT</code>，不留空。
 */
public final class EventReasonCodes {
    private EventReasonCodes() {}

    private static final Map<String, String> DEFAULTS = Map.ofEntries(
            // 提交与目标理解
            Map.entry("GOAL_SUBMITTED", "NORMAL_GOAL_SUBMITTED"),
            Map.entry("GOAL_CLARIFIED", "NORMAL_GOAL_CLARIFIED"),
            Map.entry("TASK_GOAL_UPDATED", "NORMAL_TASK_GOAL_UPDATED"),
            // 规划与校验
            Map.entry("CONTEXT_SNAPSHOT_GENERATED", "NORMAL_CONTEXT_BUILT"),
            Map.entry("PLAN_GENERATED", "NORMAL_PLAN_GENERATED"),
            Map.entry("PLAN_VALIDATED", "NORMAL_PLAN_VALIDATED"),
            Map.entry("SUPERVISION_JUDGED", "NORMAL_SUPERVISION_JUDGED"),
            Map.entry("FORCE_BYPASS_INTERCEPTED", "ERR_FORCE_BYPASS_INTERCEPTED"),
            // 降级与重规划
            Map.entry("BASELINE_DOWNGRADED", "NORMAL_BASELINE_DOWNGRADED"),
            Map.entry("BASELINE_SWITCH_REQUESTED", "NORMAL_BASELINE_SWITCH_REQUESTED"),
            Map.entry("REPLANNING_TRIGGERED", "NORMAL_REPLANNING_TRIGGERED"),
            Map.entry("PLAN_CONTINUATION_JUDGED", "NORMAL_PLAN_CONTINUATION_JUDGED"),
            Map.entry("REPLAN_SUCCEEDED", "NORMAL_REPLAN_SUCCEEDED"),
            Map.entry("REPLAN_FAILED", "ERR_REPLAN_FAILED"),
            // 分配与派发
            Map.entry("AGENT_ASSIGNMENT_REQUESTED", "NORMAL_ASSIGNMENT_REQUESTED"),
            Map.entry("AGENT_ASSIGNED", "NORMAL_AGENT_ASSIGNED"),
            Map.entry("AGENT_ASSIGNMENT_CONFLICTED", "ERR_AGENT_ASSIGNMENT_CONFLICTED"),
            Map.entry("STEP_DISPATCHED", "NORMAL_STEP_DISPATCHED"),
            Map.entry("STEP_RETRY_DISPATCHED", "NORMAL_STEP_RETRY_DISPATCHED"),
            // 反馈与完成
            Map.entry("EXECUTION_FEEDBACK_RECEIVED", "NORMAL_FEEDBACK_RECEIVED"),
            Map.entry("STEP_COMPLETED", "NORMAL_STEP_COMPLETED"),
            Map.entry("TASK_COMPLETED", "NORMAL_TASK_COMPLETED"),
            // 异常与处置
            Map.entry("EXCEPTION_RECOVERED", "NORMAL_EXCEPTION_RECOVERED"),
            Map.entry("STEP_FAILED", "ERR_STEP_FAILED"),
            Map.entry("STEP_TIMEOUT_DETECTED", "ERR_EXECUTION_TIMEOUT"),
            Map.entry("STEP_ASSIGNMENT_FAILED", "ERR_STEP_ASSIGNMENT_FAILED"),
            Map.entry("EXCEPTION_DETECTED", "ERR_EXCEPTION_DETECTED"),
            Map.entry("EXCEPTION_RECOVERY_FAILED", "ERR_EXCEPTION_RECOVERY_FAILED"),
            Map.entry("TASK_FAILED", "ERR_TASK_FAILED"),
            Map.entry("TASK_PENDING_MANUAL", "ERR_TASK_PENDING_MANUAL"),
            Map.entry("TASK_MANUAL_REQUIRED", "ERR_TASK_MANUAL_REQUIRED"),
            Map.entry("GOAL_UNDERSTANDING_FAILED", "ERR_GOAL_UNDERSTANDING_FAILED"),
            Map.entry("COMMAND_DISPATCH_BLOCKED", "ERR_COMMAND_DISPATCH_BLOCKED"),
            Map.entry("DEVICE_COMMAND_SEND_FAILED", "ERR_DEVICE_COMMAND_SEND_FAILED"),
            // 终止
            Map.entry("MANUAL_TERMINATED", "NORMAL_MANUAL_TERMINATED"),
            Map.entry("TASK_TERMINATED", "NORMAL_TASK_TERMINATED"),
            Map.entry("TASK_CANCEL_REQUESTED", "NORMAL_CANCEL_REQUESTED"),
            Map.entry("TASK_CANCEL_CONFIRMED_IDLE", "NORMAL_CANCEL_CONFIRMED_IDLE"),
            Map.entry("TASK_CANCEL_DELIVERY_FAILED", "ERR_CANCEL_DELIVERY_FAILED"),
            Map.entry("TASK_CANCEL_CONFIRMATION_TIMEOUT", "ERR_CANCEL_CONFIRMATION_TIMEOUT"),
            // 其它
            Map.entry("DRY_RUN_STARTED", "NORMAL_DRY_RUN_STARTED"),
            Map.entry("FLIGHT_CHANNEL_UNCOVERED", "WARN_FLIGHT_CHANNEL_UNCOVERED"),
            Map.entry("ESCORT_UNCOVERED", "WARN_ESCORT_UNCOVERED"),
            Map.entry("GUIDANCE_UNCOVERED", "WARN_GUIDANCE_UNCOVERED"),
            Map.entry("UNRELATED_AGENT_OFFLINE_JUDGED", "ERR_AGENT_OFFLINE_UNRELATED"),
            Map.entry("LATE_TASK_RESPONSE_IGNORED", "WARN_LATE_RESPONSE_IGNORED"),
            Map.entry("LATE_EXECUTION_FEEDBACK_IGNORED", "WARN_LATE_FEEDBACK_IGNORED"),
            Map.entry("STALE_EXECUTION_FEEDBACK_IGNORED", "WARN_STALE_FEEDBACK_IGNORED"));

    public static final String FALLBACK = "NORMAL_EVENT";

    /** 调用方给了原因码就原样用（去掉首尾空白）；没给则按事件类型补，未登记的类型用 {@link #FALLBACK}。 */
    public static String resolve(String eventType, String reasonCode) {
        if (reasonCode != null && !reasonCode.isBlank()) return reasonCode.trim();
        if (eventType == null) return FALLBACK;
        return DEFAULTS.getOrDefault(eventType, FALLBACK);
    }

    static Map<String, String> defaults() {
        return DEFAULTS;
    }
}
