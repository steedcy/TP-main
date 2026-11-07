package com.airport.ai.task;

import com.airport.ai.device.DeviceCapabilityMapper;
import com.airport.ai.taskdef.TaskDefinitionMapper;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.AnnotationConfigApplicationContext;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit.jupiter.SpringExtension;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.mock;

/**
 * 验证 DEF-S3-117：Spring 容器在存在多个构造函数时，能正确通过 @Autowired 识别并实例化 PlanValidationService，
 * 且 TaskDefinitionMapper 能够实际注入。
 */
@ExtendWith(SpringExtension.class)
@ContextConfiguration(classes = {PlanValidationService.class})
class PlanValidationServiceSpringContextTest {

    @MockBean
    private DeviceCapabilityMapper deviceCapabilityMapper;

    @MockBean
    private TaskDefinitionMapper taskDefinitionMapper;

    @MockBean
    private TaskMapper taskMapper;

    @Autowired
    private PlanValidationService planValidationService;

    @Test
    @DisplayName("Spring 容器能成功通过 @Autowired 构造器实例化 PlanValidationService 并注入 TaskDefinitionMapper 与 TaskMapper")
    void testSpringContainerInstantiatesPlanValidationServiceWithAutowiredConstructor() {
        assertNotNull(planValidationService, "PlanValidationService 必须成功被 Spring 容器实例化");
        assertNotNull(planValidationService.getTaskDefinitionMapper(), "TaskDefinitionMapper 必须成功注入 PlanValidationService");
        assertNotNull(planValidationService.getTaskMapper(), "TaskMapper 必须成功注入 PlanValidationService");
    }

    @Test
    @DisplayName("无 TaskDefinitionMapper/TaskMapper Bean 时，通过 @Nullable 优雅降级实例化")
    void testSpringContainerInstantiatesWithoutTaskDefinitionMapper() {
        try (AnnotationConfigApplicationContext context = new AnnotationConfigApplicationContext()) {
            context.registerBean(DeviceCapabilityMapper.class, () -> mock(DeviceCapabilityMapper.class));
            context.register(PlanValidationService.class);
            context.refresh();

            PlanValidationService service = context.getBean(PlanValidationService.class);
            assertNotNull(service, "PlanValidationService 在无 TaskDefinitionMapper 时应成功实例化");
            assertNull(service.getTaskDefinitionMapper(), "无 TaskDefinitionMapper Bean 时 mapper 应为 null");
            assertNull(service.getTaskMapper(), "无 TaskMapper Bean 时 taskMapper 应为 null");
        }
    }
}
