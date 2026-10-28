package com.airport.ai.dashboard;

import com.airport.ai.auth.CurrentUser;
import com.airport.ai.common.ApiResponse;
import com.airport.ai.common.BusinessException;
import com.airport.ai.common.ErrorCode;
import com.airport.ai.task.TaskStatus;
import java.time.LocalDate;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.function.Supplier;
import java.util.stream.Collectors;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/dashboard")
@PreAuthorize("hasAnyRole('OPERATOR', 'SYSTEM_ADMIN', 'CONFIG_ADMIN')")
public class DashboardController {
    private static final Logger log = LoggerFactory.getLogger(DashboardController.class);
    private static final ExecutorService POOL = Executors.newFixedThreadPool(4, r -> {
        Thread t = new Thread(r, "dashboard-metric");
        t.setDaemon(true);
        return t;
    });

    private final DashboardMapper mapper;
    private final CurrentUser currentUser;
    private final long metricTimeoutMs;
    private final Set<String> faultMetrics;
    private final String faultMode;

    public DashboardController(DashboardMapper mapper, CurrentUser currentUser,
                               @Value("${app.dashboard.metric-timeout-ms:3000}") long metricTimeoutMs,
                               @Value("${app.dashboard.fault-injection.metrics:}") String faultMetrics,
                               @Value("${app.dashboard.fault-injection.mode:FAIL}") String faultMode) {
        this.mapper = mapper;
        this.currentUser = currentUser;
        this.metricTimeoutMs = metricTimeoutMs;
        this.faultMetrics = Arrays.stream(faultMetrics.split(",")).map(String::trim)
                .filter(v -> !v.isEmpty()).collect(Collectors.toSet());
        this.faultMode = faultMode;
    }

    /**
     * 单个指标失败或超时只影响该指标：返回null并记入failedMetrics，其余指标照常返回（TC-004.S4、SRS_F002）。
     * 故障注入仅在隔离测试后端通过app.dashboard.fault-injection.*开启，默认关闭。
     */
    private <T> T metric(String name, List<String> failed, Supplier<T> query) {
        Future<T> future = POOL.submit(() -> {
            if (faultMetrics.contains(name)) {
                if ("DELAY".equalsIgnoreCase(faultMode)) Thread.sleep(metricTimeoutMs * 3);
                else throw new IllegalStateException("injected metric fault: " + name);
            }
            return query.get();
        });
        try {
            return future.get(metricTimeoutMs, TimeUnit.MILLISECONDS);
        } catch (Exception e) {
            future.cancel(true);
            log.warn("总览指标 {} 查询失败或超时: {}", name, e.toString());
            failed.add(name);
            return null;
        }
    }

    @GetMapping("/overview")
    public ApiResponse<Map<String, Object>> overview(@RequestParam(defaultValue = "TODAY") String period) {
        if (!List.of("TODAY", "LAST_7_DAYS").contains(period))
            throw new BusinessException(ErrorCode.PARAM_FORMAT_ERROR, "统计周期仅支持TODAY或LAST_7_DAYS");
        List<String> failed = new CopyOnWriteArrayList<>();
        Map<String, Object> metrics = new LinkedHashMap<>();
        metrics.put("agentTotal", metric("agentTotal", failed, mapper::countAgents));
        metrics.put("agentOnline", metric("agentOnline", failed, mapper::countOnlineAgents));
        boolean taskVisible = !"CONFIG_ADMIN".equals(currentUser.get().getRole());
        List<DashboardExceptionView> latest = List.of();
        if (taskVisible) {
            metrics.put("taskInProgress", metric("taskInProgress", failed, mapper::countInProgressTasks));
            metrics.put("pendingManual", metric("pendingManual", failed, mapper::countPendingManualTasks));
            metrics.put("unhandledExceptions", metric("unhandledExceptions", failed, mapper::countPendingExceptions));
            LocalDate since = "TODAY".equals(period) ? LocalDate.now() : LocalDate.now().minusDays(6);
            metrics.put("replanningCount", metric("replanningCount", failed,
                    () -> mapper.countReplansSince(since.atStartOfDay())));
            List<Map<String, Object>> rows = metric("statusCounts", failed, mapper::countTasksByStatus);
            if (rows == null) {
                metrics.put("statusCounts", null);
            } else {
                Map<String, Long> statusCounts = new LinkedHashMap<>();
                for (TaskStatus status : TaskStatus.values()) statusCounts.put(status.name(), 0L);
                for (Map<String, Object> row : rows) {
                    statusCounts.put(String.valueOf(row.get("status")), ((Number) row.get("total")).longValue());
                }
                metrics.put("statusCounts", statusCounts);
            }
            List<DashboardExceptionView> exceptions = metric("latestExceptions", failed, mapper::latestExceptions);
            latest = exceptions == null ? List.of() : exceptions;
        }
        Map<String, Object> data = new LinkedHashMap<>();
        data.put("metrics", metrics);
        data.put("latestExceptions", latest);
        data.put("failedMetrics", failed);
        data.put("period", period);
        return ApiResponse.ok(data);
    }
}
