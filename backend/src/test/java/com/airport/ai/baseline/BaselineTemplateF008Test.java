package com.airport.ai.baseline;

import com.airport.ai.auth.OperationLogService;
import com.airport.ai.auth.User;
import com.airport.ai.baseline.dto.CreateBaselineTemplateRequest;
import com.airport.ai.baseline.dto.ParamMapping;
import com.airport.ai.baseline.dto.TemplateStep;
import com.airport.ai.common.BusinessException;
import com.airport.ai.common.ErrorCode;
import com.airport.ai.device.DeviceCapability;
import com.airport.ai.device.DeviceCapabilityMapper;
import com.airport.ai.devicetype.dto.ParamDefinition;
import com.airport.ai.taskdef.TaskDefinition;
import com.airport.ai.taskdef.TaskDefinitionService;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/** SRS_F008：前序步骤输出引用核对（R03/R05）与运动安全字段矩阵（R06）。 */
class BaselineTemplateF008Test {
    private final BaselineTemplateMapper templates = mock(BaselineTemplateMapper.class);
    private final DeviceCapabilityMapper capabilities = mock(DeviceCapabilityMapper.class);
    private final TaskDefinitionService definitions = mock(TaskDefinitionService.class);
    private final BaselineTemplateService service = new BaselineTemplateService(templates, capabilities,
            mock(OperationLogService.class), definitions);

    BaselineTemplateF008Test() {
        when(definitions.findByCode("GENERAL_GUIDANCE")).thenReturn(Optional.of(new TaskDefinition()));
        when(capabilities.existsByCapabilityTypeAndCapabilityStatus(anyString(), eq("ENABLED"))).thenReturn(true);
        when(capabilities.findEnabledByCapabilityType("CAP_NAVIGATION")).thenReturn(List.of(
                capability("CAP_NAVIGATION", "[{\"name\":\"targetLocation\",\"type\":\"String\",\"required\":true}]",
                        "[{\"name\":\"routeGenerated\",\"type\":\"Boolean\"},{\"name\":\"estimatedDistance\",\"type\":\"Double\"},"
                                + "{\"name\":\"waypointCount\",\"type\":\"Integer\"}]")));
        when(capabilities.findEnabledByCapabilityType("CAP_INFO_DISPLAY")).thenReturn(List.of(
                capability("CAP_INFO_DISPLAY", "[{\"name\":\"contentType\",\"type\":\"String\",\"required\":true},"
                        + "{\"name\":\"contentData\",\"type\":\"String\",\"required\":true},"
                        + "{\"name\":\"displayDuration\",\"type\":\"Double\",\"required\":true}]", "[{\"name\":\"displayStatus\",\"type\":\"String\"}]")));
    }

    private DeviceCapability capability(String type, String in, String out) {
        DeviceCapability c = new DeviceCapability();
        c.setCapabilityType(type);
        c.setInputParams(in);
        c.setOutputParams(out);
        return c;
    }

    private ParamMapping map(String target, String source) {
        ParamMapping m = new ParamMapping();
        m.setTarget(target);
        m.setSource(source);
        return m;
    }

    private TemplateStep step(String type, String completion, ParamMapping... mappings) {
        TemplateStep s = new TemplateStep();
        s.setCapabilityType(type);
        s.setCompletionCondition(completion);
        s.setParamMapping(List.of(mappings));
        return s;
    }

    private CreateBaselineTemplateRequest request(TemplateStep... steps) {
        ParamDefinition input = new ParamDefinition();
        input.setName("targetLocation");
        input.setType("String");
        input.setRequired(true);
        CreateBaselineTemplateRequest r = new CreateBaselineTemplateRequest();
        r.setTemplateName("t-" + System.nanoTime());
        r.setTemplateIntent("GENERAL_GUIDANCE");
        r.setInputParams(List.of(input));
        r.setSteps(List.of(steps));
        return r;
    }

    private String rejection(CreateBaselineTemplateRequest r) {
        BusinessException ex = assertThrows(BusinessException.class, () -> service.create(r, new User()));
        assertEquals(ErrorCode.TEMPLATE_PARAM_MAPPING_INVALID, ex.getErrorCode());
        return ex.getMessage();
    }

    private TemplateStep navigationStep() {
        return step("CAP_NAVIGATION", "routeGenerated=true", map("targetLocation", "TEMPLATE_INPUT.targetLocation"));
    }

