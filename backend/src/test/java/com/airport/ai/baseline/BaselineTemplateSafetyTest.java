package com.airport.ai.baseline;

import com.airport.ai.auth.OperationLogService;
import com.airport.ai.auth.User;
import com.airport.ai.baseline.dto.CreateBaselineTemplateRequest;
import com.airport.ai.baseline.dto.ParamMapping;
import com.airport.ai.baseline.dto.TemplateStep;
import com.airport.ai.common.BusinessException;
import com.airport.ai.common.ErrorCode;
import com.airport.ai.device.DeviceCapabilityMapper;
import com.airport.ai.devicetype.dto.ParamDefinition;
import com.airport.ai.taskdef.TaskDefinition;
import com.airport.ai.taskdef.TaskDefinitionService;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class BaselineTemplateSafetyTest {
    @Test
    void speedLimitMappingIsRejectedBeforeTemplateCanBeSaved() {
        BaselineTemplateMapper templates = mock(BaselineTemplateMapper.class);
        DeviceCapabilityMapper capabilities = mock(DeviceCapabilityMapper.class);
        TaskDefinitionService definitions = mock(TaskDefinitionService.class);
        when(definitions.findByCode("GENERAL_GUIDANCE")).thenReturn(Optional.of(new TaskDefinition()));
        when(capabilities.existsByCapabilityTypeAndCapabilityStatus(anyString(), eq("ENABLED"))).thenReturn(true);
        BaselineTemplateService service = new BaselineTemplateService(templates, capabilities,
                mock(OperationLogService.class), definitions);

        ParamDefinition input = new ParamDefinition();
        input.setName("targetLocation"); input.setType("STRING"); input.setRequired(true);
        ParamMapping mapping = new ParamMapping();
        mapping.setTarget("speedLimit"); mapping.setSource("TEMPLATE_INPUT.targetLocation");
        TemplateStep step = new TemplateStep();
        step.setCapabilityType("CAP_NAVIGATION");
        step.setCompletionCondition("routeGenerated=true");
        step.setParamMapping(List.of(mapping));
        CreateBaselineTemplateRequest request = new CreateBaselineTemplateRequest();
        request.setTemplateName("stage1-safety-repro");
        request.setTemplateIntent("GENERAL_GUIDANCE");
        request.setInputParams(List.of(input)); request.setSteps(List.of(step));

        BusinessException rejected = assertThrows(BusinessException.class,
                () -> service.create(request, new User()));
        assertEquals(ErrorCode.TEMPLATE_PARAM_MAPPING_INVALID, rejected.getErrorCode());
        assertTrue(rejected.getMessage().contains("运动安全"));
        verify(templates, never()).insert(any());
    }
}
