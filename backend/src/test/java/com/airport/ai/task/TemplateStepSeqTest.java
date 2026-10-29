package com.airport.ai.task;

import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;

import java.lang.reflect.Method;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.mock;

/** DEF-S3-075：预置F2模板步骤无stepSeq时按顺序补序号，已有序号保持不变，避免分配表step_seq为空。 */
class TemplateStepSeqTest {

    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> normalize(Object target, List<Map<String, Object>> steps) throws Exception {
        Method m = target.getClass().getDeclaredMethod("normalizeTemplateSteps", List.class);
        m.setAccessible(true);
        return (List<Map<String, Object>>) m.invoke(target, steps);
    }

    private Object[] targets() throws Exception {
        Object planning = org.objenesis.ObjenesisHelper.newInstance(TaskPlanningOrchestrator.class);
        Object replanning = org.objenesis.ObjenesisHelper.newInstance(ReplanningService.class);
        return new Object[]{planning, replanning};
    }

    @Test
    void missingStepSeqIsFilledInTemplateOrder() throws Exception {
        List<Map<String, Object>> steps = List.of(
                Map.of("capabilityType", "CAP_NAVIGATION"),
                Map.of("capabilityType", "CAP_ESCORT"),
                Map.of("capabilityType", "CAP_NOTIFICATION"));
        for (Object t : targets()) {
            List<Map<String, Object>> out = normalize(t, steps);
            assertEquals(List.of(1, 2, 3), out.stream().map(s -> s.get("stepSeq")).toList(), t.getClass().getSimpleName());
        }
    }

    @Test
    void existingStepSeqIsPreserved() throws Exception {
        List<Map<String, Object>> steps = List.of(
                Map.of("capabilityType", "CAP_NAVIGATION", "stepSeq", 1),
                Map.of("capabilityType", "CAP_ESCORT", "stepSeq", 2));
        for (Object t : targets()) {
            assertEquals(List.of(1, 2), normalize(t, steps).stream().map(s -> s.get("stepSeq")).toList());
        }
        assertNotNull(mock(Object.class));
        assertNotNull(ReflectionTestUtils.class);
    }
}