    // ---------- DEF-S3-025
    @Test
    void referenceToAnOutputThePreviousStepDoesNotHaveIsRejected() {
        String msg = rejection(request(navigationStep(),
                step("CAP_INFO_DISPLAY", "displayStatus=SHOWN", map("contentData", "STEP1_OUTPUT.noSuchOutput"))));
        assertTrue(msg.contains("noSuchOutput") && msg.contains("没有输出参数"), msg);
    }

    @Test
    void outputTypeThatCannotFeedTheTargetInputIsRejected() {
        // Double 距离 → String contentData 类型不兼容
        String msg = rejection(request(navigationStep(),
                step("CAP_INFO_DISPLAY", "displayStatus=SHOWN", map("contentData", "STEP1_OUTPUT.estimatedDistance"))));
        assertTrue(msg.contains("类型不匹配") && msg.contains("Double") && msg.contains("String"), msg);
    }

    @Test
    void existingOutputWithCompatibleTypeIsAccepted() {
        // Integer 可赋给 Double；Double→Double 一致
        service.create(request(navigationStep(),
                step("CAP_INFO_DISPLAY", "displayStatus=SHOWN",
                        map("contentType", "TEMPLATE_INPUT.targetLocation"),
                        map("displayDuration", "STEP1_OUTPUT.estimatedDistance"))), new User());
        service.create(request(navigationStep(),
                step("CAP_INFO_DISPLAY", "displayStatus=SHOWN",
                        map("contentType", "TEMPLATE_INPUT.targetLocation"),
                        map("displayDuration", "STEP1_OUTPUT.waypointCount"))), new User());
        verify(templates, times(2)).insert(any());
    }

    @Test
    void forwardOrSelfReferencesAndMalformedSourcesAreStillRejected() {
        assertTrue(rejection(request(navigationStep(),
                step("CAP_INFO_DISPLAY", "x=1", map("contentData", "STEP2_OUTPUT.displayStatus")))).contains("非前序"));
        assertTrue(rejection(request(navigationStep(),
                step("CAP_INFO_DISPLAY", "x=1", map("contentData", "STEP0_OUTPUT.displayStatus")))).contains("非前序"));
        assertTrue(rejection(request(navigationStep(),
                step("CAP_INFO_DISPLAY", "x=1", map("contentData", "OTHER.x")))).contains("来源格式非法"));
    }

    @Test
    void referencesAreNotJudgedWhenTheSourceCapabilityHasNoEnabledInstanceYet() {
        when(capabilities.findEnabledByCapabilityType("CAP_NAVIGATION")).thenReturn(List.of());
        service.create(request(navigationStep(),
                step("CAP_INFO_DISPLAY", "displayStatus=SHOWN", map("contentData", "STEP1_OUTPUT.anything"))), new User());
        verify(templates).insert(any());
    }

    // ---------- DEF-S3-026
    @Test
    void everySafetyFieldInEveryCommonSpellingIsRejectedAsAMappingTarget() {
        for (String field : List.of("speed", "velocity", "acceleration", "attitude", "orientation", "pathPoints", "path_points",
                "waypoints", "obstacleAvoidance", "emergencyStop", "emergency-stop", "speedLimit", "speed_limit",
                "lostConnectionParking", "lost_connection_parking", "safeStopOnDisconnect", "速度", "急停", "限速", "路径点", "避障")) {
            String msg = rejection(request(step("CAP_NAVIGATION", "routeGenerated=true",
                    map(field, "TEMPLATE_INPUT.targetLocation"))));
            assertTrue(msg.contains("运动安全"), field + " 应被拒绝: " + msg);
        }
        verify(templates, never()).insert(any());
    }

    @Test
    void safetyControlsInACompletionConditionAreRejected() {
        for (String condition : List.of("emergencyStop=true", "emergency stop triggered", "speedLimit<=1", "pathPoints reached",
                "lostConnectionParking=true", "急停完成", "attitude=0")) {
            String msg = rejection(request(step("CAP_NAVIGATION", condition,
                    map("targetLocation", "TEMPLATE_INPUT.targetLocation"))));
            assertTrue(msg.contains("运动安全"), condition + " 应被拒绝: " + msg);
        }
    }

    @Test
    void ordinaryBusinessCompletionConditionsAndMappingsStillPass() {
        service.create(request(
                step("CAP_NAVIGATION", "routeGenerated=true and waypointCount reported",
                        map("targetLocation", "TEMPLATE_INPUT.targetLocation")),
                step("CAP_INFO_DISPLAY", "displayStatus=SHOWN",
                        map("contentType", "TEMPLATE_INPUT.targetLocation"))), new User());
        verify(templates).insert(any());
    }
}
