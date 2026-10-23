package com.airport.ai.planning;

/**
 * 目标理解服务调用抽象（方案A：与候选计划生成是外部规划模型服务的两个独立端点），
 * 对应5.4.1开放式任务目标提交与理解、附录B 5.2节。调用失败/超时由调用方（TaskService）
 * 统一处理为"不进入计划生成"，本接口实现类内部不做业务降级判断。
 */
public interface GoalUnderstandingService {

    GoalUnderstandingResponse understand(GoalUnderstandingRequest request);
}
