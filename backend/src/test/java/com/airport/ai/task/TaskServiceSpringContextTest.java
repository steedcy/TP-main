package com.airport.ai.task;

import com.airport.ai.auth.OperationLogService;
import com.airport.ai.device.DeviceAgentMapper;
import com.airport.ai.device.DeviceAgentMessagingService;
import com.airport.ai.event.TaskEventService;
import com.airport.ai.planning.GoalUnderstandingService;
import com.airport.ai.taskdef.TaskDefinitionService;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit.jupiter.SpringExtension;

import static org.junit.jupiter.api.Assertions.assertNotNull;

/**
 * 验证 DEF-S3-090：Spring 容器在存在多个构造函数时，能正确通过 @Autowired 识别并实例化 TaskService，
 * 且 ForceBypassAuditRecorder 作为独立 Bean 成功注入。
 */
@ExtendWith(SpringExtension.class)
@ContextConfiguration(classes = {TaskService.class, ForceBypassAuditRecorder.class})
class TaskServiceSpringContextTest {

    @MockBean TaskMapper taskMapper;
    @MockBean PlanVersionMapper planVersionMapper;
    @MockBean ContextSnapshotMapper contextSnapshotMapper;
    @MockBean DeviceAgentMapper deviceAgentMapper;
    @MockBean GoalUnderstandingService goalUnderstandingService;
    @MockBean TaskCodeGenerator taskCodeGenerator;
    @MockBean TaskEventService taskEventService;
    @MockBean OperationLogService operationLogService;
    @MockBean TaskPlanningOrchestrator taskPlanningOrchestrator;
    @MockBean TaskStepAssignmentMapper assignmentMapper;
    @MockBean TaskDefinitionService taskDefinitionService;
    @MockBean DeviceAgentMessagingService deviceAgentMessagingService;

    @Autowired TaskService taskService;
    @Autowired ForceBypassAuditRecorder forceBypassAuditRecorder;

    @Test
    void springContainerInstantiatesTaskServiceWithAutowiredConstructor() {
        assertNotNull(taskService, "TaskService 必须成功被 Spring 容器实例化");
        assertNotNull(forceBypassAuditRecorder, "ForceBypassAuditRecorder 必须成功被 Spring 容器实例化并注入");
    }
}
