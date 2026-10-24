package com.airport.ai.demo;

import com.airport.ai.auth.User;
import com.airport.ai.common.BusinessException;
import com.airport.ai.common.ErrorCode;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;

import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.NONE)
@EnabledIfEnvironmentVariable(named = "DEMO_RESET_TEST_SCHEMA", matches = "tip_f2_reset_20261024")
class DemoResetIntegrationTest {
    private static final String SCHEMA = "tip_f2_reset_20261024";

    @DynamicPropertySource
    static void isolatedDatabase(DynamicPropertyRegistry registry) {
        if (!SCHEMA.equals(System.getenv("DEMO_RESET_TEST_SCHEMA")))
            throw new IllegalStateException("Reset integration test requires explicitly named isolated schema");
        String host = System.getenv().getOrDefault("DB_HOST", "localhost");
        String port = System.getenv().getOrDefault("DB_PORT", "5432");
        String database = System.getenv().getOrDefault("DB_NAME", "airport_ai");
        registry.add("spring.datasource.url", () -> "jdbc:postgresql://" + host + ":" + port + "/"
                + database + "?currentSchema=" + SCHEMA);
        registry.add("spring.datasource.username", () -> System.getenv().getOrDefault("DB_USERNAME", "admin"));
        registry.add("spring.datasource.password", () -> System.getenv().getOrDefault("DB_PASSWORD", "123456"));
        registry.add("spring.flyway.schemas", () -> SCHEMA);
        registry.add("spring.flyway.default-schema", () -> SCHEMA);
        registry.add("app.demo-reset.enabled", () -> "true");
        registry.add("app.planning-model.provider", () -> "external");
    }

    @Autowired DemoResetService reset;
    @Autowired DemoResetWorker worker;
    @Autowired JdbcTemplate jdbc;

    @Test
    void repeatabilityFiveActiveGuardsAndMidResetRollback() {
        assertEquals(SCHEMA, jdbc.queryForObject("SELECT current_schema()", String.class));
        User operator = new User();
        operator.setId(jdbc.queryForObject("SELECT id FROM users WHERE username='admin'", Long.class));
        operator.setUsername("isolated-reset-test");
        operator.setRole("SYSTEM_ADMIN");
        String phrase = DemoDataset.CONFIRM_PHRASE;

        Map<String, Object> first = reset.restore(phrase, true, operator);
        String canonical = (String) first.get("contentDigest");
        assertEquals(6L, jdbc.queryForObject("SELECT count(*) FROM devices WHERE device_code LIKE 'SIM_F2_%'", Long.class));
        assertEquals(3L, jdbc.queryForObject("SELECT count(*) FROM baseline_templates WHERE is_preset=TRUE AND template_status='DRAFT'", Long.class));
        assertEquals(3L, jdbc.queryForObject("SELECT count(*) FROM task_definitions WHERE is_preset=TRUE AND definition_status='ENABLED'", Long.class));

        jdbc.update("UPDATE devices SET device_name='MUTATED_FOR_ROLLBACK' WHERE device_code='SIM_F2_DISPLAY'");
        String beforeFailure = worker.contentDigest();
        assertNotEquals(canonical, beforeFailure);
        assertThrows(IllegalStateException.class,
                () -> reset.restoreWithInjectedFailureForTest(phrase, true, operator));
        assertEquals(beforeFailure, worker.contentDigest(), "mid-reset failure must roll back to the pre-reset state");
        assertTrue(jdbc.queryForObject("""
                SELECT count(*) FROM operation_logs WHERE operation_type='DEMO_DATA_RESET'
                  AND operation_result='FAILED'
                """, Integer.class) >= 1);

        assertThrows(BusinessException.class, () -> reset.restore("错误短语", true, operator));
        assertEquals(beforeFailure, worker.contentDigest());

        int caseNumber = 0;
        for (String status : new String[] {"PLANNING", "SUPERVISING", "PENDING_ASSIGNMENT", "DOWNGRADING", "EXECUTING"}) {
            String code = "RESET-BLOCK-" + (++caseNumber);
            jdbc.update("INSERT INTO tasks (task_code,task_goal,status,created_by) VALUES (?,? ,?,?)",
                    code, "虚构阻断检查", status, "isolated-reset-test");
            try {
                BusinessException blocked = assertThrows(BusinessException.class,
                        () -> reset.restore(phrase, true, operator));
                assertEquals(ErrorCode.DEMO_RESET_BLOCKED, blocked.getErrorCode());
                assertTrue(blocked.getMessage().contains(code));
                assertEquals(beforeFailure, worker.contentDigest());
            } finally {
                jdbc.update("DELETE FROM tasks WHERE task_code=?", code);
            }
        }

        Map<String, Object> restored = reset.restore(phrase, true, operator);
        assertEquals(canonical, restored.get("contentDigest"));
        Map<String, Object> repeated = reset.restore(phrase, true, operator);
        assertEquals(canonical, repeated.get("contentDigest"));
        assertEquals(DemoDataset.VERSION, repeated.get("version"));
        assertTrue(jdbc.queryForObject("""
                SELECT count(*) FROM operation_logs WHERE operation_type='DEMO_DATA_RESET'
                  AND operation_result='SUCCESS' AND detail::text LIKE '%durationMs%'
                """, Integer.class) >= 1);
        assertEquals(0L, jdbc.queryForObject("""
                SELECT count(*) FROM device_capabilities c JOIN devices d ON d.id=c.device_id
                WHERE d.device_code LIKE 'SIM_F2_%' AND c.capability_status<>'UNTESTED'
                """, Long.class));
    }
}
