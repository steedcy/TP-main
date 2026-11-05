package com.airport.ai.task;

import com.airport.ai.baseline.BaselineDryRunLifecycle;
import com.airport.ai.device.DeviceAgentMapper;
import com.airport.ai.device.DeviceCommandMapper;
import com.airport.ai.event.TaskEventService;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;
import org.springframework.context.annotation.AnnotationConfigApplicationContext;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import static org.junit.jupiter.api.Assertions.assertNotNull;

@DisplayName("DEF-S3-104: StepTimeoutMonitorTask Spring 依赖注入与构造器实例化测试")
class StepTimeoutMonitorTaskSpringInstantiationTest {

    @Configuration
    static class MockDepsConfig {
        @Bean
        public TaskStepAssignmentMapper taskStepAssignmentMapper() {
            return Mockito.mock(TaskStepAssignmentMapper.class);
        }

        @Bean
        public DeviceAgentMapper deviceAgentMapper() {
            return Mockito.mock(DeviceAgentMapper.class);
        }

        @Bean
        public TaskEventService taskEventService() {
            return Mockito.mock(TaskEventService.class);
        }

        @Bean
        public TaskExceptionService taskExceptionService() {
            return Mockito.mock(TaskExceptionService.class);
        }

        @Bean
        public BaselineDryRunLifecycle baselineDryRunLifecycle() {
            return Mockito.mock(BaselineDryRunLifecycle.class);
        }

        @Bean
        public PlanVersionMapper planVersionMapper() {
            return Mockito.mock(PlanVersionMapper.class);
        }

        @Bean
        public DeviceCommandMapper deviceCommandMapper() {
            return Mockito.mock(DeviceCommandMapper.class);
        }
    }

    @Configuration
    static class MinimalDepsConfig {
        @Bean
        public TaskStepAssignmentMapper taskStepAssignmentMapper() {
            return Mockito.mock(TaskStepAssignmentMapper.class);
        }

        @Bean
        public DeviceAgentMapper deviceAgentMapper() {
            return Mockito.mock(DeviceAgentMapper.class);
        }

        @Bean
        public TaskEventService taskEventService() {
            return Mockito.mock(TaskEventService.class);
        }

        @Bean
        public TaskExceptionService taskExceptionService() {
            return Mockito.mock(TaskExceptionService.class);
        }

        @Bean
        public BaselineDryRunLifecycle baselineDryRunLifecycle() {
            return Mockito.mock(BaselineDryRunLifecycle.class);
        }
    }

    @Test
    @DisplayName("Spring 容器应通过 @Autowired 成功实例化 StepTimeoutMonitorTask 且不抛出 No default constructor 异常")
    void springContainerInstantiatesStepTimeoutMonitorTaskSuccessfully() {
        try (AnnotationConfigApplicationContext context = new AnnotationConfigApplicationContext()) {
            context.register(MockDepsConfig.class, StepTimeoutMonitorTask.class);
            context.refresh();

            StepTimeoutMonitorTask task = context.getBean(StepTimeoutMonitorTask.class);
            assertNotNull(task, "StepTimeoutMonitorTask 必须由 Spring 容器自动装配成功");
        }
    }

    @Test
    @DisplayName("即使可选 Mapper 未注册，Spring 容器也能通过 @Nullable 装配实例化")
    void springContainerInstantiatesWithoutOptionalMappers() {
        try (AnnotationConfigApplicationContext context = new AnnotationConfigApplicationContext()) {
            context.register(MinimalDepsConfig.class, StepTimeoutMonitorTask.class);
            context.refresh();

            StepTimeoutMonitorTask task = context.getBean(StepTimeoutMonitorTask.class);
            assertNotNull(task, "当可选 Mapper 不存在时，通过 @Nullable 仍能成功装配");
        }
    }
}
