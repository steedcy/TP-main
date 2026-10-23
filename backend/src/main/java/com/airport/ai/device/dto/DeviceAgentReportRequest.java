package com.airport.ai.device.dto;

import com.airport.ai.task.dto.ExecutionFeedbackRequest;
import com.airport.ai.task.dto.TaskResponseRequest;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;

public class DeviceAgentReportRequest {
    @NotBlank
    @Pattern(regexp = "STATUS|TASK_RESPONSE|EXECUTION_FEEDBACK")
    private String reportType;
    @NotBlank
    private String reportedAt;
    @Valid
    private StatusPayload status;
    @Valid
    private TaskResponseRequest response;
    @Valid
    private ExecutionFeedbackRequest feedback;

    public String getReportType() { return reportType; }
    public void setReportType(String reportType) { this.reportType = reportType; }
    public String getReportedAt() { return reportedAt; }
    public void setReportedAt(String reportedAt) { this.reportedAt = reportedAt; }
    public StatusPayload getStatus() { return status; }
    public void setStatus(StatusPayload status) { this.status = status; }
    public TaskResponseRequest getResponse() { return response; }
    public void setResponse(TaskResponseRequest response) { this.response = response; }
    public ExecutionFeedbackRequest getFeedback() { return feedback; }
    public void setFeedback(ExecutionFeedbackRequest feedback) { this.feedback = feedback; }

    public static class StatusPayload {
        @NotBlank
        @Pattern(regexp = "ONLINE|OFFLINE")
        private String onlineStatus;
        @NotBlank
        @Pattern(regexp = "IDLE|BUSY")
        private String workStatus;
        @Valid
        private Location location;
        private Object businessStatus;
        public String getOnlineStatus() { return onlineStatus; }
        public void setOnlineStatus(String onlineStatus) { this.onlineStatus = onlineStatus; }
        public String getWorkStatus() { return workStatus; }
        public void setWorkStatus(String workStatus) { this.workStatus = workStatus; }
        public Location getLocation() { return location; }
        public void setLocation(Location location) { this.location = location; }
        public Object getBusinessStatus() { return businessStatus; }
        public void setBusinessStatus(Object businessStatus) { this.businessStatus = businessStatus; }
    }

    public static class Location {
        @jakarta.validation.constraints.NotNull
        private java.math.BigDecimal x;
        @jakarta.validation.constraints.NotNull
        private java.math.BigDecimal y;
        private String zone;
        public java.math.BigDecimal getX() { return x; }
        public void setX(java.math.BigDecimal x) { this.x = x; }
        public java.math.BigDecimal getY() { return y; }
        public void setY(java.math.BigDecimal y) { this.y = y; }
        public String getZone() { return zone; }
        public void setZone(String zone) { this.zone = zone; }
    }
}
