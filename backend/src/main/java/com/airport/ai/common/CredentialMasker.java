package com.airport.ai.common;

import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * 凭据类字段掩码工具，对应5.2.1业务规则8（DeviceView回显）、5.7.2业务规则6（操作记录详情）、SRS_NF001敏感凭据保护。
 * 统一实现全量敏感凭据字段的识别与掩码脱敏，杜绝密码明文、哈希、访问令牌等原值暴露。
 */
public final class CredentialMasker {

    /** 详情JSON中命中以下key（大小写不敏感）的字符串value一律掩码 */
    private static final Set<String> EXACT_SENSITIVE_KEYS = Set.of(
            "accesscredentialref", "password", "passwordhash", "credential", "token", "secret",
            "devicetoken", "accesstoken", "secretkey", "apikey", "authtoken", "refreshtoken",
            "bearer", "privatekey", "clientsecret"
    );

    private CredentialMasker() {}

    /** 判断字段名是否为敏感凭据相关字段 */
    public static boolean isSensitiveKey(String key) {
        if (key == null) return false;
        String lower = key.toLowerCase();
        if (EXACT_SENSITIVE_KEYS.contains(lower)) {
            return true;
        }
        return lower.contains("password")
                || lower.contains("token")
                || lower.contains("secret")
                || lower.contains("credential");
    }

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
            Object value = entry.getValue();
            if (value instanceof String s) {
                if (isSensitiveKey(entry.getKey())) {
                    entry.setValue(mask(s));
                }
            } else if (value instanceof Map<?, ?> nested) {
                maskSensitiveFields((Map<String, Object>) nested);
            } else if (value instanceof Collection<?> col) {
                for (Object item : col) {
                    if (item instanceof Map<?, ?> nestedItem) {
                        maskSensitiveFields((Map<String, Object>) nestedItem);
                    }
                }
            }
        }
        return detail;
    }
}
