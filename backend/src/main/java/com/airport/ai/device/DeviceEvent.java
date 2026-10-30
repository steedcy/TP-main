package com.airport.ai.device;

import java.time.LocalDateTime;

/**
 * 对应5.2.2业务规则8、5.2.3业务规则2/7：代理创建/停用/启用/归档、离线判定、恢复上报等设备事件。
 * 仅追加，语义与task_events一致，不提供修改删除接口。纯POJO，持久化映射见 mapper/DeviceEventMapper.xml。
 */
public class DeviceEvent {

    private Long id;
    private Long deviceAgentId;
    private String eventType;
    private LocalDateTime occurredAt = LocalDateTime.now();
    private String trigger = "SYSTEM";
    private String reasonCode;
    private String detailSummary;
    /** 统一业务消息的指令编号与结果（查询类等设备消息事件使用），其余事件为null（DEF-S3-082） */
    private String commandId;
    private String result;

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public Long getDeviceAgentId() { return deviceAgentId; }
    public void setDeviceAgentId(Long deviceAgentId) { this.deviceAgentId = deviceAgentId; }
    public String getEventType() { return eventType; }
    public void setEventType(String eventType) { this.eventType = eventType; }
    public LocalDateTime getOccurredAt() { return occurredAt; }
    public void setOccurredAt(LocalDateTime occurredAt) { this.occurredAt = occurredAt; }
    public String getTrigger() { return trigger; }
    public void setTrigger(String trigger) { this.trigger = trigger; }
    public String getReasonCode() { return reasonCode; }
    public void setReasonCode(String reasonCode) { this.reasonCode = reasonCode; }
    public String getCommandId() { return commandId; }
    public void setCommandId(String commandId) { this.commandId = commandId; }
    public String getResult() { return result; }
    public void setResult(String result) { this.result = result; }
    public String getDetailSummary() { return detailSummary; }
    public void setDetailSummary(String detailSummary) { this.detailSummary = detailSummary; }
}
