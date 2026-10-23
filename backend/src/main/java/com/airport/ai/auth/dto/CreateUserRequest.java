package com.airport.ai.auth.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

/**
 * 对应附录B 6.2.1节，字段范围按TBD-06拍板结论
 */
public class CreateUserRequest {

    @NotBlank
    @Size(min = 1, max = 32)
    private String username;

    @NotBlank
    @Size(min = 8, max = 32)
    private String password;

    @NotBlank
    @Size(max = 32)
    private String realName;

    @NotBlank
    @Pattern(regexp = "SYSTEM_ADMIN|OPERATOR|CONFIG_ADMIN")
    private String role;

    @NotBlank
    @Size(max = 128)
    private String contact;

    public String getUsername() { return username; }
    public void setUsername(String username) { this.username = username; }
    public String getPassword() { return password; }
    public void setPassword(String password) { this.password = password; }
    public String getRealName() { return realName; }
    public void setRealName(String realName) { this.realName = realName; }
    public String getRole() { return role; }
    public void setRole(String role) { this.role = role; }
    public String getContact() { return contact; }
    public void setContact(String contact) { this.contact = contact; }
}
