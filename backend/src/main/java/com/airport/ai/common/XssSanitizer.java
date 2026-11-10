package com.airport.ai.common;

import org.springframework.web.util.HtmlUtils;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Pattern;

/**
 * XSS 与 HTML 注入输入净化工具类（对应 SRS_NF004）。
 * 对任务名称、设备名称/备注、能力描述、模板说明等文本字段执行幂等 HTML 字符转义与脚本注入清洗。
 */
public final class XssSanitizer {

    private static final Pattern HTML_TAG_OR_SCRIPT_PATTERN = Pattern.compile(
            "(?i)(<\\s*/?\\s*[a-z!]|<!--|-->|javascript\\s*:|vbscript\\s*:|data\\s*:\\s*text/html|on[a-z]{2,20}\\s*=)"
    );

    private static final Pattern DANGEROUS_PROTOCOL_PATTERN = Pattern.compile(
            "(?i)(javascript|vbscript)\\s*:"
    );

    private XssSanitizer() {
    }

    /**
     * 对名称、标题、描述、备注类文本字段进行幂等 HTML 实体转义：
     * 先还原可能已转义的实体再统一执行 HTML 转义，避免二次重复转义（如 &amp;amp;），
     * 同时对 javascript:/vbscript: 伪协议前缀做脱敏替换。
     */
    public static String escapeHtml(String input) {
        if (input == null) {
            return null;
        }
        String unescaped = HtmlUtils.htmlUnescape(input);
        String escaped = HtmlUtils.htmlEscape(unescaped);
        return neutralizeDangerousProtocols(escaped);
    }

    /**
     * 对包含业务表达式/自由文本的字段（如任务目标、模板条件、终止原因、JSON 文本参数）：
     * 当检测到 HTML 标签、事件处理器（onerror=/onload= 等）或脚本伪协议（javascript:）时执行完整 HTML 转义；
     * 普通非 HTML 业务标点（如 "A->B"）保持原样，兼顾 XSS 防护与业务契约兼容。
     */
    public static String sanitizeRichText(String input) {
        if (input == null || input.isEmpty()) {
            return input;
        }
        String unescaped = HtmlUtils.htmlUnescape(input);
        if (HTML_TAG_OR_SCRIPT_PATTERN.matcher(input).find()
                || HTML_TAG_OR_SCRIPT_PATTERN.matcher(unescaped).find()) {
            return escapeHtml(input);
        }
        return input;
    }

    /**
     * 递归净化 Map 结构中的字符串值（如 sceneParams）。
     */
    @SuppressWarnings("unchecked")
    public static Map<String, Object> sanitizeMapValues(Map<String, Object> source) {
        if (source == null || source.isEmpty()) {
            return source;
        }
        Map<String, Object> sanitized = new LinkedHashMap<>(source.size());
        for (Map.Entry<String, Object> entry : source.entrySet()) {
            String key = sanitizeRichText(entry.getKey());
            sanitized.put(key, sanitizeObjectValue(entry.getValue()));
        }
        return sanitized;
    }

    @SuppressWarnings("unchecked")
    private static Object sanitizeObjectValue(Object value) {
        if (value instanceof String str) {
            return sanitizeRichText(str);
        }
        if (value instanceof Map<?, ?> mapVal) {
            Map<String, Object> copy = new LinkedHashMap<>(mapVal.size());
            for (Map.Entry<?, ?> entry : mapVal.entrySet()) {
                String k = entry.getKey() != null ? sanitizeRichText(String.valueOf(entry.getKey())) : null;
                copy.put(k, sanitizeObjectValue(entry.getValue()));
            }
            return copy;
        }
        if (value instanceof List<?> listVal) {
            List<Object> copy = new ArrayList<>(listVal.size());
            for (Object item : listVal) {
                copy.add(sanitizeObjectValue(item));
            }
            return copy;
        }
        return value;
    }

    private static String neutralizeDangerousProtocols(String input) {
        if (input == null || input.isEmpty()) {
            return input;
        }
        return DANGEROUS_PROTOCOL_PATTERN.matcher(input).replaceAll("$1&#58;");
    }
}
