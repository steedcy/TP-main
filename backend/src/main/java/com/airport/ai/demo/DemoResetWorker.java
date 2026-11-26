package com.airport.ai.demo;

import com.airport.ai.auth.OperationLogService;
import com.airport.ai.auth.User;
import com.airport.ai.common.BusinessException;
import com.airport.ai.common.ErrorCode;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.namedparam.MapSqlParameterSource;
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.ArrayList;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/** Runs the entire reset and success audit in one database transaction. */
@Service
public class DemoResetWorker {
    private static final List<String> PRESET_SCENARIO_CODES = List.of(
            "OVERSIZE_BAGGAGE_HANDLING",
            "SPECIAL_PASSENGER_SERVICE",
            "FLIGHT_CHANGE_RESPONSE",
            "GENERAL_SERVICE"
    );

    private final JdbcTemplate jdbc;
    private final NamedParameterJdbcTemplate namedJdbc;
    private final DemoDataset dataset;
    private final ObjectMapper mapper;
    private final OperationLogService audit;

    public DemoResetWorker(JdbcTemplate jdbc, DemoDataset dataset, ObjectMapper mapper, OperationLogService audit) {
        this.jdbc = jdbc;
        this.namedJdbc = new NamedParameterJdbcTemplate(jdbc);
        this.dataset = dataset;
        this.mapper = mapper;
        this.audit = audit;
    }

    public List<String> blockingTasks() {
        return jdbc.queryForList("""
                SELECT task_code FROM tasks WHERE is_dry_run = FALSE
                  AND status IN ('PLANNING','SUPERVISING','PENDING_ASSIGNMENT','DOWNGRADING','EXECUTING')
                ORDER BY id LIMIT 20
                """, String.class);
    }

    public List<String> busyDemoAgents() {
        return namedJdbc.queryForList("""
                SELECT a.agent_code FROM device_agents a JOIN devices d ON d.id = a.device_id
                WHERE d.device_code IN (:codes) AND a.work_status = 'BUSY'
                ORDER BY a.agent_code
                """, new MapSqlParameterSource("codes", dataset.deviceCodes()), String.class);
    }

    /** injectFailure is callable from isolated integration tests only; the public API always passes false. */
    @Transactional
    public ResetOutcome restore(User operator, boolean injectFailure, String requestId,
                                String beforeDatasetVersion, String beforeContentDigest) {
        long started = System.nanoTime();
        jdbc.execute("LOCK TABLE tasks IN SHARE ROW EXCLUSIVE MODE");
        List<String> blocked = blockingTasks();
        List<String> busy = busyDemoAgents();
        if (!blocked.isEmpty() || !busy.isEmpty()) {
            throw new BusinessException(ErrorCode.DEMO_RESET_BLOCKED,
                    "复位被活动任务或忙碌代理阻断；任务: " + blocked + "；代理: " + busy);
        }

        restoreMapRegions(operator.getUsername());
        restoreMapPois(operator.getUsername());
        cleanupLegacySimulators();
        for (JsonNode device : dataset.devices()) {
            restoreDevice(device);
        }
        refreshTemplateUsageCounts();
        if (injectFailure) {
            throw new IllegalStateException("ISOLATED_RESET_INJECTED_FAILURE");
        }
        for (JsonNode baseline : dataset.baselines()) {
            restoreBaseline(baseline, operator.getUsername());
        }
        for (JsonNode scenario : dataset.scenarios()) {
            restoreScenario(scenario, operator.getUsername());
        }
        for (JsonNode riskRule : dataset.riskRules()) {
            restoreRiskRule(riskRule);
        }
        restoreValidationRules(operator.getUsername());

        String contentDigest = contentDigest();
        Map<String, Object> detail = new LinkedHashMap<>();
        detail.put("requestId", requestId);
        detail.put("beforeDatasetVersion", beforeDatasetVersion);
        detail.put("afterDatasetVersion", DemoDataset.VERSION);
        detail.put("beforeContentDigest", beforeContentDigest);
        detail.put("afterContentDigest", contentDigest);
        detail.put("sourceDigest", dataset.sourceDigest());
        detail.put("deviceCount", dataset.devices().size());
        detail.put("regionCount", dataset.mapRegions().size());
        detail.put("poiCount", dataset.mapPois().size());
        detail.put("baselineCount", dataset.baselines().size());
        detail.put("scenarioCount", dataset.scenarios().size());
        detail.put("riskRuleCount", dataset.riskRules().size());
        detail.put("durationMs", (System.nanoTime() - started) / 1_000_000);
        audit.record(operator.getId(), operator.getUsername(), operator.getRole(), "DEMO_DATA_RESET",
                DemoDataset.VERSION, "SUCCESS", null, detail);
        return new ResetOutcome(requestId, beforeDatasetVersion, beforeContentDigest,
                DemoDataset.VERSION, contentDigest);
    }

