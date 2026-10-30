package com.airport.ai.devicetype;

import com.airport.ai.auth.OperationLogService;
import com.airport.ai.auth.User;
import com.airport.ai.common.BusinessException;
import com.airport.ai.common.ErrorCode;
import com.airport.ai.device.DeviceMapper;
import com.airport.ai.devicetype.dto.CreateCapabilityTemplateRequest;
import com.airport.ai.devicetype.dto.ParamDefinition;
import com.airport.ai.devicetype.dto.UpdateCapabilityBoundaryRequest;
import com.airport.ai.devicetype.dto.UpdateCapabilityTemplateRequest;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.test.util.ReflectionTestUtils;

import java.io.ByteArrayInputStream;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.*;

/** SRS_F006A：边界审计内容、类型概览计数、矩阵Excel、模板必填输入契约、输出必须定义、版本快照。 */
class CapabilityBoundaryF006Test {

    private final DeviceTypeCapabilityMapper typeMapper = mock(DeviceTypeCapabilityMapper.class);
    private final CapabilityTemplateMapper templateMapper = mock(CapabilityTemplateMapper.class);
    private final DeviceMapper deviceMapper = mock(DeviceMapper.class);
    private final OperationLogService opLog = mock(OperationLogService.class);
    private final CapabilityTemplateVersionMapper versions = mock(CapabilityTemplateVersionMapper.class);
    private final DeviceTypeCapabilityService service =
            new DeviceTypeCapabilityService(typeMapper, templateMapper, deviceMapper, opLog);

    CapabilityBoundaryF006Test() {
        ReflectionTestUtils.setField(service, "versionMapper", versions);
    }

    private User operator() {
        User u = new User();
        u.setId(1L);
        u.setUsername("cfg");
        u.setRole("CONFIG_ADMIN");
        return u;
    }

    private DeviceTypeCapability type(String code, String name, String supported) {
        DeviceTypeCapability t = new DeviceTypeCapability();
        t.setDeviceTypeCode(code);
        t.setDeviceTypeName(name);
        t.setSupportedCapabilityTypes(supported);
        t.setTypeDescription("desc");
        when(typeMapper.findByDeviceTypeCode(code)).thenReturn(Optional.of(t));
        return t;
    }

    private ParamDefinition param(String name) {
        ParamDefinition p = new ParamDefinition();
        p.setName(name);
        p.setType("String");
        p.setRequired(true);
        return p;
    }

    private CreateCapabilityTemplateRequest displayTemplate(List<ParamDefinition> in, List<ParamDefinition> out) {
        CreateCapabilityTemplateRequest r = new CreateCapabilityTemplateRequest();
        r.setTemplateCode("T_DISPLAY");
        r.setTemplateName("n");
        r.setCapabilityType("CAP_INFO_DISPLAY");
        r.setInputParams(in);
        r.setOutputParams(out);
        return r;
    }

    // ---------- R09 / DEF-S3-019
    @Test
    @SuppressWarnings("unchecked")
    void boundaryUpdateAuditCarriesBeforeAndAfterSummary() {
        type("SMART_DISPLAY", "智慧航显", "[\"CAP_INFO_DISPLAY\",\"CAP_NAVIGATION\"]");
        UpdateCapabilityBoundaryRequest req = new UpdateCapabilityBoundaryRequest();
        req.setSupportedCapabilityTypes(List.of("CAP_INFO_DISPLAY"));
        req.setTypeDescription("x".repeat(200));
        service.updateBoundary("SMART_DISPLAY", req, operator());
        ArgumentCaptor<Map<String, Object>> detail = ArgumentCaptor.forClass(Map.class);
        verify(opLog).record(any(), any(), any(), eq("DEVICE_TYPE_BOUNDARY_UPDATE"), eq("SMART_DISPLAY"),
                eq("SUCCESS"), any(), detail.capture());
        Map<String, Object> before = (Map<String, Object>) detail.getValue().get("before");
        Map<String, Object> after = (Map<String, Object>) detail.getValue().get("after");
        assertEquals(List.of("CAP_INFO_DISPLAY", "CAP_NAVIGATION"), before.get("supportedCapabilityTypes"));
        assertEquals(List.of("CAP_INFO_DISPLAY"), after.get("supportedCapabilityTypes"));
        assertTrue(String.valueOf(after.get("typeDescription")).length() <= 81, "长文本只记摘要");
    }

