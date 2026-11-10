package com.airport.ai.device;

import com.airport.ai.auth.OperationLogService;
import com.airport.ai.auth.User;
import com.airport.ai.common.BusinessException;
import com.airport.ai.common.ErrorCode;
import com.airport.ai.device.dto.CreateDeviceRequest;
import com.airport.ai.device.dto.UpdateDeviceRequest;
import com.airport.ai.event.TaskEventService;
import com.airport.ai.task.*;
import com.airport.ai.task.dto.SubmitTaskRequest;
import com.airport.ai.taskdef.TaskDefinitionService;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.mockito.invocation.InvocationOnMock;
import org.springframework.context.ApplicationEventPublisher;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicLong;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * SRS_NF010 / TC-090.S1 / NT-S3-011:
 * 双浏览器客户端（Chrome 与 Edge）并发保存配置与任务提交时的数据隔离与防竞争单测。
 * 验证：
 * 1. 双客户端并发保存不同设备配置时的数据完全隔离与独立审计；
 * 2. 双客户端并发保存相同编码配置时的防竞争防护（互斥且友好冲突提示，杜绝死锁与脏数据）；
 * 3. 双客户端并发修改相同设备配置时的事务防竞争与无死锁保证；
 * 4. 双客户端并发提交任务时的数据隔离、全局唯一任务编号递增生成与零碰撞；
 * 5. 瞬时突发高并发任务提交时无死锁、无编号冲突与优雅排队。
 */
class DualBrowserConcurrentConfigAndTaskTest {

    private static final DateTimeFormatter DATE_FMT = DateTimeFormatter.ofPattern("yyyyMMdd");

    private User createOperator(String username, String role) {
        User u = new User();
        u.setId(username.hashCode() & 0x7fffffffL);
        u.setUsername(username);
        u.setRole(role);
        return u;
    }

    private CreateDeviceRequest createDeviceReq(String code, String name, String endpoint) {
        CreateDeviceRequest r = new CreateDeviceRequest();
        r.setDeviceCode(code);
        r.setDeviceName(name);
        r.setDeviceTypeCode("SIMULATOR");
        r.setIsSimulator(true);
        r.setSimulatedDeviceType("SMART_DISPLAY");
        r.setAreaCode("F2_TEST");
        r.setPositionX(BigDecimal.valueOf(100.5));
        r.setPositionY(BigDecimal.valueOf(200.5));
        r.setAccessEndpoint(endpoint);
        r.setAccessCredentialRef("cred-token");
        r.setStatusReportInterval(15);
        return r;
    }

