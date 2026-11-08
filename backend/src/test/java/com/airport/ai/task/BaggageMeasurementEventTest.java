package com.airport.ai.task;

import com.airport.ai.auth.OperationLogService;
import com.airport.ai.auth.User;
import com.airport.ai.common.BusinessException;
import com.airport.ai.device.DeviceAgentMapper;
import com.airport.ai.device.DeviceAgentMessagingService;
import com.airport.ai.event.TaskEventService;
import com.airport.ai.planning.GoalUnderstandingResponse;
import com.airport.ai.planning.GoalUnderstandingService;
import com.airport.ai.task.dto.BaggageMeasurementEventRequest;
import com.airport.ai.taskdef.TaskDefinitionService;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.validation.Validation;
import jakarta.validation.Validator;
import jakarta.validation.ValidatorFactory;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.Map;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.*;

/**
 * 验证 SRS_F024 / NT-S3-004 模拟行李测量事件自动触发、超规与非超规分支、柜台可选、隐私防护与输入校验
 */
@ExtendWith(MockitoExtension.class)
class BaggageMeasurementEventTest {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    @Mock TaskMapper taskMapper;
    @Mock PlanVersionMapper planVersionMapper;
    @Mock ContextSnapshotMapper contextSnapshotMapper;
    @Mock DeviceAgentMapper deviceAgentMapper;
    @Mock GoalUnderstandingService goalUnderstandingService;
    @Mock TaskCodeGenerator taskCodeGenerator;
    @Mock TaskEventService taskEventService;
    @Mock OperationLogService operationLogService;
    @Mock TaskPlanningOrchestrator taskPlanningOrchestrator;
    @Mock TaskStepAssignmentMapper assignmentMapper;
    @Mock TaskDefinitionService taskDefinitionService;
    @Mock DeviceAgentMessagingService deviceAgentMessagingService;
    @Mock ForceBypassAuditRecorder forceBypassAuditRecorder;

    private TaskService taskService;
    private Validator validator;
    private User testUser;
    private Task insertedTask;

