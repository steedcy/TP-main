package com.airport.ai.auth;

import com.airport.ai.auth.dto.LoginRequest;
import com.airport.ai.auth.dto.LoginResponse;
import com.airport.ai.common.BusinessException;
import com.airport.ai.common.ErrorCode;
import com.airport.ai.common.GlobalExceptionHandler;
import com.airport.ai.device.DeviceAgent;
import com.airport.ai.device.DeviceAgentMapper;
import com.airport.ai.device.DeviceAgentMessagingService;
import com.airport.ai.device.DeviceCapabilityMapper;
import com.airport.ai.device.DeviceEvent;
import com.airport.ai.device.DeviceEventMapper;
import com.airport.ai.device.DeviceEventService;
import com.airport.ai.device.DeviceMapper;
import com.airport.ai.event.OperationLog;
import com.airport.ai.event.OperationLogController;
import com.airport.ai.event.OperationLogMapper;
import com.airport.ai.event.TaskEvent;
import com.airport.ai.event.TaskEventMapper;
import com.airport.ai.event.TaskEventService;
import com.airport.ai.planning.GoalUnderstandingResponse;
import com.airport.ai.planning.GoalUnderstandingService;
import com.airport.ai.task.ContextSnapshotMapper;
import com.airport.ai.task.PlanVersion;
import com.airport.ai.task.PlanVersionMapper;
import com.airport.ai.task.StepParameterResolver;
import com.airport.ai.task.Task;
import com.airport.ai.task.TaskCodeGenerator;
import com.airport.ai.task.TaskController;
import com.airport.ai.task.TaskExceptionService;
import com.airport.ai.task.TaskExecutionOrchestrator;
import com.airport.ai.task.TaskMapper;
import com.airport.ai.task.TaskPlanningOrchestrator;
import com.airport.ai.task.TaskService;
import com.airport.ai.task.TaskStatus;
import com.airport.ai.task.TaskStepAssignment;
import com.airport.ai.task.TaskStepAssignmentMapper;
import com.airport.ai.task.dto.SubmitTaskRequest;
import com.airport.ai.taskdef.TaskDefinitionService;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.atomic.AtomicLong;
import java.util.regex.Pattern;

import static org.assertj.core.api.Assertions.assertThat;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

/**
 * SRS_NF016 (SRS_NF016.R01 & TC-002.S1~S4): 审计日志完整性与防篡改专项验证
 * 1. 审计日志与过程追溯接口绝对只读，全面拦截 PUT/DELETE/PATCH/POST 修改或删除操作（返回 405 + Allow: GET，数据零改动）；
 * 2. 完善长字段（如复杂嵌套 JSON、10KB+ 长错误描述、Unicode/Emoji/特殊字符）落库机制，杜绝乱码与意外截断；
 * 3. 确保关键业务生命周期（创建、调度、终止、接管、锁定、解锁）100% 留痕且脱敏合规。
 */
class AuditLogIntegrityAndTamperResistanceNF016Test {

    private static final ObjectMapper MAPPER = new ObjectMapper().findAndRegisterModules();

    private final List<OperationLog> persistedLogs = new ArrayList<>();
    private final List<TaskEvent> persistedTaskEvents = new ArrayList<>();
    private final List<DeviceEvent> persistedDeviceEvents = new ArrayList<>();
    private final AtomicLong idGenerator = new AtomicLong(1000L);

    private OperationLogMapper operationLogMapper;
    private TaskEventMapper taskEventMapper;
    private DeviceEventMapper deviceEventMapper;
    private OperationLogService operationLogService;
    private TaskEventService taskEventService;
    private DeviceEventService deviceEventService;

    @BeforeEach
    void setUp() {
        persistedLogs.clear();
        persistedTaskEvents.clear();
        persistedDeviceEvents.clear();

        operationLogMapper = mock(OperationLogMapper.class);
        when(operationLogMapper.insert(any(OperationLog.class))).thenAnswer(inv -> {
            OperationLog log = inv.getArgument(0);
            log.setId(idGenerator.incrementAndGet());
            persistedLogs.add(log);
            return 1;
        });
        when(operationLogMapper.findById(anyLong())).thenAnswer(inv -> {
            Long id = inv.getArgument(0);
            return persistedLogs.stream().filter(l -> id.equals(l.getId())).findFirst().orElse(null);
        });
        when(operationLogMapper.searchPaged(any(), any(), any(), any(), any())).thenAnswer(inv -> {
            String u = inv.getArgument(0);
            String type = inv.getArgument(1);
            String res = inv.getArgument(2);
            return persistedLogs.stream()
                    .filter(l -> u == null || u.equals(l.getUsername()))
                    .filter(l -> type == null || type.equals(l.getOperationType()))
                    .filter(l -> res == null || res.equals(l.getOperationResult()))
                    .toList();
        });

        taskEventMapper = mock(TaskEventMapper.class);
        when(taskEventMapper.insert(any(TaskEvent.class))).thenAnswer(inv -> {
            TaskEvent ev = inv.getArgument(0);
            ev.setId(idGenerator.incrementAndGet());
            persistedTaskEvents.add(ev);
            return 1;
        });
        when(taskEventMapper.findByTaskIdOrderByOccurredAtAsc(anyLong())).thenAnswer(inv -> {
            Long taskId = inv.getArgument(0);
            return persistedTaskEvents.stream().filter(e -> taskId.equals(e.getTaskId())).toList();
        });

        deviceEventMapper = mock(DeviceEventMapper.class);
        when(deviceEventMapper.insert(any(DeviceEvent.class))).thenAnswer(inv -> {
            DeviceEvent ev = inv.getArgument(0);
            ev.setId(idGenerator.incrementAndGet());
            persistedDeviceEvents.add(ev);
            return 1;
        });

        operationLogService = new OperationLogService(operationLogMapper);
        taskEventService = new TaskEventService(taskEventMapper);
        deviceEventService = new DeviceEventService(deviceEventMapper);
    }

