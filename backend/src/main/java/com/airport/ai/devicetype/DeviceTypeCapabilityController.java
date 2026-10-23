package com.airport.ai.devicetype;

import com.airport.ai.auth.CurrentUser;
import com.airport.ai.common.ApiResponse;
import com.airport.ai.common.BusinessException;
import com.airport.ai.common.ErrorCode;
import com.airport.ai.devicetype.dto.*;
import jakarta.validation.Valid;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/**
 * 对应5.2.4A设备类型能力边界管理、附录B 6.4节。查看为所有登录角色可用（供任务规划/能力配置参考），
 * 维护（边界更新、模板增删改）仅配置管理员可操作。
 */
@RestController
@RequestMapping("/api/v1/device-types")
public class DeviceTypeCapabilityController {

    private final DeviceTypeCapabilityService service;
    private final CurrentUser currentUser;

    public DeviceTypeCapabilityController(DeviceTypeCapabilityService service, CurrentUser currentUser) {
        this.service = service;
        this.currentUser = currentUser;
    }

    @GetMapping
    public ApiResponse<List<DeviceTypeCapability>> listAll() {
        return ApiResponse.ok(service.listAll());
    }

    @GetMapping("/{deviceTypeCode}/capability-boundary")
    public ApiResponse<CapabilityBoundaryView> getBoundary(@PathVariable String deviceTypeCode) {
        return ApiResponse.ok(service.getBoundaryView(deviceTypeCode));
    }

    @PutMapping("/{deviceTypeCode}/capability-boundary")
    @PreAuthorize("hasRole('CONFIG_ADMIN')")
    public ApiResponse<CapabilityBoundaryView> updateBoundary(@PathVariable String deviceTypeCode,
                                                               @Valid @RequestBody UpdateCapabilityBoundaryRequest request) {
        service.updateBoundary(deviceTypeCode, request, currentUser.get());
        return ApiResponse.ok(service.getBoundaryView(deviceTypeCode));
    }

    @GetMapping("/{deviceTypeCode}/capability-templates")
    public ApiResponse<List<CapabilityTemplateView>> listTemplates(@PathVariable String deviceTypeCode) {
        return ApiResponse.ok(service.listTemplates(deviceTypeCode).stream().map(CapabilityTemplateView::from).toList());
    }

    @PostMapping("/{deviceTypeCode}/capability-templates")
    @PreAuthorize("hasRole('CONFIG_ADMIN')")
    public ApiResponse<CapabilityTemplateView> createTemplate(@PathVariable String deviceTypeCode,
                                                                @Valid @RequestBody CreateCapabilityTemplateRequest request) {
        return ApiResponse.ok(CapabilityTemplateView.from(service.createTemplate(deviceTypeCode, request, currentUser.get())));
    }

    @PutMapping("/{deviceTypeCode}/capability-templates/{templateCode}")
    @PreAuthorize("hasRole('CONFIG_ADMIN')")
    public ApiResponse<CapabilityTemplateView> updateTemplate(@PathVariable String deviceTypeCode,
                                                                @PathVariable String templateCode,
                                                                @Valid @RequestBody UpdateCapabilityTemplateRequest request) {
        return ApiResponse.ok(CapabilityTemplateView.from(
                service.updateTemplate(deviceTypeCode, templateCode, request, currentUser.get())));
    }

    @PostMapping("/{deviceTypeCode}/capability-templates/{templateCode}/status")
    @PreAuthorize("hasRole('CONFIG_ADMIN')")
    public ApiResponse<Void> updateTemplateStatus(@PathVariable String deviceTypeCode,
                                                    @PathVariable String templateCode,
                                                    @RequestBody Map<String, String> body) {
        String status = body.get("status");
        if (!"ACTIVE".equals(status) && !"INACTIVE".equals(status)) {
            throw new BusinessException(ErrorCode.PARAM_FORMAT_ERROR, "status仅支持ACTIVE或INACTIVE");
        }
        service.updateTemplateStatus(deviceTypeCode, templateCode, status, currentUser.get());
        return ApiResponse.ok(null);
    }

    @DeleteMapping("/{deviceTypeCode}/capability-templates/{templateCode}")
    @PreAuthorize("hasRole('CONFIG_ADMIN')")
    public ApiResponse<Void> deleteTemplate(@PathVariable String deviceTypeCode, @PathVariable String templateCode) {
        service.deleteTemplate(deviceTypeCode, templateCode, currentUser.get());
        return ApiResponse.ok(null);
    }

    /** 对应8.4.4节能力约束矩阵，图5.2.4A-4 */
    @GetMapping("/capability-matrix")
    public ApiResponse<List<Map<String, Object>>> capabilityMatrix() {
        List<Map<String, Object>> matrix = service.listAll().stream()
                .map(dt -> {
                    List<String> supported = service.parseSupportedTypes(dt.getDeviceTypeCode());
                    Map<String, Object> row = new java.util.LinkedHashMap<>();
                    row.put("deviceTypeCode", dt.getDeviceTypeCode());
                    row.put("deviceTypeName", dt.getDeviceTypeName());
                    for (String cap : CapabilityCatalog.ALL_CODES) {
                        row.put(cap, supported.contains(cap));
                    }
                    return row;
                })
                .toList();
        return ApiResponse.ok(matrix);
    }
}
