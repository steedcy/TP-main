package com.airport.ai.device;

import com.airport.ai.common.ApiResponse;
import com.airport.ai.device.dto.DeviceAgentReportRequest;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/** Canonical device-facing report ingress defined by the P0 communication contract. */
@RestController
@RequestMapping("/device-api/v1/agents")
public class DeviceApiController {
    private final DeviceAgentReportService reportService;
    private final ReportRejectionRecorder rejectionRecorder;

    public DeviceApiController(DeviceAgentReportService reportService, ReportRejectionRecorder rejectionRecorder) {
        this.reportService = reportService;
        this.rejectionRecorder = rejectionRecorder;
    }

    @PostMapping("/{agentCode}/report")
    public ApiResponse<Void> report(@PathVariable String agentCode,
                                    @Valid @RequestBody DeviceAgentReportRequest request) {
        try {
            reportService.accept(agentCode, request);
        } catch (com.airport.ai.common.BusinessException ex) {
            if (ex.getErrorCode() == com.airport.ai.common.ErrorCode.PARAM_FORMAT_ERROR
                    || ex.getErrorCode() == com.airport.ai.common.ErrorCode.PARAM_MISSING
                    || ex.getErrorCode() == com.airport.ai.common.ErrorCode.PARAM_OUT_OF_RANGE) {
                rejectionRecorder.record(agentCode, ReportRejectionRecorder.INVALID_FORMAT, ex.getMessage());
            }
            throw ex;
        }
        return ApiResponse.ok(null);
    }
}
