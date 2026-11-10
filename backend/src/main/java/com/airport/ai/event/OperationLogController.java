package com.airport.ai.event;

import com.airport.ai.auth.CurrentUser;
import com.airport.ai.auth.OperationLogService;
import com.airport.ai.auth.User;
import com.airport.ai.common.ApiResponse;
import com.airport.ai.common.PageResult;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;

/**
 * 对应5.7.2操作记录，业务规则7：查询仅系统管理员可见全量，其他角色仅可见与自身相关记录
 */
@RestController
@RequestMapping("/api/v1/operation-logs")
public class OperationLogController {

    private final OperationLogService operationLogService;
    private final CurrentUser currentUser;

    public OperationLogController(OperationLogService operationLogService, CurrentUser currentUser) {
        this.operationLogService = operationLogService;
        this.currentUser = currentUser;
    }

    @GetMapping
    public ApiResponse<PageResult<OperationLog>> list(@RequestParam(required = false) String username,
                                                        @RequestParam(required = false) String operationType,
                                                        @RequestParam(required = false) String operationResult,
                                                        @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) LocalDateTime startTime,
                                                        @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) LocalDateTime endTime,
                                                        @RequestParam(defaultValue = "1") int page,
                                                        @RequestParam(defaultValue = "20") int size) {
        User operator = currentUser.get();
        // 非系统管理员仅可见自身记录，忽略前端传入的username参数，避免越权查询他人记录（业务规则7）
        String effectiveUsername = "SYSTEM_ADMIN".equals(operator.getRole()) ? username : operator.getUsername();
        return ApiResponse.ok(operationLogService.search(effectiveUsername, operationType, operationResult, startTime, endTime, page, size));
    }

    /**
     * 按ID只读查询单条审计记录（SRS_NF016.R01）：不开放任何PUT/DELETE/PATCH写方法，
     * 使得针对 /api/v1/operation-logs/{id} 的修改或删除请求由框架统一拦截并返回 405 Method Not Allowed。
     */
    @GetMapping("/{id}")
    public ApiResponse<OperationLog> getById(@PathVariable Long id) {
        User operator = currentUser.get();
        OperationLog log = operationLogService.getById(id);
        if (log == null) {
            throw new com.airport.ai.common.BusinessException(
                    com.airport.ai.common.ErrorCode.RESOURCE_NOT_FOUND, "操作记录不存在");
        }
        if (operator != null && !"SYSTEM_ADMIN".equals(operator.getRole())
                && !operator.getUsername().equals(log.getUsername())) {
            throw new org.springframework.security.access.AccessDeniedException("无权访问他人操作记录");
        }
        return ApiResponse.ok(log);
    }
}
