package com.airport.ai.auth;

import com.airport.ai.baseline.BaselineTemplate;
import com.airport.ai.baseline.BaselineTemplateMapper;
import com.airport.ai.baseline.BaselineTemplateService;
import com.airport.ai.baseline.dto.CreateBaselineTemplateRequest;
import com.airport.ai.baseline.dto.ParamMapping;
import com.airport.ai.baseline.dto.TemplateStep;
import com.airport.ai.common.XssSanitizer;
import com.airport.ai.config.AccessDeniedHandlerImpl;
import com.airport.ai.config.AuthEntryPoint;
import com.airport.ai.config.CorsOriginSecurityFilter;
import com.airport.ai.config.DeviceTokenAuthenticationFilter;
import com.airport.ai.config.SecurityConfig;
import com.airport.ai.config.TokenAuthenticationFilter;
import com.airport.ai.config.WebMvcAuthorizationConfig;
import com.airport.ai.device.Device;
import com.airport.ai.device.DeviceAdapterClient;
import com.airport.ai.device.DeviceAgentMapper;
import com.airport.ai.device.DeviceAgentMessagingService;
import com.airport.ai.device.DeviceCapability;
import com.airport.ai.device.DeviceCapabilityMapper;
import com.airport.ai.device.DeviceCapabilityService;
import com.airport.ai.device.DeviceController;
import com.airport.ai.device.DeviceEventService;
import com.airport.ai.device.DeviceMapper;
import com.airport.ai.device.DeviceService;
import com.airport.ai.device.dto.CreateDeviceCapabilityRequest;
import com.airport.ai.device.dto.CreateDeviceRequest;
import com.airport.ai.device.dto.UpdateDeviceRequest;
import com.airport.ai.devicetype.CapabilityTemplate;
import com.airport.ai.devicetype.CapabilityTemplateMapper;
import com.airport.ai.devicetype.DeviceTypeCapability;
import com.airport.ai.devicetype.DeviceTypeCapabilityMapper;
import com.airport.ai.devicetype.DeviceTypeCapabilityService;
import com.airport.ai.devicetype.dto.CreateCapabilityTemplateRequest;
import com.airport.ai.devicetype.dto.ParamDefinition;
import com.airport.ai.devicetype.dto.UpdateCapabilityBoundaryRequest;
import com.airport.ai.risk.RiskRule;
import com.airport.ai.risk.RiskRuleController;
import com.airport.ai.risk.RiskRuleMapper;
import com.airport.ai.event.TaskEventService;
import com.airport.ai.planning.GoalUnderstandingService;
import com.airport.ai.task.ContextSnapshotMapper;
import com.airport.ai.task.PlanVersionMapper;
import com.airport.ai.task.SceneParamsPrivacyGuard;
import com.airport.ai.task.TaskCodeGenerator;
import com.airport.ai.task.TaskController;
import com.airport.ai.task.TaskExceptionService;
import com.airport.ai.task.TaskMapper;
import com.airport.ai.task.TaskPlanningOrchestrator;
import com.airport.ai.task.TaskService;
import com.airport.ai.task.TaskStepAssignmentMapper;
import com.airport.ai.taskdef.TaskDefinition;
import com.airport.ai.taskdef.TaskDefinitionController;
import com.airport.ai.taskdef.TaskDefinitionMapper;
import com.airport.ai.taskdef.TaskDefinitionService;
import com.airport.ai.taskdef.dto.CreateTaskDefinitionRequest;
import com.airport.ai.taskdef.dto.UpdateTaskDefinitionRequest;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.context.annotation.Import;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.test.web.servlet.MockMvc;

import java.io.IOException;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Stream;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.ArgumentMatchers.isNull;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.options;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * SRS_NF004 跨域与接口安全攻防加固专项测试（覆盖 SRS_NF004.R01、TC-003.S1~S3、TC-085.S1~S2）：
 * 1. CORS 跨域策略加固：严格白名单放行与未知外部源跨域预检/写请求拦截（403 + 审计留痕）；
 * 2. SQL 注入全面排查与防护：全量 MyBatis Mapper 静态扫描确认 100% 采用 #{} 参数化占位符（0 处 ${} 拼接），
 *    以及 LIKE 通配符转义与注入载荷运行期验证；
 * 3. XSS 与输入净化：任务名称、设备名称/备注、能力描述、模板说明、任务目标、风险规则等文本字段 HTML 转义验证。
 */
