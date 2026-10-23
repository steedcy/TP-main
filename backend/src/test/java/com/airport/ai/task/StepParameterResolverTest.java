package com.airport.ai.task;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import java.util.*;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class StepParameterResolverTest {
    @Test void resolvesSceneAndActualPriorOutput() {
        var tasks=mock(TaskMapper.class); var assignments=mock(TaskStepAssignmentMapper.class);
        var task=new Task(); task.setSceneParams("{\"alertLevel\":\"WARNING\"}"); when(tasks.findById(1L)).thenReturn(Optional.of(task));
        var previous=new TaskStepAssignment(); previous.setStepStatus("COMPLETED"); previous.setOutputParams("{\"baggageInfo\":\"actual-result\"}");
        when(assignments.findByPlanVersionIdAndStepSeq(2L,1)).thenReturn(Optional.of(previous));
        var resolver=new StepParameterResolver(tasks,assignments,new ObjectMapper());
        var step=Map.<String,Object>of("stepSeq",2,"paramMapping",List.of(
                Map.of("target","baggageInfo","source","STEP1_OUTPUT.baggageInfo"),
                Map.of("target","alertLevel","source","TEMPLATE_INPUT.alertLevel")));
        assertEquals(Map.of("baggageInfo","actual-result","alertLevel","WARNING"),resolver.resolve(1L,2L,step));
        previous.setStepStatus("FAILED"); assertThrows(IllegalArgumentException.class,()->resolver.resolve(1L,2L,step));
    }
    @Test void rejectsFutureSource() {
        var tasks=mock(TaskMapper.class); var task=new Task(); task.setSceneParams("{}"); when(tasks.findById(1L)).thenReturn(Optional.of(task));
        var resolver=new StepParameterResolver(tasks,mock(TaskStepAssignmentMapper.class),new ObjectMapper());
        assertThrows(IllegalArgumentException.class,()->resolver.resolve(1L,2L,Map.of("stepSeq",1,"paramMapping",
                List.of(Map.of("target","value","source","STEP2_OUTPUT.value")))));
    }
}
