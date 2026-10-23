package com.airport.ai.baseline;

import java.time.LocalDateTime;

/**
 * 对应5.3.2业务规则2：试运行须为每个步骤选择具备对应能力的模拟设备。
 * 数据库设计说明书未设计该记录表，新增dry_run_device_selections仅追加保存供追溯。
 * 纯POJO，持久化映射见 mapper/DryRunDeviceSelectionMapper.xml。
 */
public class DryRunDeviceSelection {

    private Long id;
    private Long taskId;
    private Integer stepSeq;
    private Long deviceAgentId;
    private LocalDateTime createdAt = LocalDateTime.now();

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public Long getTaskId() { return taskId; }
    public void setTaskId(Long taskId) { this.taskId = taskId; }
    public Integer getStepSeq() { return stepSeq; }
    public void setStepSeq(Integer stepSeq) { this.stepSeq = stepSeq; }
    public Long getDeviceAgentId() { return deviceAgentId; }
    public void setDeviceAgentId(Long deviceAgentId) { this.deviceAgentId = deviceAgentId; }
    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }
}