    // =========================================================================
    // 1. 审计日志与事件接口绝对只读，全面拦截 PUT / DELETE / PATCH 修改或删除操作
    // =========================================================================

    @Test
    @DisplayName("SRS_NF016.R01: 审计日志与任务事件集合及单条路径全面拦截 PUT/DELETE/PATCH，返回 405 + Allow: GET 且数据零篡改")
    void auditLogAndTaskEventEndpointsStrictlyRejectPutDeletePatchWith405AndPreserveData() throws Exception {
        // 先写入一条真实操作日志和一条任务事件
        User sysAdmin = new User();
        sysAdmin.setId(1L);
        sysAdmin.setUsername("sysadmin");
        sysAdmin.setRole("SYSTEM_ADMIN");

        operationLogService.record(1L, "sysadmin", "SYSTEM_ADMIN", "USER_CREATE", "operator01", "SUCCESS", "10.0.0.1",
                Map.of("action", "CREATE", "after", Map.of("username", "operator01", "role", "OPERATOR")));
        OperationLog seededLog = persistedLogs.get(0);
        Long logId = seededLog.getId();
        String originalLogDetail = seededLog.getDetail();

        TaskEvent seededEvent = taskEventService.append(19L, "GOAL_SUBMITTED", "OPERATOR", "NORMAL_GOAL_SUBMITTED",
                "{\"summary\":\"提交任务目标\",\"taskCode\":\"TASK-20261110-0001\"}");
        Long eventId = seededEvent.getId();
        String originalEventDetail = seededEvent.getDetail();

        CurrentUser currentUser = mock(CurrentUser.class);
        when(currentUser.get()).thenReturn(sysAdmin);

        OperationLogController logController = new OperationLogController(operationLogService, currentUser);
        TaskController taskController = new TaskController(mock(TaskService.class), taskEventService, currentUser);
        MockMvc mvc = MockMvcBuilders.standaloneSetup(logController, taskController)
                .setControllerAdvice(new GlobalExceptionHandler(operationLogService))
                .build();

        String[] writeMethods = {"PUT", "DELETE", "PATCH"};
        String[] protectedPaths = {
                "/api/v1/operation-logs",
                "/api/v1/operation-logs/" + logId,
                "/api/v1/tasks/19/events",
                "/api/v1/tasks/19/events/" + eventId
        };

        for (String path : protectedPaths) {
            for (String method : writeMethods) {
                mvc.perform(request(org.springframework.http.HttpMethod.valueOf(method), path)
                                .contentType(MediaType.APPLICATION_JSON)
                                .content("{\"operationResult\":\"TAMPERED\",\"detail\":\"{}\"}"))
                        .andExpect(status().isMethodNotAllowed())
                        .andExpect(header().string(HttpHeaders.ALLOW, org.hamcrest.Matchers.containsString("GET")))
                        .andExpect(jsonPath("$.code").value(ErrorCode.METHOD_NOT_ALLOWED.getCode()))
                        .andExpect(jsonPath("$.message").value(org.hamcrest.Matchers.containsString("记录不可修改或删除")))
                        .andExpect(jsonPath("$.path").value(path))
                        .andExpect(jsonPath("$.method").value(method));
            }
        }

        // 验证只读查询仍然正常返回原始未篡改记录
        mvc.perform(get("/api/v1/operation-logs/" + logId))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.id").value(logId))
                .andExpect(jsonPath("$.data.operationTarget").value("operator01"));

        mvc.perform(get("/api/v1/tasks/19/events/" + eventId))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.id").value(eventId))
                .andExpect(jsonPath("$.data.eventType").value("GOAL_SUBMITTED"));

        // 验证非系统管理员尝试按ID读取他人操作记录时被 403 拦截并记入 ACCESS_DENIED 审计
        User operator = new User();
        operator.setId(2L);
        operator.setUsername("operator01");
        operator.setRole("OPERATOR");
        when(currentUser.get()).thenReturn(operator);
        SecurityContextHolder.getContext().setAuthentication(
                new UsernamePasswordAuthenticationToken(operator, null, List.of(new SimpleGrantedAuthority("ROLE_OPERATOR"))));
        try {
            mvc.perform(get("/api/v1/operation-logs/" + logId))
                    .andExpect(status().isForbidden())
                    .andExpect(jsonPath("$.code").value(ErrorCode.FORBIDDEN.getCode()));
        } finally {
            SecurityContextHolder.clearContext();
        }

        // 原始记录条数与内容零篡改（仅新增了一条越权拦截审计）
        assertEquals(originalLogDetail, seededLog.getDetail());
        assertEquals(originalEventDetail, seededEvent.getDetail());
        assertEquals(1, persistedTaskEvents.size());
        assertTrue(persistedLogs.stream().anyMatch(l -> "ACCESS_DENIED".equals(l.getOperationType())));
    }

