package com.airport.ai.taskdef;

import com.airport.ai.auth.CurrentUser;
import com.airport.ai.common.ApiResponse;
import com.airport.ai.taskdef.dto.CreateTaskDefinitionRequest;
import com.airport.ai.taskdef.dto.TaskDefinitionView;
import com.airport.ai.taskdef.dto.UpdateTaskDefinitionRequest;
import jakarta.validation.Valid;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * 对应5.6.1旅客服务任务定义管理。列表/详情查看不限角色（任务提交页需读取以渲染任务族下拉），
 * 增删改及启停限配置管理员，与5.3.1基线模板一致的权限模式。
 */
@RestController
@RequestMapping("/api/v1/task-definitions")
public class TaskDefinitionController {

    private final TaskDefinitionService service;
    private final CurrentUser currentUser;

    public TaskDefinitionController(TaskDefinitionService service, CurrentUser currentUser) {
        this.service = service;
        this.currentUser = currentUser;
    }

    @GetMapping
    public ApiResponse<List<TaskDefinitionView>> list() {
        return ApiResponse.ok(service.listAll().stream().map(TaskDefinitionView::from).toList());
    }

    @GetMapping("/{id}")
    public ApiResponse<TaskDefinitionView> get(@PathVariable Long id) {
        return ApiResponse.ok(TaskDefinitionView.from(service.get(id)));
    }

    @PostMapping
    @PreAuthorize("hasRole('CONFIG_ADMIN')")
    public ApiResponse<TaskDefinitionView> create(@Valid @RequestBody CreateTaskDefinitionRequest request) {
        return ApiResponse.ok(TaskDefinitionView.from(service.create(request, currentUser.get())));
    }

    @PutMapping("/{id}")
    @PreAuthorize("hasRole('CONFIG_ADMIN')")
    public ApiResponse<TaskDefinitionView> update(@PathVariable Long id, @Valid @RequestBody UpdateTaskDefinitionRequest request) {
        return ApiResponse.ok(TaskDefinitionView.from(service.update(id, request, currentUser.get())));
    }

    @PostMapping("/{id}/enable")
    @PreAuthorize("hasRole('CONFIG_ADMIN')")
    public ApiResponse<Void> enable(@PathVariable Long id) {
        service.enable(id, currentUser.get());
        return ApiResponse.ok(null);
    }

    @PostMapping("/{id}/disable")
    @PreAuthorize("hasRole('CONFIG_ADMIN')")
    public ApiResponse<Void> disable(@PathVariable Long id) {
        service.disable(id, currentUser.get());
        return ApiResponse.ok(null);
    }

    @DeleteMapping("/{id}")
    @PreAuthorize("hasRole('CONFIG_ADMIN')")
    public ApiResponse<Void> delete(@PathVariable Long id) {
        service.delete(id, currentUser.get());
        return ApiResponse.ok(null);
    }
}
