package com.airport.ai.task;

import com.airport.ai.common.BusinessException;
import com.airport.ai.common.ErrorCode;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.util.*;

/**
 * 场景参数不得携带旅客真实身份信息（SRS_F010 业务规则6、NF003，DEF-S3-032）。
 * 提交及补充时命中身份类字段名即拒绝，不建任务、不持久化、不送模型；
 * 递归检查顶层及任意层级嵌套（Map、List、JSON 文本等），键名忽略大小写与下划线/连字符/点号。
 */
public final class SceneParamsPrivacyGuard {
    private static final ObjectMapper MAPPER = new ObjectMapper();

    private static final Set<String> EXACT_IDENTITY_KEYS = Set.of(
            "passengername", "passengerid", "passenger", "pname", "passname",
            "identitydocumentnumber", "identitydocument", "identitynumber", "idnumber",
            "idcard", "idcardnumber", "idno", "idcardno",
            "documentnumber", "documentno", "docnumber", "docno",
            "passportnumber", "passportno", "passport",
            "certificateno", "certificatenumber", "certno", "certnumber",
            "ssn", "socialsecuritynumber",
            "driverlicensenumber", "driverlicense", "drivinglicensenumber", "drivinglicense",
            "phone", "phonenumber", "telephone", "tel", "mobile", "mobilenumber", "cellphone",
            "contactphone", "contactnumber",
            "email", "emailaddress",
            "realname", "fullname", "travelername", "guestname", "customername", "clientname");

    private SceneParamsPrivacyGuard() {}

    public static void reject(Object sceneParams) {
        if (sceneParams == null) return;
        List<String> hits = new ArrayList<>();
        try {
            JsonNode root = MAPPER.valueToTree(sceneParams);
            scanJsonNode("", root, hits);
        } catch (Exception ex) {
            scanObject("", sceneParams, hits);
        }
        if (!hits.isEmpty()) {
            throw new BusinessException(ErrorCode.PARAM_FORMAT_ERROR,
                    "场景参数不得包含旅客身份信息字段: " + String.join("、", hits.stream().distinct().sorted().toList()));
        }
    }

    private static void scanJsonNode(String path, JsonNode node, List<String> hits) {
        if (node == null || node.isNull()) return;
        if (node.isObject()) {
            Iterator<Map.Entry<String, JsonNode>> fields = node.fields();
            while (fields.hasNext()) {
                Map.Entry<String, JsonNode> entry = fields.next();
                String key = entry.getKey();
                String fullPath = path.isEmpty() ? key : path + "." + key;
                if (isIdentityKey(key)) {
                    hits.add(fullPath);
                }
                scanJsonNode(fullPath, entry.getValue(), hits);
            }
        } else if (node.isArray()) {
            for (int i = 0; i < node.size(); i++) {
                scanJsonNode(path + "[" + i + "]", node.get(i), hits);
            }
        } else if (node.isTextual()) {
            String text = node.asText().trim();
            if ((text.startsWith("{") && text.endsWith("}")) || (text.startsWith("[") && text.endsWith("]"))) {
                try {
                    JsonNode parsed = MAPPER.readTree(text);
                    scanJsonNode(path, parsed, hits);
                } catch (Exception ignored) {}
            }
        }
    }

    private static void scanObject(String path, Object obj, List<String> hits) {
        if (obj == null) return;
        if (obj instanceof Map<?, ?> map) {
            for (Map.Entry<?, ?> entry : map.entrySet()) {
                String key = String.valueOf(entry.getKey());
                String fullPath = path.isEmpty() ? key : path + "." + key;
                if (isIdentityKey(key)) {
                    hits.add(fullPath);
                }
                scanObject(fullPath, entry.getValue(), hits);
            }
        } else if (obj instanceof Iterable<?> iterable) {
            int i = 0;
            for (Object item : iterable) {
                scanObject(path + "[" + i++ + "]", item, hits);
            }
        }
    }

    @SuppressWarnings("unchecked")
    public static Map<String, Object> sanitize(Map<String, Object> sceneParams) {
        if (sceneParams == null) return null;
        Object cleaned = sanitizeValue(sceneParams);
        return cleaned instanceof Map ? (Map<String, Object>) cleaned : sceneParams;
    }

    private static Object sanitizeValue(Object value) {
        if (value == null) return null;
        if (value instanceof Map<?, ?> map) {
            Map<String, Object> cleanedMap = new LinkedHashMap<>();
            for (Map.Entry<?, ?> entry : map.entrySet()) {
                String key = String.valueOf(entry.getKey());
                if (isIdentityKey(key)) continue;
                cleanedMap.put(key, sanitizeValue(entry.getValue()));
            }
            return cleanedMap;
        } else if (value instanceof Iterable<?> iterable) {
            List<Object> cleanedList = new ArrayList<>();
            for (Object item : iterable) {
                cleanedList.add(sanitizeValue(item));
            }
            return cleanedList;
        } else if (value instanceof Object[] array) {
            List<Object> cleanedList = new ArrayList<>();
            for (Object item : array) {
                cleanedList.add(sanitizeValue(item));
            }
            return cleanedList;
        } else if (value instanceof String text) {
            String trimmed = text.trim();
            if ((trimmed.startsWith("{") && trimmed.endsWith("}")) || (trimmed.startsWith("[") && trimmed.endsWith("]"))) {
                try {
                    Object parsed = MAPPER.readValue(trimmed, Object.class);
                    Object cleaned = sanitizeValue(parsed);
                    return MAPPER.writeValueAsString(cleaned);
                } catch (Exception ignored) {
                    return text;
                }
            }
        }
        return value;
    }

    static boolean isIdentityKey(String key) {
        if (key == null) return false;
        String normalized = key.replaceAll("[_\\-\\s\\.]", "").toLowerCase();
        if (EXACT_IDENTITY_KEYS.contains(normalized)) return true;
        if (normalized.contains("passengername")
                || normalized.contains("identitydocument")
                || normalized.contains("passportnumber")
                || normalized.contains("passportno")
                || normalized.contains("idcardnumber")
                || normalized.contains("idcardno")
                || normalized.contains("socialsecurity")) {
            return true;
        }
        if (normalized.contains("passenger") && (normalized.contains("name") || normalized.contains("id") || normalized.contains("doc"))) {
            return true;
        }
        if (normalized.contains("identity") && (normalized.contains("number") || normalized.contains("no") || normalized.contains("card") || normalized.contains("doc"))) {
            return true;
        }
        return false;
    }
}
