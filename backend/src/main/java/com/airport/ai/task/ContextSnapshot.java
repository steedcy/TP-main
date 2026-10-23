package com.airport.ai.task;

import java.time.LocalDateTime;

/**
 * 对应5.4.2规划上下文构建，数据库设计说明书未定义此表，随V6迁移新增。
 * agents/capabilityCoverage/failedAgentCodes为JSON列，Java侧统一用String承载，
 * Service层负责Jackson序列化/反序列化。快照为不可变记录，只提供insert，不提供update。
 */
public class ContextSnapshot {

    private Long id;
    private String snapshotCode;
    private Long taskId;
    /** 参与规划的代理清单：agentId、能力、在线状态、位置、负载、可用时间 */
    private String agents;
    /** 任务族所需能力类型的可用/缺失情况 */
    private String capabilityCoverage;
    /** 状态查询失败的代理清单（对应5.4.2异常路径2b） */
    private String failedAgentCodes;
    private LocalDateTime generatedAt = LocalDateTime.now();

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public String getSnapshotCode() { return snapshotCode; }
    public void setSnapshotCode(String snapshotCode) { this.snapshotCode = snapshotCode; }
    public Long getTaskId() { return taskId; }
    public void setTaskId(Long taskId) { this.taskId = taskId; }
    public String getAgents() { return agents; }
    public void setAgents(String agents) { this.agents = agents; }
    public String getCapabilityCoverage() { return capabilityCoverage; }
    public void setCapabilityCoverage(String capabilityCoverage) { this.capabilityCoverage = capabilityCoverage; }
    public String getFailedAgentCodes() { return failedAgentCodes; }
    public void setFailedAgentCodes(String failedAgentCodes) { this.failedAgentCodes = failedAgentCodes; }
    public LocalDateTime getGeneratedAt() { return generatedAt; }
    public void setGeneratedAt(LocalDateTime generatedAt) { this.generatedAt = generatedAt; }
}
