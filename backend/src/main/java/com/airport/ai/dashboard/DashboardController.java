package com.airport.ai.dashboard;

import com.airport.ai.auth.CurrentUser;
import com.airport.ai.common.ApiResponse;
import com.airport.ai.common.BusinessException;
import com.airport.ai.common.ErrorCode;
import com.airport.ai.task.TaskStatus;
import java.time.LocalDate;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/dashboard")
@PreAuthorize("hasAnyRole('OPERATOR', 'SYSTEM_ADMIN', 'CONFIG_ADMIN')")
public class DashboardController {
    private final DashboardMapper mapper;
    private final CurrentUser currentUser;

    public DashboardController(DashboardMapper mapper, CurrentUser currentUser) {
        this.mapper = mapper;
        this.currentUser = currentUser;
    }

    @GetMapping("/overview")
    public ApiResponse<Map<String, Object>> overview(@RequestParam(defaultValue = "TODAY") String period) {
        if (!List.of("TODAY", "LAST_7_DAYS").contains(period))
            throw new BusinessException(ErrorCode.PARAM_FORMAT_ERROR, "统计周期仅支持TODAY或LAST_7_DAYS");
        Map<String, Object> metrics = new LinkedHashMap<>();
        metrics.put("agentTotal", mapper.countAgents());
        metrics.put("agentOnline", mapper.countOnlineAgents());
        boolean taskVisible = !"CONFIG_ADMIN".equals(currentUser.get().getRole());
        List<DashboardExceptionView> latest = List.of();
        if (taskVisible) {
            metrics.put("taskInProgress", mapper.countInProgressTasks());
            metrics.put("pendingManual", mapper.countPendingManualTasks());
            metrics.put("unhandledExceptions", mapper.countPendingExceptions());
            LocalDate since = "TODAY".equals(period) ? LocalDate.now() : LocalDate.now().minusDays(6);
            metrics.put("replanningCount", mapper.countReplansSince(since.atStartOfDay()));
            Map<String, Long> statusCounts = new LinkedHashMap<>();
            for (TaskStatus status : TaskStatus.values()) statusCounts.put(status.name(), 0L);
            for (Map<String, Object> row : mapper.countTasksByStatus()) {
                statusCounts.put(String.valueOf(row.get("status")), ((Number) row.get("total")).longValue());
            }
            metrics.put("statusCounts", statusCounts);
            latest = mapper.latestExceptions();
        }
        Map<String, Object> data = new LinkedHashMap<>();
        data.put("metrics", metrics);
        data.put("latestExceptions", latest);
        data.put("period", period);
        return ApiResponse.ok(data);
    }
}