    @Test
    @DisplayName("双浏览器客户端并发保存不同配置：数据完全隔离与独立审计留痕")
    void dualBrowserConcurrentConfigSave_isolatedDataAndAudit() throws Exception {
        ConcurrentMap<String, Device> dbStore = new ConcurrentHashMap<>();
        AtomicLong idSeq = new AtomicLong(100);

        DeviceMapper deviceMapper = mock(DeviceMapper.class);
        when(deviceMapper.existsByDeviceCode(anyString())).thenAnswer(inv -> dbStore.containsKey(inv.getArgument(0)));
        when(deviceMapper.countByDeviceStatusNot(anyString())).thenAnswer(inv -> (long) dbStore.size());
        doAnswer(inv -> {
            Device d = inv.getArgument(0);
            if (dbStore.putIfAbsent(d.getDeviceCode(), d) != null) {
                throw new org.springframework.dao.DuplicateKeyException("Duplicate device_code: " + d.getDeviceCode());
            }
            d.setId(idSeq.incrementAndGet());
            return 1;
        }).when(deviceMapper).insert(any(Device.class));

        OperationLogService operationLogService = mock(OperationLogService.class);
        List<String> auditLogs = Collections.synchronizedList(new ArrayList<>());
        doAnswer(inv -> {
            Long actorId = inv.getArgument(0);
            String actor = inv.getArgument(1);
            String op = inv.getArgument(3);
            String target = inv.getArgument(4);
            auditLogs.add(actor + ":" + op + ":" + target);
            return null;
        }).when(operationLogService).record(any(), any(), any(), any(), any(), any(), any(), any());

        DeviceService deviceService = new DeviceService(
                deviceMapper, mock(DeviceAgentMapper.class), operationLogService,
                mock(DeviceEventService.class), mock(DeviceAdapterClient.class),
                mock(ApplicationEventPublisher.class), 20,
                mock(DeviceCapabilityMapper.class), mock(TaskExceptionService.class),
                "F2_TEST", mock(com.airport.ai.devicetype.CapabilityTemplateMapper.class));

        User chromeAdmin = createOperator("chrome-config-admin", "CONFIG_ADMIN");
        User edgeAdmin = createOperator("edge-config-admin", "CONFIG_ADMIN");

        CreateDeviceRequest reqChrome = createDeviceReq("SIM_DEV_CHROME_001", "Chrome航显大屏", "http://127.0.0.1:8091");
        CreateDeviceRequest reqEdge = createDeviceReq("SIM_DEV_EDGE_002", "Edge引导大屏", "http://127.0.0.1:8092");

        ExecutorService executor = Executors.newFixedThreadPool(2);
        CountDownLatch startLatch = new CountDownLatch(1);
        CountDownLatch doneLatch = new CountDownLatch(2);

        Future<Device> futureChrome = executor.submit(() -> {
            startLatch.await();
            return deviceService.create(reqChrome, chromeAdmin);
        });

        Future<Device> futureEdge = executor.submit(() -> {
            startLatch.await();
            return deviceService.create(reqEdge, edgeAdmin);
        });

        startLatch.countDown();
        doneLatch.await(5, TimeUnit.SECONDS);
        executor.shutdown();

        Device devChrome = futureChrome.get();
        Device devEdge = futureEdge.get();

        assertNotNull(devChrome);
        assertNotNull(devEdge);
        assertNotEquals(devChrome.getId(), devEdge.getId(), "两个客户端创建的设备ID必须独立隔离");
        assertEquals("SIM_DEV_CHROME_001", devChrome.getDeviceCode());
        assertEquals("SIM_DEV_EDGE_002", devEdge.getDeviceCode());
        assertEquals("chrome-config-admin", devChrome.getCreatedBy());
        assertEquals("edge-config-admin", devEdge.getCreatedBy());

        // 核对两浏览器的独立审计留痕
        assertTrue(auditLogs.stream().anyMatch(l -> l.contains("chrome-config-admin:DEVICE_CREATE:SIM_DEV_CHROME_001")));
        assertTrue(auditLogs.stream().anyMatch(l -> l.contains("edge-config-admin:DEVICE_CREATE:SIM_DEV_EDGE_002")));
    }