    @Test
    @DisplayName("SRS_NF016.R01: 静态扫描确认 OperationLog / TaskEvent / DeviceEvent 的 Mapper 接口与 XML 零 UPDATE/DELETE 声明")
    void auditAndEventMappersContainZeroUpdateOrDeleteStatements() throws Exception {
        List<Path> mapperXmls = List.of(
                Path.of("src/main/resources/mapper/OperationLogMapper.xml"),
                Path.of("src/main/resources/mapper/TaskEventMapper.xml"),
                Path.of("src/main/resources/mapper/DeviceEventMapper.xml")
        );
        Pattern forbiddenSql = Pattern.compile("(?i)<\\s*(update|delete)\\b|\\b(UPDATE\\s+operation_logs|DELETE\\s+FROM\\s+operation_logs|UPDATE\\s+task_events|DELETE\\s+FROM\\s+task_events|UPDATE\\s+device_events|DELETE\\s+FROM\\s+device_events)\\b");
        for (Path xml : mapperXmls) {
            String content = Files.readString(xml, StandardCharsets.UTF_8);
            assertFalse(forbiddenSql.matcher(content).find(), "审计/事件 Mapper XML 严禁包含 UPDATE 或 DELETE: " + xml);
        }

        List<Class<?>> mapperInterfaces = List.of(OperationLogMapper.class, TaskEventMapper.class, DeviceEventMapper.class);
        for (Class<?> iface : mapperInterfaces) {
            for (var method : iface.getDeclaredMethods()) {
                String name = method.getName().toLowerCase();
                assertFalse(name.startsWith("update") || name.startsWith("delete") || name.startsWith("remove"),
                        "审计/事件 Mapper 接口严禁暴露修改或删除方法: " + iface.getSimpleName() + "." + method.getName());
            }
        }
    }

    // =========================================================================
    // 2. 完善日志长字段（如复杂 JSON、长错误描述）落库机制，杜绝乱码与意外截断
    // =========================================================================

