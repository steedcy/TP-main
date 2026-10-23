package com.airport.ai.planning;

import com.airport.ai.taskdef.TaskDefinition;
import com.airport.ai.taskdef.TaskDefinitionMapper;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import java.util.List;
import java.util.Map;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class MoonshotModelServiceTest {
    private final ObjectMapper mapper = new ObjectMapper();
    private final MoonshotChatClient client = mock(MoonshotChatClient.class);
    private final TaskDefinitionMapper definitions = mock(TaskDefinitionMapper.class);
    private MoonshotModelService service;

    @BeforeEach
    void setup() {
        when(definitions.findByDefinitionStatus("ENABLED")).thenReturn(List.of(flightDefinition()));
        service = new MoonshotModelService(client, definitions, mapper);
    }

    static TaskDefinition flightDefinition() {
        TaskDefinition definition = new TaskDefinition();
        definition.setDefinitionCode("FLIGHT_CHANGE_RESPONSE");
        definition.setTaskName("航班变更应对");
        definition.setGoalTemplate("发布航班登机口变更信息");
        definition.setSceneParams("[{\"name\":\"flightNumber\",\"type\":\"String\",\"required\":true}]");
        definition.setAvailableCapabilityTypes("[\"CAP_FLIGHT_UPDATE\"]");
        definition.setConstraintDescription("只发布场景中给出的虚构变更信息");
        definition.setCompletionCondition("航班变更信息已发布");
        return definition;
    }

    private ObjectNode goal() throws Exception {
        return (ObjectNode) mapper.readTree("""
                {"resultCode":"0","errorMessage":null,"origin":null,"destination":null,
                 "constraints":[],"completionCondition":"变更通知已发布","infoComplete":true,
                 "missingInfoQuestions":[],"unrelatedToAnyFamily":false,"inferredTaskFamily":"FLIGHT_CHANGE_RESPONSE"}
                """);
    }

    private GoalUnderstandingRequest goalRequest() {
        GoalUnderstandingRequest request = new GoalUnderstandingRequest();
        request.setTaskGoal("发布测试航班通知");
        return request;
    }

    @Test
    void rejectsMissingBooleanAndInventedFamily() throws Exception {
        ObjectNode json = goal();
        json.remove("infoComplete");
        when(client.complete(anyString(), any(), any())).thenReturn(json);
        assertFalse(service.understand(goalRequest()).isSuccess());
        json = goal();
        json.put("inferredTaskFamily", "NON_EXISTENT_FAMILY");
        when(client.complete(anyString(), any(), any())).thenReturn(json);
        assertFalse(service.understand(goalRequest()).isSuccess());
    }

    @Test
    void acceptsClarificationButRejectsIncompleteGoalWithoutQuestions() throws Exception {
        ObjectNode json = goal();
        json.put("infoComplete", false);
        json.putArray("missingInfoQuestions").add("请提供航班号");
        when(client.complete(anyString(), any(), any())).thenReturn(json);
        assertFalse(service.understand(goalRequest()).isInfoComplete());
        assertTrue(service.understand(goalRequest()).isSuccess());
        json.putArray("missingInfoQuestions");
        assertFalse(service.understand(goalRequest()).isSuccess());
    }

    @Test
    void onlySuppliesEnabledTaskDefinitionsAndPreservesModelFailure() {
        when(client.complete(anyString(), any(), any())).thenAnswer(invocation -> {
            Map<?, ?> payload = invocation.getArgument(1);
            assertTrue(payload.containsKey("enabledTaskDefinitions"));
            throw new MoonshotChatClient.CallFailure("1003", "Kimi 调用超时");
        });
        assertEquals("1003", service.understand(goalRequest()).getResultCode());
    }

    @Test
    void rejectsSuccessWithEmptyPlanAndOutOfRangeConfidence() throws Exception {
        ObjectNode json = (ObjectNode) mapper.readTree("""
                {"resultCode":"0","errorMessage":null,"planSteps":[],"planRationale":"测试",
                 "confidence":0.8,"candidateDiverse":false}
                """);
        when(client.complete(anyString(), any(), any())).thenReturn(json);
        PlanningRequest request = new PlanningRequest();
        request.setTaskFamily("FLIGHT_CHANGE_RESPONSE");
        assertFalse(service.generatePlan(request).isSuccess());
        json.put("confidence", 2);
        assertFalse(service.generatePlan(request).isSuccess());
    }
}
