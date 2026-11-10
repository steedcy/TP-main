package com.airport.ai.task;

import com.airport.ai.auth.OperationLogService;
import com.airport.ai.auth.User;
import com.airport.ai.common.BusinessException;
import com.airport.ai.event.OperationLog;
import com.airport.ai.event.OperationLogMapper;
import com.airport.ai.event.TaskEvent;
import com.airport.ai.event.TaskEventMapper;
import com.airport.ai.event.TaskEventService;
import com.airport.ai.planning.GoalUnderstandingRequest;
import com.airport.ai.planning.PlanningRequest;
import com.airport.ai.task.dto.TaskView;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

/**
 * SRS_NF003.R01 / DEF-S3-032 全链路旅客个人身份隐私保护综合验证测试：
 * 覆盖全系统全链路（目标解析、场景参数、嵌套结构、事件描述、操作日志、模型请求 Prompt）拦截旅客姓名、18位身份证号、护照号、手机号。
 */
class PassengerPrivacyEndToEndTest {

    @Test
    void taskEventServiceSanitizesIdentityInTimeline() {
        TaskEventMapper mockMapper = mock(TaskEventMapper.class);
        TaskEventService eventService = new TaskEventService(mockMapper);

        ArgumentCaptor<TaskEvent> captor = ArgumentCaptor.forClass(TaskEvent.class);

        // 1. 普通文本事件包含姓名、身份证与手机
        eventService.append(101L, "GOAL_SUBMITTED", "OPERATOR", "NORMAL",
                "运行操作员提交任务目标: 旅客姓名=张三, 身份证号=110101199003072345, 手机号=13800138000");

        verify(mockMapper, times(1)).insert(captor.capture());
        TaskEvent savedEvent1 = captor.getValue();
        assertNotNull(savedEvent1);
        String summary1 = savedEvent1.getRawDetailSummary();
        assertFalse(summary1.contains("张三"), "事件描述严禁包含真实旅客姓名");
        assertFalse(summary1.contains("110101199003072345"), "事件描述严禁包含18位身份证号");
        assertFalse(summary1.contains("13800138000"), "事件描述严禁包含手机号");
        assertTrue(summary1.contains("[PROTECTED_IDENTITY]"));

        // 2. 结构化 JSON 详情中包含身份字段与敏感值
        String jsonDetail = "{\"summary\":\"人工取消\",\"reason\":\"护照号: EA9988776\",\"operator\":\"admin\",\"passengerName\":\"CANARY\"}";
        eventService.append(101L, "MANUAL_TERMINATED", "OPERATOR", "NORMAL", jsonDetail);

        verify(mockMapper, times(2)).insert(captor.capture());
        TaskEvent savedEvent2 = captor.getValue();
        String summary2 = savedEvent2.getRawDetailSummary();
        assertFalse(summary2.contains("EA9988776"), "结构化事件严禁泄露护照号");
        assertFalse(summary2.contains("CANARY"), "结构化事件严禁泄露身份哨兵值");
        assertFalse(summary2.contains("passengerName"), "结构化事件键名已剔除");
    }

    @Test
    void operationLogServiceMasksBothCredentialsAndIdentity() {
        OperationLogMapper mockMapper = mock(OperationLogMapper.class);
        OperationLogService logService = new OperationLogService(mockMapper);

        ArgumentCaptor<OperationLog> captor = ArgumentCaptor.forClass(OperationLog.class);

        Map<String, Object> detail = Map.of(
                "action", "TERMINATE",
                "password", "secretPassword123",
                "token", "bearer-token-abc",
                "passengerName", "PrivatePassenger",
                "idCard", "110101199001012345",
                "contactPhone", "13900001111",
                "flightNumber", "CA1234",
                "baggageId", "BAG-123456"
        );

        logService.record(1L, "admin", "SYSTEM_ADMIN", "TASK_TERMINATE", "TASK-2026-0001", "SUCCESS", "127.0.0.1", detail);

        verify(mockMapper, times(1)).insert(captor.capture());
        OperationLog savedLog = captor.getValue();
        assertNotNull(savedLog);
        String detailJson = savedLog.getDetail();

        // 凭据脱敏验证 (SRS_NF001)
        assertFalse(detailJson.contains("secretPassword123"), "密码明文严禁暴露");
        assertFalse(detailJson.contains("bearer-token-abc"), "令牌原值严禁暴露");

        // 旅客隐私保护验证 (SRS_NF003 / DEF-S3-032)
        assertFalse(detailJson.contains("PrivatePassenger"), "旅客姓名严禁在操作日志中落库");
        assertFalse(detailJson.contains("110101199001012345"), "身份证号严禁在操作日志中落库");
        assertFalse(detailJson.contains("13900001111"), "手机号严禁在操作日志中落库");
        assertFalse(detailJson.contains("passengerName"), "旅客身份字段名已被过滤");

        // 业务非敏感标识正常保留
        assertTrue(detailJson.contains("CA1234"), "航班号正常保留");
        assertTrue(detailJson.contains("BAG-123456"), "行李临时编号正常保留");
    }