    @Test
    @DisplayName("SRS_NF016.R01: 12KB+ 超长错误描述、多层嵌套不可变 JSON、Emoji 代理对与特殊字符落库零截断、零乱码且脱敏完整")
    void longErrorDescriptionsAndComplexNestedJsonPersistIntactWithoutTruncationOrGarbling() throws Exception {
        // 构造 12KB+ 的含中文、英文、Emoji（UTF-16 代理对）、换行、引号、斜杠的长错误描述
        String unitError = "【规划监督与设备协同异常堆栈】Step-03 航显信道响应超时 (ERR_TIMEOUT_504) 🚀✈️🧳 -> 重试第1次失败; line=\"quoted\\value\"\n";
        StringBuilder longErrorBuilder = new StringBuilder(14000);
        for (int i = 0; i < 160; i++) {
            longErrorBuilder.append("Frame#").append(i).append(": ").append(unitError);
        }
        String twelveKbError = longErrorBuilder.toString();
        assertThat(twelveKbError.length()).isGreaterThan(12000);

        // 构造超过 500 字符的长操作目标与含 Emoji 边界的超长用户名/原因码
        String longTarget = "TASK-20261110-9999 -> 批量跨区域协同调度目标（" + "T2航站楼北指廊远机位登机口G88_".repeat(30) + "）";
        assertThat(longTarget.length()).isGreaterThan(500);
        String longUsernameWithEmoji = "operator_🚀_" + "a".repeat(300) + "✈️";

        // 构造包含不可变 Map.of、List.of、数组、Java 8 LocalDateTime、敏感凭据、旅客隐私字段的复杂嵌套结构
        Map<String, Object> complexDetail = new LinkedHashMap<>();
        complexDetail.put("action", "COMPLEX_FAILURE_DIAGNOSIS");
        complexDetail.put("occurredAt", LocalDateTime.of(2026, 11, 10, 23, 0, 0));
        complexDetail.put("longErrorDescription", twelveKbError);
        complexDetail.put("immutableNestedMap", Map.of(
                "subAction", "FALLBACK_TO_BASELINE",
                "deviceToken", "secret-device-token-99887766",
                "deepList", List.of(
                        Map.of("stepSeq", 1, "status", "COMPLETED", "apiKey", "sk-secret-api-key-123456"),
                        Map.of("stepSeq", 2, "status", "FAILED", "errorDetail", twelveKbError)
                )
        ));
        complexDetail.put("arrayPayload", new Object[]{
                Map.of("channel", "FLIGHT_DISPLAY", "password", "PlaintextPass#2026"),
                "normal-string-element-中文测试-🧳"
        });
        complexDetail.put("passengerName", "张三"); // 应被隐私卫士自动剔除

        operationLogService.record(99L, longUsernameWithEmoji, "OPERATOR", "TASK_MANUAL_ACTION",
                longTarget, "FAILED", "192.168.10.88", complexDetail);

        assertEquals(1, persistedLogs.size());
        OperationLog savedLog = persistedLogs.get(0);

        // 1) 验证长用户名按代码点安全截断至 256 个代码点，且末尾不会产生半个代理对（\uD800-\uDFFF 孤立字符）
        assertNotNull(savedLog.getUsername());
        assertThat(savedLog.getUsername().codePointCount(0, savedLog.getUsername().length())).isLessThanOrEqualTo(256);
        assertFalse(containsIsolatedSurrogate(savedLog.getUsername()), "截断不得破坏 UTF-16 Emoji 代理对");
        assertFalse(savedLog.getUsername().contains("\uFFFD"), "不得出现乱码替换符");

        // 2) 验证长 operation_target (TEXT) 完整保留，未被 128 字符截断
        assertEquals(longTarget, savedLog.getOperationTarget());

        // 3) 验证 detail JSON 非空、可完整反序列化、12KB+ 错误描述完整无截断且无乱码
        assertNotNull(savedLog.getDetail(), "复杂嵌套 JSON 落库不得因不可变集合或时间类型返回 null");
        JsonNode root = MAPPER.readTree(savedLog.getDetail());
        assertEquals(twelveKbError, root.get("longErrorDescription").asText(), "12KB+ 长错误描述必须 100% 完整落库无截断");
        assertEquals(twelveKbError,
                root.get("immutableNestedMap").get("deepList").get(1).get("errorDetail").asText(),
                "嵌套列表中的 12KB+ 长错误描述同样完整无截断");
        assertEquals("normal-string-element-中文测试-🧳", root.get("arrayPayload").get(1).asText());

        // 4) 验证嵌套不可变 Map/List/Array 中的敏感凭据全部被掩码，旅客身份字段被剥离
        assertFalse(savedLog.getDetail().contains("secret-device-token-99887766"));
        assertFalse(savedLog.getDetail().contains("sk-secret-api-key-123456"));
        assertFalse(savedLog.getDetail().contains("PlaintextPass#2026"));
        assertFalse(savedLog.getDetail().contains("张三"));
        assertNull(root.get("passengerName"));

        // 5) 验证 TaskEvent 与 DeviceEvent 对 12KB+ 结构化 JSON 与长错误描述同样零截断、零乱码
        String taskEventJson = MAPPER.writeValueAsString(Map.of(
                "summary", "任务执行异常恢复失败: " + twelveKbError,
                "errorDescription", twelveKbError,
                "accessToken", "bearer-secret-xyz987"
        ));
        TaskEvent savedTaskEvent = taskEventService.append(88L, "STEP_FAILED", "SYSTEM",
                "ERR_LONG_REASON_" + "X".repeat(300), taskEventJson);
        assertNotNull(savedTaskEvent.getDetail());
        JsonNode eventNode = MAPPER.readTree(savedTaskEvent.getDetail());
        assertEquals(twelveKbError, eventNode.get("errorDescription").asText());
        assertFalse(savedTaskEvent.getDetail().contains("bearer-secret-xyz987"), "TaskEvent 内嵌 JSON 中的敏感凭据也须脱敏");
        assertThat(savedTaskEvent.getReasonCode().length()).isLessThanOrEqualTo(256);

        DeviceEvent savedDeviceEvent = deviceEventService.appendMessage(77L, "EXECUTION_FEEDBACK",
                "CMD-001", "FAILED", "ERR_DEVICE_LONG_" + "Y".repeat(300), twelveKbError);
        assertEquals(twelveKbError, savedDeviceEvent.getDetailSummary(), "DeviceEvent 长错误描述必须完整保留");
        assertThat(savedDeviceEvent.getReasonCode().length()).isLessThanOrEqualTo(256);
    }

    // =========================================================================
    // 3. 关键业务生命周期（创建、调度、终止、接管、锁定、解锁）100% 留痕与 TC-002.S1~S4
    // =========================================================================