    // ---------- DEF-S3-017
    @Test
    void overviewCarriesSupportedTemplateAndInstanceCounts() {
        DeviceTypeCapability t = type("SMART_DISPLAY", "智慧航显", "[\"CAP_INFO_DISPLAY\",\"CAP_NAVIGATION\"]");
        when(typeMapper.findAll()).thenReturn(List.of(t));
        when(templateMapper.findByDeviceTypeCode("SMART_DISPLAY")).thenReturn(List.of(new CapabilityTemplate()));
        when(deviceMapper.countByDeviceTypeCodeAndDeviceStatusNot("SMART_DISPLAY", "DELETED")).thenReturn(3L);
        var view = service.overview().get(0);
        assertEquals(2, view.getSupportedCapabilityTypes().size());
        assertEquals(1, view.getTemplateCount());
        assertEquals(3, view.getInstanceCount());
    }

    // ---------- DEF-S3-018
    @Test
    void matrixXlsxIsAValidWorkbookWithMatchingCells() throws Exception {
        DeviceTypeCapability t = type("SMART_DISPLAY", "智慧航显", "[\"CAP_INFO_DISPLAY\"]");
        when(typeMapper.findAll()).thenReturn(List.of(t));
        byte[] xlsx = service.exportMatrixXlsx();
        String sheet = null;
        boolean hasWorkbook = false;
        try (ZipInputStream zip = new ZipInputStream(new ByteArrayInputStream(xlsx), StandardCharsets.UTF_8)) {
            for (ZipEntry e = zip.getNextEntry(); e != null; e = zip.getNextEntry()) {
                if (e.getName().equals("xl/workbook.xml")) hasWorkbook = true;
                if (e.getName().equals("xl/worksheets/sheet1.xml")) sheet = new String(zip.readAllBytes(), StandardCharsets.UTF_8);
            }
        }
        assertTrue(hasWorkbook);
        assertNotNull(sheet);
        assertTrue(sheet.contains("智慧航显"));
        assertEquals(1, count(sheet, "<t>支持</t>"), "仅综合信息展示被支持");
        assertEquals(7, count(sheet, "<t>不支持</t>"), "其余七类不支持");
        for (String cap : CapabilityCatalog.ALL_CODES) assertTrue(sheet.contains(cap));
    }

    private static int count(String text, String needle) {
        int n = 0;
        for (int i = text.indexOf(needle); i >= 0; i = text.indexOf(needle, i + 1)) n++;
        return n;
    }

    // ---------- R10 / R11 / DEF-S3-022
    @Test
    void templateMissingRequiredInputsIsRejectedNamingTheMissingOnes() {
        type("SMART_DISPLAY", "智慧航显", "[\"CAP_INFO_DISPLAY\"]");
        var req = displayTemplate(List.of(param("anything")), List.of(param("displayStatus")));
        BusinessException ex = assertThrows(BusinessException.class, () -> service.createTemplate("SMART_DISPLAY", req, operator()));
        assertEquals(ErrorCode.PARAM_MISSING, ex.getErrorCode());
        assertTrue(ex.getMessage().contains("contentType") && ex.getMessage().contains("contentData")
                && ex.getMessage().contains("displayDuration"));
        verify(templateMapper, never()).insert(any());
    }

    @Test
    void templateWithoutOutputsIsRejected() {
        type("SMART_DISPLAY", "智慧航显", "[\"CAP_INFO_DISPLAY\"]");
        var req = displayTemplate(List.of(param("contentType"), param("contentData"), param("displayDuration")), List.of());
        BusinessException ex = assertThrows(BusinessException.class, () -> service.createTemplate("SMART_DISPLAY", req, operator()));
        assertTrue(ex.getMessage().contains("输出"));
    }

