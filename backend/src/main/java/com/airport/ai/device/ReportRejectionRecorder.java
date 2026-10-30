package com.airport.ai.device;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

import java.util.concurrent.ConcurrentHashMap;

/**
 * 被拒绝的设备上报（格式非法 / 身份校验失败）记录一次脱敏设备事件（SRS_F005.R08、DEF-S3-016）。
 * 独立事务：上报主流程回滚后事件仍落库；业务状态本身不被改动。事件只含原因码与摘要，不含令牌或原始载荷。
 * 同一代理同一原因在节流窗口内只记一次，避免被恶意刷屏。
 */
@Service
public class ReportRejectionRecorder {
    public static final String INVALID_FORMAT = "ERR_REPORT_INVALID_FORMAT";
    public static final String AUTH_FAILED = "ERR_REPORT_AUTH_FAILED";
    static final long THROTTLE_MILLIS = 5_000;

    private final DeviceAgentMapper agentMapper;
    private final DeviceEventService eventService;
    private final ConcurrentHashMap<String, Long> lastRecorded = new ConcurrentHashMap<>();

    public ReportRejectionRecorder(DeviceAgentMapper agentMapper, DeviceEventService eventService) {
        this.agentMapper = agentMapper;
        this.eventService = eventService;
    }

    /** 记录成功返回true；代理不存在或被节流返回false。绝不抛出异常影响上报响应。 */
    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public boolean record(String agentCode, String reasonCode, String summary) {
        try {
            if (agentCode == null || agentCode.isBlank()) return false;
            long now = System.currentTimeMillis();
            String key = agentCode + "|" + reasonCode;
            Long previous = lastRecorded.get(key);
            if (previous != null && now - previous < THROTTLE_MILLIS) return false;
            DeviceAgent agent = agentMapper.findByAgentCode(agentCode).orElse(null);
            if (agent == null) return false;
            lastRecorded.put(key, now);
            eventService.append(agent.getId(), "STATUS_REPORT_REJECTED", "SYSTEM", reasonCode,
                    "上报被丢弃，未改变代理状态：" + sanitize(summary));
            return true;
        } catch (RuntimeException ex) {
            return false;
        }
    }

    /** 从上报路径解析代理编号；无法解析返回null。 */
    public static String agentCodeFromPath(String path) {
        if (path == null) return null;
        String[] s = path.split("/");
        if (path.startsWith("/device-api/v1/agents/") && s.length >= 5) return s[4];
        if (path.startsWith("/api/v1/device-agents/report/")) return null; // 该兼容路径按设备编码寻址
        if (path.startsWith("/api/v1/device-agents/") && s.length >= 5) return s[4];
        return null;
    }

    private static String sanitize(String text) {
        if (text == null) return "";
        String cleaned = text.replaceAll("[\\r\\n]+", " ");
        return cleaned.length() > 120 ? cleaned.substring(0, 120) : cleaned;
    }
}
