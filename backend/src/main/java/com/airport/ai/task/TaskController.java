package com.airport.ai.task;

import com.airport.ai.auth.CurrentUser;
import com.airport.ai.common.ApiResponse;
import com.airport.ai.common.PageResult;
import com.airport.ai.event.TaskEvent;
import com.airport.ai.event.TaskEventService;
import com.airport.ai.task.dto.CancelTaskRequest;
import com.airport.ai.task.dto.ClarifyTaskRequest;
import com.airport.ai.task.dto.ManualActionRequest;
import com.airport.ai.task.dto.PlanVersionView;
import com.airport.ai.task.dto.SubmitTaskRequest;
import com.airport.ai.task.dto.TaskView;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * 对应5.4.1开放式任务目标提交与理解、附录B 6.7节任务规划与执行模块。
 * 任务提交/补充/取消由运行操作员发起，不限角色（登录即可，与前端TaskListView约定一致）。
 */
@RestController
@RequestMapping("/api/v1/tasks")
public class TaskController {

    private final TaskService taskService;
    private final TaskEventService taskEventService;
    private final CurrentUser currentUser;

    public TaskController(TaskService taskService, TaskEventService taskEventService, CurrentUser currentUser) {
        this.taskService = taskService;
        this.taskEventService = taskEventService;
        this.currentUser = currentUser;
    }

    @PostMapping
    public ApiResponse<TaskView> submit(@Valid @RequestBody SubmitTaskRequest request) {
        return ApiResponse.ok(TaskView.from(taskService.submit(request, currentUser.get())));
    }

    @GetMapping
    public ApiResponse<PageResult<TaskView>> list(@RequestParam(required = false) String taskCode,
                                                    @RequestParam(required = false) TaskStatus status,
                                                    @RequestParam(required = false) String taskFamily,
                                                    @RequestParam(required = false) @org.springframework.format.annotation.DateTimeFormat(iso = org.springframework.format.annotation.DateTimeFormat.ISO.DATE_TIME) java.time.LocalDateTime createdFrom,
                                                    @RequestParam(required = false) @org.springframework.format.annotation.DateTimeFormat(iso = org.springframework.format.annotation.DateTimeFormat.ISO.DATE_TIME) java.time.LocalDateTime createdTo,
                                                    @RequestParam(defaultValue = "1") int page,
                                                    @RequestParam(defaultValue = "20") int size) {
        return ApiResponse.ok(taskService.list(taskCode, status, taskFamily, createdFrom, createdTo, page, size).map(TaskView::from));
    }

    @GetMapping("/{taskId}")
    public ApiResponse<TaskView> get(@PathVariable Long taskId) {
        return ApiResponse.ok(TaskView.from(taskService.get(taskId)));
    }

    @PostMapping("/{taskId}/clarify")
    public ApiResponse<TaskView> clarify(@PathVariable Long taskId, @Valid @RequestBody ClarifyTaskRequest request) {
        return ApiResponse.ok(TaskView.from(taskService.clarify(taskId, request, currentUser.get())));
    }

    @PostMapping("/{taskId}/cancel")
    public ApiResponse<TaskView> cancel(@PathVariable Long taskId, @Valid @RequestBody CancelTaskRequest request) {
        return ApiResponse.ok(TaskView.from(taskService.cancel(taskId, request.getReason(), currentUser.get())));
    }

    /** 对应5.5.6人工终止，与cancel区分：cancel仅限计划生成前，terminate覆盖6种运行期可终止状态 */
    @PostMapping("/{taskId}/terminate")
    public ApiResponse<TaskView> terminate(@PathVariable Long taskId,
                                            @Valid @RequestBody com.airport.ai.task.dto.TerminateTaskRequest request) {
        if (!Boolean.TRUE.equals(request.getConfirmed())) {
            throw new com.airport.ai.common.BusinessException(com.airport.ai.common.ErrorCode.TERMINATE_REASON_REQUIRED);
        }
        return ApiResponse.ok(TaskView.from(taskService.terminate(taskId, request.getReason(), currentUser.get())));
    }

    @GetMapping("/{taskId}/events")
    public ApiResponse<List<TaskEvent>> events(@PathVariable Long taskId) {
        return ApiResponse.ok(taskEventService.listByTask(taskId));
    }

    @PostMapping("/{taskId}/manual-actions")
    public ApiResponse<TaskView> manualAction(@PathVariable Long taskId, @Valid @RequestBody ManualActionRequest request) {
        return ApiResponse.ok(TaskView.from(taskService.manualAction(taskId, request.getAction(), currentUser.get())));
    }

    @GetMapping("/{taskId}/plan-versions")
    public ApiResponse<List<PlanVersionView>> planVersions(@PathVariable Long taskId) {
        return ApiResponse.ok(taskService.listPlanVersions(taskId).stream().map(PlanVersionView::from).toList());
    }

    @GetMapping("/{taskId}/context-snapshots")
    public ApiResponse<List<ContextSnapshot>> contextSnapshots(@PathVariable Long taskId) {
        return ApiResponse.ok(taskService.listContextSnapshots(taskId));
    }

    /** 对应5.5.1/5.5.2界面元素：步骤设备分配、指令与执行反馈情况 */
    @GetMapping("/{taskId}/step-assignments")
    public ApiResponse<List<com.airport.ai.task.dto.TaskStepAssignmentView>> stepAssignments(@PathVariable Long taskId) {
        return ApiResponse.ok(taskService.listStepAssignments(taskId));
    }
}