@WebMvcTest({UserController.class, DeviceController.class, TaskController.class})
@Import({
        SecurityConfig.class,
        CorsOriginSecurityFilter.class,
        AccessDeniedHandlerImpl.class,
        AuthEntryPoint.class,
        TokenAuthenticationFilter.class,
        DeviceTokenAuthenticationFilter.class,
        com.airport.ai.common.GlobalExceptionHandler.class,
        com.airport.ai.config.PreAuthorizeInterceptor.class,
        WebMvcAuthorizationConfig.class
})
class CorsSqlInjectionAndXssSecurityTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private UserService userService;
    @MockBean
    private AuthService authService;
    @MockBean
    private CurrentUser currentUser;
    @MockBean
    private DeviceService deviceService;
    @MockBean
    private com.airport.ai.device.DeviceCredentialService deviceCredentialService;
    @MockBean
    private TaskService taskService;
    @MockBean
    private TaskEventService taskEventService;
    @MockBean
    private SessionService sessionService;
    @MockBean
    private UserMapper userMapper;
    @MockBean
    private DeviceMapper deviceMapper;
    @MockBean
    private OperationLogService operationLogService;

    private User buildUser(Long id, String username, String role) {
        User user = new User();
        user.setId(id);
        user.setUsername(username);
        user.setRole(role);
        user.setStatus("ACTIVE");
        return user;
    }

    // ==================== 1. CORS 跨域白名单与外部源写请求拦截 ====================

    @Test
    void corsWhitelistedOriginPreflightAndAuthorizedRequestAreAllowed() throws Exception {
        User configAdmin = buildUser(3L, "cfgadmin01", "CONFIG_ADMIN");
        when(sessionService.touchAndGetUserId("tok-cfg")).thenReturn(3L);
        when(userMapper.findById(3L)).thenReturn(Optional.of(configAdmin));
        when(deviceService.list(any(), any(), any(), org.mockito.ArgumentMatchers.anyInt(), org.mockito.ArgumentMatchers.anyInt()))
                .thenReturn(new com.airport.ai.common.PageResult<>(Collections.emptyList(), 0, 1, 20));

        // 1) 白名单源预检 OPTIONS 请求放行并返回规范 CORS 响应头
        mockMvc.perform(options("/api/v1/tasks")
                        .header(HttpHeaders.ORIGIN, "http://localhost:5173")
                        .header(HttpHeaders.ACCESS_CONTROL_REQUEST_METHOD, "POST"))
                .andExpect(status().isOk())
                .andExpect(header().string(HttpHeaders.ACCESS_CONTROL_ALLOW_ORIGIN, "http://localhost:5173"))
                .andExpect(header().string(HttpHeaders.ACCESS_CONTROL_ALLOW_CREDENTIALS, "true"))
                .andExpect(header().string(HttpHeaders.VARY, HttpHeaders.ORIGIN));

        // 2) 127.0.0.1 本地测试端口白名单跨域请求放行
        mockMvc.perform(get("/api/v1/devices")
                        .header(HttpHeaders.ORIGIN, "http://127.0.0.1:15180")
                        .header(HttpHeaders.AUTHORIZATION, "Bearer tok-cfg"))
                .andExpect(status().isOk())
                .andExpect(header().string(HttpHeaders.ACCESS_CONTROL_ALLOW_ORIGIN, "http://127.0.0.1:15180"))
                .andExpect(header().string(HttpHeaders.ACCESS_CONTROL_ALLOW_CREDENTIALS, "true"));
    }

    @Test
    void corsUnknownExternalOriginsOnWriteAndPreflightAreBlockedWith403AndAudited() throws Exception {
        User configAdmin = buildUser(3L, "cfgadmin01", "CONFIG_ADMIN");
        when(sessionService.touchAndGetUserId("tok-cfg")).thenReturn(3L);
        when(userMapper.findById(3L)).thenReturn(Optional.of(configAdmin));

        List<String> maliciousOrigins = List.of(
                "https://evil.example.com",
                "http://attacker.org:8080",
                "http://localhost.evil.com",
                "http://127.0.0.1.attacker.com",
                "null",
                "*",
                "ftp://localhost:5173"
        );

        for (String maliciousOrigin : maliciousOrigins) {
            // 预检请求被直接拦截
            mockMvc.perform(options("/api/v1/devices")
                            .header(HttpHeaders.ORIGIN, maliciousOrigin)
                            .header(HttpHeaders.ACCESS_CONTROL_REQUEST_METHOD, "POST"))
                    .andExpect(status().isForbidden())
                    .andExpect(header().doesNotExist(HttpHeaders.ACCESS_CONTROL_ALLOW_ORIGIN))
                    .andExpect(jsonPath("$.code").value(2003));

            // 携带有效管理员会话令牌的跨域写请求同样被拦截且不触发业务层副作用
            mockMvc.perform(post("/api/v1/devices")
                            .header(HttpHeaders.ORIGIN, maliciousOrigin)
                            .header(HttpHeaders.AUTHORIZATION, "Bearer tok-cfg")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content("{\"deviceCode\":\"DEV-CORS-1\",\"deviceName\":\"测试设备\"}"))
                    .andExpect(status().isForbidden())
                    .andExpect(header().doesNotExist(HttpHeaders.ACCESS_CONTROL_ALLOW_ORIGIN))
                    .andExpect(jsonPath("$.code").value(2003));
        }

        verify(deviceService, never()).create(any(), any());
        verify(operationLogService, org.mockito.Mockito.atLeastOnce()).record(
                eq(3L), eq("cfgadmin01"), eq("CONFIG_ADMIN"),
                eq("ACCESS_DENIED"), eq("/api/v1/devices"), eq("FAILED"), any()
        );
    }

    // ==================== 2. SQL 注入全面排查（全量 Mapper 静态扫描 + 运行期探测） ====================

    @Test
    void allMyBatisXmlAndJavaMappersStrictlyUseParameterizedPlaceholdersWithoutDollarConcatenation() throws IOException {
        Path mapperDir = Path.of("src/main/resources/mapper");
        assertThat(Files.isDirectory(mapperDir)).isTrue();

        Pattern dollarInterpolation = Pattern.compile("\\$\\{[^}]+}");
        Pattern sharpPlaceholder = Pattern.compile("#\\{[^}]+}");

        List<Path> xmlFiles;
        try (Stream<Path> stream = Files.list(mapperDir)) {
            xmlFiles = stream.filter(p -> p.toString().endsWith(".xml")).sorted().toList();
        }
        assertThat(xmlFiles).hasSizeGreaterThanOrEqualTo(20);

        int totalSharpPlaceholders = 0;
        for (Path xmlFile : xmlFiles) {
            String content = Files.readString(xmlFile, StandardCharsets.UTF_8);
            Matcher dollarMatcher = dollarInterpolation.matcher(content);
            assertThat(dollarMatcher.find())
                    .withFailMessage("Mapper XML %s contains forbidden ${} SQL string interpolation", xmlFile.getFileName())
                    .isFalse();

            Matcher sharpMatcher = sharpPlaceholder.matcher(content);
            while (sharpMatcher.find()) {
                totalSharpPlaceholders++;
            }

            if (xmlFile.getFileName().toString().equals("DeviceMapper.xml")
                    || xmlFile.getFileName().toString().equals("TaskMapper.xml")) {
                assertThat(content)
                        .withFailMessage("%s must declare ESCAPE '\\' on LIKE/ILIKE clauses", xmlFile.getFileName())
                        .contains("ESCAPE '\\'");
            }
        }
        assertThat(totalSharpPlaceholders).isGreaterThan(100);

        // 扫描全量 Java Mapper 接口确认无 ${} 拼接
        Path javaRoot = Path.of("src/main/java");
        List<Path> javaMapperFiles;
        try (Stream<Path> walk = Files.walk(javaRoot)) {
            javaMapperFiles = walk.filter(p -> p.toString().endsWith("Mapper.java")).sorted().toList();
        }
        assertThat(javaMapperFiles).hasSizeGreaterThanOrEqualTo(20);
        for (Path javaMapper : javaMapperFiles) {
            String src = Files.readString(javaMapper, StandardCharsets.UTF_8);
            assertThat(dollarInterpolation.matcher(src).find())
                    .withFailMessage("Java Mapper %s contains forbidden ${} SQL interpolation", javaMapper.getFileName())
                    .isFalse();
        }
    }

    @Test
    void deviceAndTaskSearchEscapeLikeWildcardsAndNeutralizeSqlInjectionPayloads() {
        DeviceMapper rawDeviceMapper = mock(DeviceMapper.class);
        when(rawDeviceMapper.searchPaged(any(), any(), any())).thenReturn(Collections.emptyList());
        DeviceService realDeviceService = new DeviceService(
                rawDeviceMapper,
                mock(DeviceAgentMapper.class),
                mock(OperationLogService.class),
                mock(DeviceEventService.class),
                mock(DeviceAdapterClient.class),
                mock(ApplicationEventPublisher.class),
                20,
                mock(DeviceCapabilityMapper.class),
                mock(TaskExceptionService.class),
                "F2_TEST",
                mock(CapabilityTemplateMapper.class)
        );

        String sqliAndWildcardPayload = "100%_test\\name' OR '1'='1'; DROP TABLE devices; --";
        realDeviceService.list("SMART_DISPLAY", "ONLINE", sqliAndWildcardPayload, 1, 10);

        ArgumentCaptor<String> deviceKwCaptor = ArgumentCaptor.forClass(String.class);
        verify(rawDeviceMapper).searchPaged(eq("SMART_DISPLAY"), deviceKwCaptor.capture(), eq("ONLINE"));
        assertThat(deviceKwCaptor.getValue())
                .isEqualTo("100\\%\\_test\\\\name' OR '1'='1'; DROP TABLE devices; --");

        TaskMapper rawTaskMapper = mock(TaskMapper.class);
        when(rawTaskMapper.searchPaged(any(), any(), any(), any(), any(), any())).thenReturn(Collections.emptyList());
        TaskService realTaskService = new TaskService(
                rawTaskMapper,
                mock(PlanVersionMapper.class),
                mock(ContextSnapshotMapper.class),
                mock(DeviceAgentMapper.class),
                mock(GoalUnderstandingService.class),
                mock(TaskCodeGenerator.class),
                mock(TaskEventService.class),
                mock(OperationLogService.class),
                mock(TaskPlanningOrchestrator.class),
                mock(TaskStepAssignmentMapper.class),
                mock(TaskDefinitionService.class),
                mock(DeviceAgentMessagingService.class)
        );

        realTaskService.list("TSK-001' UNION SELECT * FROM users --", null, null,
                "50%_goal\\inject' OR 1=1 --", null, null, 1, 10);

        ArgumentCaptor<String> taskGoalKwCaptor = ArgumentCaptor.forClass(String.class);
        verify(rawTaskMapper).searchPaged(
                eq("TSK-001' UNION SELECT * FROM users --"),
                isNull(),
                isNull(),
                taskGoalKwCaptor.capture(),
                isNull(),
                isNull()
        );
        assertThat(taskGoalKwCaptor.getValue())
                .isEqualTo("50\\%\\_goal\\\\inject' OR 1=1 --");
    }

    // ==================== 3. XSS 与输入净化（HTML 转义与幂等性验证） ====================

    @Test
    void xssSanitizerEscapesHtmlTagsAndScriptsIdempotently() {
        String scriptPayload = "<script>alert('xss')</script>";
        String escaped = XssSanitizer.escapeHtml(scriptPayload);
        assertThat(escaped)
                .doesNotContain("<script>", "</script>")
                .contains("&lt;script&gt;", "&lt;/script&gt;");
        // 幂等性：重复调用不会产生双重转义 &amp;lt;
        assertThat(XssSanitizer.escapeHtml(escaped)).isEqualTo(escaped);

        String imgOnError = "<img src=x onerror=\"alert(1)\">设备描述";
        assertThat(XssSanitizer.escapeHtml(imgOnError))
                .doesNotContain("<img")
                .contains("&lt;img", "&quot;alert(1)&quot;&gt;");

        String jsProtocol = "javascript:alert(document.cookie)";
        assertThat(XssSanitizer.escapeHtml(jsProtocol))
                .doesNotContain("javascript:")
                .contains("javascript&#58;");

        // sanitizeRichText 保留普通业务箭头 "A->B"，但对 HTML 标签执行转义
        assertThat(XssSanitizer.sanitizeRichText("区域A->区域B正常引导")).isEqualTo("区域A->区域B正常引导");
        assertThat(XssSanitizer.sanitizeRichText("引导<svg onload=alert(1)>任务"))
                .doesNotContain("<svg")
                .contains("&lt;svg onload=alert(1)&gt;");
    }

    @Test
    void taskNameDeviceDescriptionAndCapabilityTextFieldsAreHtmlEscapedInServices() {
        User cfgAdmin = buildUser(3L, "cfgadmin01", "CONFIG_ADMIN");

        // 1) TaskDefinitionService: taskName, goalTemplate, constraintDescription, completionCondition
        TaskDefinitionMapper tdMapper = mock(TaskDefinitionMapper.class);
        DeviceCapabilityMapper capMapper = mock(DeviceCapabilityMapper.class);
        when(capMapper.existsByCapabilityTypeAndCapabilityStatus("CAP_INFO_DISPLAY", "ENABLED")).thenReturn(true);
        TaskDefinitionService tdService = new TaskDefinitionService(tdMapper, capMapper, mock(OperationLogService.class));

        CreateTaskDefinitionRequest createTd = new CreateTaskDefinitionRequest();
        createTd.setTaskName("异常引导<script>alert(1)</script>");
        createTd.setGoalTemplate("目标模板<img src=x onerror=alert(1)>");
        ParamDefinition param = new ParamDefinition();
        param.setName("flightNo");
        param.setType("String");
        param.setRequired(true);
        createTd.setSceneParams(List.of(param));
        createTd.setAvailableCapabilityTypes(List.of("CAP_INFO_DISPLAY"));
        createTd.setConstraintDescription("约束<svg onload=alert(2)>");
        createTd.setCompletionCondition("完成条件<b>OK</b>");

        TaskDefinition savedTd = tdService.create(createTd, cfgAdmin);
        assertThat(savedTd.getTaskName()).isEqualTo("异常引导&lt;script&gt;alert(1)&lt;/script&gt;");
        assertThat(savedTd.getGoalTemplate()).isEqualTo("目标模板&lt;img src=x onerror=alert(1)&gt;");
        assertThat(savedTd.getConstraintDescription()).isEqualTo("约束&lt;svg onload=alert(2)&gt;");
        assertThat(savedTd.getCompletionCondition()).isEqualTo("完成条件&lt;b&gt;OK&lt;/b&gt;");

        when(tdMapper.findById(10L)).thenReturn(Optional.of(savedTd));
        UpdateTaskDefinitionRequest updateTd = new UpdateTaskDefinitionRequest();
        updateTd.setGoalTemplate("更新模板<iframe src=\"javascript:alert(1)\"></iframe>");
        updateTd.setSceneParams(List.of(param));
        updateTd.setAvailableCapabilityTypes(List.of("CAP_INFO_DISPLAY"));
        updateTd.setConstraintDescription("更新约束<script>evil()</script>");
        updateTd.setCompletionCondition("更新完成条件<a href=\"javascript:alert(1)\">link</a>");
        TaskDefinition updatedTd = tdService.update(10L, updateTd, cfgAdmin);
        assertThat(updatedTd.getGoalTemplate()).doesNotContain("<iframe").doesNotContain("javascript:");
        assertThat(updatedTd.getConstraintDescription()).doesNotContain("<script>");

        // 2) DeviceService: deviceName & remark
        DeviceMapper rawDeviceMapper = mock(DeviceMapper.class);
        DeviceService realDeviceService = new DeviceService(
                rawDeviceMapper,
                mock(DeviceAgentMapper.class),
                mock(OperationLogService.class),
                mock(DeviceEventService.class),
                mock(DeviceAdapterClient.class),
                mock(ApplicationEventPublisher.class),
                20,
                capMapper,
                mock(TaskExceptionService.class),
                "F2_TEST",
                mock(CapabilityTemplateMapper.class)
        );
        CreateDeviceRequest createDev = new CreateDeviceRequest();
        createDev.setDeviceCode("DEV-XSS-01");
        createDev.setDeviceName("航显屏<script>alert('dev')</script>");
        createDev.setDeviceTypeCode("SMART_DISPLAY");
        createDev.setIsSimulator(false);
        createDev.setAreaCode("F2_TEST");
        createDev.setPositionX(BigDecimal.TEN);
        createDev.setPositionY(BigDecimal.TEN);
        createDev.setAccessEndpoint("http://127.0.0.1:8091");
        createDev.setAccessCredentialRef("CRED-01");
        createDev.setStatusReportInterval(15);
        createDev.setRemark("设备描述<img src=x onerror=alert('remark')>");

        Device savedDev = realDeviceService.create(createDev, cfgAdmin);
        assertThat(savedDev.getDeviceName()).isEqualTo("航显屏&lt;script&gt;alert(&#39;dev&#39;)&lt;/script&gt;");
        assertThat(savedDev.getRemark()).isEqualTo("设备描述&lt;img src=x onerror=alert(&#39;remark&#39;)&gt;");

        savedDev.setId(99L);
        when(rawDeviceMapper.findById(99L)).thenReturn(Optional.of(savedDev));
        UpdateDeviceRequest updateDev = new UpdateDeviceRequest();
        updateDev.setDeviceName("航显屏更新<svg onload=alert(1)>");
        updateDev.setAreaCode("F2_TEST");
        updateDev.setPositionX(BigDecimal.TEN);
        updateDev.setPositionY(BigDecimal.TEN);
        updateDev.setAccessEndpoint("http://127.0.0.1:8091");
        updateDev.setStatusReportInterval(15);
        updateDev.setRemark("更新备注<body onload=alert(2)>");
        Device updatedDev = realDeviceService.update(99L, updateDev, cfgAdmin);
        assertThat(updatedDev.getDeviceName()).doesNotContain("<svg");
        assertThat(updatedDev.getRemark()).doesNotContain("<body");

        // 3) DeviceCapabilityService & DeviceTypeCapabilityService & BaselineTemplateService
        DeviceTypeCapabilityService dtService = mock(DeviceTypeCapabilityService.class);
        when(dtService.isCapabilityTypeSupported(any(), any(), eq("CAP_INFO_DISPLAY"))).thenReturn(true);
        DeviceCapabilityService capService = new DeviceCapabilityService(
                capMapper, rawDeviceMapper, mock(CapabilityTemplateMapper.class),
                dtService, mock(OperationLogService.class), mock(DeviceAgentMapper.class),
                mock(DeviceAgentMessagingService.class)
        );
        CreateDeviceCapabilityRequest createCap = new CreateDeviceCapabilityRequest();
        createCap.setCapabilityCode("CAP_XSS");
        createCap.setCapabilityName("信息发布<script>1</script>");
        createCap.setCapabilityType("CAP_INFO_DISPLAY");
        createCap.setInputParams(List.of(param));
        createCap.setOutputParams(List.of(param));
        createCap.setApplicableCondition("条件<img src=x onerror=1>");
        createCap.setCapabilityDescription("能力描述<svg onload=1>");
        DeviceCapability savedCap = capService.create(99L, createCap, cfgAdmin);
        assertThat(savedCap.getCapabilityName()).doesNotContain("<script>");
        assertThat(savedCap.getCapabilityDescription()).doesNotContain("<svg");
        assertThat(savedCap.getApplicableConditions()).doesNotContain("<img");

        // 4) SceneParamsPrivacyGuard (TaskGoal & SceneParams) + UserService + RiskRuleController
        String dirtyGoal = "引导航班CA1234旅客<script>fetch('https://evil.com')</script>前往登机口";
        assertThat(SceneParamsPrivacyGuard.sanitizeGoal(dirtyGoal))
                .doesNotContain("<script>")
                .contains("&lt;script&gt;");
        Map<String, Object> dirtyScene = Map.of("noticeText", "<img src=x onerror=alert(1)>登机口变更");
        Map<String, Object> cleanScene = SceneParamsPrivacyGuard.sanitize(dirtyScene);
        assertThat(String.valueOf(cleanScene.get("noticeText")))
                .doesNotContain("<img")
                .contains("&lt;img");

        UserMapper uMapper = mock(UserMapper.class);
        UserService uService = new UserService(uMapper, new BCryptPasswordEncoder(), mock(OperationLogService.class));
        com.airport.ai.auth.dto.CreateUserRequest createUserReq = new com.airport.ai.auth.dto.CreateUserRequest();
        createUserReq.setUsername("op_xss");
        createUserReq.setPassword("Pass1234!");
        createUserReq.setRealName("张操作<script>alert(1)</script>");
        createUserReq.setRole("OPERATOR");
        createUserReq.setContact("010-8888<img onerror=alert(1)>");
        User createdUser = uService.create(createUserReq, buildUser(1L, "admin", "SYSTEM_ADMIN"));
        assertThat(createdUser.getRealName()).doesNotContain("<script>");
        assertThat(createdUser.getContact()).doesNotContain("<img");

        RiskRuleMapper rrMapper = mock(RiskRuleMapper.class);
        CurrentUser cu = mock(CurrentUser.class);
        when(cu.get()).thenReturn(cfgAdmin);
        RiskRuleController rrController = new RiskRuleController(rrMapper, mock(OperationLogService.class), cu);
        RiskRule createdRule = rrController.create(Map.of(
                "ruleCode", "RULE_XSS_01",
                "ruleContent", "高风险规则<script>alert('rule')</script>",
                "enabled", true
        )).getData();
        assertThat(createdRule.getRuleContent())
                .doesNotContain("<script>")
                .contains("&lt;script&gt;");
    }
}
