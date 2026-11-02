package com.airport.ai.task;

import com.airport.ai.devicetype.dto.ParamDefinition;
import com.airport.ai.taskdef.TaskDefinition;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * 目标理解后由系统自己核对“必要信息”是否齐全，不再把模型自由生成的追问清单直接交给操作员
 * （SRS_F010.R03、F024.R03、F025.R01、F026.R04；DEF-S3-003/004/005）。
 *
 * 之前的问题：模型判定信息不完整后，系统原样保存其追问并在三轮后转人工，于是出现
 * 已提交的 baggageLocation 被反复追问、追问任务定义外的字段与旅客身份、追问机器人ID/路线编码等
 * 系统自己选择设备时才会决定的内容。
 *
 * 规则：
 * 1. 必要信息由任务族决定（见 {@link #requirementsFor}）；某项只要在场景参数里有值，或目标理解已解析出
 *    对应的起点/目的地，就算已提供；
 * 2. 全部必要信息已提供时，不论模型怎么说都按“完整”处理，进入规划；
 * 3. 仍有缺失时，追问内容由系统按缺失项生成，只问缺的那几项，不问身份、设备、路线等。
 * 4. 没有任务族（开放式目标）时没有可核对的清单，沿用模型的追问。
 */
public final class RequiredInfoGuard {
    private static final ObjectMapper JSON = new ObjectMapper();

    /** 一项必要信息：满足条件是场景参数 sceneKeys 之一有值，或目标理解的 parsedKey 有值。 */
    public record Requirement(String label, List<String> sceneKeys, String parsedKey, String question) {}

    public record Verdict(boolean complete, List<String> questions, List<String> missing) {}

    private RequiredInfoGuard() {}

    /** 预置三类任务族的必要信息；扩展定义取其声明的必填场景参数；其余返回 null 表示无法核对。 */
    public static List<Requirement> requirementsFor(String taskFamily, TaskDefinition definition) {
        if (taskFamily == null || taskFamily.isBlank()) return null;
        switch (taskFamily) {
            case "OVERSIZE_BAGGAGE_HANDLING":
                return List.of(new Requirement("行李所在位置", List.of("baggageLocation"), null,
                        "请补充行李当前所在位置"));
            case "SPECIAL_PASSENGER_SERVICE":
                // F025.R01：只检查协助类型、起点、目的地；不要求也不保存旅客真实身份信息
                return List.of(
                        new Requirement("协助类型", List.of("assistanceType"), null, "请补充协助类型（如轮椅、视障或听障陪同）"),
                        new Requirement("起点", List.of("origin", "startLocation", "originLocation"), "origin", "请补充服务起点"),
                        new Requirement("目的地", List.of("destination", "targetLocation", "targetPlace"), "destination", "请补充服务目的地"));
            case "FLIGHT_CHANGE_RESPONSE":
                // F026.R04：只需航班变更事实；机器人、路线、设备由系统在规划与分配时选择，不向操作员追问
                return List.of(
                        new Requirement("航班号", List.of("flightNumber"), null, "请补充航班号"),
                        new Requirement("变更内容", List.of("changeType", "changeDescription", "updateType", "updateContent"), null,
                                "请补充航班变更内容"));
            default:
                return fromDefinition(definition);
        }
    }

    private static List<Requirement> fromDefinition(TaskDefinition definition) {
        if (definition == null || definition.getSceneParams() == null || definition.getSceneParams().isBlank()) return null;
        try {
            List<ParamDefinition> declared = JSON.readValue(definition.getSceneParams(),
                    JSON.getTypeFactory().constructCollectionType(List.class, ParamDefinition.class));
            List<Requirement> out = new ArrayList<>();
            for (ParamDefinition p : declared) {
                if (Boolean.TRUE.equals(p.getRequired())) {
                    out.add(new Requirement(p.getName(), List.of(p.getName()), null, "请补充" + p.getName()));
                }
            }
            return out;
        } catch (Exception ex) {
            return null;
        }
    }

    /** 核对必要信息。requirements 为 null（无法核对）时返回 null，由调用方沿用模型判断。 */
    public static Verdict check(List<Requirement> requirements, Map<String, Object> scene, Map<String, Object> parsed) {
        if (requirements == null) return null;
        List<String> missing = new ArrayList<>();
        List<String> questions = new ArrayList<>();
        for (Requirement r : requirements) {
            if (!provided(r, scene, parsed)) {
                missing.add(r.label());
                questions.add(r.question());
            }
        }
        return new Verdict(missing.isEmpty(), questions, missing);
    }

    private static boolean provided(Requirement r, Map<String, Object> scene, Map<String, Object> parsed) {
        if (scene != null) {
            for (String key : r.sceneKeys()) if (hasValue(scene.get(key))) return true;
            if (answeredByClarification(r, scene.get("clarificationAnswers"))) return true;
        }
        return r.parsedKey() != null && parsed != null && hasValue(parsed.get(r.parsedKey()));
    }

    /**
     * 操作员的补充回答以“问题原文”为键保存在 clarificationAnswers 里。系统生成的追问文字固定，
     * 所以回答过该项的问题就算已提供；否则回答之后会一直被问同一个问题。
     */
    private static boolean answeredByClarification(Requirement r, Object rounds) {
        if (!(rounds instanceof Iterable<?> list)) return false;
        for (Object round : list) {
            if (!(round instanceof Map<?, ?> roundMap)) continue;
            Object answers = roundMap.get("answers");
            if (answers instanceof Map<?, ?> byQuestion && hasValue(byQuestion.get(r.question()))) return true;
        }
        return false;
    }

    private static boolean hasValue(Object value) {
        if (value == null) return false;
        if (value instanceof String s) return !s.isBlank();
        if (value instanceof Iterable<?> it) return it.iterator().hasNext();
        if (value instanceof Map<?, ?> m) return !m.isEmpty();
        return true;
    }
}
