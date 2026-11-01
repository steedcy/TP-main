package com.airport.ai.task;

import com.airport.ai.common.BusinessException;
import com.airport.ai.common.ErrorCode;
import com.airport.ai.devicetype.dto.ParamDefinition;
import com.airport.ai.taskdef.TaskDefinition;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * 提交前按任务定义声明的场景参数核对必填与类型（SRS_F010.R01、SRS_F022.R03、DEF-S3-029）。
 * 只针对运营人员自行新增的扩展定义：预置任务族的关键信息缺失走提交后的追问流程（R03），不在提交时拒绝。
 * 校验未通过时不建任务、不调用目标理解模型。未声明的额外参数不拒绝（航班表单等会带附加字段）。
 */
public final class SceneParamsValidator {
    private static final ObjectMapper JSON = new ObjectMapper();

    private SceneParamsValidator() {}

    public static void validate(TaskDefinition definition, Map<String, Object> supplied) {
        if (definition == null || Boolean.TRUE.equals(definition.getIsPreset())) return;
        List<ParamDefinition> declared = parse(definition.getSceneParams());
        for (ParamDefinition p : declared) {
            Object value = supplied == null ? null : supplied.get(p.getName());
            boolean blank = value == null || (value instanceof String s && s.isBlank());
            if (blank) {
                if (Boolean.TRUE.equals(p.getRequired())) {
                    throw new BusinessException(ErrorCode.PARAM_MISSING, "场景参数" + p.getName() + "为必填项");
                }
                continue;
            }
            checkType(p, value);
        }
    }

    private static void checkType(ParamDefinition p, Object value) {
        String type = p.getType() == null ? "String" : p.getType();
        boolean ok = switch (type) {
            case "String" -> value instanceof String;
            case "Integer" -> value instanceof Integer || value instanceof Long
                    || (value instanceof Number n && n.doubleValue() == Math.rint(n.doubleValue()));
            case "Double" -> value instanceof Number;
            case "Boolean" -> value instanceof Boolean || Set.of("true", "false").contains(String.valueOf(value));
            default -> true;
        };
        if (!ok) {
            throw new BusinessException(ErrorCode.PARAM_FORMAT_ERROR, "场景参数" + p.getName() + "类型应为" + type);
        }
        if (value instanceof String text && "String".equals(type) && text.length() > 500) {
            throw new BusinessException(ErrorCode.PARAM_FORMAT_ERROR, "场景参数" + p.getName() + "过长");
        }
    }

    private static List<ParamDefinition> parse(String json) {
        if (json == null || json.isBlank()) return List.of();
        try {
            return JSON.readValue(json, JSON.getTypeFactory().constructCollectionType(List.class, ParamDefinition.class));
        } catch (Exception e) {
            return List.of();
        }
    }
}
