package com.airport.ai.task;

import com.airport.ai.device.DeviceAgentMapper;
import com.airport.ai.device.DeviceCapabilityMapper;
import com.airport.ai.device.DeviceMapper;
import com.airport.ai.event.TaskEventService;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit.jupiter.SpringExtension;

import static org.junit.jupiter.api.Assertions.assertNotNull;

/**
 * 验证 DEF-S3-096：Spring 容器在存在多个构造函数时，能正确通过 @Autowired 识别并实例化 TaskExceptionService，
 * 且 TaskExecutionOrchestrator 依赖注入链路通畅。
 */
@ExtendWith(SpringExtension.class)
@ContextConfiguration(classes = {TaskExceptionService.class, TaskExecutionOrchestrator.class})
class TaskExceptionServiceSpringContextTest {

    @MockBean TaskMapper taskMapper;
    @MockBean TaskStepAssignmentMapper assignmentMapper;
    @MockBean TaskExceptionMapper taskExceptionMapper;
    @MockBean DeviceAgentMapper deviceAgentMapper;
    @MockBean DeviceMapper deviceMapper;
    @MockBean DeviceCapabilityMapper deviceCapabilityMapper;
    @MockBean TaskEventService taskEventService;
    @MockBean ReplanningService replanningService;
    @MockBean PlanVersionMapper planVersionMapper;
    @MockBean com.airport.ai.device.DeviceAgentMessagingService deviceAgentMessagingService;
    @MockBean com.airport.ai.baseline.BaselineDryRunLifecycle dryRunLifecycle;
    @MockBean com.airport.ai.baseline.DryRunDeviceSelectionMapper selections;
    @MockBean StepParameterResolver parameterResolver;

    @Autowired TaskExceptionService taskExceptionService;
    @Autowired TaskExecutionOrchestrator taskExecutionOrchestrator;

    @Test
    void springContainerInstantiatesTaskExceptionServiceWithAutowiredConstructor() {
        assertNotNull(taskExceptionService, "TaskExceptionService 必须成功被 Spring 容器实例化");
        assertNotNull(taskExecutionOrchestrator, "TaskExecutionOrchestrator 必须成功注入 TaskExceptionService");
    }
}