    @Test
    void modelRequestsSanitizeTaskGoalAndSceneParams() {
        // GoalUnderstandingRequest
        GoalUnderstandingRequest guReq = new GoalUnderstandingRequest();
        guReq.setTaskGoal("协助特殊旅客 旅客姓名=李四 护照: G12345678 手机=13800001111 前往F2_TEST_GATE");
        guReq.setSceneParams(Map.of(
                "assistanceType", "WHEELCHAIR",
                "passengerName", "LEAKED_CANARY",
                "metadata", Map.of("phone", "13800001111", "destination", "F2_TEST_GATE")
        ));
        guReq.setClarificationAnswers(List.of(
                Map.of("answers", Map.of("origin", "F2_GATE_A", "passengerName", "LEAKED_ANSWER"))
        ));

        assertFalse(guReq.getTaskGoal().contains("李四"));
        assertFalse(guReq.getTaskGoal().contains("G12345678"));
        assertFalse(guReq.getTaskGoal().contains("13800001111"));
        assertTrue(guReq.getTaskGoal().contains("F2_TEST_GATE"));

        assertFalse(guReq.getSceneParams().containsKey("passengerName"));
        @SuppressWarnings("unchecked")
        Map<String, Object> meta = (Map<String, Object>) guReq.getSceneParams().get("metadata");
        assertFalse(meta.containsKey("phone"));
        assertEquals("F2_TEST_GATE", meta.get("destination"));

        Map<String, Object> round1 = guReq.getClarificationAnswers().get(0);
        @SuppressWarnings("unchecked")
        Map<String, Object> roundAnswers = (Map<String, Object>) round1.get("answers");
        assertFalse(roundAnswers.containsKey("passengerName"));
        assertEquals("F2_GATE_A", roundAnswers.get("origin"));

        // PlanningRequest
        PlanningRequest pReq = new PlanningRequest();
        pReq.setTaskGoal("为旅客提供轮椅协助 身份证: 110101199003072345");
        pReq.setSceneParams(Map.of("passengerName", "CANARY_PLAN", "targetLocation", "F2_TEST_GATE"));
        pReq.setConstraints(List.of("不得进入施工区", "联系电话: 13800000000"));
        pReq.setCompletedSteps(List.of(Map.of("stepGoal", "会合旅客", "passengerName", "STEP_CANARY")));

        assertFalse(pReq.getTaskGoal().contains("110101199003072345"));
        assertFalse(pReq.getSceneParams().containsKey("passengerName"));
        assertEquals("F2_TEST_GATE", pReq.getSceneParams().get("targetLocation"));
        assertFalse(pReq.getConstraints().get(1).contains("13800000000"));
        assertFalse(pReq.getCompletedSteps().get(0).containsKey("passengerName"));
    }

    @Test
    void taskViewSanitizesAllOutputFields() {
        Task task = new Task();
        task.setId(99L);
        task.setTaskCode("TASK-2026-0099");
        task.setTaskGoal("前往登机口 旅客姓名=王五 手机: 13912345678");
        task.setSceneParams("{\"targetLocation\":\"F2_TEST_GATE\",\"passengerName\":\"CANARY\",\"phone\":\"13800000000\"}");
        task.setGoalParsingResult("{\"originalGoal\":\"旅客姓名=王五\",\"passengerName\":\"CANARY\",\"destination\":\"F2_GATE\"}");
        task.setFailureReason("因旅客姓名=王五，身份证=110101199001011234未核验导致失败");
        task.setManualTerminateReason("操作员因旅客手机: 13800001111 取消");
        task.setDowngradeReason("降级联系人电话: 13700002222");

        TaskView view = TaskView.from(task);

        assertFalse(view.getTaskGoal().contains("王五"));
        assertFalse(view.getTaskGoal().contains("13912345678"));
        assertFalse(view.getSceneParams().containsKey("passengerName"));
        assertFalse(view.getSceneParams().containsKey("phone"));
        assertEquals("F2_TEST_GATE", view.getSceneParams().get("targetLocation"));

        assertFalse(view.getGoalParsingResult().containsKey("passengerName"));
        assertFalse(String.valueOf(view.getGoalParsingResult().get("originalGoal")).contains("王五"));

        assertFalse(view.getFailureReason().contains("王五"));
        assertFalse(view.getFailureReason().contains("110101199001011234"));
        assertFalse(view.getManualTerminateReason().contains("13800001111"));
        assertFalse(view.getDowngradeReason().contains("13700002222"));
    }
}
