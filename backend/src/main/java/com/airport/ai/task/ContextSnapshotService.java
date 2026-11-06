package com.airport.ai.task;

import com.airport.ai.device.Device;
import com.airport.ai.device.DeviceAgent;
import com.airport.ai.device.DeviceAgentMapper;
import com.airport.ai.device.DeviceCapability;
import com.airport.ai.device.DeviceCapabilityMapper;
import com.airport.ai.device.DeviceMapper;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.stream.Collectors;

/**
 * 对应5.4.2规划上下文构建。查询全部启用且在线代理的能力、在线状态、位置、负载和可用时间，
 * 生成规划上下文快照并持久化关联任务，作为候选计划生成的唯一设备事实来源（业务规则1/4）。
 * 离线、停用、归档代理不纳入候选集合（业务规则2）；未通过测试或已停用的能力不纳入
 * 可用能力集合（业务规则3）。
 */
@Service
public class ContextSnapshotService {

    private static final DateTimeFormatter DATE_FMT = DateTimeFormatter.ofPattern("yyyyMMdd");
    private static final ObjectMapper MAPPER = new ObjectMapper();

    private final DeviceAgentMapper deviceAgentMapper;
    private final DeviceMapper deviceMapper;
    private final DeviceCapabilityMapper deviceCapabilityMapper;
    private final ContextSnapshotMapper contextSnapshotMapper;
    private volatile String currentDatePart;
    private long sequence;

    public ContextSnapshotService(DeviceAgentMapper deviceAgentMapper,
                                   DeviceMapper deviceMapper,
                                   DeviceCapabilityMapper deviceCapabilityMapper,
                                   ContextSnapshotMapper contextSnapshotMapper) {
        this.deviceAgentMapper = deviceAgentMapper;
        this.deviceMapper = deviceMapper;
        this.deviceCapabilityMapper = deviceCapabilityMapper;
        this.contextSnapshotMapper = contextSnapshotMapper;
    }

    @org.springframework.beans.factory.annotation.Value("${app.context.fault-injection.failed-agent-codes:}")
    private String faultInjectedFailedAgentCodes = "";

    public void setFaultInjectedFailedAgentCodes(String faultInjectedFailedAgentCodes) {
        this.faultInjectedFailedAgentCodes = faultInjectedFailedAgentCodes;
    }

    private Set<String> parseInjectedFailures() {
        if (faultInjectedFailedAgentCodes == null || faultInjectedFailedAgentCodes.isBlank()) {
            return Collections.emptySet();
        }
        return Arrays.stream(faultInjectedFailedAgentCodes.split(","))
                .map(String::trim)
                .filter(s -> !s.isBlank())
                .collect(Collectors.toSet());
    }

