package com.airport.ai.event;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.time.LocalDateTime;

/**
 * 对应5.7.1任务过程追溯：事件仅可追加，不可修改或删除。
 * 本实体不提供任何update场景的Mapper方法；数据库层已撤销应用账号的UPDATE/DELETE权限（见V2迁移脚本注释）。
 */
public class TaskEvent {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private Long id;
    private Long taskId;
    private String eventType;
    private LocalDateTime occurredAt = LocalDateTime.now();

    /** SYSTEM / OPERATOR */
    private String trigger = "SYSTEM";
    private String reasonCode;

    /** 对应数据库 task_events.detail_summary 字段（结构化事件持久化存储完整 JSON，普通事件为文本） */
    private String detailSummary;

    /** 结构化详情字符串（保证满足 json.loads 整体解析且包含业务字段） */
    private String detail;

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public Long getTaskId() { return taskId; }
    public void setTaskId(Long taskId) { this.taskId = taskId; }
    public String getEventType() { return eventType; }
    public void setEventType(String eventType) { this.eventType = eventType; }
    public LocalDateTime getOccurredAt() { return occurredAt; }
    public void setOccurredAt(LocalDateTime occurredAt) { this.occurredAt = occurredAt; }
    public String getTrigger() { return trigger; }
    public void setTrigger(String trigger) { this.trigger = trigger; }
    public String getReasonCode() { return reasonCode; }
    public void setReasonCode(String reasonCode) { this.reasonCode = reasonCode; }

    /**
     * 持久化到 SQL task_events.detail_summary 字段的原始字符串
     */
    public String getRawDetailSummary() {
        if (detail != null && !detail.isBlank()) {
            return detail;
        }
        return detailSummary;
    }

    /**
     * 人类可读的时间线摘要文本（用于 UI 与时间线展示）
     */
    public String getDetailSummary() {
        if (detailSummary != null && detailSummary.trim().startsWith("{")) {
            try {
                JsonNode node = MAPPER.readTree(detailSummary);
                if (node.has("summary") && !node.get("summary").isNull()) {
                    return node.get("summary").asText();
                }
            } catch (Exception ignored) {
            }
        }
        return detailSummary;
    }

    public void setDetailSummary(String detailSummary) {
        String clean = com.airport.ai.task.SceneParamsPrivacyGuard.sanitizeText(detailSummary);
        this.detailSummary = clean;
        if (this.detail == null || this.detail.isBlank()) {
            this.detail = clean;
        }
    }

    /**
     * 兼容接口与审计统一查询：提供 detail 访问器，返回完整可整体 json.loads 解析的 JSON 字符串。
     */
    public String getDetail() {
        if (detail != null && !detail.isBlank()) {
            return detail;
        }
        return detailSummary;
    }

    public void setDetail(String detail) {
        String clean = com.airport.ai.task.SceneParamsPrivacyGuard.sanitizeText(detail);
        this.detail = clean;
        if (this.detailSummary == null || this.detailSummary.isBlank()) {
            this.detailSummary = clean;
        }
    }
}
