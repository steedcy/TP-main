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
}
