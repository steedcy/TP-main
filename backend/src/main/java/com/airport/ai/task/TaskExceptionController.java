package com.airport.ai.task;

import com.airport.ai.common.ApiResponse;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * 对应5.5.3/5.5.5异常列表：类型+状态筛选、未处置异常计数（运行总览引用）
 */
@RestController
@RequestMapping("/api/v1/task-exceptions")
public class TaskExceptionController {

    private final TaskExceptionService taskExceptionService;

    public TaskExceptionController(TaskExceptionService taskExceptionService) {
        this.taskExceptionService = taskExceptionService;
    }

    @GetMapping
    @PreAuthorize("hasAnyRole('SYSTEM_ADMIN', 'OPERATOR')")
    public ApiResponse<List<TaskException>> search(@RequestParam(required = false) String exceptionType,
                                                    @RequestParam(required = false) String exceptionStatus) {
        return ApiResponse.ok(taskExceptionService.search(exceptionType, exceptionStatus));
    }

    @GetMapping("/pending-count")
    @PreAuthorize("hasAnyRole('SYSTEM_ADMIN', 'OPERATOR')")
    public ApiResponse<Long> pendingCount() {
        return ApiResponse.ok(taskExceptionService.countPending());
    }
}