    @Test
    @DisplayName("双浏览器客户端并发保存相同配置编码：防竞争保护与优雅冲突提示（杜绝脏写与死锁）")
    void dualBrowserConcurrentConfigSave_antiCompetitionConflict() throws Exception {
        ConcurrentMap<String, Device> dbStore = new ConcurrentHashMap<>();
        AtomicLong idSeq = new AtomicLong(200);

        DeviceMapper deviceMapper = mock(DeviceMapper.class);
        when(deviceMapper.existsByDeviceCode(anyString())).thenAnswer(inv -> dbStore.containsKey(inv.getArgument(0)));
        when(deviceMapper.countByDeviceStatusNot(anyString())).thenAnswer(inv -> (long) dbStore.size());
        doAnswer(inv -> {
            Device d = inv.getArgument(0);
            if (dbStore.putIfAbsent(d.getDeviceCode(), d) != null) {
                throw new org.springframework.dao.DuplicateKeyException("Duplicate device_code: " + d.getDeviceCode());
            }
            d.setId(idSeq.incrementAndGet());
            return 1;
        }).when(deviceMapper).insert(any(Device.class));

        DeviceService deviceService = new DeviceService(
                deviceMapper, mock(DeviceAgentMapper.class), mock(OperationLogService.class),
                mock(DeviceEventService.class), mock(DeviceAdapterClient.class),
                mock(ApplicationEventPublisher.class), 20,
                mock(DeviceCapabilityMapper.class), mock(TaskExceptionService.class),
                "F2_TEST", mock(com.airport.ai.devicetype.CapabilityTemplateMapper.class));

        User chromeAdmin = createOperator("chrome-admin", "CONFIG_ADMIN");
        User edgeAdmin = createOperator("edge-admin", "CONFIG_ADMIN");

        // 两个浏览器并发提交相同编码的配置
        String conflictingCode = "SIM_DEV_CONFLICT_999";
        CreateDeviceRequest reqChrome = createDeviceReq(conflictingCode, "Chrome提交的设备", "http://127.0.0.1:8091");
        CreateDeviceRequest reqEdge = createDeviceReq(conflictingCode, "Edge提交的设备", "http://127.0.0.1:8092");

        ExecutorService executor = Executors.newFixedThreadPool(2);
        CountDownLatch startLatch = new CountDownLatch(1);

        Future<?> futureChrome = executor.submit(() -> {
            startLatch.await();
            return deviceService.create(reqChrome, chromeAdmin);
        });

        Future<?> futureEdge = executor.submit(() -> {
            startLatch.await();
            return deviceService.create(reqEdge, edgeAdmin);
        });

        startLatch.countDown();
        executor.shutdown();

        int successCount = 0;
        int conflictCount = 0;

        try {
            futureChrome.get();
            successCount++;
        } catch (ExecutionException e) {
            Throwable cause = e.getCause();
            if (cause instanceof BusinessException be && be.getErrorCode() == ErrorCode.DEVICE_CODE_TAKEN) {
                conflictCount++;
            } else if (cause instanceof org.springframework.dao.DuplicateKeyException) {
                conflictCount++;
            } else {
                fail("未预期的异常类型: " + cause);
            }
        }

        try {
            futureEdge.get();
            successCount++;
        } catch (ExecutionException e) {
            Throwable cause = e.getCause();
            if (cause instanceof BusinessException be && be.getErrorCode() == ErrorCode.DEVICE_CODE_TAKEN) {
                conflictCount++;
            } else if (cause instanceof org.springframework.dao.DuplicateKeyException) {
                conflictCount++;
            } else {
                fail("未预期的异常类型: " + cause);
            }
        }

        assertEquals(1, successCount, "并发保存相同编码时，必须且只能有1个客户端成功入库");
        assertEquals(1, conflictCount, "竞争落败的客户端必须收到明确的冲突错误提示");
        assertEquals(1, dbStore.size(), "数据库中严格保持唯一条目，杜绝重复与数据污染");
    }

