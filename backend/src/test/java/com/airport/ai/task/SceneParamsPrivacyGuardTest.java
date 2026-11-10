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
        String businessGoal = "Synthetic navigation to F2_TEST_GATE; targetLocation=F2_TEST_GATE; flightNumber=CA1234; baggageId=BAG-123456; tempPassenger=P-R08-OVERSIZE";
        String sanitized = SceneParamsPrivacyGuard.sanitizeGoal(businessGoal);
        assertEquals(businessGoal, sanitized, "非身份属性与临时编号原样保留");
    }

    @Test
    void sanitizesPassportAndPhoneVariants() {
        String passportGoal = "协助旅客登机，护照号: EA1234567，手机号: 13912345678，电子邮箱: passenger@example.com";
        String cleanPassport = SceneParamsPrivacyGuard.sanitizeGoal(passportGoal);
        assertFalse(cleanPassport.contains("EA1234567"));
        assertFalse(cleanPassport.contains("13912345678"));
        assertFalse(cleanPassport.contains("passenger@example.com"));
        assertTrue(cleanPassport.contains("[PROTECTED_IDENTITY]"));

        String standaloneContacts = "协助旅客登机 13912345678 passenger@example.com";
        String cleanStandalone = SceneParamsPrivacyGuard.sanitizeGoal(standaloneContacts);
        assertFalse(cleanStandalone.contains("13912345678"));
        assertFalse(cleanStandalone.contains("passenger@example.com"));
        assertTrue(cleanStandalone.contains("[PROTECTED_PHONE]"));
        assertTrue(cleanStandalone.contains("[PROTECTED_EMAIL]"));

        String spacePassport = "核验旅客 护照 G87654321 并在登机口 F2_TEST_GATE 会合";
        String cleanSpace = SceneParamsPrivacyGuard.sanitizeGoal(spacePassport);
        assertFalse(cleanSpace.contains("G87654321"));
        assertTrue(cleanSpace.contains("F2_TEST_GATE"));

        String telGoal = "紧急联络电话: 010-88889999 或手机 13800000000";
        String cleanTel = SceneParamsPrivacyGuard.sanitizeGoal(telGoal);
        assertFalse(cleanTel.contains("010-88889999"));
        assertFalse(cleanTel.contains("13800000000"));
    }

    @Test
    void rejectsChineseIdentityKeysAndPhoneVariants() {
        assertThrows(BusinessException.class, () -> SceneParamsPrivacyGuard.reject(Map.of("手机", "13800138000")));
        assertThrows(BusinessException.class, () -> SceneParamsPrivacyGuard.reject(Map.of("护照", "E12345678")));
        assertThrows(BusinessException.class, () -> SceneParamsPrivacyGuard.reject(Map.of("证件", "110101199003072345")));
        assertThrows(BusinessException.class, () -> SceneParamsPrivacyGuard.reject(Map.of("passengerPhone", "13800138000")));
        assertThrows(BusinessException.class, () -> SceneParamsPrivacyGuard.reject(Map.of("passenger_passport", "EA1234567")));
    }

    @Test
    void sanitizeTextCleansJsonAndPlainText() {
        String jsonWithIdentity = "{\"location\":\"F2_GATE\",\"passengerName\":\"Canary\",\"phone\":\"13800138000\",\"note\":\"safe\"}";
        String cleanJson = SceneParamsPrivacyGuard.sanitizeText(jsonWithIdentity);
        assertFalse(cleanJson.contains("Canary"));
        assertFalse(cleanJson.contains("13800138000"));
        assertTrue(cleanJson.contains("F2_GATE"));
        assertTrue(cleanJson.contains("safe"));

        String plainText = "操作员处理目标: 旅客姓名=张三，电话: 13912345678";
        String cleanText = SceneParamsPrivacyGuard.sanitizeText(plainText);
        assertFalse(cleanText.contains("张三"));
        assertFalse(cleanText.contains("13912345678"));
        assertTrue(cleanText.contains("[PROTECTED_IDENTITY]"));
    }
}
