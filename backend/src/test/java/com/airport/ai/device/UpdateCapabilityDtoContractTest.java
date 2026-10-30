package com.airport.ai.device;

import com.airport.ai.device.dto.UpdateDeviceCapabilityRequest;
import com.airport.ai.devicetype.dto.UpdateCapabilityTemplateRequest;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.exc.UnrecognizedPropertyException;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/**
 * DEF-S3-081：后端 Update DTO 必须拒绝未知字段，确保前端只能按白名单提交。
 * 对应 GlobalExceptionHandler 将 UnrecognizedPropertyException 映射为 400。
 */
class UpdateCapabilityDtoContractTest {

    private final ObjectMapper mapper = new ObjectMapper();

    @Test
    void deviceCapabilityDtoRejectsUnknownCapabilityCode() {
        String body = """
                {
                  "capabilityCode": "G119_LIVE",
                  "capabilityName": "GPT V120 UI edit",
                  "capabilityType": "CAP_INFO_DISPLAY",
                  "inputParams": [{"name":"contentType","type":"String","required":true}],
                  "outputParams": [{"name":"displayStatus","type":"String","required":true}],
                  "applicableCondition": "x",
                  "capabilityDescription": "y"
                }
                """;
        assertThrows(UnrecognizedPropertyException.class,
                () -> mapper.readValue(body, UpdateDeviceCapabilityRequest.class));
    }

    @Test
    void deviceCapabilityDtoAcceptsWhitelistFields() throws Exception {
        String body = """
                {
                  "capabilityName": "GPT V120 UI edit",
                  "inputParams": [{"name":"contentType","type":"String","required":true}],
                  "outputParams": [{"name":"displayStatus","type":"String","required":true}],
                  "applicableCondition": "x",
                  "capabilityDescription": "y"
                }
                """;
        UpdateDeviceCapabilityRequest req = mapper.readValue(body, UpdateDeviceCapabilityRequest.class);
        assertEquals("GPT V120 UI edit", req.getCapabilityName());
        assertEquals(1, req.getInputParams().size());
        assertEquals(1, req.getOutputParams().size());
    }

    @Test
    void capabilityTemplateDtoRejectsUnknownTemplateCode() {
        String body = """
                {
                  "templateCode": "TMPL-01",
                  "templateName": "edited",
                  "capabilityType": "CAP_INFO_DISPLAY",
                  "inputParams": [{"name":"contentType","type":"String","required":true}],
                  "outputParams": [{"name":"displayStatus","type":"String","required":true}],
                  "templateDescription": "z"
                }
                """;
        assertThrows(UnrecognizedPropertyException.class,
                () -> mapper.readValue(body, UpdateCapabilityTemplateRequest.class));
    }

    @Test
    void capabilityTemplateDtoAcceptsWhitelistFields() throws Exception {
        String body = """
                {
                  "templateName": "edited",
                  "inputParams": [{"name":"contentType","type":"String","required":true}],
                  "outputParams": [{"name":"displayStatus","type":"String","required":true}],
                  "templateDescription": "z"
                }
                """;
        UpdateCapabilityTemplateRequest req = mapper.readValue(body, UpdateCapabilityTemplateRequest.class);
        assertEquals("edited", req.getTemplateName());
    }
}
