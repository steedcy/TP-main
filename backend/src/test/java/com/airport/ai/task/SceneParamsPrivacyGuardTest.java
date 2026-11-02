package com.airport.ai.task;

import com.airport.ai.common.BusinessException;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

/** DEF-S3-032：场景参数中的旅客身份类字段在提交及补充时被严格拒绝（支持顶层与任意层级嵌套）。 */
class SceneParamsPrivacyGuardTest {

    @Test
    void rejectsIdentityFieldsCaseAndSeparatorInsensitive() {
        var ex = assertThrows(BusinessException.class, () -> SceneParamsPrivacyGuard.reject(
                Map.of("baggageLocation", "F2_GATE", "passengerName", "X", "identity_document_number", "Y")));
        assertTrue(ex.getMessage().contains("passengerName"));
    }

    @Test
    void allowsBusinessFieldsAndNull() {
        assertDoesNotThrow(() -> SceneParamsPrivacyGuard.reject(
                Map.of("baggageLocation", "A", "assistanceType", "WHEELCHAIR", "flightNo", "MU1")));
        assertDoesNotThrow(() -> SceneParamsPrivacyGuard.reject(null));
    }

    @Test
    void rejectsNestedIdentityInMap() {
        // GPT 实测中发现的 DEF-S3-032 绕过模式：嵌套在 metadata.passengerName
        var ex = assertThrows(BusinessException.class, () -> SceneParamsPrivacyGuard.reject(
                Map.of("assistanceType", "wheelchair",
                        "metadata", Map.of("passengerName", "FICTIONAL_NESTED_CANARY_135"))));
        assertTrue(ex.getMessage().contains("passengerName"));
    }

    @Test
    void rejectsNestedIdentityInList() {
        var ex = assertThrows(BusinessException.class, () -> SceneParamsPrivacyGuard.reject(
                Map.of("assistanceType", "wheelchair",
                        "passengers", List.of(Map.of("identityDocumentNumber", "CANARY_123")))));
        assertTrue(ex.getMessage().contains("identityDocumentNumber"));
    }

    @Test
    void rejectsNestedIdentityInJsonString() {
        var ex = assertThrows(BusinessException.class, () -> SceneParamsPrivacyGuard.reject(
                Map.of("assistanceType", "wheelchair",
                        "metadata", "{\"passengerName\":\"FICTIONAL_CANARY\"}")));
        assertTrue(ex.getMessage().contains("passengerName"));
    }

    @Test
    void sanitizesNestedIdentityFields() {
        Map<String, Object> input = Map.of(
                "assistanceType", "wheelchair",
                "targetLocation", "F2_GATE",
                "metadata", Map.of("passengerName", "CANARY", "note", "safe_note"));
        Map<String, Object> cleaned = SceneParamsPrivacyGuard.sanitize(input);
        assertNotNull(cleaned);
        assertEquals("wheelchair", cleaned.get("assistanceType"));
        assertEquals("F2_GATE", cleaned.get("targetLocation"));

        @SuppressWarnings("unchecked")
        Map<String, Object> cleanedMeta = (Map<String, Object>) cleaned.get("metadata");
        assertNotNull(cleanedMeta);
        assertFalse(cleanedMeta.containsKey("passengerName"));
        assertEquals("safe_note", cleanedMeta.get("note"));
    }

    @Test
    void rejectsAnswersWithIdentityKey() {
        var ex = assertThrows(BusinessException.class, () -> SceneParamsPrivacyGuard.reject(
                Map.of("passengerName", "John Doe")));
        assertTrue(ex.getMessage().contains("passengerName"));
    }

    @Test
    void sanitizesCanaryInTaskGoal() {
        // DEF-S3-088: 任务 85 自然语言目标中包含虚构身份哨兵
        String rawGoal = "Synthetic navigation to F2_TEST_GATE; passengerName=FICTIONAL_PASSENGER_NAME_CANARY_F011_137";
        String sanitized = SceneParamsPrivacyGuard.sanitizeGoal(rawGoal);

        assertNotNull(sanitized);
        assertFalse(sanitized.contains("FICTIONAL_PASSENGER_NAME_CANARY_F011_137"), "送模副本目标不得包含旅客身份哨兵");
        assertFalse(sanitized.contains("passengerName"), "送模副本目标不得包含身份字段名");
        assertTrue(sanitized.contains("Synthetic navigation to F2_TEST_GATE"), "保留业务目标主体");
        assertTrue(sanitized.contains("[PROTECTED_IDENTITY]"), "身份信息替换为脱敏标识");
    }

    @Test
    void sanitizesVariousIdentityKeyFormatsInGoal() {
        String colonGoal = "Navigate to Gate; passenger_name: Alice";
        String cleanColon = SceneParamsPrivacyGuard.sanitizeGoal(colonGoal);
        assertFalse(cleanColon.contains("Alice"));
        assertFalse(cleanColon.contains("passenger_name"));

        String chineseGoal = "协助旅客前往F2_TEST_GATE，旅客姓名=张三，身份证号=110101199003072345，联系电话: 13800138000";
        String cleanChinese = SceneParamsPrivacyGuard.sanitizeGoal(chineseGoal);
        assertFalse(cleanChinese.contains("张三"));
        assertFalse(cleanChinese.contains("110101199003072345"));
        assertFalse(cleanChinese.contains("13800138000"));
        assertTrue(cleanChinese.contains("协助旅客前往F2_TEST_GATE"));

        String standaloneId = "协助旅客前往登机口 110101199003072345";
        String cleanStandalone = SceneParamsPrivacyGuard.sanitizeGoal(standaloneId);
        assertFalse(cleanStandalone.contains("110101199003072345"));
        assertTrue(cleanStandalone.contains("[PROTECTED_ID]"));
    }

    @Test
    void preservesNonIdentityAttributesInGoal() {
        String businessGoal = "Synthetic navigation to F2_TEST_GATE; targetLocation=F2_TEST_GATE; flightNumber=CA1234";
        String sanitized = SceneParamsPrivacyGuard.sanitizeGoal(businessGoal);
        assertEquals(businessGoal, sanitized, "非身份属性原样保留");
    }
}
