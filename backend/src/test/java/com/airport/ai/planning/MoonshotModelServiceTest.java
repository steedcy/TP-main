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
    @Test
    void planningPromptOnlyOffersCapabilitiesAllowedByTaskFamilyAndOnlineCandidates() {
        PlanningRequest request = new PlanningRequest();
        request.setTaskFamily("FLIGHT_CHANGE_RESPONSE");
        request.setCapabilityContext(List.of(
                Map.of("capabilityType", "CAP_FLIGHT_UPDATE", "candidateCount", 1),
                Map.of("capabilityType", "CAP_ESCORT", "candidateCount", 1),
                Map.of("capabilityType", "CAP_NOTIFICATION", "candidateCount", 0)));
        when(client.complete(anyString(), any(), any())).thenAnswer(invocation -> {
            String prompt = invocation.getArgument(0);
            Map<?, ?> payload = invocation.getArgument(1);
            assertTrue(prompt.contains("eligibleCapabilityTypes"));
            assertEquals(List.of("CAP_FLIGHT_UPDATE"), payload.get("eligibleCapabilityTypes"));
            throw new MoonshotChatClient.CallFailure("1002", "fixture response");
        });
        assertFalse(service.generatePlan(request).isSuccess());
    }

    @Test
    void supportsGeneralServiceCatchAllFamilyForUnderstandingAndPlanning() throws Exception {
        TaskDefinition general = new TaskDefinition();
        general.setDefinitionCode("GENERAL_SERVICE");
        general.setTaskName("通用协同服务");
        general.setGoalTemplate("开放式机场服务目标");
        general.setSceneParams("[]");
        general.setAvailableCapabilityTypes("[\"CAP_INFO_DISPLAY\",\"CAP_NAVIGATION\",\"CAP_NOTIFICATION\"]");
        general.setConstraintDescription("禁止进入商铺区");
        general.setCompletionCondition("任务目标已完成");
        when(definitions.findByDefinitionStatus("ENABLED")).thenReturn(List.of(flightDefinition(), general));

        ObjectNode json = (ObjectNode) mapper.readTree("""
                {"resultCode":"0","errorMessage":null,"origin":"SERVICE_DESK","destination":"GATE_04",
                 "constraints":[],"completionCondition":"已在智慧屏发布提示并完成引导","infoComplete":true,
                 "missingInfoQuestions":[],"unrelatedToAnyFamily":false,"inferredTaskFamily":"GENERAL_SERVICE"}
                """);
        when(client.complete(anyString(), any(), any())).thenAnswer(invocation -> {
            String prompt = invocation.getArgument(0);
            assertTrue(prompt.contains("GENERAL_SERVICE"));
            return json;
        });

        GoalUnderstandingResponse understood = service.understand(goalRequest());
        assertTrue(understood.isSuccess());
        assertFalse(understood.isUnrelatedToAnyFamily());
        assertTrue(understood.isInfoComplete());
        assertEquals("GENERAL_SERVICE", understood.getInferredTaskFamily());

        PlanningRequest planReq = new PlanningRequest();
        planReq.setTaskFamily("GENERAL_SERVICE");
        planReq.setCapabilityContext(List.of(
                Map.of("capabilityType", "CAP_INFO_DISPLAY", "candidateCount", 1),
                Map.of("capabilityType", "CAP_NAVIGATION", "candidateCount", 2),
                Map.of("capabilityType", "CAP_ESCORT", "candidateCount", 1),
                Map.of("capabilityType", "CAP_NOTIFICATION", "candidateCount", 0)));
        doAnswer(invocation -> {
            Map<?, ?> payload = invocation.getArgument(1);
            assertEquals(List.of("CAP_INFO_DISPLAY", "CAP_NAVIGATION"), payload.get("eligibleCapabilityTypes"));
            throw new MoonshotChatClient.CallFailure("1002", "fixture response");
        }).when(client).complete(anyString(), any(), any());
        assertFalse(service.generatePlan(planReq).isSuccess());
    }

    @Test
    void oversizeBaggagePlanningDefaultsPassengerLocationToBaggageLocation() {
        PlanningRequest planReq = new PlanningRequest();
        planReq.setTaskFamily("OVERSIZE_BAGGAGE_HANDLING");
        planReq.setSceneParams(Map.of("baggageLocation", "MEASURE_WEST", "targetCounter", "CHECKIN_WEST"));
        planReq.setCapabilityContext(List.of(Map.of("capabilityType", "CAP_BAGGAGE_MEASURE", "candidateCount", 1)));
        when(client.complete(anyString(), any(), any())).thenAnswer(invocation -> {
            String prompt = invocation.getArgument(0);
            Map<?, ?> payload = invocation.getArgument(1);
            Map<?, ?> req = (Map<?, ?>) payload.get("request");
            Map<?, ?> scene = (Map<?, ?>) req.get("sceneParams");
            assertTrue(prompt.contains("OVERSIZE_BAGGAGE_HANDLING"));
            assertEquals("MEASURE_WEST", scene.get("passengerLocation"));
            throw new MoonshotChatClient.CallFailure("1002", "fixture response");
        });
        assertFalse(service.generatePlan(planReq).isSuccess());
    }
}