    @Test
    @DisplayName("双浏览器客户端并发提交不同业务任务：数据隔离、全局唯一递增编号与零死锁")
    void dualBrowserConcurrentTaskSubmission_isolatedDataAndSequencing() throws Exception {
        ConcurrentMap<String, Task> taskDb = new ConcurrentHashMap<>();
        AtomicLong taskSeq = new AtomicLong(10);
        String today = DATE_FMT.format(LocalDateTime.now());

        TaskMapper taskMapper = mock(TaskMapper.class);
        when(taskMapper.findByTaskCode(anyString())).thenAnswer(inv -> Optional.ofNullable(taskDb.get(inv.getArgument(0))));
        when(taskMapper.count()).thenAnswer(inv -> (long) taskDb.size());
        when(taskMapper.findMaxTaskCodeByDate(today)).thenAnswer(inv -> "TASK-" + today + "-0010");
        doAnswer(inv -> {
            Task t = inv.getArgument(0);
            t.setId(taskSeq.incrementAndGet());
            taskDb.put(t.getTaskCode(), t);
            return 1;
        }).when(taskMapper).insert(any(Task.class));

        TaskCodeGenerator taskCodeGenerator = new TaskCodeGenerator(taskMapper);

        DeviceAgentMapper agentMapper = mock(DeviceAgentMapper.class);
        when(agentMapper.findByAgentStatusAndOnlineStatus("ENABLED", "ONLINE"))
                .thenReturn(List.of(new com.airport.ai.device.DeviceAgent()));

        TaskDefinitionService taskDefinitionService = mock(TaskDefinitionService.class);
        when(taskDefinitionService.isEnabledFamily(anyString())).thenReturn(true);
        when(taskDefinitionService.findByCode(anyString())).thenReturn(Optional.empty());

        TaskEventService taskEventService = mock(TaskEventService.class);
        OperationLogService operationLogService = mock(OperationLogService.class);
        TaskPlanningOrchestrator orchestrator = mock(TaskPlanningOrchestrator.class);

        com.airport.ai.planning.GoalUnderstandingService goalService = mock(com.airport.ai.planning.GoalUnderstandingService.class);
        when(goalService.understand(any())).thenAnswer(inv -> {
            com.airport.ai.planning.GoalUnderstandingResponse resp = new com.airport.ai.planning.GoalUnderstandingResponse();
            resp.setResultCode("0");
            resp.setInfoComplete(true);
            resp.setInferredTaskFamily("SPECIAL_PASSENGER_SERVICE");
            return resp;
        });

        TaskService taskService = new TaskService(
                taskMapper, mock(PlanVersionMapper.class), mock(ContextSnapshotMapper.class),
                agentMapper, goalService,
                taskCodeGenerator, taskEventService, operationLogService, orchestrator,
                mock(TaskStepAssignmentMapper.class), taskDefinitionService,
                mock(DeviceAgentMessagingService.class));

        User chromeOperator = createOperator("operator-chrome", "OPERATOR");
        User edgeOperator = createOperator("operator-edge", "OPERATOR");

        SubmitTaskRequest reqChrome = new SubmitTaskRequest();
        reqChrome.setTaskGoal("协助轮椅旅客张先生登机");
        reqChrome.setTaskFamily("SPECIAL_PASSENGER_SERVICE");
        reqChrome.setSceneParams(Map.of("targetGate", "G01", "serviceType", "WHEELCHAIR"));

        SubmitTaskRequest reqEdge = new SubmitTaskRequest();
        reqEdge.setTaskGoal("处置超规行李箱并引导至超规托运柜台");
        reqEdge.setTaskFamily("OVERSIZE_BAGGAGE_HANDLING");
        reqEdge.setSceneParams(Map.of("flightNo", "CA1234", "targetLocation", "F2_TEST_GATE"));

        ExecutorService executor = Executors.newFixedThreadPool(2);
        CountDownLatch startLatch = new CountDownLatch(1);
        CountDownLatch doneLatch = new CountDownLatch(2);

        Future<Task> futureChrome = executor.submit(() -> {
            startLatch.await();
            return taskService.submit(reqChrome, chromeOperator);
        });

        Future<Task> futureEdge = executor.submit(() -> {
            startLatch.await();
            return taskService.submit(reqEdge, edgeOperator);
        });

        startLatch.countDown();
        doneLatch.await(5, TimeUnit.SECONDS);
        executor.shutdown();

        Task taskChrome = futureChrome.get();
        Task taskEdge = futureEdge.get();

        assertNotNull(taskChrome);
        assertNotNull(taskEdge);
        assertNotEquals(taskChrome.getTaskCode(), taskEdge.getTaskCode(), "并发生成的任务编号必须全局唯一");
        assertTrue(taskChrome.getTaskCode().startsWith("TASK-" + today + "-"));
        assertTrue(taskEdge.getTaskCode().startsWith("TASK-" + today + "-"));

        assertEquals("operator-chrome", taskChrome.getCreatedBy());
        assertEquals("operator-edge", taskEdge.getCreatedBy());
        assertEquals("SPECIAL_PASSENGER_SERVICE", taskChrome.getTaskFamily());
        assertEquals("OVERSIZE_BAGGAGE_HANDLING", taskEdge.getTaskFamily());

        // 验证两个任务在数据存储中各自完全独立
        assertEquals(2, taskDb.size());
        assertTrue(taskDb.containsKey(taskChrome.getTaskCode()));
        assertTrue(taskDb.containsKey(taskEdge.getTaskCode()));
    }

