package com.airport.ai.planning;

/**
 * 规划模型服务调用抽象，对应附录A第3.4节。屏蔽具体模型服务差异，支持替换为
 * 不同的外部模型服务或本地模型部署。调用失败/超时由调用方（TaskPlanningService）
 * 统一转5.4.6高风险基线降级流程，本接口实现类内部不做业务降级判断。
 */
public interface PlanningModelService {

    PlanningResponse generatePlan(PlanningRequest request);
}
