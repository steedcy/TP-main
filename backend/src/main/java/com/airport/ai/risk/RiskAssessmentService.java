package com.airport.ai.risk;

import com.airport.ai.common.BusinessException;
import com.airport.ai.common.ErrorCode;
import com.airport.ai.task.CoreScenarioChannelPolicy;
import com.airport.ai.task.PlanStepRules;
import com.airport.ai.task.PlanVersion;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

/**
 * 对应附录B 4.4节监督判定接口 + V1.4正文5.4.5节。
 * 采用"确定性风险规则优先、风险信号辅助"策略（对应5.4.5业务规则4）。
 *
 * 三类确定性高风险规则命中条件（TBD-03拍板结论）：
 * 1. RULE_ESCORT_SPECIAL_PASSENGER：任务族=SPECIAL_PASSENGER_SERVICE 且含绑定移动服务机器人的会合（CAP_NAVIGATION）或陪同（CAP_ESCORT）步骤
 * 2. RULE_CROSS_ZONE：移动服务机器人步骤序列跨越预定义区域边界1次及以上
 * 3. RULE_RESOURCE_CRITICAL：申请资源时可用备用候选设备数量低于配置阈值（默认1）
 *
 * 风险信号（两个及以上组合才触发降级，TBD-04拍板结论）：
 * - 模型置信度 < 0.8（低置信度）
 * - 候选差异较大（直接采信规划模型输出的信号标签，不做平台层量化）
 * - 上下文快照生成时间距当前 > 60秒（接近过期）
 */
@Service
public class RiskAssessmentService {

    private static final ObjectMapper MAPPER = new ObjectMapper();
    private static final String RULE_ESCORT_SPECIAL_PASSENGER = "RULE_ESCORT_SPECIAL_PASSENGER";
    private static final String RULE_CROSS_ZONE = "RULE_CROSS_ZONE";
    private static final String RULE_RESOURCE_CRITICAL = "RULE_RESOURCE_CRITICAL";

    private final RiskRuleMapper riskRuleMapper;
    private final BigDecimal lowConfidenceThreshold;
    private final long contextStaleSeconds;
    private final int resourceCriticalCandidateThreshold;

    /**
     * 隔离测试用故障注入（默认关闭，仅隔离后端通过app.risk.fault-injection.mode开启）：
     * UNAVAILABLE=监督服务不可用，UNDETERMINED=监督无法判定，用于覆盖TC-005.S3（NT-S3-028）。
     */
    @Value("${app.risk.fault-injection.mode:}")
    private String faultInjectionMode = "";

    public RiskAssessmentService(RiskRuleMapper riskRuleMapper,
                                  @Value("${app.risk.low-confidence-threshold:0.8}") double lowConfidenceThreshold,
                                  @Value("${app.risk.context-stale-seconds:60}") long contextStaleSeconds,
                                  @Value("${app.risk.resource-critical-candidate-threshold:1}") int resourceCriticalCandidateThreshold) {
        this.riskRuleMapper = riskRuleMapper;
        this.lowConfidenceThreshold = BigDecimal.valueOf(lowConfidenceThreshold);
        this.contextStaleSeconds = contextStaleSeconds;
        this.resourceCriticalCandidateThreshold = resourceCriticalCandidateThreshold;
    }

