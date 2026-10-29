package com.airport.ai.device;

import com.airport.ai.device.dto.UpdateDeviceRequest;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.exc.UnrecognizedPropertyException;
import org.junit.jupiter.api.Test;
import org.springframework.http.converter.json.Jackson2ObjectMapperBuilder;

import static org.junit.jupiter.api.Assertions.*;

/**
 * DEF-S3-078：设备编辑表单发送的 PUT 载荷必须只含 UpdateDeviceRequest 的字段。
 * 前端 buildUpdatePayload 的字段集合在此固定为契约；含 deviceCode 等只读字段的旧载荷会被拒绝解析。
 */
class UpdateDevicePayloadContractTest {

    private final ObjectMapper mapper = Jackson2ObjectMapperBuilder.json()
            .featuresToEnable(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES).build();

    private static final String FORM_PAYLOAD = """
            {"deviceName":"n","areaCode":"F2_TEST","positionX":1,"positionY":2,
             "accessEndpoint":"http://127.0.0.1:18110","statusReportInterval":15,"remark":"r"}""";

    @Test
    void currentFormPayloadDeserializes() throws Exception {
        UpdateDeviceRequest r = mapper.readValue(FORM_PAYLOAD, UpdateDeviceRequest.class);
        assertEquals("n", r.getDeviceName());
        assertNull(r.getAccessCredentialRef(), "留空凭据不上送，保持不修改");
    }

    @Test
    void credentialIsSentOnlyWhenProvided() throws Exception {
        String withCredential = FORM_PAYLOAD.replace("\"remark\":\"r\"", "\"remark\":\"r\",\"accessCredentialRef\":\"new-ref\"");
        assertEquals("new-ref", mapper.readValue(withCredential, UpdateDeviceRequest.class).getAccessCredentialRef());
    }

    @Test
    void legacyWholeFormPayloadIsRejectedByStrictMapper() {
        String legacy = FORM_PAYLOAD.replace("{\"deviceName\"",
                "{\"deviceCode\":\"D\",\"deviceTypeCode\":\"SIMULATOR\",\"isSimulator\":true,"
                        + "\"accessCredentialRefMasked\":\"ab***\",\"deviceName\"");
        assertThrows(UnrecognizedPropertyException.class, () -> mapper.readValue(legacy, UpdateDeviceRequest.class));
    }
}