    @Test
    @DisplayName("TC-002.S1~S4 & SRS_NF016.R01: 认证失败统一提示、第3次错密锁定、管理员解锁、跨账号计数隔离与故障恢复全链路留痕")
    void authenticationLockoutUnlockAndRecoveryLifecycleFullAuditTrail() throws Exception {
        UserMapper userMapper = mock(UserMapper.class);
        PasswordEncoder passwordEncoder = new BCryptPasswordEncoder();
        SessionService sessionService = mock(SessionService.class);
        when(sessionService.createSession(anyLong())).thenReturn("session-token-user-a");
        when(sessionService.getIdleTimeoutSeconds()).thenReturn(1800L);

        AuthService authService = new AuthService(userMapper, passwordEncoder, sessionService, operationLogService, 3);

        User userA = new User();
        userA.setId(10L);
        userA.setUsername("operator_a");
        userA.setRealName("操作员A");
        userA.setRole("OPERATOR");
        userA.setStatus("ACTIVE");
        userA.setPasswordHash(passwordEncoder.encode("CorrectPass#123"));
        userA.setFailedLoginAttempts(0);

        User userB = new User();
        userB.setId(11L);
        userB.setUsername("operator_b");
        userB.setRealName("操作员B");
        userB.setRole("OPERATOR");
        userB.setStatus("ACTIVE");
        userB.setPasswordHash(passwordEncoder.encode("CorrectPassB#123"));
        userB.setFailedLoginAttempts(0);

        User inactiveUser = new User();
        inactiveUser.setId(12L);
        inactiveUser.setUsername("inactive_op");
        inactiveUser.setRole("OPERATOR");
        inactiveUser.setStatus("INACTIVE");
        inactiveUser.setPasswordHash(passwordEncoder.encode("CorrectPassC#123"));
        inactiveUser.setFailedLoginAttempts(0);

        User sysAdmin = new User();
        sysAdmin.setId(1L);
        sysAdmin.setUsername("sysadmin");
        sysAdmin.setRole("SYSTEM_ADMIN");

        when(userMapper.findByUsername("operator_a")).thenReturn(Optional.of(userA));
        when(userMapper.findByUsername("operator_b")).thenReturn(Optional.of(userB));
        when(userMapper.findByUsername("inactive_op")).thenReturn(Optional.of(inactiveUser));
        when(userMapper.findByUsername("ghost_user")).thenReturn(Optional.empty());
        when(userMapper.findById(10L)).thenReturn(Optional.of(userA));

        // --- TC-002.S1: 不存在账号、停用账号、账号B错密均返回统一提示“账号或密码错误”，不建会话，不污染账号A计数 ---
        BusinessException exGhost = assertThrows(BusinessException.class,
                () -> authService.login(loginReq("ghost_user", "AnyPass#1"), "10.10.1.1"));
        assertEquals("账号或密码错误", exGhost.getMessage());

        BusinessException exInactive = assertThrows(BusinessException.class,
                () -> authService.login(loginReq("inactive_op", "CorrectPassC#123"), "10.10.1.2"));
        assertEquals("账号或密码错误", exInactive.getMessage());

        BusinessException exUserB = assertThrows(BusinessException.class,
                () -> authService.login(loginReq("operator_b", "WrongPassB#1"), "10.10.1.3"));
        assertEquals("账号或密码错误", exUserB.getMessage());

        verify(sessionService, never()).createSession(anyLong());
        assertEquals(0, userA.getFailedLoginAttempts(), "其他账号失败不得污染账号A的失败计数");
        assertEquals(1, userB.getFailedLoginAttempts());
        assertEquals(3, persistedLogs.size());
        assertTrue(persistedLogs.stream().allMatch(l -> "LOGIN".equals(l.getOperationType()) && "FAILED".equals(l.getOperationResult())));

        // --- TC-002.S2: 账号A第1、2次错密不锁定；第3次错密立即锁定并写独立 ACCOUNT_LOCKED 审计；锁定后输入正确密码仍失败 ---
        for (int attempt = 1; attempt <= 2; attempt++) {
            BusinessException ex = assertThrows(BusinessException.class,
                    () -> authService.login(loginReq("operator_a", "WrongPass#" + UUID_SUFFIX), "10.10.2.1"));
            assertEquals("账号或密码错误", ex.getMessage());
            assertEquals("ACTIVE", userA.getStatus(), "第" + attempt + "次失败不应提前锁定");
            assertEquals(attempt, userA.getFailedLoginAttempts());
        }
        assertFalse(persistedLogs.stream().anyMatch(l -> "ACCOUNT_LOCKED".equals(l.getOperationType())));

        // 第3次错密触发锁定
        BusinessException exLock = assertThrows(BusinessException.class,
                () -> authService.login(loginReq("operator_a", "WrongPass#3"), "10.10.2.1"));
        assertEquals("账号或密码错误", exLock.getMessage());
        assertEquals("LOCKED", userA.getStatus());
        assertEquals(3, userA.getFailedLoginAttempts());
        assertNotNull(userA.getLockedAt());

        OperationLog lockLog = persistedLogs.stream()
                .filter(l -> "ACCOUNT_LOCKED".equals(l.getOperationType()))
                .findFirst()
                .orElseThrow(() -> new AssertionError("必须写入独立 ACCOUNT_LOCKED 审计日志"));
        assertEquals("operator_a", lockLog.getUsername());
        assertEquals("operator_a", lockLog.getOperationTarget());
        assertEquals("10.10.2.1", lockLog.getSourceIp());
        JsonNode lockDetail = MAPPER.readTree(lockLog.getDetail());
        assertEquals("LOCK", lockDetail.get("action").asText());
        assertEquals(3, lockDetail.get("failedAttempts").asInt());
        assertEquals("ACTIVE", lockDetail.get("before").get("status").asText());
        assertEquals("LOCKED", lockDetail.get("after").get("status").asText());

        // 锁定状态下即使输入正确密码仍被拒绝且不建会话
        BusinessException exWhileLocked = assertThrows(BusinessException.class,
                () -> authService.login(loginReq("operator_a", "CorrectPass#123"), "10.10.2.2"));
        assertEquals("账号或密码错误", exWhileLocked.getMessage());
        verify(sessionService, never()).createSession(anyLong());

        // --- TC-002.S3: 管理员解锁账号A（记录 MANUAL_HANDLING 含 before/after），随后2次错密+1次正确登录清零计数，再1次错密不锁定 ---
        authService.unlock(10L, sysAdmin);
        assertEquals("ACTIVE", userA.getStatus());
        assertEquals(0, userA.getFailedLoginAttempts());
        assertNull(userA.getLockedAt());
        assertNull(userA.getLockedReason());

        OperationLog unlockLog = persistedLogs.stream()
                .filter(l -> "MANUAL_HANDLING".equals(l.getOperationType()))
                .findFirst()
                .orElseThrow(() -> new AssertionError("解锁必须写入 MANUAL_HANDLING 审计日志"));
        assertEquals("sysadmin", unlockLog.getUsername());
        assertEquals("operator_a", unlockLog.getOperationTarget());
        JsonNode unlockDetail = MAPPER.readTree(unlockLog.getDetail());
        assertEquals("UNLOCK", unlockDetail.get("action").asText());
        assertEquals("LOCKED", unlockDetail.get("before").get("status").asText());
        assertEquals(3, unlockDetail.get("before").get("failedLoginAttempts").asInt());
        assertEquals("ACTIVE", unlockDetail.get("after").get("status").asText());
        assertEquals(0, unlockDetail.get("after").get("failedLoginAttempts").asInt());

        // 连续2次错密 -> 1次正确密码登录成功（计数清零） -> 再1次错密不触发锁定
        assertThrows(BusinessException.class, () -> authService.login(loginReq("operator_a", "WrongAgain#1"), "10.10.3.1"));
        assertThrows(BusinessException.class, () -> authService.login(loginReq("operator_a", "WrongAgain#2"), "10.10.3.1"));
        assertEquals(2, userA.getFailedLoginAttempts());

        LoginResponse loginOk = authService.login(loginReq("operator_a", "CorrectPass#123"), "10.10.3.1");
        assertNotNull(loginOk.getToken());
        assertEquals(0, userA.getFailedLoginAttempts(), "登录成功后失败计数必须归零");

        assertThrows(BusinessException.class, () -> authService.login(loginReq("operator_a", "WrongAfterReset#1"), "10.10.3.1"));
        assertEquals("ACTIVE", userA.getStatus(), "清零后第1次错密不得触发锁定");
        assertEquals(1, userA.getFailedLoginAttempts());

        // 校验全部审计日志不含任何密码明文或哈希
        for (OperationLog log : persistedLogs) {
            String raw = log.getUsername() + "|" + log.getOperationTarget() + "|" + log.getDetail();
            assertFalse(raw.contains("CorrectPass"));
            assertFalse(raw.contains("WrongPass"));
            assertFalse(raw.contains("WrongAgain"));
            assertFalse(raw.contains(userA.getPasswordHash()));
        }
    }

