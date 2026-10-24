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
import java.util.List;
import java.util.Map;

/** Runs the entire reset and success audit in one database transaction. */
@Service
public class DemoResetWorker {
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
    public String restore(User operator, boolean injectFailure) {
        long started = System.nanoTime();
        jdbc.execute("LOCK TABLE tasks IN SHARE ROW EXCLUSIVE MODE");
        List<String> blocked = blockingTasks();
        List<String> busy = busyDemoAgents();
        if (!blocked.isEmpty() || !busy.isEmpty()) {
            throw new BusinessException(ErrorCode.DEMO_RESET_BLOCKED,
                    "复位被活动任务或忙碌代理阻断；任务: " + blocked + "；代理: " + busy);
        }
        for (JsonNode device : dataset.devices()) restoreDevice(device);
        if (injectFailure) throw new IllegalStateException("ISOLATED_RESET_INJECTED_FAILURE");
        for (JsonNode baseline : dataset.baselines()) restoreBaseline(baseline, operator.getUsername());
        for (JsonNode scenario : dataset.scenarios()) restoreScenario(scenario, operator.getUsername());
        String contentDigest = contentDigest();
        audit.record(operator.getId(), operator.getUsername(), operator.getRole(), "DEMO_DATA_RESET",
                DemoDataset.VERSION, "SUCCESS", null,
                Map.of("sourceDigest", dataset.sourceDigest(), "contentDigest", contentDigest,
                        "deviceCount", 6, "baselineCount", 3, "scenarioCount", 3,
                        "durationMs", (System.nanoTime() - started) / 1_000_000));
        return contentDigest;
    }

    private void restoreDevice(JsonNode device) {
        String code = device.path("deviceCode").asText();
        jdbc.update("""
                INSERT INTO devices (device_code,device_name,device_type_code,is_simulator,simulated_device_type,
                    area_code,position_x,position_y,access_endpoint,access_credential_ref,status_report_interval,
                    remark,connection_test_status,device_status)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,'UNTESTED','ACTIVE')
                ON CONFLICT (device_code) DO UPDATE SET
                    device_name=EXCLUDED.device_name,device_type_code=EXCLUDED.device_type_code,
                    is_simulator=EXCLUDED.is_simulator,simulated_device_type=EXCLUDED.simulated_device_type,
                    area_code=EXCLUDED.area_code,position_x=EXCLUDED.position_x,position_y=EXCLUDED.position_y,
                    access_endpoint=EXCLUDED.access_endpoint,status_report_interval=EXCLUDED.status_report_interval,
                    remark=EXCLUDED.remark,connection_test_status='UNTESTED',connection_test_result=NULL,
                    device_status='ACTIVE',updated_at=CURRENT_TIMESTAMP
                """, code, device.path("deviceName").asText(), device.path("deviceTypeCode").asText(),
                device.path("isSimulator").asBoolean(), device.path("simulatedDeviceType").asText(),
                device.path("areaCode").asText(), device.path("positionX").decimalValue(),
                device.path("positionY").decimalValue(), device.path("accessEndpoint").asText(),
                device.path("accessCredentialRef").asText(), device.path("statusReportInterval").asInt(),
                device.path("remark").asText());
        Long id = jdbc.queryForObject("SELECT id FROM devices WHERE device_code=?", Long.class, code);
        List<String> fixtureCodes = new ArrayList<>();
        for (JsonNode capability : device.path("capabilities")) fixtureCodes.add(capability.path("capabilityCode").asText());
        namedJdbc.update("""
                DELETE FROM device_capabilities WHERE device_id=:deviceId AND capability_code NOT IN (:codes)
                """, new MapSqlParameterSource().addValue("deviceId", id).addValue("codes", fixtureCodes));
        for (JsonNode capability : device.path("capabilities")) {
            jdbc.update("""
                    INSERT INTO device_capabilities (device_id,capability_code,capability_name,capability_type,
                        input_params,output_params,capability_status,capability_description)
                    VALUES (?,?,?,?,?::json,?::json,'UNTESTED',?)
                    ON CONFLICT (device_id,capability_code) DO UPDATE SET
                        capability_name=EXCLUDED.capability_name,capability_type=EXCLUDED.capability_type,
                        input_params=EXCLUDED.input_params,output_params=EXCLUDED.output_params,
                        capability_status='UNTESTED',test_result=NULL,last_test_at=NULL,
                        capability_description=EXCLUDED.capability_description,template_id=NULL,
                        updated_at=CURRENT_TIMESTAMP
                    """, id, capability.path("capabilityCode").asText(), capability.path("capabilityName").asText(),
                    capability.path("capabilityType").asText(), capability.path("inputParams").toString(),
                    capability.path("outputParams").toString(), capability.path("capabilityDescription").asText());
        }
    }

    private void restoreBaseline(JsonNode baseline, String username) {
        String family = baseline.path("taskFamily").asText();
        String name = switch (family) {
            case "OVERSIZE_BAGGAGE_HANDLING" -> "超规行李处置标准模板";
            case "SPECIAL_PASSENGER_SERVICE" -> "特殊旅客服务标准模板";
            case "FLIGHT_CHANGE_RESPONSE" -> "航班变更应对标准模板";
            default -> throw new IllegalStateException("F2 演示数据包含未知任务族: " + family);
        };
        List<Long> existing = jdbc.queryForList(
                "SELECT id FROM baseline_templates WHERE task_family=? AND is_preset=TRUE", Long.class, family);
        if (existing.size() > 1) throw new IllegalStateException("预置模板重复: " + family);
        if (existing.isEmpty()) {
            jdbc.update("""
                    INSERT INTO baseline_templates (template_name,task_family,is_preset,input_params,steps,
                        template_version,template_status,updated_by)
                    VALUES (?,?,TRUE,?::json,?::json,'F2.1','DRAFT',?)
                    """, name, family, baseline.path("inputParams").toString(), baseline.path("steps").toString(), username);
        } else {
            jdbc.update("""
                    UPDATE baseline_templates SET template_name=?,input_params=?::json,steps=?::json,
                        template_version='F2.1',template_status='DRAFT',updated_by=?,updated_at=CURRENT_TIMESTAMP
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

    public String contentDigest() {
        MapSqlParameterSource codes = new MapSqlParameterSource("codes", dataset.deviceCodes());
        List<Object> content = new ArrayList<>();
        content.add(namedJdbc.queryForList("""
                SELECT device_code,device_name,device_type_code,is_simulator,simulated_device_type,area_code,
                    position_x,position_y,access_endpoint,status_report_interval,remark,connection_test_status,device_status
                FROM devices WHERE device_code IN (:codes) ORDER BY device_code
                """, codes));
        content.add(namedJdbc.queryForList("""
                SELECT d.device_code,c.capability_code,c.capability_name,c.capability_type,
                    c.input_params::text AS input_params,c.output_params::text AS output_params,
                    c.capability_status,c.capability_description
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
        content.add(jdbc.queryForList("""
                SELECT definition_code,task_name,goal_template,scene_params::text AS scene_params,
                    available_capability_types::text AS available_capability_types,
                    constraint_description,completion_condition,definition_status
                FROM task_definitions WHERE definition_code IN
                    ('OVERSIZE_BAGGAGE_HANDLING','SPECIAL_PASSENGER_SERVICE','FLIGHT_CHANGE_RESPONSE')
                ORDER BY definition_code
                """));
        try { return DemoDataset.sha256(mapper.writeValueAsString(content)); }
        catch (Exception ex) { throw new IllegalStateException("复位后摘要计算失败", ex); }
    }
}
