package com.airport.ai.device;

import com.airport.ai.auth.CurrentUser;
import com.airport.ai.common.ApiResponse;
import com.airport.ai.common.BusinessException;
import com.airport.ai.common.ErrorCode;
import com.airport.ai.device.dto.CreateDeviceCapabilityRequest;
import com.airport.ai.device.dto.DeviceCapabilityView;
import com.airport.ai.device.dto.UpdateDeviceCapabilityRequest;
import jakarta.validation.Valid;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/**
 * 对应5.2.4设备能力画像管理、附录B 6.5节，设备实例能力维护仅配置管理员可操作
 */
@RestController
@RequestMapping("/api/v1/devices/{deviceCode}/capabilities")
@PreAuthorize("hasRole('CONFIG_ADMIN')")
public class DeviceCapabilityController {

    private final DeviceCapabilityService deviceCapabilityService;
    private final DeviceService deviceService;
    private final CurrentUser currentUser;

    public DeviceCapabilityController(DeviceCapabilityService deviceCapabilityService,
                                       DeviceService deviceService,
                                       CurrentUser currentUser) {
        this.deviceCapabilityService = deviceCapabilityService;
        this.deviceService = deviceService;
        this.currentUser = currentUser;
    }

    @GetMapping
    public ApiResponse<List<DeviceCapabilityView>> list(@PathVariable String deviceCode) {
        Long deviceId = deviceService.getByCode(deviceCode).getId();
        return ApiResponse.ok(deviceCapabilityService.list(deviceId).stream().map(DeviceCapabilityView::from).toList());
    }

    @PostMapping
    public ApiResponse<DeviceCapabilityView> create(@PathVariable String deviceCode,
                                                      @Valid @RequestBody CreateDeviceCapabilityRequest request) {
        Long deviceId = deviceService.getByCode(deviceCode).getId();
        return ApiResponse.ok(DeviceCapabilityView.from(
                deviceCapabilityService.create(deviceId, request, currentUser.get())));
    }

    @PutMapping("/{capabilityCode}")
    public ApiResponse<DeviceCapabilityView> update(@PathVariable String deviceCode,
                                                       @PathVariable String capabilityCode,
                                                       @Valid @RequestBody UpdateDeviceCapabilityRequest request) {
        Long deviceId = deviceService.getByCode(deviceCode).getId();
        return ApiResponse.ok(DeviceCapabilityView.from(
                deviceCapabilityService.update(deviceId, capabilityCode, request, currentUser.get())));
    }

    @PostMapping("/{capabilityCode}/test")
    public ApiResponse<DeviceCapabilityView> test(@PathVariable String deviceCode, @PathVariable String capabilityCode) {
        Long deviceId = deviceService.getByCode(deviceCode).getId();
        return ApiResponse.ok(DeviceCapabilityView.from(
                deviceCapabilityService.test(deviceId, capabilityCode, currentUser.get())));
    }

    @PostMapping("/{capabilityCode}/status")
    public ApiResponse<Void> updateStatus(@PathVariable String deviceCode, @PathVariable String capabilityCode,
                                            @RequestBody Map<String, String> body) {
        String status = body.get("status");
        if (!"ENABLED".equals(status) && !"DISABLED".equals(status)) {
            throw new BusinessException(ErrorCode.PARAM_FORMAT_ERROR, "status仅支持ENABLED或DISABLED");
        }
        Long deviceId = deviceService.getByCode(deviceCode).getId();
        deviceCapabilityService.updateStatus(deviceId, capabilityCode, status, currentUser.get());
        return ApiResponse.ok(null);
    }
}
