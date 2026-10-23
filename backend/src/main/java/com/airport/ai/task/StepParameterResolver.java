package com.airport.ai.task;

import com.airport.ai.device.ParameterValues;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.stereotype.Component;
import java.util.*;

@Component
public class StepParameterResolver {
    private final TaskMapper tasks;
    private final TaskStepAssignmentMapper assignments;
    private final ObjectMapper mapper;
    public StepParameterResolver(TaskMapper tasks, TaskStepAssignmentMapper assignments, ObjectMapper mapper) {
        this.tasks = tasks; this.assignments = assignments; this.mapper = mapper;
    }

    @SuppressWarnings("unchecked")
    public Map<String, Object> resolve(Long taskId, Long versionId, Map<String, Object> step) {
        try {
            if (!(step.get("paramMapping") instanceof List<?> mappings)) {
                return step.get("inputParams") instanceof Map<?, ?> map ? (Map<String, Object>)map : Map.of();
            }
            Task task = tasks.findById(taskId).orElseThrow();
            Map<String, Object> scene = mapper.readValue(task.getSceneParams(), Map.class);
            Map<String, Object> result = new LinkedHashMap<>();
            for (Object item : mappings) {
                Map<String, Object> mapping = (Map<String, Object>) item;
                String source = String.valueOf(mapping.get("source"));
                Object value;
                if (source.startsWith("TEMPLATE_INPUT.")) {
                    value = scene.get(source.substring("TEMPLATE_INPUT.".length()));
                } else if (source.matches("STEP\\d+_OUTPUT\\..+")) {
                    int marker = source.indexOf("_OUTPUT.");
                    int seq = Integer.parseInt(source.substring(4, marker));
                    if (seq >= ((Number)step.get("stepSeq")).intValue()) throw new IllegalArgumentException("参数映射不能引用当前或后续步骤");
                    TaskStepAssignment previous = assignments.findByPlanVersionIdAndStepSeq(versionId, seq).orElseThrow();
                    if (!"COMPLETED".equals(previous.getStepStatus())) throw new IllegalArgumentException("映射来源步骤尚未完成");
                    Map<String, Object> output = mapper.readValue(previous.getOutputParams(), Map.class);
                    value = output.get(source.substring(marker + "_OUTPUT.".length()));
                } else throw new IllegalArgumentException("不支持的参数映射来源");
                if (value == null) throw new IllegalArgumentException("参数映射来源缺失: " + source);
                result.put(String.valueOf(mapping.get("target")), value);
            }
            return result;
        } catch (IllegalArgumentException ex) { throw ex; }
        catch (Exception ex) { throw new IllegalArgumentException("步骤参数映射失败", ex); }
    }
}