    @BeforeEach
    void setUp() {
        taskService = new TaskService(
                taskMapper,
                planVersionMapper,
                contextSnapshotMapper,
                deviceAgentMapper,
                goalUnderstandingService,
                taskCodeGenerator,
                taskEventService,
                operationLogService,
                taskPlanningOrchestrator,
                assignmentMapper,
                taskDefinitionService,
                deviceAgentMessagingService,
                forceBypassAuditRecorder
        );

        ValidatorFactory factory = Validation.buildDefaultValidatorFactory();
        validator = factory.getValidator();

        testUser = new User();
        testUser.setId(101L);
        testUser.setUsername("test-operator");
        testUser.setRole("OPERATOR");

        lenient().when(taskCodeGenerator.next()).thenReturn("TSK-BG-TEST-001");
        lenient().doAnswer(invocation -> {
            Task t = invocation.getArgument(0);
            t.setId(999L);
            insertedTask = t;
            return 1;
        }).when(taskMapper).insert(any(Task.class));

        lenient().when(taskMapper.findById(anyLong())).thenAnswer(invocation -> Optional.ofNullable(insertedTask));

        GoalUnderstandingResponse mockResponse = new GoalUnderstandingResponse();
        mockResponse.setResultCode("0");
        mockResponse.setInfoComplete(true);
        mockResponse.setInferredTaskFamily("OVERSIZE_BAGGAGE_HANDLING");
        lenient().when(goalUnderstandingService.understand(any())).thenReturn(mockResponse);
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> parseSceneParams(String json) {
        try {
            return MAPPER.readValue(json, Map.class);
        } catch (Exception e) {
            throw new RuntimeException("解析 sceneParams 失败", e);
        }
    }

    @Test
    @DisplayName("非超规行李测量事件：尺寸重量均在限额内，直接COMPLETED留痕，不触发规划引导")
    void nonOversizeEventCompletesDirectlyWithoutPlanning() {
        BaggageMeasurementEventRequest req = new BaggageMeasurementEventRequest();
        req.setBaggageLocation("T2值机岛A02");
        req.setLength(50.0);
        req.setWidth(40.0);
        req.setHeight(20.0); // 合计 110cm <= 158cm
        req.setWeight(12.0); // 12kg <= 20kg

        Task result = taskService.submitMeasurementEvent(req, testUser);

        assertNotNull(result);
        assertEquals(TaskStatus.COMPLETED, result.getStatus());
        assertEquals("OVERSIZE_BAGGAGE_HANDLING", result.getTaskFamily());
        assertNotNull(result.getSceneParams());

        Map<String, Object> params = parseSceneParams(result.getSceneParams());
        assertEquals(Boolean.FALSE, params.get("isOversize"));
        assertEquals("T2值机岛A02", params.get("baggageLocation"));

        // 验证记录了 BAGGAGE_WITHIN_LIMIT 留痕事件
        verify(taskEventService).append(eq(999L), eq("TASK_COMPLETED"), eq("SYSTEM"), eq("BAGGAGE_WITHIN_LIMIT"), anyString());
        // 验证未调用自动规划
        verify(taskPlanningOrchestrator, never()).advance(anyLong());
    }

    @Test
    @DisplayName("超规行李测量事件（三边超限）：合计 200cm > 158cm，状态进入 PLANNING 并触发规划")
    void oversizeEventByDimensionsAdvancesToPlanning() {
        BaggageMeasurementEventRequest req = new BaggageMeasurementEventRequest();
        req.setBaggageLocation("T2值机岛A03");
        req.setLength(100.0);
        req.setWidth(60.0);
        req.setHeight(40.0); // 合计 200cm > 158cm
        req.setWeight(15.0); // 15kg <= 20kg
        req.setTargetCounter("超规行李专柜B01");

        Task result = taskService.submitMeasurementEvent(req, testUser);

        assertNotNull(result);
        assertEquals(TaskStatus.PLANNING, result.getStatus());
        assertEquals("OVERSIZE_BAGGAGE_HANDLING", result.getTaskFamily());

        Map<String, Object> params = parseSceneParams(result.getSceneParams());
        assertEquals(Boolean.TRUE, params.get("isOversize"));
        assertEquals("超规行李专柜B01", params.get("targetCounter"));
        assertTrue(params.get("tempBusinessId").toString().startsWith("BAG-"));

        // 验证触发规划
        verify(taskPlanningOrchestrator).advance(eq(999L));
    }

    @Test
    @DisplayName("超规行李测量事件（单件超重）：重量 25kg > 20kg，状态进入 PLANNING 并触发规划")
    void oversizeEventByWeightAdvancesToPlanning() {
        BaggageMeasurementEventRequest req = new BaggageMeasurementEventRequest();
        req.setBaggageLocation("T2值机岛A05");
        req.setLength(40.0);
        req.setWidth(40.0);
        req.setHeight(40.0); // 合计 120cm <= 158cm
        req.setWeight(25.0); // 25kg > 20kg

        Task result = taskService.submitMeasurementEvent(req, testUser);

        assertNotNull(result);
        assertEquals(TaskStatus.PLANNING, result.getStatus());

        Map<String, Object> params = parseSceneParams(result.getSceneParams());
        assertEquals(Boolean.TRUE, params.get("isOversize"));
        // 目标柜台未填时使用默认专柜
        assertEquals("F2_TEST_GATE", params.get("targetCounter"));

        verify(taskPlanningOrchestrator).advance(eq(999L));
    }

    @Test
    @DisplayName("目标柜台为可选字段：未填时自动填充默认柜台，不引发报错或澄清循环")
    void targetCounterIsOptional() {
        BaggageMeasurementEventRequest req = new BaggageMeasurementEventRequest();
        req.setBaggageLocation("T2值机岛A01");
        req.setLength(120.0);
        req.setWidth(60.0);
        req.setHeight(40.0);
        req.setWeight(30.0);
        req.setTargetCounter(null); // 可选

        Task result = taskService.submitMeasurementEvent(req, testUser);

        assertNotNull(result);
        Map<String, Object> params = parseSceneParams(result.getSceneParams());
        assertNotNull(params.get("targetCounter"));
        verify(taskPlanningOrchestrator).advance(eq(999L));
    }

    @Test
    @DisplayName("隐私守卫：事件中包含真实旅客身份字段（passengerName/idCard等）时拒绝处理")
    void privacyGuardRejectsPassengerIdentityInEvent() {
        BaggageMeasurementEventRequest req = new BaggageMeasurementEventRequest();
        req.setBaggageLocation("T2值机岛A01");
        req.setLength(120.0);
        req.setWidth(60.0);
        req.setHeight(40.0);
        req.setWeight(30.0);
        req.setExtraParams(Map.of("passengerName", "张三", "idCard", "110101199001011234"));

        BusinessException ex = assertThrows(BusinessException.class, () ->
                taskService.submitMeasurementEvent(req, testUser));

        assertTrue(ex.getMessage().contains("信息字段") || ex.getMessage().contains("idCard"));
    }

    @Test
    @DisplayName("参数校验：有效与无效边界验证")
    void validationBoundaries() {
        // 1. 缺失位置
        BaggageMeasurementEventRequest invalidReq1 = new BaggageMeasurementEventRequest();
        invalidReq1.setLength(50.0);
        invalidReq1.setWidth(40.0);
        invalidReq1.setHeight(20.0);
        invalidReq1.setWeight(10.0);
        assertFalse(validator.validate(invalidReq1).isEmpty(), "缺失 baggageLocation 必须被拒绝");

        // 2. 负数尺寸
        BaggageMeasurementEventRequest invalidReq2 = new BaggageMeasurementEventRequest();
        invalidReq2.setBaggageLocation("T2-A01");
        invalidReq2.setLength(-10.0);
        invalidReq2.setWidth(40.0);
        invalidReq2.setHeight(20.0);
        invalidReq2.setWeight(10.0);
        assertFalse(validator.validate(invalidReq2).isEmpty(), "负数尺寸必须被拒绝");

        // 3. 负数或零重量
        BaggageMeasurementEventRequest invalidReq3 = new BaggageMeasurementEventRequest();
        invalidReq3.setBaggageLocation("T2-A01");
        invalidReq3.setLength(50.0);
        invalidReq3.setWidth(40.0);
        invalidReq3.setHeight(20.0);
        invalidReq3.setWeight(0.0);
        assertFalse(validator.validate(invalidReq3).isEmpty(), "零重量必须被拒绝");

        // 4. 正确合法参数
        BaggageMeasurementEventRequest validReq = new BaggageMeasurementEventRequest();
        validReq.setBaggageLocation("T2-A01");
        validReq.setLength(50.0);
        validReq.setWidth(40.0);
        validReq.setHeight(20.0);
        validReq.setWeight(10.0);
        assertTrue(validator.validate(validReq).isEmpty(), "合法参数应该通过校验");
    }
}
