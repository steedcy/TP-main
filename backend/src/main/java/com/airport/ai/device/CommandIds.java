package com.airport.ai.device;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.UUID;

/**
 * 统一生成设备业务消息的指令编号（SRS_F007.R02）：CMD-yyyyMMddHHmmss-8位大写十六进制，共27字符，
 * 在列宽32内。承接、执行、取消各为独立逻辑消息，各自调用一次；同一逻辑消息的重试沿用原编号并递增尝试序号。
 */
public final class CommandIds {
    private static final DateTimeFormatter STAMP = DateTimeFormatter.ofPattern("yyyyMMddHHmmss");

    private CommandIds() {}

    public static String next() {
        return "CMD-" + LocalDateTime.now().format(STAMP) + "-"
                + UUID.randomUUID().toString().replace("-", "").substring(0, 8).toUpperCase();
    }
}
