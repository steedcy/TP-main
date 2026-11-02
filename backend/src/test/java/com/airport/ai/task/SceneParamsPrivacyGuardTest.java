package com.airport.ai.task;

import com.airport.ai.common.BusinessException;
import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

/** DEF-S3-032：场景参数中的旅客身份类字段在提交时被拒绝。 */
class SceneParamsPrivacyGuardTest {
    @Test void rejectsIdentityFieldsCaseAndSeparatorInsensitive() {
        var ex = assertThrows(BusinessException.class, () -> SceneParamsPrivacyGuard.reject(
                Map.of("baggageLocation", "F2_GATE", "passengerName", "X", "identity_document_number", "Y")));
        assertTrue(ex.getMessage().contains("passengerName"));
    }
    @Test void allowsBusinessFieldsAndNull() {
        assertDoesNotThrow(() -> SceneParamsPrivacyGuard.reject(Map.of("baggageLocation", "A", "assistanceType", "WHEELCHAIR", "flightNo", "MU1")));
        assertDoesNotThrow(() -> SceneParamsPrivacyGuard.reject(null));
    }
}
