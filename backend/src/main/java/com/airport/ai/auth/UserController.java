package com.airport.ai.auth;

import com.airport.ai.common.ApiResponse;
import com.airport.ai.auth.dto.CreateUserRequest;
import com.airport.ai.auth.dto.ResetPasswordRequest;
import com.airport.ai.auth.dto.UpdateStatusRequest;
import com.airport.ai.common.PageResult;
import jakarta.validation.Valid;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

/**
 * 对应附录B 6.1.3/6.2节，账号管理仅系统管理员可操作
 */
@RestController
@RequestMapping("/api/v1/users")
@PreAuthorize("hasRole('SYSTEM_ADMIN')")
public class UserController {

    private final UserService userService;
    private final AuthService authService;
    private final CurrentUser currentUser;

    public UserController(UserService userService, AuthService authService, CurrentUser currentUser) {
        this.userService = userService;
        this.authService = authService;
        this.currentUser = currentUser;
    }

    @PostMapping
    public ApiResponse<User> create(@Valid @RequestBody CreateUserRequest request) {
        return ApiResponse.ok(userService.create(request, currentUser.get()));
    }

    @GetMapping
    public ApiResponse<PageResult<User>> list(@RequestParam(required = false) String status,
                                               @RequestParam(defaultValue = "1") int page,
                                               @RequestParam(defaultValue = "20") int size) {
        return ApiResponse.ok(userService.list(status, page, size));
    }

    @PostMapping("/{userId}/unlock")
    public ApiResponse<Void> unlock(@PathVariable Long userId) {
        User operator = currentUser.get();
        authService.unlock(userId, operator);
        return ApiResponse.ok(null);
    }

    @PostMapping("/{userId}/reset-password")
    public ApiResponse<Void> resetPassword(@PathVariable Long userId, @Valid @RequestBody ResetPasswordRequest request) {
        userService.resetPassword(userId, request.getNewPassword(), currentUser.get());
        return ApiResponse.ok(null);
    }

    @PostMapping("/{userId}/status")
    public ApiResponse<Void> updateStatus(@PathVariable Long userId, @Valid @RequestBody UpdateStatusRequest request) {
        userService.updateStatus(userId, request.getStatus(), currentUser.get());
        return ApiResponse.ok(null);
    }
}