    /**
     * @param requiredCapabilityTypes 任务族所需能力类型清单，用于计算能力覆盖情况（业务规则7：
     *                                完全缺失时调用方应直接生成能力缺口异常，不再调用规划模型，
     *                                本方法只负责生成快照与覆盖情况，是否短路由调用方TaskPlanningOrchestrator判断）
     */
    public ContextSnapshot buildSnapshot(Long taskId, List<String> requiredCapabilityTypes) {
        List<DeviceAgent> onlineEnabledAgents = deviceAgentMapper.findByAgentStatusAndOnlineStatus("ENABLED", "ONLINE");

        List<Long> deviceIds = onlineEnabledAgents.stream().map(DeviceAgent::getDeviceId).distinct().toList();
        Map<Long, Device> deviceById = deviceIds.isEmpty() ? Map.of()
                : deviceMapper.findByIds(deviceIds).stream().collect(Collectors.toMap(Device::getId, d -> d));

        List<Map<String, Object>> agentViews = new ArrayList<>();
        List<String> failedAgentCodes = new ArrayList<>();
        Set<String> availableCapabilityTypes = new HashSet<>();
        Set<String> injectedFailures = parseInjectedFailures();

        for (DeviceAgent agent : onlineEnabledAgents) {
            Device device = deviceById.get(agent.getDeviceId());
            if (device == null || injectedFailures.contains(agent.getAgentCode())) {
                // 代理存在但关联设备查询失败（对应异常路径2b）
                failedAgentCodes.add(agent.getAgentCode());
                continue;
            }
            if (!"ACTIVE".equals(device.getDeviceStatus())) continue;
            List<DeviceCapability> enabledCapabilities =
                    deviceCapabilityMapper.findByDeviceIdAndCapabilityStatus(device.getId(), "ENABLED");
            List<String> capabilityTypes = enabledCapabilities.stream()
                    .map(DeviceCapability::getCapabilityType).distinct().toList();
            availableCapabilityTypes.addAll(capabilityTypes);

            Map<String, Object> agentView = new LinkedHashMap<>();
            agentView.put("agentId", agent.getAgentCode());
            agentView.put("deviceCode", device.getDeviceCode());
            agentView.put("deviceTypeCode", device.getDeviceTypeCode());
            agentView.put("simulatedDeviceType", device.getSimulatedDeviceType());
            agentView.put("businessStatus", parseJson(agent.getBusinessStatus()));
            agentView.put("capabilities", capabilityTypes);
            agentView.put("capabilitySchemas", enabledCapabilities.stream().map(capability -> {
                Map<String, Object> schema = new LinkedHashMap<>();
                schema.put("capabilityType", capability.getCapabilityType());
                schema.put("inputParams", parseJson(capability.getInputParams()));
                schema.put("outputParams", parseJson(capability.getOutputParams()));
                return schema;
            }).toList());
            agentView.put("onlineStatus", agent.getOnlineStatus());
            Map<String, Object> location = new LinkedHashMap<>();
            location.put("x", device.getPositionX());
            location.put("y", device.getPositionY());
            location.put("zone", device.getAreaCode());
            agentView.put("location", location);
            agentView.put("workload", agent.getWorkStatus());
            agentView.put("currentTaskId", agent.getCurrentTaskId());
            agentView.put("currentStepSeq", agent.getCurrentStepSeq());
            agentView.put("availableUntil", availableAt(agent));
            agentViews.add(agentView);
        }

        Map<String, Object> coverage = new LinkedHashMap<>();
        List<String> available = requiredCapabilityTypes.stream().filter(availableCapabilityTypes::contains).toList();
        List<String> missing = requiredCapabilityTypes.stream().filter(c -> !availableCapabilityTypes.contains(c)).toList();
        coverage.put("available", available);
        coverage.put("missing", missing);

        ContextSnapshot snapshot = new ContextSnapshot();
        snapshot.setSnapshotCode(generateSnapshotCode());
        snapshot.setTaskId(taskId);
        snapshot.setAgents(toJson(agentViews));
        snapshot.setCapabilityCoverage(toJson(coverage));
        snapshot.setFailedAgentCodes(toJson(failedAgentCodes));
        snapshot.setGeneratedAt(LocalDateTime.now());
        contextSnapshotMapper.insert(snapshot);
        return snapshot;
    }

    @org.springframework.beans.factory.annotation.Autowired(required = false)
    private TaskStepAssignmentMapper assignmentMapper;
    @org.springframework.beans.factory.annotation.Autowired(required = false)
    private PlanVersionMapper planVersionMapper;
    @org.springframework.beans.factory.annotation.Value("${app.task.step-timeout-default-seconds:60}")
    private int defaultStepTimeoutSeconds = 60;

    /**
     * 代理预计可用时间（SRS_F011.R01、DEF-S3-031）：空闲=当前时刻；忙碌=其进行中步骤的下发时刻加该步骤超时，
     * 即最迟到此时刻未收到反馈会判超时并释放；没有进行中步骤的忙碌代理（占用待核查等）无法预测，返回null。
     */
    private String availableAt(DeviceAgent agent) {
        LocalDateTime now = LocalDateTime.now();
        if (!"BUSY".equals(agent.getWorkStatus())) return now.toString();
        if (assignmentMapper == null || agent.getId() == null) return null;
        LocalDateTime latest = null;
        for (TaskStepAssignment a : assignmentMapper.findActiveByAgentId(agent.getId())) {
            if (!"EXECUTING".equals(a.getStepStatus()) || a.getDispatchedAt() == null) continue;
            LocalDateTime until = a.getDispatchedAt().plusSeconds(stepTimeout(a));
            if (latest == null || until.isAfter(latest)) latest = until;
        }
        if (latest == null) return null;
        return (latest.isBefore(now) ? now : latest).toString();
    }