    /**
     * @param planVersion          待判定的计划版本（须已通过三类校验，否则拒绝判定，见4109）
     * @param taskFamily           所属任务的任务族，用于RULE_ESCORT_SPECIAL_PASSENGER的前提判断——
     *                             该规则仅服务对象为特殊旅客（taskFamily=SPECIAL_PASSENGER_SERVICE）时命中，
     *                             普通空间引导场景即便步骤含CAP_ESCORT也不命中（对应5.4.5业务规则5、TBD-03结论②）
     * @param snapshotGeneratedAt  规划上下文快照生成时间，用于"接近过期"信号判定
     * @param modelCandidateDiverse 规划模型输出的候选差异信号标签（true=差异较大），由外部模型返回，不在本方法内计算
     * @param minCandidateCount    本次任务申请资源时的最小可用候选设备总数（跨全部步骤取最小值）
     */
    public RiskAssessmentResult assess(PlanVersion planVersion, String taskFamily, LocalDateTime snapshotGeneratedAt,
                                        boolean modelCandidateDiverse, int minCandidateCount) {
        if (!"PASS".equals(planVersion.getStructureCheckResult())
                || !"PASS".equals(planVersion.getCapabilityCheckResult())
                || !"PASS".equals(planVersion.getConstraintCheckResult())) {
            throw new BusinessException(ErrorCode.SUPERVISION_ON_UNVALIDATED_PLAN);
        }

        if ("UNAVAILABLE".equalsIgnoreCase(faultInjectionMode)) {
            throw new IllegalStateException("injected supervision fault: service unavailable");
        }

        List<RiskRule> enabledRules = riskRuleMapper.findByEnabled(true);
        Set<String> enabledCodes = enabledRules.stream().map(RiskRule::getRuleCode).collect(Collectors.toSet());
        List<RiskRule> allRules = riskRuleMapper.findAll();
        String ruleSetVersion = RiskRuleSetVersion.of(allRules == null || allRules.isEmpty() ? enabledRules : allRules);
        // SRS_F014.R01：每个通过校验的计划都输出置信度；置信度只作参考，不改变确定性规则命中结论（R07）
        BigDecimal confidence = planVersion.getConfidence();

        if ("UNDETERMINED".equalsIgnoreCase(faultInjectionMode)) {
            return new RiskAssessmentResult("UNDETERMINED", "INJECTED_UNDETERMINED", "注入：监督智能体输出无法确定",
                    confidence, "MANUAL_HANDLING", ruleSetVersion);
        }

        // 1. 确定性规则优先判定
        if (enabledCodes.contains(RULE_ESCORT_SPECIAL_PASSENGER) && "SPECIAL_PASSENGER_SERVICE".equals(taskFamily)) {
            List<String> robotServiceSteps = escortOrRendezvousRobotSteps(planVersion, taskFamily);
            if (!robotServiceSteps.isEmpty()) {
                return highRisk(RULE_ESCORT_SPECIAL_PASSENGER,
                        "移动机器人会合或陪同对象为特殊旅客，命中确定性高风险规则；命中步骤：" + String.join("、", robotServiceSteps),
                        confidence, ruleSetVersion);
            }
        }
        if (enabledCodes.contains(RULE_CROSS_ZONE) && hitsCrossZone(planVersion)) {
            return highRisk(RULE_CROSS_ZONE, "移动服务机器人跨区域连续服务，命中确定性高风险规则", confidence, ruleSetVersion);
        }
        // The selected device consumes one candidate. The rule is about spare devices,
        // so a single online candidate means zero backups, not one.
        int backupCandidateCount = Math.max(0, minCandidateCount - 1);
        if (enabledCodes.contains(RULE_RESOURCE_CRITICAL) && backupCandidateCount < resourceCriticalCandidateThreshold) {
            return highRisk(RULE_RESOURCE_CRITICAL,
                    "可用备用候选设备数量(" + backupCandidateCount + ")低于配置阈值(" + resourceCriticalCandidateThreshold + ")，命中确定性高风险规则",
                    confidence, ruleSetVersion);
        }

        // 2. 风险信号辅助判定：两个及以上组合才触发降级，单一信号不阻断
        boolean lowConfidence = confidence != null && confidence.compareTo(lowConfidenceThreshold) < 0;
        boolean contextStale = isContextStale(snapshotGeneratedAt);

        List<String> hitSignals = new ArrayList<>();
        if (lowConfidence) {
            hitSignals.add("模型低置信度(" + confidence + "<" + lowConfidenceThreshold + ")");
        }
        if (modelCandidateDiverse) {
            hitSignals.add("候选差异较大");
        }
        if (contextStale) {
            hitSignals.add("上下文快照接近过期(>" + contextStaleSeconds + "秒)");
        }

        if (hitSignals.size() >= 2) {
            StringBuilder basis = new StringBuilder("风险信号组合触发基线降级：");
            for (String s : hitSignals) {
                basis.append(s).append("；");
            }
            return new RiskAssessmentResult("HIGH", "RISK_SIGNAL_COMBINATION", basis.toString(),
                    confidence, "BASELINE_DOWNGRADE", ruleSetVersion);
        }

        if (hitSignals.size() == 1) {
            // DEF-S3-095/TC-045.S2: 单一信号不直接阻断（LOW/AUTO_EXECUTE），但须在判定依据和事件中明确列出命中信号
            String basis = "未命中确定性高风险规则；命中单一风险信号（" + hitSignals.get(0) + "），单一信号不直接阻断，低风险自动执行";
            return new RiskAssessmentResult("LOW", null, basis,
                    confidence, "AUTO_EXECUTE", ruleSetVersion);
        }

        // 3. 未命中任何规则/信号组合：低风险，自动执行
        return new RiskAssessmentResult("LOW", null, "未命中确定性高风险规则，风险信号数量不足以触发降级",
                confidence, "AUTO_EXECUTE", ruleSetVersion);
    }

    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> parseSteps(String planStepsJson) {
        try {
            return MAPPER.readValue(planStepsJson, MAPPER.getTypeFactory().constructCollectionType(List.class, Map.class));
        } catch (Exception e) {
            throw new RuntimeException("解析计划步骤失败: " + planStepsJson, e);
        }
    }

