package com.airport.ai.auth.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/**
 * 对应附录B 6.2.3节，密码长度约束与创建账号一致（8~32位）
 */
public class ResetPasswordRequest {

    @NotBlank(message = "请输入新密码")
    @Size(min = 8, max = 32, message = "密码长度需为8~32位")
    private String newPassword;

    public String getNewPassword() { return newPassword; }
    public void setNewPassword(String newPassword) { this.newPassword = newPassword; }
}
