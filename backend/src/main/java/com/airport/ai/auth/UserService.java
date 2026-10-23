package com.airport.ai.auth;

import com.airport.ai.auth.dto.CreateUserRequest;
import com.airport.ai.common.BusinessException;
import com.airport.ai.common.ErrorCode;
import com.airport.ai.common.PageResult;
import com.github.pagehelper.PageHelper;
import com.github.pagehelper.PageInfo;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;

/**
 * 对应附录B 6.2节账号管理模块。创建/重置密码/停用启用均为账号管理关键操作，
 * 写入操作记录（对应5.7.2业务规则1、3）。
 */
@Service
public class UserService {

    private final UserMapper userMapper;
    private final PasswordEncoder passwordEncoder;
    private final OperationLogService operationLogService;

    public UserService(UserMapper userMapper, PasswordEncoder passwordEncoder,
                        OperationLogService operationLogService) {
        this.userMapper = userMapper;
        this.passwordEncoder = passwordEncoder;
        this.operationLogService = operationLogService;
    }

    @Transactional
    public User create(CreateUserRequest request, User operator) {
        if (userMapper.existsByUsername(request.getUsername())) {
            throw new BusinessException(ErrorCode.USERNAME_TAKEN);
        }
        User user = new User();
        user.setUsername(request.getUsername());
        user.setPasswordHash(passwordEncoder.encode(request.getPassword()));
        user.setRealName(request.getRealName());
        user.setRole(request.getRole());
        user.setContact(request.getContact());
        user.setStatus("ACTIVE");
        userMapper.insert(user);
        operationLogService.record(operator.getId(), operator.getUsername(), operator.getRole(),
                "USER_CREATE", user.getUsername(), "SUCCESS", null);
        return user;
    }

    public PageResult<User> list(String status, int page, int size) {
        PageHelper.startPage(page, size);
        if (status != null && !status.isBlank()) {
            return PageResult.of(new PageInfo<>(userMapper.findByStatusPaged(status)));
        }
        return PageResult.of(new PageInfo<>(userMapper.findAllPaged()));
    }

    @Transactional
    public void resetPassword(Long userId, String newPassword, User operator) {
        User user = userMapper.findById(userId)
                .orElseThrow(() -> new BusinessException(ErrorCode.USER_NOT_FOUND));
        user.setPasswordHash(passwordEncoder.encode(newPassword));
        user.setUpdatedAt(LocalDateTime.now());
        userMapper.update(user);
        operationLogService.record(operator.getId(), operator.getUsername(), operator.getRole(),
                "PASSWORD_RESET", user.getUsername(), "SUCCESS", null);
    }

    @Transactional
    public void updateStatus(Long userId, String status, User operator) {
        if (userId.equals(operator.getId()) && "INACTIVE".equals(status)) {
            throw new BusinessException(ErrorCode.CANNOT_DISABLE_SELF);
        }
        User user = userMapper.findById(userId)
                .orElseThrow(() -> new BusinessException(ErrorCode.USER_NOT_FOUND));
        user.setStatus(status);
        user.setUpdatedAt(LocalDateTime.now());
        userMapper.update(user);
        operationLogService.record(operator.getId(), operator.getUsername(), operator.getRole(),
                "USER_STATUS_CHANGE", user.getUsername() + " -> " + status, "SUCCESS", null);
    }
}
