package com.airport.ai.planning;

import com.airport.ai.taskdef.TaskDefinitionMapper;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;

import java.nio.file.Files;
import java.nio.file.Path;
import java.time.ZoneId;
import java.time.ZonedDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

/** Explicit opt-in only. Three bounded live calls using fictitious data; not the 95-case acceptance run. */
@EnabledIfEnvironmentVariable(named = "TIP_MOONSHOT_LIVE_PROBE", matches = "true")
class MoonshotReadinessProbeTest {
    @Test
    void verifiesUnderstandingClarificationAndPlanContractWithoutDevices() throws Exception {
        ObjectMapper mapper = new ObjectMapper();
        String key = System.getenv("MOONSHOT_API_KEY");
        assertNotNull(key, "MOONSHOT_API_KEY is required");
        String model = System.getenv().getOrDefault("MOONSHOT_MODEL", "kimi-k2.6");
        MoonshotChatClient client = new MoonshotChatClient(mapper, "https://api.moonshot.cn/v1", key, model, 2048, 60000);
        TaskDefinitionMapper definitions = mock(TaskDefinitionMapper.class);
        when(definitions.findByDefinitionStatus("ENABLED"))
                .thenReturn(List.of(MoonshotModelServiceTest.flightDefinition()));
        MoonshotModelService service = new MoonshotModelService(client, definitions, mapper);
        List<Map<String, Object>> checks = new ArrayList<>();

        GoalUnderstandingRequest goal = new GoalUnderstandingRequest();
        goal.setRequestId(UUID.randomUUID().toString());
        goal.setTaskFamily("FLIGHT_CHANGE_RESPONSE");
        goal.setTaskGoal("为虚构测试航班 TEST_FLIGHT_001 发布登机口从 TEST_A 改为 TEST_B 的通知，以变更信息已发布为完成条件。");
        goal.setSceneParams(Map.of("flightNumber", "TEST_FLIGHT_001", "origin", "TEST_A", "destination", "TEST_B",
                "content", "虚构测试航班 TEST_FLIGHT_001 登机口从 TEST_A 改为 TEST_B"));
        long started = System.nanoTime();
        GoalUnderstandingResponse understood = service.understand(goal);
        boolean understandingPassed = understood.isSuccess() && understood.isInfoComplete()
                && "FLIGHT_CHANGE_RESPONSE".equals(understood.getInferredTaskFamily());
        checks.add(Map.of("check", "goal_understanding", "passed", understandingPassed,
                "elapsedMs", (System.nanoTime() - started) / 1_000_000,
                "response", mapper.valueToTree(understood)));

        GoalUnderstandingRequest incomplete = new GoalUnderstandingRequest();
        incomplete.setRequestId(UUID.randomUUID().toString());
        incomplete.setTaskFamily("FLIGHT_CHANGE_RESPONSE");
        incomplete.setTaskGoal("请为该航班发布变更通知。");
        incomplete.setSceneParams(Map.of());
        started = System.nanoTime();
        GoalUnderstandingResponse clarification = service.understand(incomplete);
        boolean clarificationPassed = clarification.isSuccess() && !clarification.isInfoComplete()
                && clarification.getMissingInfoQuestions() != null && !clarification.getMissingInfoQuestions().isEmpty();
        checks.add(Map.of("check", "missing_information", "passed", clarificationPassed,
                "elapsedMs", (System.nanoTime() - started) / 1_000_000,
                "response", mapper.valueToTree(clarification)));

        PlanningRequest planning = new PlanningRequest();
        planning.setRequestId(UUID.randomUUID().toString());
        planning.setTaskGoal(goal.getTaskGoal());
        planning.setTaskFamily(goal.getTaskFamily());
        planning.setSceneParams(goal.getSceneParams());
        planning.setConstraints(List.of("只生成发布变更信息的业务步骤，不执行设备指令"));
        planning.setCapabilityContext(List.of(Map.of("capabilityType", "CAP_FLIGHT_UPDATE", "candidateCount", 2)));
        planning.setRemainingStepQuota(5);
        planning.setCompletedSteps(List.of());
        started = System.nanoTime();
        PlanningResponse plan = service.generatePlan(planning);
        boolean planningPassed = plan.isSuccess() && plan.getPlanSteps() != null
                && !plan.getPlanSteps().isEmpty() && plan.getPlanSteps().size() <= 5
                && plan.getPlanSteps().stream().allMatch(s -> "CAP_FLIGHT_UPDATE".equals(s.get("capabilityType")));
        checks.add(Map.of("check", "candidate_plan", "passed", planningPassed,
                "elapsedMs", (System.nanoTime() - started) / 1_000_000,
                "response", mapper.valueToTree(plan)));

        Path evidence = Path.of("target", "moonshot-readiness-probe.json");
        Files.createDirectories(evidence.getParent());
        Files.writeString(evidence, mapper.writerWithDefaultPrettyPrinter().writeValueAsString(Map.of(
                "checkedAt", ZonedDateTime.now(ZoneId.of("Asia/Shanghai")).toString(), "model", model,
                "scope", "Adapter readiness only; fictitious data; no device commands or database writes", "checks", checks)));
        assertAll(() -> assertTrue(understandingPassed, "Goal understanding failed; see sanitized probe evidence"),
                () -> assertTrue(clarificationPassed, "Missing-information handling failed; see probe evidence"),
                () -> assertTrue(planningPassed, "Candidate plan contract failed; see probe evidence"));
    }
}
