package com.airport.ai.device;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * 统一设备业务消息的指令号（SRS_F007.R02：CMD-yyyyMMddHHmmss-8位大写十六进制，共27字符，
 * 在列宽32以内）。承接、执行、取消各为独立逻辑消息，首发各取一次，同一逻辑消息重试沿用原编号。
 */
public final class CommandIds {
    private static final DateTimeFormatter STAMP = DateTimeFormatter.ofPattern("yyyyMMddHHmmss");
    private static final AtomicInteger COUNTER =
            new AtomicInteger(new java.security.SecureRandom().nextInt() & 0xFFFF0000);

    private CommandIds() {}

    public static String next() {
        int seq = COUNTER.getAndIncrement();
        return "CMD-" + LocalDateTime.now().format(STAMP) + "-"
                + String.format("%08X", seq);
    }
}
