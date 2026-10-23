package com.airport.ai.auth.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public class LoginRequest {

    @NotBlank(message = "请输入账号")
    @Size(min = 1, max = 32)
    private String username;

    @NotBlank(message = "请输入密码")
    @Size(min = 8, max = 32)
    private String password;

    public String getUsername() { return username; }
    public void setUsername(String username) { this.username = username; }
    public String getPassword() { return password; }
    public void setPassword(String password) { this.password = password; }
}
