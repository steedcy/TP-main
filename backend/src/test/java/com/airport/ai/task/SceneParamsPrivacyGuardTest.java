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
}
