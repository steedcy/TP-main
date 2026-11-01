package com.airport.ai.task;

import com.airport.ai.common.BusinessException;
import com.airport.ai.common.ErrorCode;
import com.airport.ai.taskdef.TaskDefinition;
import org.junit.jupiter.api.Test;

import java.util.HashMap;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

/** DEF-S3-029：扩展任务定义声明的必填场景参数与类型在建任务前核对；预置任务族不在提交时拒绝。 */
class SceneParamsValidatorTest {

    private TaskDefinition extension(String sceneParams) {
        TaskDefinition d = new TaskDefinition();
        d.setDefinitionCode("EXT_1");
        d.setIsPreset(false);
        d.setSceneParams(sceneParams);
        return d;
    }

    private static final String DECLARED = "[{\"name\":\"sampleLocation\",\"type\":\"String\",\"required\":true},"
            + "{\"name\":\"headcount\",\"type\":\"Integer\",\"required\":false},"
            + "{\"name\":\"ratio\",\"type\":\"Double\",\"required\":false},"
            + "{\"name\":\"urgent\",\"type\":\"Boolean\",\"required\":false}]";

    private void assertRejected(ErrorCode code, Map<String, Object> scene) {
        BusinessException ex = assertThrows(BusinessException.class,
                () -> SceneParamsValidator.validate(extension(DECLARED), scene));
        assertEquals(code, ex.getErrorCode());
    }

    @Test
    void missingNullAndBlankRequiredParametersAreRejected() {
        assertRejected(ErrorCode.PARAM_MISSING, null);
        assertRejected(ErrorCode.PARAM_MISSING, Map.of());
        assertRejected(ErrorCode.PARAM_MISSING, Map.of("headcount", 3));
        Map<String, Object> nulled = new HashMap<>();
        nulled.put("sampleLocation", null);
        assertRejected(ErrorCode.PARAM_MISSING, nulled);
        assertRejected(ErrorCode.PARAM_MISSING, Map.of("sampleLocation", "   "));
        var ex = assertThrows(BusinessException.class, () -> SceneParamsValidator.validate(extension(DECLARED), Map.of()));
        assertTrue(ex.getMessage().contains("sampleLocation"));
    }

    @Test
    void wrongTypesAreRejected() {
        assertRejected(ErrorCode.PARAM_FORMAT_ERROR, Map.of("sampleLocation", 12));
        assertRejected(ErrorCode.PARAM_FORMAT_ERROR, Map.of("sampleLocation", "A", "headcount", "three"));
        assertRejected(ErrorCode.PARAM_FORMAT_ERROR, Map.of("sampleLocation", "A", "headcount", 2.5));
        assertRejected(ErrorCode.PARAM_FORMAT_ERROR, Map.of("sampleLocation", "A", "ratio", "x"));
        assertRejected(ErrorCode.PARAM_FORMAT_ERROR, Map.of("sampleLocation", "A", "urgent", "maybe"));
        assertRejected(ErrorCode.PARAM_FORMAT_ERROR, Map.of("sampleLocation", "x".repeat(501)));
    }

    @Test
    void validAndOptionalParametersPass() {
        SceneParamsValidator.validate(extension(DECLARED), Map.of("sampleLocation", "F2 北侧"));
        SceneParamsValidator.validate(extension(DECLARED), Map.of("sampleLocation", "A", "headcount", 3, "ratio", 0.5, "urgent", true));
        SceneParamsValidator.validate(extension(DECLARED), Map.of("sampleLocation", "A", "headcount", 3.0, "urgent", "false"));
        SceneParamsValidator.validate(extension(DECLARED), Map.of("sampleLocation", "A", "undeclaredExtra", "ok"));
    }

    @Test
    void presetFamiliesAndMissingDefinitionsAreNotRejectedAtSubmit() {
        TaskDefinition preset = extension(DECLARED);
        preset.setIsPreset(true);
        SceneParamsValidator.validate(preset, Map.of());
        SceneParamsValidator.validate(null, Map.of());
        SceneParamsValidator.validate(extension(null), Map.of());
        SceneParamsValidator.validate(extension("not json"), Map.of());
        SceneParamsValidator.validate(extension("[]"), null);
    }
}