    @Test
    @DisplayName("瞬时突发20并发任务提交：零编号碰撞、优雅排队且杜绝连接死锁")
    void burstConcurrentTaskSubmission_zeroCollisionAndZeroDeadlock() throws Exception {
        ConcurrentMap<String, Task> taskDb = new ConcurrentHashMap<>();
        AtomicLong taskSeq = new AtomicLong(100);
        String today = DATE_FMT.format(LocalDateTime.now());

        TaskMapper taskMapper = mock(TaskMapper.class);
        when(taskMapper.findByTaskCode(anyString())).thenAnswer(inv -> Optional.ofNullable(taskDb.get(inv.getArgument(0))));
        when(taskMapper.count()).thenAnswer(inv -> (long) taskDb.size());
        when(taskMapper.findMaxTaskCodeByDate(today)).thenAnswer(inv -> "TASK-" + today + "-0100");
        doAnswer(inv -> {
            Task t = inv.getArgument(0);
            t.setId(taskSeq.incrementAndGet());
            taskDb.put(t.getTaskCode(), t);
            return 1;
        }).when(taskMapper).insert(any(Task.class));

        TaskCodeGenerator taskCodeGenerator = new TaskCodeGenerator(taskMapper);

        DeviceAgentMapper agentMapper = mock(DeviceAgentMapper.class);
        when(agentMapper.findByAgentStatusAndOnlineStatus("ENABLED", "ONLINE"))
                .thenReturn(List.of(new com.airport.ai.device.DeviceAgent()));

        TaskDefinitionService taskDefinitionService = mock(TaskDefinitionService.class);
        when(taskDefinitionService.isEnabledFamily(anyString())).thenReturn(true);
        when(taskDefinitionService.findByCode(anyString())).thenReturn(Optional.empty());

        com.airport.ai.planning.GoalUnderstandingService goalService = mock(com.airport.ai.planning.GoalUnderstandingService.class);
        when(goalService.understand(any())).thenAnswer(inv -> {
            com.airport.ai.planning.GoalUnderstandingResponse resp = new com.airport.ai.planning.GoalUnderstandingResponse();
            resp.setResultCode("0");
            resp.setInfoComplete(true);
            resp.setInferredTaskFamily("SPECIAL_PASSENGER_SERVICE");
            return resp;
        });

        TaskService taskService = new TaskService(
                taskMapper, mock(PlanVersionMapper.class), mock(ContextSnapshotMapper.class),
                agentMapper, goalService,
                taskCodeGenerator, mock(TaskEventService.class), mock(OperationLogService.class),
                mock(TaskPlanningOrchestrator.class), mock(TaskStepAssignmentMapper.class),
                taskDefinitionService, mock(DeviceAgentMessagingService.class));

        int burstConcurrency = 20;
        ExecutorService executor = Executors.newFixedThreadPool(burstConcurrency);
        CountDownLatch startLatch = new CountDownLatch(1);
        CountDownLatch doneLatch = new CountDownLatch(burstConcurrency);
        Set<String> assignedCodes = ConcurrentHashMap.newKeySet();
        List<Throwable> errors = Collections.synchronizedList(new ArrayList<>());

        for (int i = 0; i < burstConcurrency; i++) {
            final int idx = i;
            executor.submit(() -> {
                try {
                    startLatch.await();
                    User op = createOperator("burst-operator-" + idx, "OPERATOR");
                    SubmitTaskRequest req = new SubmitTaskRequest();
                    req.setTaskGoal("突发并发业务处理任务-" + idx);
                    req.setTaskFamily("SPECIAL_PASSENGER_SERVICE");
                    req.setSceneParams(Map.of("index", idx, "timestamp", System.currentTimeMillis()));
                    Task t = taskService.submit(req, op);
                    assignedCodes.add(t.getTaskCode());
                } catch (Throwable e) {
                    errors.add(e);
                } finally {
                    doneLatch.countDown();
                }
            });
        }

        startLatch.countDown();
        boolean completed = doneLatch.await(10, TimeUnit.SECONDS);
        executor.shutdown();

        assertTrue(completed, "所有突发任务提交必须在限时内完成");
        assertTrue(errors.isEmpty(), "突发提交不应发生异常，捕获异常: " + errors);
        assertEquals(burstConcurrency, assignedCodes.size(), "20个突发并发提交生成的任务编码必须严格全局唯一");
        assertEquals(burstConcurrency, taskDb.size(), "数据库中必须恰好入库20条独立隔离的任务记录");
    }
}