    /**
     * RULE_ESCORT_SPECIAL_PASSENGER命中步骤（DEF-S3-043/SRS_F014.R05）：规则原文为"移动机器人会合或陪同"，
     * 不只看CAP_ESCORT。会合（前往旅客所在区域会合，业务意图为空间引导CAP_NAVIGATION）与陪同（CAP_ESCORT）
     * 两类步骤，只要在该任务族的渠道约束下绑定到移动服务机器人（CoreScenarioChannelPolicy，与候选代理过滤、
     * 分配时使用的同一约束），即为机器人会合/陪同特殊旅客。条件节点不是业务动作，不计入。
     * 航显/现场通知等非机器人会合陪同步骤不命中；非特殊旅客任务族的前提已在assess()调用处判断。
     */
    private List<String> escortOrRendezvousRobotSteps(PlanVersion planVersion, String taskFamily) {
        List<String> hits = new ArrayList<>();
        for (Map<String, Object> step : parseSteps(planVersion.getPlanSteps())) {
            if (PlanStepRules.isConditionNode(step)) continue;
            String capabilityType = step.get("capabilityType") == null ? null : String.valueOf(step.get("capabilityType"));
            String intent = "CAP_ESCORT".equals(capabilityType) ? "陪同"
                    : "CAP_NAVIGATION".equals(capabilityType) ? "会合" : null;
            if (intent == null) continue;
            if (!"MOBILE_ROBOT".equals(CoreScenarioChannelPolicy.requiredType(taskFamily, capabilityType))) continue;
            Object seq = step.get("stepSeq");
            hits.add("步骤" + (seq == null ? "?" : seq) + "(" + capabilityType + "，" + intent + "，绑定移动服务机器人)");
        }
        return hits;
    }

    @SuppressWarnings("unchecked")
    private boolean hitsCrossZone(PlanVersion planVersion) {
        // 统计移动服务机器人步骤（capabilityType为机器人专属能力）涉及的不同区域数量
        Set<Object> zones = parseSteps(planVersion.getPlanSteps()).stream()
                .filter(step -> isMobileRobotCapability((String) step.get("capabilityType")))
                .map(step -> {
                    Object inputParams = step.get("inputParams");
                    if (inputParams instanceof Map) {
                        return ((Map<String, Object>) inputParams).get("targetZone");
                    }
                    return null;
                })
                .filter(zone -> zone != null)
                .collect(Collectors.toSet());
        return zones.size() >= 2;
    }

    private boolean isMobileRobotCapability(String capabilityType) {
        return "CAP_NAVIGATION".equals(capabilityType) || "CAP_ESCORT".equals(capabilityType)
                || "CAP_NOTIFICATION".equals(capabilityType);
    }

    private boolean isContextStale(LocalDateTime snapshotGeneratedAt) {
        if (snapshotGeneratedAt == null) {
            return false;
        }
        try {
            return snapshotGeneratedAt.plusSeconds(contextStaleSeconds).isBefore(LocalDateTime.now());
        } catch (DateTimeParseException e) {
            return false;
        }
    }

    private RiskAssessmentResult highRisk(String reasonCode, String basis, BigDecimal confidence, String ruleSetVersion) {
        return new RiskAssessmentResult("HIGH", reasonCode, basis, confidence, "BASELINE_DOWNGRADE", ruleSetVersion);
    }
}
