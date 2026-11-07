package com.airport.ai.taskdef;

import com.airport.ai.auth.CurrentUser;
import com.airport.ai.auth.OperationLogService;
import com.airport.ai.auth.User;
import com.airport.ai.common.GlobalExceptionHandler;
import com.airport.ai.devicetype.dto.ParamDefinition;
import com.airport.ai.taskdef.dto.CreateTaskDefinitionRequest;
import com.airport.ai.taskdef.dto.UpdateTaskDefinitionRequest;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.validation.ConstraintViolation;
import jakarta.validation.Validation;
import jakarta.validation.Validator;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * SRS_F022 / TC-068.S2 / TC-069.S2 / DEF-S3-030:
 * 任务定义新增与编辑时，约束条件（constraintDescription）必须填写（非空且非全空白），
 * 长度严格限制在 1~500 字符内。超长或缺失均被严格拦截并返回 HTTP 400（参数校验异常）。
 */
class TaskDefinitionConstraintF022Test {

    private final Validator validator = Validation.buildDefaultValidatorFactory().getValidator();
    private final ObjectMapper objectMapper = new ObjectMapper();

    private TaskDefinitionService taskDefinitionService;
    private CurrentUser currentUser;
    private MockMvc mockMvc;

    @BeforeEach
    void setUp() {
        taskDefinitionService = mock(TaskDefinitionService.class);
        currentUser = mock(CurrentUser.class);
        OperationLogService operationLogService = mock(OperationLogService.class);

        User configAdmin = new User();
        configAdmin.setId(2L);
        configAdmin.setUsername("config-admin");
        configAdmin.setRole("CONFIG_ADMIN");
        when(currentUser.get()).thenReturn(configAdmin);

        TaskDefinition dummy = new TaskDefinition();
        dummy.setId(100L);
        dummy.setTaskName("测试任务");
        dummy.setDefinitionCode("EXT_TEST100");
        dummy.setGoalTemplate("目标模板");
        dummy.setSceneParams("[]");
        dummy.setAvailableCapabilityTypes("[\"CAP_NAVIGATION\"]");
        dummy.setConstraintDescription("合规约束");
        dummy.setCompletionCondition("到达目的地");
        dummy.setIsPreset(false);
        dummy.setDefinitionStatus("ENABLED");

        when(taskDefinitionService.create(any(), any())).thenReturn(dummy);
        when(taskDefinitionService.update(eq(100L), any(), any())).thenReturn(dummy);

        TaskDefinitionController controller = new TaskDefinitionController(taskDefinitionService, currentUser);
        mockMvc = MockMvcBuilders.standaloneSetup(controller)
                .setControllerAdvice(new GlobalExceptionHandler(operationLogService))
                .build();
    }

    private ParamDefinition validParam() {
        ParamDefinition p = new ParamDefinition();
        p.setName("sampleLocation");
        p.setType("String");
        p.setRequired(true);
        return p;
    }

    private CreateTaskDefinitionRequest createReq(String constraint) {
        CreateTaskDefinitionRequest r = new CreateTaskDefinitionRequest();
        r.setTaskName("扩展任务定义");
        r.setGoalTemplate("引导旅客前往登机口");
        r.setSceneParams(List.of(validParam()));
        r.setAvailableCapabilityTypes(List.of("CAP_NAVIGATION"));
        r.setConstraintDescription(constraint);
        r.setCompletionCondition("旅客安全到达目标登机口");
        return r;
    }

    private UpdateTaskDefinitionRequest updateReq(String constraint) {
        UpdateTaskDefinitionRequest r = new UpdateTaskDefinitionRequest();
        r.setGoalTemplate("更新自然语言目标模板");
        r.setSceneParams(List.of(validParam()));
        r.setAvailableCapabilityTypes(List.of("CAP_NAVIGATION"));
        r.setConstraintDescription(constraint);
        r.setCompletionCondition("更新后的完成条件");
        return r;
    }

    private Set<String> getViolations(Set<? extends ConstraintViolation<?>> violations) {
        return violations.stream()
                .map(v -> v.getPropertyPath() + ":" + v.getMessage())
                .collect(Collectors.toSet());
    }

    // ==================== 1. Bean Validation 单元校验 ====================

