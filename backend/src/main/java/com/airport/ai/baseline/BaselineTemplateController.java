package com.airport.ai.baseline;

import com.airport.ai.auth.CurrentUser;
import com.airport.ai.baseline.dto.*;
import com.airport.ai.common.ApiResponse;
import jakarta.validation.Valid;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * 对应5.3.1基线服务模板定义、5.3.2试运行与启用、附录B 6.6节。仅配置管理员可维护，
 * 与5.2.4A/5.2.4一致的权限模式：列表/详情查看不限角色，增删改及生命周期操作限CONFIG_ADMIN。
 */
@RestController
@RequestMapping("/api/v1/baseline-templates")
public class BaselineTemplateController {

    private final BaselineTemplateService templateService;
    private final BaselineDryRunService dryRunService;
    private final CurrentUser currentUser;

    public BaselineTemplateController(BaselineTemplateService templateService,
                                       BaselineDryRunService dryRunService,
                                       CurrentUser currentUser) {
        this.templateService = templateService;
        this.dryRunService = dryRunService;
        this.currentUser = currentUser;
    }

    @GetMapping
    public ApiResponse<List<BaselineTemplateView>> list() {
        return ApiResponse.ok(templateService.listAll().stream().map(BaselineTemplateView::from).toList());
    }

    @GetMapping("/{templateId}")
    public ApiResponse<BaselineTemplateView> get(@PathVariable Long templateId) {
        return ApiResponse.ok(BaselineTemplateView.from(templateService.get(templateId)));
    }

    @PostMapping
    @PreAuthorize("hasRole('CONFIG_ADMIN')")
    public ApiResponse<BaselineTemplateView> create(@Valid @RequestBody CreateBaselineTemplateRequest request) {
        return ApiResponse.ok(BaselineTemplateView.from(templateService.create(request, currentUser.get())));
    }

    @PutMapping("/{templateId}")
    @PreAuthorize("hasRole('CONFIG_ADMIN')")
    public ApiResponse<BaselineTemplateView> update(@PathVariable Long templateId,
                                                      @Valid @RequestBody UpdateBaselineTemplateRequest request) {
        return ApiResponse.ok(BaselineTemplateView.from(templateService.update(templateId, request, currentUser.get())));
    }

    @PostMapping("/{templateId}/dry-run")
    @PreAuthorize("hasRole('CONFIG_ADMIN')")
    public ApiResponse<DryRunResultView> dryRun(@PathVariable Long templateId, @Valid @RequestBody DryRunRequest request) {
        return ApiResponse.ok(dryRunService.dryRun(templateId, request, currentUser.get()));
    }

    @GetMapping("/{templateId}/dry-runs/{taskId}")
    @PreAuthorize("hasRole('CONFIG_ADMIN')")
    public ApiResponse<DryRunResultView> dryRunResult(@PathVariable Long templateId, @PathVariable Long taskId) {
        return ApiResponse.ok(dryRunService.result(templateId, taskId));
    }

    @PostMapping("/{templateId}/dry-runs/{taskId}/cancel")
    @PreAuthorize("hasRole('CONFIG_ADMIN')")
    public ApiResponse<DryRunResultView> cancelDryRun(@PathVariable Long templateId, @PathVariable Long taskId) {
        return ApiResponse.ok(dryRunService.cancel(templateId,taskId,currentUser.get()));
    }

    @PostMapping("/{templateId}/enable")
    @PreAuthorize("hasRole('CONFIG_ADMIN')")
    public ApiResponse<Void> enable(@PathVariable Long templateId) {
        templateService.enable(templateId, currentUser.get());
        return ApiResponse.ok(null);
    }

    @PostMapping("/{templateId}/disable")
    @PreAuthorize("hasRole('CONFIG_ADMIN')")
    public ApiResponse<Void> disable(@PathVariable Long templateId) {
        templateService.disable(templateId, currentUser.get());
        return ApiResponse.ok(null);
    }

    @DeleteMapping("/{templateId}")
    @PreAuthorize("hasRole('CONFIG_ADMIN')")
    public ApiResponse<Void> delete(@PathVariable Long templateId) {
        templateService.delete(templateId, currentUser.get());
        return ApiResponse.ok(null);
    }
}
