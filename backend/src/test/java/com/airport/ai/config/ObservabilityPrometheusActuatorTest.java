package com.airport.ai.config;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * 验证 SRS_NF018 监控可观测性与 Actuator/Prometheus 指标暴露端点：
 * 1. GET /actuator/prometheus 暴露 Prometheus 标准抓取格式指标；
 * 2. 覆盖 JVM、堆/非堆内存、线程状态、系统/进程及 HTTP 请求等关键性能指标；
 * 3. GET /actuator/health 与 GET /actuator/metrics 端点健康可用；
 * 4. Actuator 监控端点无鉴权拦截放行（SecurityConfig 中 permitAll）。
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.MOCK)
@AutoConfigureMockMvc
@TestPropertySource(properties = {
        "spring.flyway.enabled=false",
        "management.endpoints.web.exposure.include=health,info,prometheus,metrics",
        "management.endpoint.prometheus.enabled=true",
        "management.prometheus.metrics.export.enabled=true",
        "management.metrics.export.prometheus.enabled=true"
})
class ObservabilityPrometheusActuatorTest {

    @Autowired
    private MockMvc mockMvc;

    @Test
    @DisplayName("验证 /actuator/health 端点健康状态为 UP 且无鉴权放行")
    void testActuatorHealthEndpoint() throws Exception {
        mockMvc.perform(get("/actuator/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("UP"));
    }

    @Test
    @DisplayName("验证 /actuator/metrics 元数据端点列出核心指标")
    void testActuatorMetricsEndpoint() throws Exception {
        mockMvc.perform(get("/actuator/metrics"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.names").isArray())
                .andExpect(jsonPath("$.names").value(org.hamcrest.Matchers.hasItem("jvm.memory.used")))
                .andExpect(jsonPath("$.names").value(org.hamcrest.Matchers.hasItem("jvm.threads.live")));
    }

    @Test
    @DisplayName("验证 /actuator/prometheus 暴露 JVM、内存、线程与 HTTP 等 Prometheus 监控指标")
    void testActuatorPrometheusEndpoint() throws Exception {
        // 先发送一次正常请求以产生 HTTP 请求吞吐量统计数据
        mockMvc.perform(get("/actuator/health")).andExpect(status().isOk());

        MvcResult result = mockMvc.perform(get("/actuator/prometheus"))
                .andExpect(status().isOk())
                .andReturn();

        String body = result.getResponse().getContentAsString();
        assertThat(body).isNotEmpty();

        // 1. 验证 JVM 核心指标
        assertThat(body)
                .as("Prometheus endpoint must expose JVM class/buffer/gc metrics")
                .contains("jvm_classes_loaded_classes");

        // 2. 验证 JVM 堆/非堆内存指标
        assertThat(body)
                .as("Prometheus endpoint must expose JVM memory usage metrics")
                .contains("jvm_memory_used_bytes")
                .contains("jvm_memory_max_bytes");

        // 3. 验证 JVM 线程指标
        assertThat(body)
                .as("Prometheus endpoint must expose JVM thread metrics")
                .contains("jvm_threads_live_threads")
                .contains("jvm_threads_states_threads");

        // 4. 验证系统与进程运行指标
        assertThat(body)
                .as("Prometheus endpoint must expose process uptime/cpu metrics")
                .contains("process_uptime_seconds");

        // 5. 验证 HTTP 请求吞吐与时延统计指标
        assertThat(body)
                .as("Prometheus endpoint must expose HTTP server request metrics")
                .contains("http_server_requests_seconds_count");
    }
}