    @Test
    @DisplayName("CreateTaskDefinitionRequest - 合法约束描述（1字与500字边界）通过校验")
    void testCreateWithValidConstraint() {
        // 1 字
        Set<ConstraintViolation<CreateTaskDefinitionRequest>> v1 = validator.validate(createReq("不"));
        assertTrue(v1.isEmpty(), "1字合法约束应通过校验: " + getViolations(v1));

        // 500 字
        Set<ConstraintViolation<CreateTaskDefinitionRequest>> v500 = validator.validate(createReq("X".repeat(500)));
        assertTrue(v500.isEmpty(), "500字合法约束应通过校验: " + getViolations(v500));

        // 正常业务文字
        Set<ConstraintViolation<CreateTaskDefinitionRequest>> vNormal = validator.validate(createReq("超规行李处置全程不得引导旅客脱离监控区域"));
        assertTrue(vNormal.isEmpty(), "正常业务约束应通过校验: " + getViolations(vNormal));
    }

    @Test
    @DisplayName("CreateTaskDefinitionRequest - 缺失、空串、纯空白约束条件应被拒绝 (DEF-S3-030)")
    void testCreateRejectsMissingBlankConstraint() {
        for (String bad : new String[]{null, "", "   ", "\t\r\n"}) {
            Set<ConstraintViolation<CreateTaskDefinitionRequest>> violations = validator.validate(createReq(bad));
            assertFalse(violations.isEmpty(), "应拒绝缺失/空白约束: [" + bad + "]");
            assertTrue(violations.stream().anyMatch(v -> "constraintDescription".equals(v.getPropertyPath().toString())
                            && v.getMessage().contains("约束条件")),
                    "违反信息应包含约束条件提示: " + getViolations(violations));
        }
    }

    @Test
    @DisplayName("CreateTaskDefinitionRequest - 超长约束条件（501字）应被拒绝")
    void testCreateRejectsOverlongConstraint() {
        Set<ConstraintViolation<CreateTaskDefinitionRequest>> violations = validator.validate(createReq("X".repeat(501)));
        assertFalse(violations.isEmpty(), "501字超长约束应被拦截");
        assertTrue(violations.stream().anyMatch(v -> "constraintDescription".equals(v.getPropertyPath().toString())
                        && v.getMessage().contains("500")),
                "违反信息应包含500字长度限制: " + getViolations(violations));
    }

    @Test
    @DisplayName("UpdateTaskDefinitionRequest - 合法约束描述（1字与500字边界）通过校验")
    void testUpdateWithValidConstraint() {
        Set<ConstraintViolation<UpdateTaskDefinitionRequest>> v1 = validator.validate(updateReq("限"));
        assertTrue(v1.isEmpty(), "1字合法约束应通过校验: " + getViolations(v1));

        Set<ConstraintViolation<UpdateTaskDefinitionRequest>> v500 = validator.validate(updateReq("Y".repeat(500)));
        assertTrue(v500.isEmpty(), "500字合法约束应通过校验: " + getViolations(v500));

        Set<ConstraintViolation<UpdateTaskDefinitionRequest>> vPreset = validator.validate(updateReq("全程与现场人员保持通知联动"));
        assertTrue(vPreset.isEmpty(), "预置业务约束应通过校验: " + getViolations(vPreset));
    }

    @Test
    @DisplayName("UpdateTaskDefinitionRequest - 缺失、空串、纯空白约束条件应被拒绝 (DEF-S3-030)")
    void testUpdateRejectsMissingBlankConstraint() {
        for (String bad : new String[]{null, "", "   ", "\n  \t"}) {
            Set<ConstraintViolation<UpdateTaskDefinitionRequest>> violations = validator.validate(updateReq(bad));
            assertFalse(violations.isEmpty(), "更新操作应拒绝缺失/空白约束: [" + bad + "]");
            assertTrue(violations.stream().anyMatch(v -> "constraintDescription".equals(v.getPropertyPath().toString())
                            && v.getMessage().contains("约束条件")),
                    "违反信息应包含约束条件提示: " + getViolations(violations));
        }
    }

    @Test
    @DisplayName("UpdateTaskDefinitionRequest - 超长约束条件（501字）应被拒绝")
    void testUpdateRejectsOverlongConstraint() {
        Set<ConstraintViolation<UpdateTaskDefinitionRequest>> violations = validator.validate(updateReq("Z".repeat(501)));
        assertFalse(violations.isEmpty(), "更新操作501字超长约束应被拦截");
        assertTrue(violations.stream().anyMatch(v -> "constraintDescription".equals(v.getPropertyPath().toString())
                        && v.getMessage().contains("500")),
                "违反信息应包含500字长度限制: " + getViolations(violations));
    }

    // ==================== 2. HTTP Controller MockMvc 拦截与响应校验 ====================

