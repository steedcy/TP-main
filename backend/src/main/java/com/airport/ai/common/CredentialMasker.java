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

    /** 就地对detail Map中命中敏感key的value做掩码，返回同一个Map（不可变Map则返回脱敏副本）便于链式调用 */
    @SuppressWarnings("unchecked")
    public static Map<String, Object> maskSensitiveFields(Map<String, Object> detail) {
        if (detail == null) return null;
        try {
            for (Map.Entry<String, Object> entry : detail.entrySet()) {
                String key = entry.getKey();
                Object value = entry.getValue();
                if (value instanceof String s) {
                    if (isSensitiveKey(key)) {
                        entry.setValue(mask(s));
                    }
                } else if (value instanceof Map<?, ?> nested) {
                    Map<String, Object> maskedNested = maskSensitiveFields((Map<String, Object>) nested);
                    if (maskedNested != nested) {
                        entry.setValue(maskedNested);
                    }
                } else if (value instanceof Collection<?> col) {
                    Collection<?> maskedCol = maskCollection(col);
                    if (maskedCol != col) {
                        entry.setValue(maskedCol);
                    }
                } else if (value instanceof Object[] arr) {
                    entry.setValue(maskArray(arr));
                }
            }
            return detail;
        } catch (UnsupportedOperationException ex) {
            Map<String, Object> copy = new java.util.LinkedHashMap<>();
            for (Map.Entry<String, Object> entry : detail.entrySet()) {
                String key = entry.getKey();
                Object value = entry.getValue();
                if (value instanceof String s) {
                    if (isSensitiveKey(key)) {
                        copy.put(key, mask(s));
                    } else {
                        copy.put(key, s);
                    }
                } else if (value instanceof Map<?, ?> nested) {
                    copy.put(key, maskSensitiveFields((Map<String, Object>) nested));
                } else if (value instanceof Collection<?> col) {
                    copy.put(key, maskCollection(col));
                } else if (value instanceof Object[] arr) {
                    copy.put(key, maskArray(arr));
                } else {
                    copy.put(key, value);
                }
            }
            return copy;
        }
    }

    @SuppressWarnings("unchecked")
    private static Collection<?> maskCollection(Collection<?> col) {
        java.util.List<Object> copyList = new java.util.ArrayList<>(col.size());
        boolean changed = false;
        for (Object item : col) {
            if (item instanceof Map<?, ?> nestedItem) {
                Map<String, Object> masked = maskSensitiveFields((Map<String, Object>) nestedItem);
                if (masked != nestedItem) {
                    changed = true;
                }
                copyList.add(masked);
            } else if (item instanceof Collection<?> nestedCol) {
                Collection<?> masked = maskCollection(nestedCol);
                if (masked != nestedCol) {
                    changed = true;
                }
                copyList.add(masked);
            } else if (item instanceof Object[] arr) {
                changed = true;
                copyList.add(maskArray(arr));
            } else {
                copyList.add(item);
            }
        }
        return changed ? copyList : col;
    }

    @SuppressWarnings("unchecked")
    private static java.util.List<Object> maskArray(Object[] arr) {
        java.util.List<Object> copyList = new java.util.ArrayList<>(arr.length);
        for (Object item : arr) {
            if (item instanceof Map<?, ?> nestedItem) {
                copyList.add(maskSensitiveFields((Map<String, Object>) nestedItem));
            } else if (item instanceof Collection<?> nestedCol) {
                copyList.add(maskCollection(nestedCol));
            } else if (item instanceof Object[] nestedArr) {
                copyList.add(maskArray(nestedArr));
            } else {
                copyList.add(item);
            }
        }
        return copyList;
    }
}
