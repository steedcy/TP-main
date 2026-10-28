package com.airport.ai.dashboard;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

@Mapper
public interface DashboardMapper {
    @Select("SELECT COUNT(*) FROM device_agents WHERE agent_status <> 'ARCHIVED'")
    long countAgents();

    @Select("SELECT COUNT(*) FROM device_agents WHERE agent_status = 'ENABLED' AND online_status = 'ONLINE'")
    long countOnlineAgents();

    @Select("SELECT COUNT(*) FROM tasks WHERE is_dry_run = FALSE AND status IN ('PENDING_ASSIGNMENT', 'DOWNGRADING', 'EXECUTING')")
    long countInProgressTasks();

    @Select("SELECT COUNT(*) FROM tasks WHERE is_dry_run = FALSE AND status = 'PENDING_MANUAL'")
    long countPendingManualTasks();

    @Select("SELECT COUNT(*) FROM task_exceptions e JOIN tasks t ON t.id = e.task_id WHERE t.is_dry_run = FALSE AND e.exception_status = 'PENDING'")
    long countPendingExceptions();

    @Select("SELECT COUNT(*) FROM task_events ev JOIN tasks t ON t.id = ev.task_id WHERE t.is_dry_run = FALSE AND ev.event_type = 'REPLANNING_TRIGGERED' AND ev.occurred_at >= #{since}")
    long countReplansSince(@Param("since") LocalDateTime since);

    @Select("SELECT status, COUNT(*) AS total FROM tasks WHERE is_dry_run = FALSE GROUP BY status")
    List<Map<String, Object>> countTasksByStatus();

    @Select("""
            SELECT e.id, e.task_id, t.task_code, e.exception_type, e.occurred_at,
                   e.exception_status, e.reason_code, e.impact_conclusion
            FROM task_exceptions e JOIN tasks t ON t.id = e.task_id
            WHERE t.is_dry_run = FALSE
            ORDER BY e.occurred_at DESC, e.id DESC LIMIT 5
            """)
    List<DashboardExceptionView> latestExceptions();
}
