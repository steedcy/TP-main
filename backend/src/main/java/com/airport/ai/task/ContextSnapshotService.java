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

        for (DeviceAgent agent : onlineEnabledAgents) {
            Device device = deviceById.get(agent.getDeviceId());
            if (device == null) {
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
            agentView.put("availableUntil", null);
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
            sequence = contextSnapshotMapper.count();
        }
        sequence++;
        return "CTX-" + datePart + "-" + String.format("%04d", sequence);
    }

    private String toJson(Object value) {
        try {
            return MAPPER.writeValueAsString(value);
        } catch (Exception e) {
            throw new RuntimeException("序列化失败", e);
        }
    }
}