    @Test
    void completeTemplateIsSavedAndSnapshotAsV10() {
        type("SMART_DISPLAY", "智慧航显", "[\"CAP_INFO_DISPLAY\"]");
        var req = displayTemplate(List.of(param("contentType"), param("contentData"), param("displayDuration")),
                List.of(param("displayStatus")));
        service.createTemplate("SMART_DISPLAY", req, operator());
        verify(templateMapper).insert(any());
        verify(versions).insert(any(), eq("V1.0"), anyString(), anyString(), anyString(), any(), eq("cfg"));
    }

    @Test
    void simStatusNeedsNoInputsButStillNeedsOutputs() {
        assertTrue(CapabilityContract.requiredInputs("CAP_SIM_STATUS").isEmpty());
        assertEquals(List.of("flightNumber", "updateType", "updateContent", "displayDuration"),
                CapabilityContract.requiredInputs("CAP_FLIGHT_UPDATE"));
        assertEquals(CapabilityCatalog.ALL_CODES.size(),
                CapabilityCatalog.ALL_CODES.stream().filter(c -> CapabilityContract.requiredInputs(c) != null).count());
    }

    // ---------- R12 / DEF-S3-023
    @Test
    void editingATemplateAppendsANewVersionSnapshotAndKeepsOldOnes() {
        type("SMART_DISPLAY", "智慧航显", "[\"CAP_INFO_DISPLAY\"]");
        CapabilityTemplate existing = new CapabilityTemplate();
        existing.setId(5L);
        existing.setDeviceTypeCode("SMART_DISPLAY");
        existing.setTemplateCode("T_DISPLAY");
        existing.setCapabilityType("CAP_INFO_DISPLAY");
        existing.setTemplateVersion("V1.0");
        when(templateMapper.findByDeviceTypeCodeAndTemplateCode("SMART_DISPLAY", "T_DISPLAY")).thenReturn(Optional.of(existing));
        UpdateCapabilityTemplateRequest req = new UpdateCapabilityTemplateRequest();
        req.setTemplateName("new");
        req.setInputParams(List.of(param("contentType"), param("contentData"), param("displayDuration")));
        req.setOutputParams(List.of(param("displayStatus")));
        service.updateTemplate("SMART_DISPLAY", "T_DISPLAY", req, operator());
        assertEquals("V1.1", existing.getTemplateVersion());
        verify(versions).insert(eq(5L), eq("V1.1"), eq("new"), anyString(), anyString(), any(), eq("cfg"));
        verify(versions, never()).insert(any(), eq("V1.0"), any(), any(), any(), any(), any());
    }

    @Test
    void editRejectsTemplateThatDropsRequiredInputs() {
        type("SMART_DISPLAY", "智慧航显", "[\"CAP_INFO_DISPLAY\"]");
        CapabilityTemplate existing = new CapabilityTemplate();
        existing.setId(5L);
        existing.setCapabilityType("CAP_INFO_DISPLAY");
        existing.setTemplateVersion("V1.0");
        when(templateMapper.findByDeviceTypeCodeAndTemplateCode("SMART_DISPLAY", "T_DISPLAY")).thenReturn(Optional.of(existing));
        UpdateCapabilityTemplateRequest req = new UpdateCapabilityTemplateRequest();
        req.setTemplateName("n");
        req.setInputParams(List.of(param("contentType")));
        req.setOutputParams(List.of(param("displayStatus")));
        assertThrows(BusinessException.class, () -> service.updateTemplate("SMART_DISPLAY", "T_DISPLAY", req, operator()));
        assertEquals("V1.0", existing.getTemplateVersion(), "被拒绝的编辑不改变版本");
    }

    @Test
    void versionHistoryIsListedFromTheVersionMapper() {
        type("SMART_DISPLAY", "智慧航显", "[\"CAP_INFO_DISPLAY\"]");
        CapabilityTemplate existing = new CapabilityTemplate();
        existing.setId(5L);
        when(templateMapper.findByDeviceTypeCodeAndTemplateCode("SMART_DISPLAY", "T_DISPLAY")).thenReturn(Optional.of(existing));
        when(versions.findByTemplateId(5L)).thenReturn(List.of(Map.of("templateVersion", "V1.1"), Map.of("templateVersion", "V1.0")));
        assertEquals(2, service.listTemplateVersions("SMART_DISPLAY", "T_DISPLAY").size());
    }
}
