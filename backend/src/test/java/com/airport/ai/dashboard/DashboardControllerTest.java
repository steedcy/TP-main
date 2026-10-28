package com.airport.ai.dashboard;

import com.airport.ai.auth.CurrentUser;
import com.airport.ai.auth.User;
import com.airport.ai.task.TaskMapper;
import org.apache.ibatis.annotations.Select;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Method;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

/** SRS_F002：单指标失败/超时隔离（TC-004.S4）与试运行任务不计入正式统计（DEF-S3-002）。 */
class DashboardControllerTest {

    private final DashboardMapper mapper = mock(DashboardMapper.class);
    private final CurrentUser currentUser = mock(CurrentUser.class);

    private DashboardController controller(String faultMetrics, String mode, long timeoutMs, String role) {
        User u = new User();
        u.setRole(role);
        when(currentUser.get()).thenReturn(u);
        when(mapper.countAgents()).thenReturn(5L);
        when(mapper.countOnlineAgents()).thenReturn(3L);
        when(mapper.countInProgressTasks()).thenReturn(2L);
        when(mapper.countPendingManualTasks()).thenReturn(1L);
        when(mapper.countPendingExceptions()).thenReturn(4L);
        when(mapper.countReplansSince(any())).thenReturn(7L);
        when(mapper.countTasksByStatus()).thenReturn(List.<Map<String, Object>>of(Map.of("status", "COMPLETED", "total", 6L)));
        when(mapper.latestExceptions()).thenReturn(List.of());
        return new DashboardController(mapper, currentUser, timeoutMs, faultMetrics, mode);
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> metrics(DashboardController c) {
        return (Map<String, Object>) c.overview("TODAY").getData().get("metrics");
    }

    @SuppressWarnings("unchecked")
    private List<String> failed(DashboardController c) {
        return (List<String>) c.overview("TODAY").getData().get("failedMetrics");
    }

    @Test
    void noFaultReturnsAllMetricsAndNoFailures() {
        DashboardController c = controller("", "FAIL", 2000, "SYSTEM_ADMIN");
        assertEquals(5L, metrics(c).get("agentTotal"));
        assertEquals(7L, metrics(c).get("replanningCount"));
        assertTrue(failed(c).isEmpty());
    }

    @Test
    void singleMetricFailureYieldsNullForThatMetricOnly() {
        DashboardController c = controller("agentOnline", "FAIL", 2000, "OPERATOR");
        Map<String, Object> m = metrics(c);
        assertNull(m.get("agentOnline"));
        assertEquals(5L, m.get("agentTotal"));
        assertEquals(2L, m.get("taskInProgress"));
        assertEquals(List.of("agentOnline"), failed(c));
    }

    @Test
    void singleMetricTimeoutIsIsolatedAndBounded() {
        DashboardController c = controller("pendingManual", "DELAY", 300, "OPERATOR");
        long start = System.currentTimeMillis();
        Map<String, Object> m = metrics(c);
        assertTrue(System.currentTimeMillis() - start < 3000);
        assertNull(m.get("pendingManual"));
        assertEquals(4L, m.get("unhandledExceptions"));
    }

    @Test
    void realQueryExceptionIsAlsoIsolated() {
        DashboardController c = controller("", "FAIL", 2000, "SYSTEM_ADMIN");
        when(mapper.countPendingExceptions()).thenThrow(new IllegalStateException("db"));
        assertNull(metrics(c).get("unhandledExceptions"));
        assertEquals(List.of("unhandledExceptions"), failed(c));
    }

    @Test
    void configAdminSeesNoTaskMetrics() {
        DashboardController c = controller("", "FAIL", 2000, "CONFIG_ADMIN");
        Map<String, Object> m = metrics(c);
        assertFalse(m.containsKey("taskInProgress"));
        assertFalse(m.containsKey("statusCounts"));
        assertEquals(3L, m.get("agentOnline"));
    }

    @Test
    void everyFormalTaskQueryExcludesDryRunTasks() {
        for (String name : List.of("countInProgressTasks", "countPendingManualTasks", "countPendingExceptions",
                "countReplansSince", "countTasksByStatus", "latestExceptions")) {
            Method method = java.util.Arrays.stream(DashboardMapper.class.getDeclaredMethods())
                    .filter(m -> m.getName().equals(name)).findFirst().orElseThrow();
            String sql = String.join(" ", method.getAnnotation(Select.class).value());
            assertTrue(sql.contains("is_dry_run = FALSE"), name + " must exclude dry-run tasks: " + sql);
        }
        assertNotNull(TaskMapper.class);
    }
}
