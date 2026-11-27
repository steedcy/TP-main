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
    @org.springframework.beans.factory.annotation.Autowired(required = false)
    private com.airport.ai.task.TerminalMapMapper terminalMapMapper;
    @org.springframework.beans.factory.annotation.Autowired(required = false)
    private com.airport.ai.task.TaskMapper taskMapper;

    /**
     * 隔离测试用故障注入（默认关闭，仅隔离后端通过app.risk.fault-injection.mode开启）：
     * UNAVAILABLE=监督服务不可用，UNDETERMINED=监督无法判定，用于覆盖TC-005.S3（NT-S3-028）。
     */
    @Value("${app.risk.fault-injection.mode:}")
    private String faultInjectionMode = "";

    public RiskAssessmentService(RiskRuleMapper riskRuleMapper,
                                  @Value("${app.risk.low-confidence-threshold:0.8}") double lowConfidenceThreshold,
                                  @Value("${app.risk.context-stale-seconds:60}") long contextStaleSeconds,
                                  @Value("${app.risk.resource-critical-candidate-threshold:0}") int resourceCriticalCandidateThreshold) {
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
        if (enabledCodes.contains(RULE_CROSS_ZONE) && hitsCrossZone(planVersion, taskFamily)) {
            return highRisk(RULE_CROSS_ZONE, "移动服务机器人跨区域（隔离区外↔隔离区内）连续服务，命中确定性高风险规则", confidence, ruleSetVersion);
        }
        // The selected device consumes one candidate. When threshold == 0, only require available candidates > 0
        // (no extra spare device required); when threshold > 0, require at least that many spare devices.
        int backupCandidateCount = Math.max(0, minCandidateCount - 1);
        boolean resourceCriticalHit = resourceCriticalCandidateThreshold <= 0
                ? minCandidateCount <= 0
                : backupCandidateCount < resourceCriticalCandidateThreshold;
        if (enabledCodes.contains(RULE_RESOURCE_CRITICAL) && resourceCriticalHit) {
            return highRisk(RULE_RESOURCE_CRITICAL,
                    resourceCriticalCandidateThreshold <= 0
                            ? "可用候选设备数量(" + minCandidateCount + ")不大于0，命中确定性高风险规则"
                            : "可用备用候选设备数量(" + backupCandidateCount + ")低于配置阈值(" + resourceCriticalCandidateThreshold + ")，命中确定性高风险规则",
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
    private boolean hitsCrossZone(PlanVersion planVersion, String taskFamily) {
        List<Map<String, Object>> steps = parseSteps(planVersion.getPlanSteps());
        List<Map<String, Object>> robotSteps = steps.stream()
                .filter(step -> !PlanStepRules.isConditionNode(step))
                .filter(step -> isMobileRobotStep((String) step.get("capabilityType"), taskFamily))
                .toList();
        if (robotSteps.isEmpty()) return false;

        // 1. 兼容显式 targetZone 参数
        Set<Object> explicitZones = robotSteps.stream()
                .map(step -> {
                    Object inputParams = step.get("inputParams");
                    if (inputParams instanceof Map) {
                        return ((Map<String, Object>) inputParams).get("targetZone");
                    }
                    return null;
                })
                .filter(zone -> zone != null && !String.valueOf(zone).isBlank())
                .collect(Collectors.toSet());
        if (explicitZones.size() >= 2) return true;

        // 2. 基于当前候机楼室内地图 POI 坐标与任务起终点判定是否跨越隔离区边界（隔离区内 y<235 vs 隔离区外 y>341）
        if (terminalMapMapper == null) return false;
        Map<String, String> poiIsolationZone = loadPoiIsolationZones();
        if (poiIsolationZone.isEmpty()) return false;

        Set<String> touchedZones = new java.util.LinkedHashSet<>();
        if (taskMapper != null && planVersion.getTaskId() != null) {
            try {
                taskMapper.findById(planVersion.getTaskId()).ifPresent(task -> {
                    collectZoneFromTaskJson(task.getSceneParams(), List.of("origin", "startLocation", "originLocation", "baggageLocation"), poiIsolationZone, touchedZones);
                    collectZoneFromTaskJson(task.getGoalParsingResult(), List.of("origin"), poiIsolationZone, touchedZones);
                });
            } catch (Exception ignored) {}
        }
        for (Map<String, Object> step : robotSteps) {
            Object inputParams = step.get("inputParams");
            if (inputParams instanceof Map<?, ?> map) {
                for (String key : List.of("origin", "targetLocation", "destination")) {
                    String z = resolveIsolationZone(map.get(key), poiIsolationZone);
                    if (z != null) touchedZones.add(z);
                }
            }
        }
        return touchedZones.size() >= 2;
    }

    private boolean isMobileRobotStep(String capabilityType, String taskFamily) {
        if (!isMobileRobotCapability(capabilityType)) return false;
        String required = CoreScenarioChannelPolicy.requiredType(taskFamily, capabilityType);
        return required == null || "MOBILE_ROBOT".equals(required);
    }

    private Map<String, String> loadPoiIsolationZones() {
        Map<String, String> map = new java.util.HashMap<>();
        try {
            for (Map<String, Object> poi : terminalMapMapper.findAllPois()) {
                String isoZone = com.airport.ai.task.SpatialRuleConfig.resolveIsolationZone(poi);
                if (isoZone == null) continue;
                if (poi.get("poiCode") != null) map.put(String.valueOf(poi.get("poiCode")).trim().toUpperCase(), isoZone);
                if (poi.get("poiName") != null) map.putIfAbsent(String.valueOf(poi.get("poiName")).trim().toUpperCase(), isoZone);
            }
        } catch (Exception ignored) {}
        return map;
    }

    @SuppressWarnings("unchecked")
    private void collectZoneFromTaskJson(String json, List<String> keys, Map<String, String> poiIsolationZone, Set<String> out) {
        if (json == null || json.isBlank()) return;
        try {
            Map<String, Object> parsed = MAPPER.readValue(json, Map.class);
            for (String k : keys) {
                String z = resolveIsolationZone(parsed.get(k), poiIsolationZone);
                if (z != null) out.add(z);
            }
        } catch (Exception ignored) {}
    }

    private String resolveIsolationZone(Object rawLoc, Map<String, String> poiIsolationZone) {
        if (rawLoc == null) return null;
        String text = String.valueOf(rawLoc).trim();
        if (text.isEmpty()) return null;
        if ("隔离区内".equals(text) || "隔离区外".equals(text)) return text;
        String normalized = com.airport.ai.task.TerminalLocationNormalizer.normalize(text);
        if (normalized != null) {
            String byNorm = poiIsolationZone.get(normalized.toUpperCase());
            if (byNorm != null) return byNorm;
        }
        String direct = poiIsolationZone.get(text.toUpperCase());
        if (direct != null) return direct;
        int open = text.indexOf('('), close = text.indexOf(')', open + 1);
        if (open < 0) { open = text.indexOf('（'); close = text.indexOf('）', open + 1); }
        if (open >= 0 && close > open + 1) {
            String inner = text.substring(open + 1, close).trim().toUpperCase();
            if (poiIsolationZone.containsKey(inner)) return poiIsolationZone.get(inner);
        }
        return null;
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
