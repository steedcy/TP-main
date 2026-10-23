package com.airport.ai.event;

import java.time.LocalDateTime;

/**
 * 对应5.7.1任务过程追溯：事件仅可追加，不可修改或删除。
 * 本实体不提供任何update场景的Mapper方法；数据库层已撤销应用账号的UPDATE/DELETE权限（见V2迁移脚本注释）。
 */
public class TaskEvent {

    private Long id;
    private Long taskId;
    private String eventType;
    private LocalDateTime occurredAt = LocalDateTime.now();

    /** SYSTEM / OPERATOR */
    private String trigger = "SYSTEM";
    private String reasonCode;
    private String detailSummary;

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
    public String getDetailSummary() { return detailSummary; }
    public void setDetailSummary(String detailSummary) { this.detailSummary = detailSummary; }
}
