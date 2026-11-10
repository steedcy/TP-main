package com.airport.ai.task;

import com.airport.ai.common.BusinessException;
import com.airport.ai.common.ErrorCode;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

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
            "realname", "fullname", "travelername", "guestname", "customername", "clientname",
            "passengerphone", "passengermobile", "passengeremail", "passengerpassport", "passengeridcard",
            "旅客姓名", "乘客姓名", "旅客身份", "乘客身份", "身份证号", "身份证号码", "身份证", "身份证件",
            "证件号码", "证件号", "证件", "护照号码", "护照号", "护照", "手机号码", "手机号", "手机",
            "联系电话", "联系方式", "电话号码", "电话", "电子邮箱", "邮箱", "真实姓名", "姓名",
            "旅客电话", "旅客手机", "旅客护照", "旅客身份证", "旅客", "乘客", "身份");

    private static final Pattern IDENTITY_KV_PATTERN = Pattern.compile(
            "(?i)(?<prefix>[;；,，]?\\s*)(?<key>[a-zA-Z_\\u4e00-\\u9fa5][a-zA-Z0-9_\\-\\u4e00-\\u9fa5]*)\\s*(?:[:=＝：]|(?:为|是))\\s*(?<val>\"[^\"]*\"|'[^']*'|[^;；,，\\s\\n\\r\\)）\\]\\}]+(?:\\s+(?![a-zA-Z_\\u4e00-\\u9fa5]+[\\s]*[:=＝：为是]|(?:前往|去往|到达|在|到|并|由|从|并由|并在|且))[a-zA-Z0-9_\\-\\u4e00-\\u9fa5]+){0,2})");

    private static final Pattern CHINESE_NAME_PATTERN = Pattern.compile(
            "(?i)(?:旅客姓名|乘客姓名|真实姓名|姓名|passenger\\s*name)\\s*[:：=＝为是\\s]\\s*([\\u4e00-\\u9fa5]{2,4}|[A-Za-z0-9_\\-]{2,30})");

    private static final Pattern PASSPORT_PATTERN = Pattern.compile(
            "(?i)(?:护照(?:号码?|号)?|passport(?:\\s*(?:no|number))?)\\s*[:：=＝为是\\s]\\s*([A-Za-z0-9_\\-]{6,16})");

    private static final Pattern TEL_PATTERN = Pattern.compile(
            "(?i)(?:联系电话|联系方式|电话(?:号码?|号)?|手机(?:号码?|号)?|phone(?:\\s*(?:no|number))?|tel|mobile)\\s*[:：=＝为是\\s]\\s*(\\+?\\d[\\d\\-\\s]{6,15}\\d)");

    private static final Pattern ID_CARD_PATTERN = Pattern.compile(
            "\\b[1-9]\\d{5}(?:18|19|20)\\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\\d|3[01])\\d{3}[\\dXx]\\b");

    private static final Pattern PHONE_PATTERN = Pattern.compile(
            "(?<!\\d)1[3-9]\\d{9}(?!\\d)");

    private static final Pattern EMAIL_PATTERN = Pattern.compile(
            "[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}");

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

    public static boolean containsIdentityText(String text) {
        if (text == null || text.isBlank()) return false;
        Matcher m = IDENTITY_KV_PATTERN.matcher(text);
        while (m.find()) {
            String key = m.group("key");
            if (isIdentityKey(key)) return true;
        }
        if (CHINESE_NAME_PATTERN.matcher(text).find()) return true;
        if (PASSPORT_PATTERN.matcher(text).find()) return true;
        if (TEL_PATTERN.matcher(text).find()) return true;
        if (ID_CARD_PATTERN.matcher(text).find()) return true;
        if (PHONE_PATTERN.matcher(text).find()) return true;
        if (EMAIL_PATTERN.matcher(text).find()) return true;
        return false;
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
            if (containsIdentityText(text)) {
                hits.add(path.isEmpty() ? "[identity text in value]" : path);
            }
        }
    }

    /** 检测澄清问题是否索要身份或联系方式，供特殊旅客流程拒绝过期/错误问题。 */
    public static boolean asksForIdentity(String question) {
        if (question == null || question.isBlank()) return false;
        String normalized = question.toLowerCase(Locale.ROOT).replaceAll("[_\\-\\s]", "");
        return normalized.contains("姓名")
                || normalized.contains("身份证")
                || normalized.contains("证件")
                || normalized.contains("护照")
                || normalized.contains("手机")
                || normalized.contains("电话")
                || normalized.contains("电子邮箱")
                || normalized.contains("邮箱")
                || normalized.contains("identity")
                || normalized.contains("passport")
                || normalized.contains("phone")
                || normalized.contains("mobile")
                || normalized.contains("email");
    }

    /** 特殊旅客澄清值持久化或送模前，脱敏其中可识别的身份字段和联系方式。 */
    public static Map<String, String> sanitizeFreeTextAnswers(Map<String, String> answers) {
        if (answers == null) return null;
        Map<String, String> cleaned = new LinkedHashMap<>();
        answers.forEach((question, answer) -> cleaned.put(question, sanitizeGoal(answer)));
        return cleaned;
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
        } else if (obj instanceof String text) {
            String trimmed = text.trim();
            if ((trimmed.startsWith("{") && trimmed.endsWith("}")) || (trimmed.startsWith("[") && trimmed.endsWith("]"))) {
                try {
                    JsonNode parsed = MAPPER.readTree(trimmed);
                    scanJsonNode(path, parsed, hits);
                } catch (Exception ignored) {}
            }
            if (containsIdentityText(text)) {
                hits.add(path.isEmpty() ? "[identity text in value]" : path);
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
                    return sanitizeGoal(text);
                }
            }
            return sanitizeGoal(text);
        }
        return value;
    }

    public static String sanitizeText(String text) {
        if (text == null || text.isBlank()) return text;
        String trimmed = text.trim();
        if ((trimmed.startsWith("{") && trimmed.endsWith("}")) || (trimmed.startsWith("[") && trimmed.endsWith("]"))) {
            try {
                Object parsed = MAPPER.readValue(trimmed, Object.class);
                Object cleaned = sanitizeValue(parsed);
                return MAPPER.writeValueAsString(cleaned);
            } catch (Exception ignored) {
                return sanitizeGoal(text);
            }
        }
        return sanitizeGoal(text);
    }

    public static boolean isIdentityKey(String key) {
        if (key == null) return false;
        String normalized = key.replaceAll("[_\\-\\s\\.]", "").toLowerCase(Locale.ROOT);
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
        if (normalized.contains("passenger") && (normalized.contains("name") || normalized.contains("id") || normalized.contains("doc") || normalized.contains("phone") || normalized.contains("mobile") || normalized.contains("passport") || normalized.contains("card") || normalized.contains("mail"))) {
            return true;
        }
        if (normalized.contains("identity") && (normalized.contains("number") || normalized.contains("no") || normalized.contains("card") || normalized.contains("doc") || normalized.contains("text"))) {
            return true;
        }
        if (normalized.contains("旅客") && (normalized.contains("名") || normalized.contains("身份") || normalized.contains("号") || normalized.contains("证") || normalized.contains("手机") || normalized.contains("电话") || normalized.contains("护照"))) {
            return true;
        }
        if (normalized.contains("乘客") && (normalized.contains("名") || normalized.contains("身份") || normalized.contains("号") || normalized.contains("证") || normalized.contains("手机") || normalized.contains("电话") || normalized.contains("护照"))) {
            return true;
        }
        if (normalized.contains("身份证") || normalized.contains("护照") || normalized.contains("手机") || normalized.contains("电话") || normalized.contains("证件")) {
            return true;
        }
        if (normalized.contains("phone") || normalized.contains("mobile") || normalized.contains("telephone")
                || normalized.contains("passport") || normalized.contains("idcard")
                || normalized.contains("email") || normalized.contains("idnumber")
                || normalized.contains("idno") || normalized.contains("docnumber")
                || normalized.contains("docno") || normalized.contains("ssn")) {
            return true;
        }
        return false;
    }

    /**
     * 对送模副本中的自然语言任务目标进行旅客身份信息脱敏（SRS_F011.R06、DEF-S3-088、SRS_NF003.R01）。
     * 内部持久化及任务追溯保留原始目标，送外部模型前剥离或替换身份字段与敏感值。
     */
    public static String sanitizeGoal(String goal) {
        if (goal == null || goal.isBlank()) return goal;
        String text = goal;

        // 1. 结构化/键值对形式的身份字段脱敏（key=val, key: val 等）
        Matcher m = IDENTITY_KV_PATTERN.matcher(text);
        StringBuffer sb = new StringBuffer();
        while (m.find()) {
            String key = m.group("key");
            if (isIdentityKey(key)) {
                String prefix = m.group("prefix");
                String replacement = (prefix != null && !prefix.isBlank() ? prefix : "") + "[PROTECTED_IDENTITY]";
                m.appendReplacement(sb, Matcher.quoteReplacement(replacement));
            } else {
                m.appendReplacement(sb, Matcher.quoteReplacement(m.group(0)));
            }
        }
        m.appendTail(sb);
        text = sb.toString();

        // 2. 中英文自然语言姓名脱敏
        text = CHINESE_NAME_PATTERN.matcher(text).replaceAll("[PROTECTED_IDENTITY]");

        // 3. 护照号码脱敏
        text = PASSPORT_PATTERN.matcher(text).replaceAll("[PROTECTED_IDENTITY]");

        // 4. 电话/手机关键字组合脱敏
        text = TEL_PATTERN.matcher(text).replaceAll("[PROTECTED_PHONE]");

        // 5. 独立身份证号脱敏（18位身份证）
        text = ID_CARD_PATTERN.matcher(text).replaceAll("[PROTECTED_ID]");

        // 6. 独立手机号脱敏（11位中国手机号）
        text = PHONE_PATTERN.matcher(text).replaceAll("[PROTECTED_PHONE]");

        // 7. 独立电子邮箱脱敏
        text = EMAIL_PATTERN.matcher(text).replaceAll("[PROTECTED_EMAIL]");

        // 8. XSS 与 HTML 注入字符转义净化（SRS_NF004）
        text = com.airport.ai.common.XssSanitizer.sanitizeRichText(text);

        return text;
    }
}
