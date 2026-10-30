package com.airport.ai.device;

import com.airport.ai.auth.OperationLogService;
import com.airport.ai.auth.User;
import com.airport.ai.common.BusinessException;
import com.airport.ai.common.ErrorCode;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

/**
 * 心跳超时阈值（SRS_F005，默认30秒，允许10~120秒）。配置值持久化，新值对其后每一轮离线判断生效；
 * 未配置时使用 app.device.heartbeat-timeout-seconds。
 */
@Service
public class HeartbeatSettingService {
    public static final String KEY = "heartbeat.timeout.seconds";
    public static final int MIN_SECONDS = 10;
    public static final int MAX_SECONDS = 120;

    private final SystemSettingMapper mapper;
    private final OperationLogService operationLogService;
    private final int defaultSeconds;

    public HeartbeatSettingService(SystemSettingMapper mapper, OperationLogService operationLogService,
                                   @Value("${app.device.heartbeat-timeout-seconds:30}") int defaultSeconds) {
        this.mapper = mapper;
        this.operationLogService = operationLogService;
        this.defaultSeconds = defaultSeconds;
    }

    public int timeoutSeconds() {
        String stored = mapper.findValue(KEY);
        if (stored == null) return defaultSeconds;
        try {
            int value = Integer.parseInt(stored.trim());
            return value >= MIN_SECONDS && value <= MAX_SECONDS ? value : defaultSeconds;
        } catch (NumberFormatException ex) {
            return defaultSeconds;
        }
    }

    public int update(Integer seconds, User operator) {
        if (seconds == null) {
            throw new BusinessException(ErrorCode.PARAM_MISSING, "请输入心跳超时阈值");
        }
        if (seconds < MIN_SECONDS || seconds > MAX_SECONDS) {
            throw new BusinessException(ErrorCode.PARAM_OUT_OF_RANGE,
                    "心跳超时阈值须在" + MIN_SECONDS + "~" + MAX_SECONDS + "秒之间");
        }
        int before = timeoutSeconds();
        mapper.upsert(KEY, String.valueOf(seconds), operator.getUsername());
        operationLogService.record(operator.getId(), operator.getUsername(), operator.getRole(),
                "HEARTBEAT_TIMEOUT_UPDATE", before + "s -> " + seconds + "s", "SUCCESS", null);
        return seconds;
    }
}
