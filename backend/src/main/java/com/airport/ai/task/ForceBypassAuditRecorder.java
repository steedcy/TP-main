package com.airport.ai.task;

import com.airport.ai.auth.OperationLogService;
import com.airport.ai.auth.User;
import com.airport.ai.event.TaskEventService;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

/**
 * 对应 SRS_F013.R07 / DEF-S3-089：
 * 记录强行放行拦截时间线事件与操作审计日志。
 * 采用独立物理事务（REQUIRES_NEW），确保在 manualAction 抛出
 * BusinessException(ErrorCode.FORCE_BYPASS_HARD_CHECK, 4110) 导致外层事务回滚时，
 * 拦截事件（FORCE_BYPASS_INTERCEPTED）与审计记录（FORCE_BYPASS_ATTEMPT，结果为 INTERCEPTED）
 * 仍能成功落库持久化，保障安全审计链条完整。
 */
@Service
public class ForceBypassAuditRecorder {

    private final TaskEventService taskEventService;
    private final OperationLogService operationLogService;

    public ForceBypassAuditRecorder(TaskEventService taskEventService, OperationLogService operationLogService) {
        this.taskEventService = taskEventService;
        this.operationLogService = operationLogService;
    }

    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public void recordInterception(Long taskId, String taskCode, String action, User operator) {
        taskEventService.append(taskId, "FORCE_BYPASS_INTERCEPTED", "OPERATOR", "ERR_FORCE_BYPASS_REJECTED",
                "操作员试图强行放行硬性校验失败的计划，系统已拦截并拒绝（操作: " + action + "）");
        Long userId = operator == null ? null : operator.getId();
        String username = operator == null ? "OPERATOR" : operator.getUsername();
        String role = operator == null ? "OPERATOR" : operator.getRole();
        operationLogService.record(userId, username, role,
                "FORCE_BYPASS_ATTEMPT", (taskCode != null ? taskCode : String.valueOf(taskId)) + " -> " + action, "INTERCEPTED", null);
    }
}
