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

/** SRS_F012.R01~R04（DEF-S3-034、DEF-S3-071）：步骤六项完整性、五步上限、条件节点计数与循环/动态代码文字的结构硬校验。 */
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

    private Map<String, Object> conditionNode(int seq, String condition) {
        Map<String, Object> s = new LinkedHashMap<>();
        s.put("stepSeq", seq);
        s.put("conditionNode", true);
        s.put("nodeType", "CONDITION");
        s.put("condition", condition);
        s.put("stepGoal", "判断条件: " + condition);
        return s;
    }

    private List<Map<String, Object>> agents() {
        return List.of(Map.of("agentId", "A1", "capabilities", List.of("CAP_INFO_DISPLAY", "CAP_FLIGHT_UPDATE", "CAP_NOTIFICATION"), "onlineStatus", "ONLINE",
                "workload", "IDLE", "location", Map.of(), "deviceTypeCode", "SIMULATOR", "simulatedDeviceType", "SMART_DISPLAY"));
    }

    private PlanValidationResult validate(Map<String, Object> step) {
        return service.validate(new ArrayList<>(List.of(step)), agents());
    }

    private PlanValidationResult validateSteps(List<Map<String, Object>> steps) {
        return service.validate(new ArrayList<>(steps), agents());
    }

    private void assertStructureFails(Map<String, Object> step, String reasonCode, String mention) {
        PlanValidationResult r = validate(step);
        assertFalse(r.isAllPassed());
        assertEquals("FAIL", r.getStructureCheckResult());
        assertTrue(r.getErrors().stream().anyMatch(e -> reasonCode.equals(e.getReasonCode())),
                "应有 " + reasonCode + ": " + r.getErrors());
        if (mention != null) {
            assertTrue(r.getErrors().stream().anyMatch(e -> e.getDescription().contains(mention)),
                    mention + " 应出现在错误清单: " + r.getErrors());
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
    void nonStringValuesInSixFieldsAreRejected() {
        for (String field : List.of("stepGoal", "precondition", "completionCondition", "failureHandling")) {
            Map<String, Object> s = step(1);
            s.put(field, 12345);
            assertStructureFails(s, "ERR_STEP_FIELD_MISSING", field);
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
                "生成并执行代码", "死循环", "无限期重试", "回到步骤 1", "反复重试");
        for (String field : List.of("stepGoal", "precondition", "completionCondition", "failureHandling")) {
            for (String text : bad) {
                Map<String, Object> s = step(1);
                s.put(field, text);
                assertStructureFails(s, "ERR_STEP_LOOP_DETECTED", null);
            }
        }
    }

    @Test
    void loopsAndDynamicCodeInInputParamsAreRejected() {
        // key containing loop/dynamic code
        Map<String, Object> s1 = step(1);
        s1.put("inputParams", Map.of("eval(code)", "val"));
        assertStructureFails(s1, "ERR_STEP_LOOP_DETECTED", null);

        // value containing while(true)
        Map<String, Object> s2 = step(1);
        s2.put("inputParams", Map.of("script", "while(true) { run(); }"));
        assertStructureFails(s2, "ERR_STEP_LOOP_DETECTED", null);

        // nested value containing loop text
        Map<String, Object> s3 = step(1);
        s3.put("inputParams", Map.of("nested", Map.of("code", "repeat forever")));
        assertStructureFails(s3, "ERR_STEP_LOOP_DETECTED", null);
    }

    @Test
    void explicitLoopMarkerIsStillRejected() {
        Map<String, Object> s = step(1);
        s.put("inputParams", new LinkedHashMap<>(Map.of("__loop__", true)));
        assertStructureFails(s, "ERR_STEP_LOOP_DETECTED", null);

        // nested loop marker
        Map<String, Object> s2 = step(1);
        s2.put("inputParams", Map.of("meta", Map.of("__loop__", "true")));
        assertStructureFails(s2, "ERR_STEP_LOOP_DETECTED", null);
    }

    @Test
    void ordinaryBusinessWordingIsNotMistakenForALoop() {
        for (String text : List.of("重试一次或转人工处理", "最多重试2次", "重试2次", "等待设备就绪后展示", "展示直到完成条件满足",
                "候选设备在线且空闲", "displayStatus=SHOWN", "Retry once then escalate to a human operator", "步骤1完成后执行",
                "展示航班延误信息并确认", "after step 1", "the display shows the notice for 30 seconds", "wait for (30 seconds)")) {
            Map<String, Object> s = step(1);
            s.put("failureHandling", text);
            s.put("completionCondition", text.contains("=") ? text : "displayStatus=SHOWN");
            assertTrue(validate(s).isAllPassed(), text + " -> " + validate(s).getErrors());
        }
    }

    @Test
    void fiveExecutableStepsPass() {
        List<Map<String, Object>> steps = new ArrayList<>();
        for (int i = 1; i <= 5; i++) {
            steps.add(step(i));
        }
        PlanValidationResult r = validateSteps(steps);
        assertTrue(r.isAllPassed(), String.valueOf(r.getErrors()));
    }

    @Test
    void sixExecutableStepsFailWithoutTruncation() {
        List<Map<String, Object>> steps = new ArrayList<>();
        for (int i = 1; i <= 6; i++) {
            steps.add(step(i));
        }
        PlanValidationResult r = validateSteps(steps);
        assertFalse(r.isAllPassed());
        assertEquals("FAIL", r.getStructureCheckResult());
        assertTrue(r.getErrors().stream().anyMatch(e -> "ERR_STEP_LIMIT_EXCEEDED".equals(e.getReasonCode())));
    }

    @Test
    void conditionNodesDoNotCountTowardFiveStepLimit() {
        // 5 executable steps + 2 condition nodes = 7 total nodes, but executableCount = 5 -> PASS
        List<Map<String, Object>> steps = new ArrayList<>();
        steps.add(step(1));
        steps.add(conditionNode(2, "旅客是否有超规行李"));
        Map<String, Object> branch1 = step(3);
        branch1.put("branchOf", 2);
        steps.add(branch1);
        steps.add(conditionNode(4, "是否有值机柜台可用"));
        Map<String, Object> branch2 = step(5);
        branch2.put("branchOf", 4);
        steps.add(branch2);
        steps.add(step(6));
        steps.add(step(7));

        assertEquals(5, PlanStepRules.executableCount(steps));
        PlanValidationResult r = validateSteps(steps);
        assertTrue(r.isAllPassed(), String.valueOf(r.getErrors()));

        // Fold condition nodes -> exactly 5 actions, branch actions carry branchCondition
        List<Map<String, Object>> folded = PlanStepRules.foldConditionNodes(steps);
        assertEquals(5, folded.size());
        assertEquals("旅客是否有超规行李", folded.get(1).get("branchCondition"));
        assertEquals("是否有值机柜台可用", folded.get(2).get("branchCondition"));
    }

    @Test
    void sixExecutableStepsWithConditionNodeFails() {
        // 6 executable steps + 1 condition node = 7 nodes, executableCount = 6 -> FAIL
        List<Map<String, Object>> steps = new ArrayList<>();
        steps.add(step(1));
        steps.add(conditionNode(2, "是否下雨"));
        for (int i = 3; i <= 7; i++) {
            steps.add(step(i));
        }
        assertEquals(6, PlanStepRules.executableCount(steps));
        PlanValidationResult r = validateSteps(steps);
        assertFalse(r.isAllPassed());
        assertTrue(r.getErrors().stream().anyMatch(e -> "ERR_STEP_LIMIT_EXCEEDED".equals(e.getReasonCode())));
    }

    @Test
    void conditionNodeMissingConditionFails() {
        Map<String, Object> badCond = new LinkedHashMap<>();
        badCond.put("stepSeq", 1);
        badCond.put("conditionNode", true);
        badCond.put("condition", "");
        badCond.put("stepGoal", "   ");

        List<Map<String, Object>> steps = List.of(badCond, step(2));
        PlanValidationResult r = validateSteps(steps);
        assertFalse(r.isAllPassed());
        assertTrue(r.getErrors().stream().anyMatch(e -> "ERR_STEP_FIELD_MISSING".equals(e.getReasonCode())
                && e.getDescription().contains("condition")));
    }

    @Test
    void conditionNodeWithLoopTextFails() {
        Map<String, Object> loopCond = conditionNode(1, "while(true) 判断航班状态");
        List<Map<String, Object>> steps = List.of(loopCond, step(2));
        PlanValidationResult r = validateSteps(steps);
        assertFalse(r.isAllPassed());
        assertTrue(r.getErrors().stream().anyMatch(e -> "ERR_STEP_LOOP_DETECTED".equals(e.getReasonCode())));
    }

    @Test
    void branchActionReferencingFutureConditionNodeFails() {
        Map<String, Object> branch = step(1);
        branch.put("branchOf", 2); // references step 2 which hasn't appeared yet
        Map<String, Object> cond = conditionNode(2, "是否可用");
        List<Map<String, Object>> steps = List.of(branch, cond);
        PlanValidationResult r = validateSteps(steps);
        assertFalse(r.isAllPassed());
        assertTrue(r.getErrors().stream().anyMatch(e -> "ERR_STEP_DEPENDENCY_ORDER".equals(e.getReasonCode())));
    }
}