    private static final String UUID_SUFFIX = "secret";

    @Test
    @DisplayName("SRS_NF016.R01: 任务关键业务生命周期（创建、调度、接管、终止）100% 写入审计日志与过程事件")
    void taskCreationSchedulingTakeoverAndTerminationLifecycleFullAuditTrail() {
        TaskMapper taskMapper = mock(TaskMapper.class);
        PlanVersionMapper planVersionMapper = mock(PlanVersionMapper.class);
        ContextSnapshotMapper contextSnapshotMapper = mock(ContextSnapshotMapper.class);
        DeviceAgentMapper deviceAgentMapper = mock(DeviceAgentMapper.class);
        GoalUnderstandingService goalUnderstandingService = mock(GoalUnderstandingService.class);
        TaskCodeGenerator taskCodeGenerator = mock(TaskCodeGenerator.class);
        TaskPlanningOrchestrator planningOrchestrator = mock(TaskPlanningOrchestrator.class);
        TaskStepAssignmentMapper assignmentMapper = mock(TaskStepAssignmentMapper.class);
        TaskDefinitionService taskDefinitionService = mock(TaskDefinitionService.class);
        DeviceAgentMessagingService messagingService = mock(DeviceAgentMessagingService.class);

        DeviceAgent onlineAgent = new DeviceAgent();
        onlineAgent.setId(501L);
        onlineAgent.setDeviceId(601L);
        onlineAgent.setAgentCode("AGENT-ROBOT-01");
        onlineAgent.setAgentStatus("ENABLED");
        onlineAgent.setOnlineStatus("ONLINE");
        onlineAgent.setWorkStatus("IDLE");

        when(deviceAgentMapper.findByAgentStatusAndOnlineStatus("ENABLED", "ONLINE")).thenReturn(List.of(onlineAgent));
        when(deviceAgentMapper.findById(501L)).thenReturn(Optional.of(onlineAgent));
        when(deviceAgentMapper.findByIdForUpdate(501L)).thenReturn(Optional.of(onlineAgent));
        when(deviceAgentMapper.findByAgentCode("AGENT-ROBOT-01")).thenReturn(Optional.of(onlineAgent));
        when(deviceAgentMapper.findByAgentCodeForUpdate("AGENT-ROBOT-01")).thenReturn(Optional.of(onlineAgent));
        when(deviceAgentMapper.claimAgent(anyLong(), anyLong(), any())).thenReturn(1);
        when(taskDefinitionService.isEnabledFamily("SPECIAL_PASSENGER_SERVICE")).thenReturn(true);
        when(taskDefinitionService.findByCode("SPECIAL_PASSENGER_SERVICE")).thenReturn(Optional.empty());
        when(taskCodeGenerator.next()).thenReturn("TASK-20261110-0088");

        GoalUnderstandingResponse guResp = new GoalUnderstandingResponse();
        guResp.setResultCode("0");
        guResp.setInfoComplete(true);
        guResp.setInferredTaskFamily("SPECIAL_PASSENGER_SERVICE");
        guResp.setOrigin("T2_CHECKIN_A");
        guResp.setDestination("F2_TEST_GATE");
        when(goalUnderstandingService.understand(any())).thenReturn(guResp);

        final Task[] storedTask = new Task[1];
        doAnswer(inv -> {
            Task t = inv.getArgument(0);
            t.setId(88L);
            storedTask[0] = t;
            return 1;
        }).when(taskMapper).insert(any(Task.class));
        when(taskMapper.findById(88L)).thenAnswer(inv -> Optional.ofNullable(storedTask[0]));

        TaskService taskService = new TaskService(
                taskMapper, planVersionMapper, contextSnapshotMapper, deviceAgentMapper,
                goalUnderstandingService, taskCodeGenerator, taskEventService, operationLogService,
                planningOrchestrator, assignmentMapper, taskDefinitionService, messagingService);

        User operator = new User();
        operator.setId(20L);
        operator.setUsername("operator_li");
        operator.setRole("OPERATOR");

        // 1) 创建阶段 (TASK_SUBMIT + GOAL_SUBMITTED)
        SubmitTaskRequest submitReq = new SubmitTaskRequest();
        submitReq.setTaskFamily("SPECIAL_PASSENGER_SERVICE");
        submitReq.setTaskGoal("请协助轮椅旅客从T2_CHECKIN_A前往F2_TEST_GATE登机口");
        submitReq.setSceneParams(Map.of(
                "assistanceType", "WHEELCHAIR",
                "pickupLocation", "T2_CHECKIN_A",
                "targetLocation", "F2_TEST_GATE"
        ));
        Task created = taskService.submit(submitReq, operator);
        assertEquals("TASK-20261110-0088", created.getTaskCode());
        assertTrue(persistedLogs.stream().anyMatch(l -> "TASK_SUBMIT".equals(l.getOperationType()) && "SUCCESS".equals(l.getOperationResult())));
        assertTrue(persistedTaskEvents.stream().anyMatch(e -> "GOAL_SUBMITTED".equals(e.getEventType())));

        // 2) 调度阶段 (AGENT_ASSIGNMENT_REQUESTED -> AGENT_ASSIGNED -> STEP_DISPATCHED)
        PlanVersion pv = new PlanVersion();
        pv.setId(301L);
        pv.setTaskId(88L);
        pv.setVersionNo(1);
        pv.setPlanSteps("[{\"stepSeq\":1,\"stepGoal\":\"护送轮椅旅客前往登机口\",\"capabilityType\":\"CAP_ESCORT\",\"inputParams\":{\"pickupLocation\":\"T2_CHECKIN_A\",\"targetLocation\":\"F2_TEST_GATE\"},\"completionCondition\":\"到达F2_TEST_GATE\"}]");
        when(planVersionMapper.findById(301L)).thenReturn(Optional.of(pv));

        com.airport.ai.device.Device robotDevice = new com.airport.ai.device.Device();
        robotDevice.setId(601L);
        robotDevice.setDeviceCode("DEV-ROBOT-01");
        robotDevice.setDeviceTypeCode("MOBILE_ROBOT");
        robotDevice.setDeviceStatus("ACTIVE");
        robotDevice.setAreaCode("F2_TEST");
        DeviceMapper deviceMapper = mock(DeviceMapper.class);
        when(deviceMapper.findById(601L)).thenReturn(Optional.of(robotDevice));
        when(deviceMapper.findByIds(any())).thenReturn(List.of(robotDevice));

        DeviceCapabilityMapper capabilityMapper = mock(DeviceCapabilityMapper.class);
        when(capabilityMapper.existsByDeviceIdAndCapabilityTypeAndCapabilityStatus(601L, "CAP_ESCORT", "ENABLED"))
                .thenReturn(true);

        final TaskStepAssignment[] storedAssign = new TaskStepAssignment[1];
        doAnswer(inv -> {
            TaskStepAssignment a = inv.getArgument(0);
            a.setId(701L);
            storedAssign[0] = a;
            return 1;
        }).when(assignmentMapper).insert(any(TaskStepAssignment.class));
        when(assignmentMapper.findByPlanVersionIdAndStepSeq(301L, 1)).thenAnswer(inv -> Optional.ofNullable(storedAssign[0]));
        when(assignmentMapper.findByPlanVersionIdOrderByStepSeqAsc(301L)).thenAnswer(inv -> storedAssign[0] == null ? List.of() : List.of(storedAssign[0]));
        when(assignmentMapper.findByCommandId(anyString())).thenAnswer(inv -> Optional.ofNullable(storedAssign[0]));

        TaskExecutionOrchestrator executionOrchestrator = new TaskExecutionOrchestrator(
                taskMapper, planVersionMapper, assignmentMapper, deviceAgentMapper, deviceMapper,
                capabilityMapper, taskEventService, mock(TaskExceptionService.class), messagingService,
                mock(com.airport.ai.baseline.BaselineDryRunLifecycle.class),
                mock(com.airport.ai.baseline.DryRunDeviceSelectionMapper.class),
                new StepParameterResolver(taskMapper, assignmentMapper, MAPPER));

        created.setCurrentPlanVersionId(301L);
        created.setStatus(TaskStatus.PENDING_ASSIGNMENT);
        executionOrchestrator.startExecution(88L, 301L);
        assertTrue(persistedTaskEvents.stream().anyMatch(e -> "AGENT_ASSIGNMENT_REQUESTED".equals(e.getEventType())));

        executionOrchestrator.onTaskResponse("AGENT-ROBOT-01", storedAssign[0].getCommandId(), true, null);
        assertTrue(persistedTaskEvents.stream().anyMatch(e -> "AGENT_ASSIGNED".equals(e.getEventType())));
        assertTrue(persistedTaskEvents.stream().anyMatch(e -> "STEP_DISPATCHED".equals(e.getEventType())));

        // 3) 人工接管处置阶段 (PENDING_MANUAL -> TASK_MANUAL_ACTION)
        created.setStatus(TaskStatus.PENDING_MANUAL);
        doAnswer(inv -> {
            created.setStatus(TaskStatus.EXECUTING);
            return null;
        }).when(planningOrchestrator).switchToBaseline(88L);

        taskService.manualAction(88L, "SWITCH_TO_BASELINE", "自主规划超时，人工接管切换基线模板", null, operator);
        assertTrue(persistedTaskEvents.stream().anyMatch(e -> "BASELINE_SWITCH_REQUESTED".equals(e.getEventType())));
        assertTrue(persistedLogs.stream().anyMatch(l -> "TASK_MANUAL_ACTION".equals(l.getOperationType()) && "SUCCESS".equals(l.getOperationResult())));

        // 4) 人工终止阶段 (TASK_TERMINATE + MANUAL_TERMINATED / TASK_TERMINATED)
        when(deviceAgentMapper.findByCurrentTaskId(88L)).thenReturn(List.of(onlineAgent));
        taskService.terminate(88L, "现场航班计划取消，人工终止协同任务", operator);
        assertEquals(TaskStatus.MANUAL_TERMINATED, created.getStatus());
        assertTrue(persistedTaskEvents.stream().anyMatch(e -> "MANUAL_TERMINATED".equals(e.getEventType())));
        assertTrue(persistedTaskEvents.stream().anyMatch(e -> "TASK_TERMINATED".equals(e.getEventType())));
        assertTrue(persistedLogs.stream().anyMatch(l -> "TASK_TERMINATE".equals(l.getOperationType()) && "SUCCESS".equals(l.getOperationResult())));
    }

    private LoginRequest loginReq(String username, String password) {
        LoginRequest req = new LoginRequest();
        req.setUsername(username);
        req.setPassword(password);
        return req;
    }

    private boolean containsIsolatedSurrogate(String s) {
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            if (Character.isHighSurrogate(c)) {
                if (i + 1 >= s.length() || !Character.isLowSurrogate(s.charAt(i + 1))) {
                    return true;
                }
                i++;
            } else if (Character.isLowSurrogate(c)) {
                return true;
            }
        }
        return false;
    }
}
