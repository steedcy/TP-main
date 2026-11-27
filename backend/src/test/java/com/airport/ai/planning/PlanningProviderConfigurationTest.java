package com.airport.ai.planning;

import com.airport.ai.taskdef.TaskDefinitionMapper;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.runner.ApplicationContextRunner;
import org.springframework.boot.web.client.RestTemplateBuilder;
import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;

class PlanningProviderConfigurationTest {
    private final ApplicationContextRunner runner = new ApplicationContextRunner()
            .withBean(ObjectMapper.class, ObjectMapper::new)
            .withBean(RestTemplateBuilder.class, RestTemplateBuilder::new)
            .withBean(TaskDefinitionMapper.class, () -> mock(TaskDefinitionMapper.class))
            .withUserConfiguration(ExternalPlanningModelServiceImpl.class, ExternalGoalUnderstandingServiceImpl.class,
                    MoonshotChatClient.class, FailoverChatClient.class, MoonshotModelService.class);

    @Test
    void moonshotSelectsOneImplementationForEachContract() {
        runner.withPropertyValues("app.planning-model.provider=moonshot").run(context -> {
            assertThat(context).hasSingleBean(PlanningModelService.class).hasSingleBean(GoalUnderstandingService.class);
            assertThat(context.getBean(PlanningModelService.class)).isInstanceOf(MoonshotModelService.class);
            assertThat(context.getBean(PlanningChatClient.class)).isInstanceOf(FailoverChatClient.class);
            assertThat(context.getBean(FailoverChatClient.class).isFallbackEnabled()).isFalse();
            assertThat(context.getBean(FailoverChatClient.class).activeMode()).isEqualTo(FailoverChatClient.MODE_SECONDARY_ONLY);
            assertThat(context).doesNotHaveBean(ExternalPlanningModelServiceImpl.class);
        });
    }

    @Test
    void moonshotWithFallbackEnabledUsesFailoverClientAsPrimary() {
        runner.withPropertyValues("app.planning-model.provider=moonshot",
                "app.planning-model.fallback.enabled=true").run(context -> {
            assertThat(context).hasSingleBean(PlanningModelService.class).hasSingleBean(GoalUnderstandingService.class);
            assertThat(context.getBean(PlanningChatClient.class)).isInstanceOf(FailoverChatClient.class);
            assertThat(context.getBean(FailoverChatClient.class).isFallbackEnabled()).isTrue();
        });
    }

    @Test
    void existingExternalProviderRemainsDefault() {
        runner.run(context -> {
            assertThat(context).hasSingleBean(PlanningModelService.class).hasSingleBean(GoalUnderstandingService.class);
            assertThat(context.getBean(PlanningModelService.class)).isInstanceOf(ExternalPlanningModelServiceImpl.class);
            assertThat(context).doesNotHaveBean(MoonshotChatClient.class);
        });
    }
}
