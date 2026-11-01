package com.airport.ai.task;

import com.airport.ai.device.DeviceCapabilityMapper;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.*;

/** SRS_F012.R03/R04（DEF-S3-034、DEF-S3-071）：步骤六项完整性与循环/动态代码文字的结构硬校验。 */
class PlanStepFieldsF012Test {
    private final DeviceCapabilityMapper capabilities = mock(DeviceCapabilityMapper.class);
    private final PlanValidationService service = new PlanValidationService(capabilities);

    PlanStepFieldsF012Test() {
        when(capabilities.existsByCapabilityTypeAndCapabilityStatus(anyString(), anyString())).thenReturn(true);
    }

    private Map<String, Object> step(int seq) {
        Map<String, Object> s = new LinkedHashMap<>();
        s.put("stepSeq", seq);
        s.put("stepGoal", "展示航班信息");
        s.put("capabilityType", "CAP_INFO_DISPLAY");
        s.put("inputParams", new LinkedHashMap<>(Map.of("contentType", "TEXT")));
        s.put("precondition", "候选设备在线且空闲");
        s.put("completionCondition", "displayStatus=SHOWN");
        s.put("failureHandling", "重试一次或转人工处理");
        return s;
    }

    private List<Map<String, Object>> agents() {
        return List.of(Map.of("agentId", "A1", "capabilities", List.of("CAP_INFO_DISPLAY"), "onlineStatus", "ONLINE",
                "workload", "IDLE", "location", Map.of(), "deviceTypeCode", "SIMULATOR", "simulatedDeviceType", "SMART_DISPLAY"));
    }

    private PlanValidationResult validate(Map<String, Object> step) {
        return service.validate(new ArrayList<>(List.of(step)), agents());
    }

    private void assertStructureFails(Map<String, Object> step, String reasonCode, String mention) {
        PlanValidationResult r = validate(step);
        assertFalse(r.isAllPassed());
        assertEquals("FAIL", r.getStructureCheckResult());
        assertTrue(r.getErrors().stream().anyMatch(e -> reasonCode.equals(e.getReasonCode())),
                "应有 " + reasonCode + ": " + r.getErrors());
        if (mention != null) {
            assertTrue(r.getErrors().stream().anyMatch(e -> String.valueOf(e).contains(mention)
                    || (e.getReasonCode() != null && e.toString().contains(mention))
                    || descriptionOf(e).contains(mention)), mention + " 应出现在错误清单: " + r.getErrors());
        }
    }

    private String descriptionOf(PlanValidationResult.ValidationError e) {
        try {
            return String.valueOf(e.getClass().getMethod("getDescription").invoke(e));
        } catch (Exception ex) {
            return e.toString();
        }
    }

    @Test
    void aCompleteSixFieldStepPasses() {
        assertTrue(validate(step(1)).isAllPassed(), String.valueOf(validate(step(1)).getErrors()));
    }

    @Test
    void everyMissingBlankOrNullFieldIsRejectedAndNamed() {
        for (String field : List.of("stepGoal", "capabilityType", "precondition", "completionCondition", "failureHandling")) {
            for (Object bad : new Object[]{null, "", "   "}) {
                Map<String, Object> s = step(1);
                if (bad == null) s.remove(field); else s.put(field, bad);
                if ("capabilityType".equals(field)) {
                    PlanValidationResult r = validate(s);
                    assertFalse(r.isAllPassed(), field);
                } else {
                    assertStructureFails(s, "ERR_STEP_FIELD_MISSING", field);
                }
            }
        }
    }

    @Test
    void inputParamsMustBePresentAsAnObjectButMayBeEmpty() {
        Map<String, Object> missing = step(1);
        missing.remove("inputParams");
        assertStructureFails(missing, "ERR_STEP_FIELD_MISSING", "inputParams");
        Map<String, Object> wrongType = step(1);
        wrongType.put("inputParams", "contentType=TEXT");
        assertStructureFails(wrongType, "ERR_STEP_FIELD_MISSING", "inputParams");
        Map<String, Object> empty = step(1);
        empty.put("inputParams", new LinkedHashMap<>());
        assertTrue(validate(empty).isAllPassed());
    }

    @Test
    void loopsDynamicCodeAndEndlessNegotiationTextAreRejectedInEveryTextField() {
        List<String> bad = List.of("while(true) { repeat this display step forever; }", "for (int i=0;;i++) show()",
                "do { show } while (1)", "eval(userInput)", "exec('rm')", "repeat forever until the operator stops it",
                "loop until success", "retry indefinitely", "unlimited retries", "无限循环展示", "一直重复询问旅客", "循环执行该步骤",
                "生成并执行代码", "死循环");
        for (String field : List.of("stepGoal", "precondition", "completionCondition", "failureHandling")) {
            for (String text : bad) {
                Map<String, Object> s = step(1);
                s.put(field, text);
                assertStructureFails(s, "ERR_STEP_LOOP_DETECTED", null);
            }
        }
    }

    @Test
    void explicitLoopMarkerIsStillRejected() {
        Map<String, Object> s = step(1);
        s.put("inputParams", new LinkedHashMap<>(Map.of("__loop__", true)));
        assertStructureFails(s, "ERR_STEP_LOOP_DETECTED", null);
    }

    @Test
    void ordinaryBusinessWordingIsNotMistakenForALoop() {
        for (String text : List.of("重试一次或转人工处理", "等待设备就绪后展示", "展示直到完成条件满足", "候选设备在线且空闲",
                "displayStatus=SHOWN", "Retry once then escalate to a human operator", "步骤1完成后执行", "展示航班延误信息并确认",
                "after step 1", "the display shows the notice for 30 seconds")) {
            Map<String, Object> s = step(1);
            s.put("failureHandling", text);
            s.put("completionCondition", text.contains("=") ? text : "displayStatus=SHOWN");
            assertTrue(validate(s).isAllPassed(), text + " -> " + validate(s).getErrors());
        }
    }
}
