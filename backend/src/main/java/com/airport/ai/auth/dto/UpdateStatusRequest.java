package com.airport.ai.auth.dto;

import jakarta.validation.constraints.Pattern;

public class UpdateStatusRequest {

    @Pattern(regexp = "ACTIVE|INACTIVE", message = "status仅支持ACTIVE或INACTIVE")
    private String status;

    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }
}
