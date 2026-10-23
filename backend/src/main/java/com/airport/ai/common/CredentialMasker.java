package com.airport.ai.common;

import java.util.Map;
import java.util.Set;

/**
 * 凭据类字段掩码工具，对应5.2.1业务规则8（DeviceView回显）、5.7.2业务规则6（操作记录详情）。
 * 两处此前各自实现了不完全一致的掩码规则，本类统一为唯一实现，避免掩码口径分叉。
 */
public final class CredentialMasker {

    /** 详情JSON中命中以下key（大小写不敏感）的字符串value一律掩码，不区分是否为凭据本身 */
    private static final Set<String> SENSITIVE_KEYS = Set.of(
            "accesscredentialref", "password", "passwordhash", "credential", "token", "secret");

    private CredentialMasker() {}

    /** 保留首尾各2位，中间掩码；4位以内全部掩码 */
    public static String mask(String raw) {
        if (raw == null || raw.length() <= 4) {
            return "****";
        }
        return raw.substring(0, 2) + "****" + raw.substring(raw.length() - 2);
    }

    /** 就地对detail Map中命中敏感key的value做掩码，返回同一个Map便于链式调用 */
    @SuppressWarnings("unchecked")
    public static Map<String, Object> maskSensitiveFields(Map<String, Object> detail) {
        if (detail == null) return null;
        for (Map.Entry<String, Object> entry : detail.entrySet()) {
            if (SENSITIVE_KEYS.contains(entry.getKey().toLowerCase())) {
                if (entry.getValue() instanceof String s) {
                    entry.setValue(mask(s));
                }
            } else if (entry.getValue() instanceof Map<?, ?> nested) {
                maskSensitiveFields((Map<String, Object>) nested);
            }
        }
        return detail;
    }
}
