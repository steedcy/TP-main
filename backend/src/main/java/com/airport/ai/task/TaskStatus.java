package com.airport.ai.task;

/**
 * 对应V1.4正文3.2节任务状态机，共9种状态
 */
public enum TaskStatus {
    PLANNING,             // 待规划
    SUPERVISING,          // 监督判定中
    PENDING_ASSIGNMENT,   // 待分配
    DOWNGRADING,          // 降级执行中
    EXECUTING,            // 执行中
    COMPLETED,            // 已完成
    FAILED,               // 失败
    PENDING_MANUAL,       // 待人工处理
    MANUAL_TERMINATED     // 人工终止
}