    /** Backward-compatible helper for package callers that do not need audit context. */
    @Transactional
    public String restore(User operator, boolean injectFailure) {
        String requestId = UUID.randomUUID().toString();
        String beforeDigest = contentDigest();
        return restore(operator, injectFailure, requestId, currentDatasetVersion(), beforeDigest).afterContentDigest();
    }

    String currentDatasetVersion() {
        List<String> details = jdbc.queryForList("""
                SELECT detail::text FROM operation_logs
                WHERE operation_type='DEMO_DATA_RESET' AND operation_result='SUCCESS'
                ORDER BY id DESC LIMIT 1
                """, String.class);
        if (details.isEmpty()) return DemoDataset.VERSION;
        try {
            JsonNode detail = mapper.readTree(details.get(0));
            String version = detail.path("afterDatasetVersion").asText("");
            if (!version.isBlank()) return version;
            return detail.path("datasetVersion").asText(DemoDataset.VERSION);
        } catch (Exception ignored) {
            return DemoDataset.VERSION;
        }
    }

    record ResetOutcome(String requestId, String beforeDatasetVersion, String beforeContentDigest,
                        String afterDatasetVersion, String afterContentDigest) {}

    private void restoreMapRegions(String username) {
        jdbc.update("DELETE FROM terminal_map_regions");
        for (JsonNode region : dataset.mapRegions()) {
            jdbc.update("""
                    INSERT INTO terminal_map_regions (region_code, region_name, region_type, geometry_json, created_by)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    region.path("regionCode").asText(),
                    region.path("regionName").asText(),
                    region.path("regionType").asText(),
                    region.path("geometryJson").asText(),
                    username);
        }
    }

    private void restoreMapPois(String username) {
        jdbc.update("DELETE FROM terminal_pois");
        for (JsonNode poi : dataset.mapPois()) {
            String linked = poi.path("linkedDeviceCode").isNull() ? null : poi.path("linkedDeviceCode").asText(null);
            jdbc.update("""
                    INSERT INTO terminal_pois (poi_code, poi_name, category, pos_x, pos_y, zone_name, linked_device_code, created_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    poi.path("poiCode").asText(),
                    poi.path("poiName").asText(),
                    poi.path("category").asText(),
                    poi.path("posX").decimalValue(),
                    poi.path("posY").decimalValue(),
                    poi.path("zoneName").asText(),
                    linked,
                    username);
        }
    }

    private void cleanupLegacySimulators() {
        jdbc.update("""
                UPDATE task_step_assignments SET device_agent_id = NULL
                WHERE device_agent_id IN (
                    SELECT a.id FROM device_agents a
                    JOIN devices d ON d.id = a.device_id
                    WHERE d.device_code LIKE 'SIM_F2_%' OR d.device_code LIKE 'F2_%'
                )
                """);
        jdbc.update("""
                DELETE FROM device_agents
                WHERE device_id IN (SELECT id FROM devices WHERE device_code LIKE 'SIM_F2_%' OR device_code LIKE 'F2_%')
                """);
        jdbc.update("""
                DELETE FROM device_capabilities
                WHERE device_id IN (SELECT id FROM devices WHERE device_code LIKE 'SIM_F2_%' OR device_code LIKE 'F2_%')
                """);
        jdbc.update("DELETE FROM devices WHERE device_code LIKE 'SIM_F2_%' OR device_code LIKE 'F2_%'");
    }

    private void restoreDevice(JsonNode device) {
        String code = device.path("deviceCode").asText();
        String simType = device.path("simulatedDeviceType").asText();
        jdbc.update("""
                INSERT INTO devices (device_code,device_name,device_type_code,is_simulator,simulated_device_type,
                    area_code,position_x,position_y,access_endpoint,access_credential_ref,status_report_interval,
                    remark,connection_test_status,connection_test_result,device_status,onboarding_status)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,'PASSED','连接测试通过','ACTIVE','MANUAL')
                ON CONFLICT (device_code) DO UPDATE SET
                    device_name=EXCLUDED.device_name,device_type_code=EXCLUDED.device_type_code,
                    is_simulator=EXCLUDED.is_simulator,simulated_device_type=EXCLUDED.simulated_device_type,
                    area_code=EXCLUDED.area_code,position_x=EXCLUDED.position_x,position_y=EXCLUDED.position_y,
                    access_endpoint=EXCLUDED.access_endpoint,access_credential_ref=EXCLUDED.access_credential_ref,
                    status_report_interval=EXCLUDED.status_report_interval,
                    remark=EXCLUDED.remark,connection_test_status='PASSED',connection_test_result='连接测试通过',
                    device_status='ACTIVE',onboarding_status='MANUAL',updated_at=CURRENT_TIMESTAMP
                """, code, device.path("deviceName").asText(), device.path("deviceTypeCode").asText(),
                device.path("isSimulator").asBoolean(), simType,
                device.path("areaCode").asText(), device.path("positionX").decimalValue(),
                device.path("positionY").decimalValue(), device.path("accessEndpoint").asText(),
                device.path("accessCredentialRef").asText(), device.path("statusReportInterval").asInt(),
                device.path("remark").asText());
        Long id = jdbc.queryForObject("SELECT id FROM devices WHERE device_code=?", Long.class, code);

        List<String> fixtureCodes = new ArrayList<>();
        for (JsonNode capability : device.path("capabilities")) {
            fixtureCodes.add(capability.path("capabilityCode").asText());
        }
        namedJdbc.update("""
                DELETE FROM device_capabilities WHERE device_id=:deviceId AND capability_code NOT IN (:codes)
                """, new MapSqlParameterSource().addValue("deviceId", id).addValue("codes", fixtureCodes));

        for (JsonNode capability : device.path("capabilities")) {
            String capCode = capability.path("capabilityCode").asText();
            String capType = capability.path("capabilityType").asText();
            Long templateId = null;
            if (!"CAP_SIM_STATUS".equals(capType)) {
                List<Long> tplIds = jdbc.queryForList("""
                        SELECT id FROM capability_template
                        WHERE device_type_code = ? AND template_code = ? AND template_status = 'ACTIVE'
                        LIMIT 1
                        """, Long.class, simType, capCode);
                if (!tplIds.isEmpty()) {
                    templateId = tplIds.get(0);
                }
            }
            jdbc.update("""
                    INSERT INTO device_capabilities (device_id,template_id,capability_code,capability_name,capability_type,
                        input_params,output_params,capability_status,test_passed,last_test_at,test_result,capability_description)
                    VALUES (?,?,?,?,?,?::json,?::json,'ENABLED',TRUE,CURRENT_TIMESTAMP,'测试通过',?)
                    ON CONFLICT (device_id,capability_code) DO UPDATE SET
                        template_id=EXCLUDED.template_id,
                        capability_name=EXCLUDED.capability_name,capability_type=EXCLUDED.capability_type,
                        input_params=EXCLUDED.input_params,output_params=EXCLUDED.output_params,
                        capability_status='ENABLED',test_passed=TRUE,
                        last_test_at=CURRENT_TIMESTAMP,test_result='测试通过',
                        capability_description=EXCLUDED.capability_description,
                        updated_at=CURRENT_TIMESTAMP
                    """, id, templateId, capCode, capability.path("capabilityName").asText(),
                    capType, capability.path("inputParams").toString(),
                    capability.path("outputParams").toString(), capability.path("capabilityDescription").asText());
        }

        jdbc.update("""
                INSERT INTO device_agents (agent_code, device_id, agent_status, online_status, work_status)
                VALUES (?, ?, 'ENABLED', 'OFFLINE', 'IDLE')
                ON CONFLICT (agent_code) DO UPDATE SET
                    device_id = EXCLUDED.device_id,
                    agent_status = 'ENABLED',
                    work_status = 'IDLE',
                    updated_at = CURRENT_TIMESTAMP
                """, "AGENT_" + code, id);
    }

    private void refreshTemplateUsageCounts() {
        jdbc.update("UPDATE capability_template t SET usage_count = (SELECT COUNT(*) FROM device_capabilities c WHERE c.template_id = t.id)");
    }

    private void restoreBaseline(JsonNode baseline, String username) {
        String family = baseline.path("taskFamily").asText();
        String name = switch (family) {
            case "OVERSIZE_BAGGAGE_HANDLING" -> "超规行李处置标准模板";
            case "SPECIAL_PASSENGER_SERVICE" -> "特殊旅客服务标准模板";
            case "FLIGHT_CHANGE_RESPONSE" -> "航班变更应对标准模板";
            default -> throw new IllegalStateException("标准演示数据包含未知任务族: " + family);
        };
        List<Long> existing = jdbc.queryForList(
                "SELECT id FROM baseline_templates WHERE task_family=? AND is_preset=TRUE", Long.class, family);
        if (existing.size() > 1) throw new IllegalStateException("预置模板重复: " + family);
        if (existing.isEmpty()) {
            jdbc.update("""
                    INSERT INTO baseline_templates (template_name,task_family,is_preset,input_params,steps,
                        template_version,template_status,updated_by)
                    VALUES (?,?,TRUE,?::json,?::json,'V1.5','ENABLED',?)
                    """, name, family, baseline.path("inputParams").toString(), baseline.path("steps").toString(), username);
        } else {
            jdbc.update("""
                    UPDATE baseline_templates SET template_name=?,input_params=?::json,steps=?::json,
                        template_version='V1.5',template_status='ENABLED',updated_by=?,updated_at=CURRENT_TIMESTAMP
                    WHERE id=?
                    """, name, baseline.path("inputParams").toString(), baseline.path("steps").toString(),
                    username, existing.get(0));
        }
    }

    private void restoreScenario(JsonNode scenario, String username) {
        jdbc.update("""
                INSERT INTO task_definitions (definition_code,task_name,goal_template,scene_params,
                    available_capability_types,constraint_description,completion_condition,is_preset,
                    definition_status,updated_by)
                VALUES (?,?,?,?::json,?::json,?,?,TRUE,'ENABLED',?)
                ON CONFLICT (definition_code) DO UPDATE SET
                    task_name=EXCLUDED.task_name,goal_template=EXCLUDED.goal_template,
                    scene_params=EXCLUDED.scene_params,available_capability_types=EXCLUDED.available_capability_types,
                    constraint_description=EXCLUDED.constraint_description,
                    completion_condition=EXCLUDED.completion_condition,is_preset=TRUE,
                    definition_status='ENABLED',updated_by=EXCLUDED.updated_by,updated_at=CURRENT_TIMESTAMP
                """, scenario.path("definitionCode").asText(), scenario.path("taskName").asText(),
                scenario.path("goalTemplate").asText(), scenario.path("sceneParams").toString(),
                scenario.path("availableCapabilityTypes").toString(), scenario.path("constraintDescription").asText(),
                scenario.path("completionCondition").asText(), username);
    }

    private void restoreRiskRule(JsonNode riskRule) {
        jdbc.update("""
                INSERT INTO risk_rules (rule_code, rule_content, rule_version, enabled)
                VALUES (?, ?, ?, ?)
                ON CONFLICT (rule_code) DO UPDATE SET
                    rule_content = EXCLUDED.rule_content,
                    rule_version = EXCLUDED.rule_version,
                    enabled = EXCLUDED.enabled,
                    updated_at = CURRENT_TIMESTAMP
                """,
                riskRule.path("ruleCode").asText(),
                riskRule.path("ruleContent").asText(),
                riskRule.path("ruleVersion").asText("V1.0"),
                riskRule.path("enabled").asBoolean(true));
    }

    private void restoreValidationRules(String username) {
        Iterator<Map.Entry<String, JsonNode>> fields = dataset.validationRules().fields();
        while (fields.hasNext()) {
            Map.Entry<String, JsonNode> entry = fields.next();
            String key = "validation_baseline." + entry.getKey();
            String value = entry.getValue().isValueNode() ? entry.getValue().asText() : entry.getValue().toString();
            jdbc.update("""
                    INSERT INTO system_settings (setting_key, setting_value, updated_by, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT (setting_key) DO UPDATE SET
                        setting_value = EXCLUDED.setting_value,
                        updated_by = EXCLUDED.updated_by,
                        updated_at = CURRENT_TIMESTAMP
                    """, key, value, username);
        }
    }

    public String contentDigest() {
        MapSqlParameterSource codes = new MapSqlParameterSource("codes", dataset.deviceCodes());
        List<Object> content = new ArrayList<>();
        content.add(jdbc.queryForList("""
                SELECT region_code, region_name, region_type, geometry_json
                FROM terminal_map_regions ORDER BY region_code
                """));
        content.add(jdbc.queryForList("""
                SELECT poi_code, poi_name, category, pos_x, pos_y, zone_name, linked_device_code
                FROM terminal_pois ORDER BY poi_code
                """));
        content.add(namedJdbc.queryForList("""
                SELECT device_code,device_name,device_type_code,is_simulator,simulated_device_type,area_code,
                    position_x,position_y,access_endpoint,status_report_interval,remark,connection_test_status,device_status
                FROM devices WHERE device_code IN (:codes) ORDER BY device_code
                """, codes));
        content.add(namedJdbc.queryForList("""
                SELECT d.device_code,c.capability_code,c.capability_name,c.capability_type,
                    c.input_params::text AS input_params,c.output_params::text AS output_params,
                    c.capability_status,c.test_passed,c.capability_description
                FROM device_capabilities c JOIN devices d ON d.id=c.device_id
                WHERE d.device_code IN (:codes) ORDER BY d.device_code,c.capability_code
                """, codes));
        content.add(jdbc.queryForList("""
                SELECT task_family,template_name,input_params::text AS input_params,steps::text AS steps,
                    template_version,template_status FROM baseline_templates
                WHERE is_preset=TRUE AND task_family IN
                    ('OVERSIZE_BAGGAGE_HANDLING','SPECIAL_PASSENGER_SERVICE','FLIGHT_CHANGE_RESPONSE')
                ORDER BY task_family
                """));
        content.add(namedJdbc.queryForList("""
                SELECT definition_code,task_name,goal_template,scene_params::text AS scene_params,
                    available_capability_types::text AS available_capability_types,
                    constraint_description,completion_condition,definition_status
                FROM task_definitions WHERE definition_code IN (:scenarios)
                ORDER BY definition_code
                """, new MapSqlParameterSource("scenarios", PRESET_SCENARIO_CODES)));
        content.add(jdbc.queryForList("""
                SELECT rule_code, rule_content, rule_version, enabled
                FROM risk_rules ORDER BY rule_code
                """));
        content.add(jdbc.queryForList("""
                SELECT setting_key, setting_value
                FROM system_settings WHERE setting_key LIKE 'validation_baseline.%'
                ORDER BY setting_key
                """));
        try {
            return DemoDataset.sha256(mapper.writeValueAsString(content));
        } catch (Exception ex) {
            throw new IllegalStateException("复位后摘要计算失败", ex);
        }
    }
}