    @SuppressWarnings("unchecked")
    private int stepTimeout(TaskStepAssignment assignment) {
        if (planVersionMapper == null || assignment.getPlanVersionId() == null) return defaultStepTimeoutSeconds;
        try {
            PlanVersion plan = planVersionMapper.findById(assignment.getPlanVersionId()).orElseThrow();
            List<Map<String, Object>> steps = new ObjectMapper().readValue(plan.getPlanSteps(), List.class);
            return steps.stream()
                    .filter(step -> assignment.getStepSeq() != null
                            && assignment.getStepSeq().equals(((Number) step.get("stepSeq")).intValue()))
                    .map(step -> ((Number) step.getOrDefault("stepTimeout", defaultStepTimeoutSeconds)).intValue())
                    .findFirst().orElse(defaultStepTimeoutSeconds);
        } catch (Exception e) {
            return defaultStepTimeoutSeconds;
        }
    }

    /** 统计指定能力类型的在线候选代理数量（供B6监督判定的资源冲突临界规则使用） */
    public int countOnlineCandidates(ContextSnapshot snapshot, String capabilityType) {
        List<Map<String, Object>> agents = parseAgents(snapshot.getAgents());
        int count = 0;
        for (Map<String, Object> agent : agents) {
            Object caps = agent.get("capabilities");
            if (caps instanceof List<?> list && list.contains(capabilityType)) {
                count++;
            }
        }
        return count;
    }

    /** Count agents that can actually serve this step now, for the spare-resource risk rule. */
    public int countAvailableCandidates(ContextSnapshot snapshot, String capabilityType, String taskFamily) {
        int count = 0;
        for (Map<String, Object> agent : parseAgents(snapshot.getAgents())) {
            Object caps = agent.get("capabilities");
            if (caps instanceof List<?> list && list.contains(capabilityType)
                    && "IDLE".equals(agent.get("workload"))
                    && CoreScenarioChannelPolicy.matches(taskFamily, capabilityType,
                    String.valueOf(agent.get("deviceTypeCode")), String.valueOf(agent.get("simulatedDeviceType")))) {
                count++;
            }
        }
        return count;
    }

    /** Reuse the same persisted snapshot facts for initial planning and replanning. */
    public List<Map<String, Object>> capabilityContext(ContextSnapshot snapshot, List<String> requiredTypes) {
        List<Map<String, Object>> agents = parseAgents(snapshot.getAgents());
        return requiredTypes.stream().map(type -> {
            List<Map<String, Object>> candidates = agents.stream().filter(agent ->
                    agent.get("capabilities") instanceof List<?> caps && caps.contains(type)).toList();
            Map<String, Object> context = new LinkedHashMap<>();
            context.put("capabilityType", type);
            context.put("candidateCount", candidates.size());
            context.put("candidates", candidates);
            return context;
        }).toList();
    }

    private Object parseJson(String json) {
        if (json == null || json.isBlank()) return List.of();
        try { return MAPPER.readValue(json, Object.class); }
        catch (Exception ex) { throw new IllegalStateException("能力参数定义不是有效JSON", ex); }
    }

    @SuppressWarnings("unchecked")
    public List<Map<String, Object>> parseAgents(String agentsJson) {
        if (agentsJson == null || agentsJson.isBlank()) {
            return Collections.emptyList();
        }
        try {
            return MAPPER.readValue(agentsJson, List.class);
        } catch (Exception e) {
            throw new RuntimeException("解析上下文快照代理清单失败", e);
        }
    }

    private synchronized String generateSnapshotCode() {
        String datePart = DATE_FMT.format(LocalDateTime.now());
        if (!datePart.equals(currentDatePart)) {
            currentDatePart = datePart;
            long maxSeq = 0L;
            try {
                String maxCode = contextSnapshotMapper.findMaxSnapshotCodeByDate(datePart);
                if (maxCode != null && maxCode.startsWith("CTX-" + datePart + "-")) {
                    String seqPart = maxCode.substring(("CTX-" + datePart + "-").length());
                    maxSeq = Long.parseLong(seqPart);
                }
            } catch (Exception ignored) {
            }
            sequence = Math.max(contextSnapshotMapper.count(), maxSeq);
        }
        while (true) {
            sequence++;
            String candidateCode = "CTX-" + datePart + "-" + String.format("%04d", sequence);
            if (contextSnapshotMapper.findBySnapshotCode(candidateCode).isEmpty()) {
                return candidateCode;
            }
        }
    }

    private String toJson(Object value) {
        try {
            return MAPPER.writeValueAsString(value);
        } catch (Exception e) {
            throw new RuntimeException("序列化失败", e);
        }
    }
}
