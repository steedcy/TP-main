package com.airport.ai.device;

import com.airport.ai.auth.CurrentUser;
import com.airport.ai.common.ApiResponse;
import com.airport.ai.common.BusinessException;
import com.airport.ai.common.ErrorCode;
import com.airport.ai.device.dto.CreateDeviceRequest;
import com.airport.ai.device.dto.DeviceView;
import com.airport.ai.device.dto.DeviceTokenRotationView;
import com.airport.ai.device.dto.UpdateDeviceRequest;
import com.airport.ai.common.PageResult;
import jakarta.validation.Valid;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

/**
 * 对应5.2.1设备档案与连接测试、附录B 6.3节。设备档案维护仅配置管理员可操作，
 * 与5.7.2业务规则7一致：这类关键配置操作不做数据级过滤，仅角色级限制。
 */
@RestController
@RequestMapping("/api/v1/devices")
@PreAuthorize("hasRole('CONFIG_ADMIN')")
public class DeviceController {

    private final DeviceService deviceService;
    private final DeviceCredentialService deviceCredentialService;
    private final CurrentUser currentUser;
    private final com.airport.ai.auth.OperationLogService operationLogService;

    public DeviceController(DeviceService deviceService, DeviceCredentialService deviceCredentialService,
                            CurrentUser currentUser, com.airport.ai.auth.OperationLogService operationLogService) {
        this.deviceService = deviceService;
        this.deviceCredentialService = deviceCredentialService;
        this.currentUser = currentUser;
        this.operationLogService = operationLogService;
    }

    @PostMapping
    public ApiResponse<DeviceView> create(@Valid @RequestBody CreateDeviceRequest request) {
        return ApiResponse.ok(DeviceView.from(deviceService.create(request, currentUser.get())));
    }

    @GetMapping
    public ApiResponse<PageResult<DeviceView>> list(@RequestParam(required = false) String deviceTypeCode,
                                                     @RequestParam(required = false) String keyword,
                                                     @RequestParam(defaultValue = "1") int page,
                                                     @RequestParam(defaultValue = "20") int size) {
        PageResult<Device> result = deviceService.list(deviceTypeCode, null, keyword, page, size);
        return ApiResponse.ok(result.map(DeviceView::from));
    }

    @GetMapping("/{deviceCode}")
    public ApiResponse<DeviceView> get(@PathVariable String deviceCode) {
        return ApiResponse.ok(DeviceView.from(deviceService.getByCode(deviceCode)));
    }

    @PutMapping("/{deviceCode}")
    public ApiResponse<DeviceView> update(@PathVariable String deviceCode, @Valid @RequestBody UpdateDeviceRequest request) {
        return ApiResponse.ok(DeviceView.from(deviceService.updateByCode(deviceCode, request, currentUser.get())));
    }

    @PostMapping("/{deviceCode}/connection-test")
    public ApiResponse<Map<String, String>> testConnection(@PathVariable String deviceCode) {
        Device device = deviceService.testConnectionByCode(deviceCode, currentUser.get());
        boolean passed = "PASSED".equals(device.getConnectionTestStatus());
        Map<String, String> data = new java.util.HashMap<>();
        data.put("result", device.getConnectionTestStatus());
        data.put("failReason", passed ? null : device.getConnectionTestResult());
        return ApiResponse.ok(data);
    }

    /** The generated device token is returned once; only its hash and encrypted copy are persisted. */
    @PostMapping("/{deviceCode}/device-token/rotate")
    public ApiResponse<DeviceTokenRotationView> rotateDeviceToken(@PathVariable String deviceCode) {
        DeviceCredentialService.IssuedToken issued = deviceCredentialService.rotate(deviceCode);
        var operator = currentUser.get();
        operationLogService.record(operator.getId(), operator.getUsername(), operator.getRole(),
                "DEVICE_TOKEN_ROTATE", deviceCode, "SUCCESS", null);
        return ApiResponse.ok(new DeviceTokenRotationView(deviceCode, issued.token(), issued.issuedAt()));
    }

    @PostMapping("/{deviceCode}/status")
    public ApiResponse<Void> updateStatus(@PathVariable String deviceCode, @RequestBody Map<String, String> body) {
        String status = body.get("status");
        if (!"ACTIVE".equals(status) && !"INACTIVE".equals(status)) {
            throw new BusinessException(ErrorCode.PARAM_FORMAT_ERROR, "status仅支持ACTIVE或INACTIVE");
        }
        deviceService.updateStatusByCode(deviceCode, status, currentUser.get());
        return ApiResponse.ok(null);
    }

    @DeleteMapping("/{deviceCode}")
    public ApiResponse<Void> delete(@PathVariable String deviceCode) {
        deviceService.deleteByCode(deviceCode, currentUser.get());
        return ApiResponse.ok(null);
    }
}