    @Test
    @DisplayName("POST /api/v1/task-definitions - 缺失约束描述返回 HTTP 400")
    void testPostTaskDefinitionMissingConstraintReturns400() throws Exception {
        CreateTaskDefinitionRequest req = createReq(null);
        mockMvc.perform(post("/api/v1/task-definitions")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(req)))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value(3001))
                .andExpect(jsonPath("$.message").value("请输入约束条件"));
    }

    @Test
    @DisplayName("POST /api/v1/task-definitions - 纯空白约束描述返回 HTTP 400")
    void testPostTaskDefinitionBlankConstraintReturns400() throws Exception {
        CreateTaskDefinitionRequest req = createReq("    ");
        mockMvc.perform(post("/api/v1/task-definitions")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(req)))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value(3001))
                .andExpect(jsonPath("$.message").value("请输入约束条件"));
    }

    @Test
    @DisplayName("POST /api/v1/task-definitions - 501字超长约束描述返回 HTTP 400")
    void testPostTaskDefinitionOverlongConstraintReturns400() throws Exception {
        CreateTaskDefinitionRequest req = createReq("A".repeat(501));
        mockMvc.perform(post("/api/v1/task-definitions")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(req)))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value(3001))
                .andExpect(jsonPath("$.message").value("约束条件不得超过500字"));
    }

    @Test
    @DisplayName("POST /api/v1/task-definitions - 合法约束描述返回 HTTP 200 并持久化")
    void testPostTaskDefinitionValidConstraintReturns200() throws Exception {
        CreateTaskDefinitionRequest req = createReq("合法约束条件：全流程保持现场安全告警");
        mockMvc.perform(post("/api/v1/task-definitions")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(req)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.constraintDescription").value("合规约束"));
    }

    @Test
    @DisplayName("PUT /api/v1/task-definitions/{id} - 纯空白约束描述返回 HTTP 400")
    void testPutTaskDefinitionBlankConstraintReturns400() throws Exception {
        UpdateTaskDefinitionRequest req = updateReq("  \t\n  ");
        mockMvc.perform(put("/api/v1/task-definitions/100")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(req)))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value(3001))
                .andExpect(jsonPath("$.message").value("请输入约束条件"));
    }

    @Test
    @DisplayName("PUT /api/v1/task-definitions/{id} - 501字超长约束描述返回 HTTP 400")
    void testPutTaskDefinitionOverlongConstraintReturns400() throws Exception {
        UpdateTaskDefinitionRequest req = updateReq("B".repeat(501));
        mockMvc.perform(put("/api/v1/task-definitions/100")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(req)))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value(3001))
                .andExpect(jsonPath("$.message").value("约束条件不得超过500字"));
    }

    @Test
    @DisplayName("PUT /api/v1/task-definitions/{id} - 合法约束描述返回 HTTP 200")
    void testPutTaskDefinitionValidConstraintReturns200() throws Exception {
        UpdateTaskDefinitionRequest req = updateReq("更新后的合法约束描述");
        mockMvc.perform(put("/api/v1/task-definitions/100")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(req)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200));
    }

    // ==================== 3. DEF-S3-116 / SRS_F022.R07: 任务定义约束参与硬校验 ====================

    @Test
    @DisplayName("PlanValidationService - 任务定义明确禁止地点时，违规候选计划硬拦截为 FAIL (DEF-S3-116)")
    void testPlanValidationHardRejectsProhibitedLocation_DEF_S3_116() {
        com.airport.ai.device.DeviceCapabilityMapper devCapMapper = mock(com.airport.ai.device.DeviceCapabilityMapper.class);
        when(devCapMapper.existsByCapabilityTypeAndCapabilityStatus(eq("CAP_NAVIGATION"), eq("ENABLED"))).thenReturn(true);

        com.airport.ai.task.PlanValidationService validatorService = new com.airport.ai.task.PlanValidationService(devCapMapper);

        Map<String, Object> candidateStep = new java.util.HashMap<>();
        candidateStep.put("stepSeq", 1);
        candidateStep.put("stepGoal", "前往区域");
        candidateStep.put("capabilityType", "CAP_NAVIGATION");
        candidateStep.put("inputParams", Map.of("targetLocation", "F2_TEST_GATE"));
        candidateStep.put("precondition", "device online");
        candidateStep.put("completionCondition", "routeGenerated=true");
        candidateStep.put("failureHandling", "manual handling");
        candidateStep.put("stepTimeout", 600);

        List<Map<String, Object>> agents = List.of(Map.of(
                "onlineStatus", "ONLINE",
                "capabilities", List.of("CAP_NAVIGATION")
        ));

        // 定义约束: 禁止前往F2_TEST_GATE；仅允许前往F2_ZONE_A。
        String constraint = "禁止前往F2_TEST_GATE；仅允许前往F2_ZONE_A。";
        com.airport.ai.task.PlanValidationResult result = validatorService.validate(
                List.of(candidateStep), agents, List.of("CAP_NAVIGATION"), "EXT_TEST", 0, 100L, "routeGenerated=true", constraint
        );

        assertEquals("FAIL", result.getConstraintCheckResult(), "包含禁止地点应判定约束校验失败");
        assertFalse(result.isAllPassed(), "整体验收不应通过");
        assertTrue(result.getErrors().stream().anyMatch(e -> "ERR_TASK_DEFINITION_CONSTRAINT".equals(e.getReasonCode())),
                "错误清单应包含 ERR_TASK_DEFINITION_CONSTRAINT: " + result.getErrors().stream().map(com.airport.ai.task.PlanValidationResult.ValidationError::getDescription).toList());
    }

    @Test
    @DisplayName("PlanValidationService - 任务定义允许合法地点时，校验通过 (PASS)")
    void testPlanValidationPassesAllowedLocation_DEF_S3_116() {
        com.airport.ai.device.DeviceCapabilityMapper devCapMapper = mock(com.airport.ai.device.DeviceCapabilityMapper.class);
        when(devCapMapper.existsByCapabilityTypeAndCapabilityStatus(eq("CAP_NAVIGATION"), eq("ENABLED"))).thenReturn(true);

        com.airport.ai.task.PlanValidationService validatorService = new com.airport.ai.task.PlanValidationService(devCapMapper);

        Map<String, Object> candidateStep = new java.util.HashMap<>();
        candidateStep.put("stepSeq", 1);
        candidateStep.put("stepGoal", "前往区域");
        candidateStep.put("capabilityType", "CAP_NAVIGATION");
        candidateStep.put("inputParams", Map.of("targetLocation", "F2_TEST_GATE"));
        candidateStep.put("precondition", "device online");
        candidateStep.put("completionCondition", "routeGenerated=true");
        candidateStep.put("failureHandling", "manual handling");
        candidateStep.put("stepTimeout", 600);

        List<Map<String, Object>> agents = List.of(Map.of(
                "onlineStatus", "ONLINE",
                "capabilities", List.of("CAP_NAVIGATION")
        ));

        // 正例对照: 仅允许前往F2_TEST_GATE。
        String constraint = "仅允许前往F2_TEST_GATE。";
        com.airport.ai.task.PlanValidationResult result = validatorService.validate(
                List.of(candidateStep), agents, List.of("CAP_NAVIGATION"), "EXT_TEST", 0, 100L, "routeGenerated=true", constraint
        );

        assertEquals("PASS", result.getConstraintCheckResult(), "目标符合约束限定范围应通过");
        assertTrue(result.isAllPassed(), "整体验收应全部通过");
    }

    @Test
    @DisplayName("PlanValidationService - 计划步骤符合白名单允许区域时通过校验")
    void testPlanValidationCompliantWithWhitelist_DEF_S3_116() {
        com.airport.ai.device.DeviceCapabilityMapper devCapMapper = mock(com.airport.ai.device.DeviceCapabilityMapper.class);
        when(devCapMapper.existsByCapabilityTypeAndCapabilityStatus(eq("CAP_NAVIGATION"), eq("ENABLED"))).thenReturn(true);

        com.airport.ai.task.PlanValidationService validatorService = new com.airport.ai.task.PlanValidationService(devCapMapper);

        Map<String, Object> candidateStep = new java.util.HashMap<>();
        candidateStep.put("stepSeq", 1);
        candidateStep.put("stepGoal", "前往指定区域");
        candidateStep.put("capabilityType", "CAP_NAVIGATION");
        candidateStep.put("inputParams", Map.of("targetLocation", "F2_ZONE_A"));
        candidateStep.put("precondition", "device online");
        candidateStep.put("completionCondition", "routeGenerated=true");
        candidateStep.put("failureHandling", "manual handling");
        candidateStep.put("stepTimeout", 600);

        List<Map<String, Object>> agents = List.of(Map.of(
                "onlineStatus", "ONLINE",
                "capabilities", List.of("CAP_NAVIGATION")
        ));

        // 白名单约束: 禁止前往F2_TEST_GATE；仅允许前往F2_ZONE_A。
        String constraint = "禁止前往F2_TEST_GATE；仅允许前往F2_ZONE_A。";
        com.airport.ai.task.PlanValidationResult result = validatorService.validate(
                List.of(candidateStep), agents, List.of("CAP_NAVIGATION"), "EXT_TEST", 0, 100L, "routeGenerated=true", constraint
        );

        assertEquals("PASS", result.getConstraintCheckResult(), "目标为F2_ZONE_A应符合仅允许前往F2_ZONE_A约束");
        assertTrue(result.isAllPassed(), "全部校验应通过");
    }
}
