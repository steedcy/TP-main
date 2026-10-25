package com.airport.ai.risk;

import com.airport.ai.common.BusinessException;
import com.airport.ai.common.ErrorCode;
import com.airport.ai.task.PlanVersion;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.time.format.DateTimeParseException;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

/**
 * 对应附录B 4.4节监督判定接口 + V1.4正文5.4.5节。
 * 采用"确定性风险规则优先、风险信号辅助"策略（对应5.4.5业务规则4）。
 *
 * 三类确定性高风险规则命中条件（TBD-03拍板结论）：
 * 1. RULE_ESCORT_SPECIAL_PASSENGER：任务族=SPECIAL_PASSENGER_SERVICE 且步骤含CAP_ESCORT能力
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

        List<RiskRule> enabledRules = riskRuleMapper.findByEnabled(true);
        Set<String> enabledCodes = enabledRules.stream().map(RiskRule::getRuleCode).collect(Collectors.toSet());
        String ruleSetVersion = enabledRules.isEmpty() ? "V1.0" : enabledRules.get(0).getRuleVersion();

        // 1. 确定性规则优先判定
        if (enabledCodes.contains(RULE_ESCORT_SPECIAL_PASSENGER) && "SPECIAL_PASSENGER_SERVICE".equals(taskFamily)
                && hitsEscortSpecialPassenger(planVersion)) {
            return highRisk(RULE_ESCORT_SPECIAL_PASSENGER, "移动机器人陪同对象为特殊旅客，命中确定性高风险规则", null, ruleSetVersion);
        }
        if (enabledCodes.contains(RULE_CROSS_ZONE) && hitsCrossZone(planVersion)) {
            return highRisk(RULE_CROSS_ZONE, "移动服务机器人跨区域连续服务，命中确定性高风险规则", null, ruleSetVersion);
        }
        // The selected device consumes one candidate. The rule is about spare devices,
        // so a single online candidate means zero backups, not one.
        int backupCandidateCount = Math.max(0, minCandidateCount - 1);
        if (enabledCodes.contains(RULE_RESOURCE_CRITICAL) && backupCandidateCount < resourceCriticalCandidateThreshold) {
            return highRisk(RULE_RESOURCE_CRITICAL,
                    "可用备用候选设备数量(" + backupCandidateCount + ")低于配置阈值(" + resourceCriticalCandidateThreshold + ")，命中确定性高风险规则",
                    null, ruleSetVersion);
        }

        // 2. 风险信号辅助判定：两个及以上组合才触发降级，单一信号不阻断
        BigDecimal confidence = planVersion.getConfidence();
        boolean lowConfidence = confidence != null && confidence.compareTo(lowConfidenceThreshold) < 0;
        boolean contextStale = isContextStale(snapshotGeneratedAt);
        int signalCount = (lowConfidence ? 1 : 0) + (modelCandidateDiverse ? 1 : 0) + (contextStale ? 1 : 0);

        if (signalCount >= 2) {
            StringBuilder basis = new StringBuilder("风险信号组合触发基线降级：");
            if (lowConfidence) basis.append("模型低置信度(").append(confidence).append("<").append(lowConfidenceThreshold).append(")；");
            if (modelCandidateDiverse) basis.append("候选差异较大；");
            if (contextStale) basis.append("上下文快照接近过期(>").append(contextStaleSeconds).append("秒)；");
            return new RiskAssessmentResult("HIGH", "RISK_SIGNAL_COMBINATION", basis.toString(),
                    confidence, "BASELINE_DOWNGRADE", ruleSetVersion);
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

    private boolean hitsEscortSpecialPassenger(PlanVersion planVersion) {
        // task_family=SPECIAL_PASSENGER_SERVICE的前提判断已在assess()调用处完成，本方法只检查
        // 步骤是否含CAP_ESCORT。taskFamily作为assess()参数传入而非本类反查Task表，避免循环依赖
        return parseSteps(planVersion.getPlanSteps()).stream()
                .anyMatch(step -> "CAP_ESCORT".equals(step.get("capabilityType")));
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
