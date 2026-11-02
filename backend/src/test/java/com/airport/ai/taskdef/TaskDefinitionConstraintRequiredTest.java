package com.airport.ai.taskdef;

import com.airport.ai.devicetype.dto.ParamDefinition;
import com.airport.ai.taskdef.dto.CreateTaskDefinitionRequest;
import com.airport.ai.taskdef.dto.UpdateTaskDefinitionRequest;
import jakarta.validation.ConstraintViolation;
import jakarta.validation.Validation;
import jakarta.validation.Validator;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Set;
import java.util.stream.Collectors;

import static org.junit.jupiter.api.Assertions.*;

/** DEF-S3-030 / SRS_F022.R03：任务定义新增和编辑都必须填写约束条件。 */
class TaskDefinitionConstraintRequiredTest {
    private final Validator validator = Validation.buildDefaultValidatorFactory().getValidator();

    private ParamDefinition param() {
        ParamDefinition p = new ParamDefinition();
        p.setName("sampleLocation");
        p.setType("String");
        p.setRequired(true);
        return p;
    }

    private CreateTaskDefinitionRequest create(String constraint) {
        CreateTaskDefinitionRequest r = new CreateTaskDefinitionRequest();
        r.setTaskName("扩展任务");
        r.setGoalTemplate("目标模板");
        r.setSceneParams(List.of(param()));
        r.setAvailableCapabilityTypes(List.of("CAP_NAVIGATION"));
        r.setConstraintDescription(constraint);
        r.setCompletionCondition("完成");
        return r;
    }

    private UpdateTaskDefinitionRequest update(String constraint) {
        UpdateTaskDefinitionRequest r = new UpdateTaskDefinitionRequest();
        r.setGoalTemplate("目标模板");
        r.setSceneParams(List.of(param()));
        r.setAvailableCapabilityTypes(List.of("CAP_NAVIGATION"));
        r.setConstraintDescription(constraint);
        r.setCompletionCondition("完成");
        return r;
    }

    private Set<String> messages(Set<? extends ConstraintViolation<?>> violations) {
        return violations.stream().map(v -> v.getPropertyPath() + ":" + v.getMessage()).collect(Collectors.toSet());
    }

    @Test
    void createWithAConstraintPasses() {
        var v = validator.validate(create("不得引导旅客脱离监控区域"));
        assertTrue(v.isEmpty(), messages(v).toString());
    }

    @Test
    void createRejectsMissingEmptyAndBlankConstraint() {
        for (String bad : new String[]{null, "", "   "}) {
            var v = validator.validate(create(bad));
            assertTrue(messages(v).stream().anyMatch(m -> m.startsWith("constraintDescription:") && m.contains("约束条件")),
                    "应拒绝: [" + bad + "] " + messages(v));
        }
    }

    @Test
    void updateRejectsMissingEmptyAndBlankConstraint() {
        for (String bad : new String[]{null, "", "   "}) {
            var v = validator.validate(update(bad));
            assertTrue(messages(v).stream().anyMatch(m -> m.startsWith("constraintDescription:")), "应拒绝: [" + bad + "] " + messages(v));
        }
        assertTrue(validator.validate(update("全程保持通知联动")).isEmpty());
    }

    @Test
    void overlongConstraintIsRejectedButPresetSizedOnesPass() {
        assertFalse(validator.validate(create("x".repeat(501))).isEmpty());
        assertTrue(validator.validate(create("x".repeat(500))).isEmpty());
        // 预置定义的约束文字都在40字以内，编辑预置定义不受影响
        assertTrue(validator.validate(update("超规行李处置全程不得引导旅客脱离监控区域；测量结果超标须触发超规事件上报")).isEmpty());
    }
}
