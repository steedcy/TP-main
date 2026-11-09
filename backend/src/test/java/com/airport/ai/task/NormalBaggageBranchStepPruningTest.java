package com.airport.ai.task;

import com.airport.ai.baseline.BaselineDryRunLifecycle;
import com.airport.ai.baseline.DryRunDeviceSelectionMapper;
import com.airport.ai.device.DeviceAgent;
import com.airport.ai.device.DeviceAgentMapper;
import com.airport.ai.device.DeviceAgentMessagingService;
import com.airport.ai.device.DeviceCapabilityMapper;
import com.airport.ai.device.DeviceMapper;
import com.airport.ai.event.TaskEventService;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.*;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * 验证 SRS_F024.R03 / DEF-S3-119：
 * 正常行李完成测量后，任务置为 COMPLETED 并留痕，
 * 严格清除后续引导步骤：数据库中删除 stepSeq > 1 的分派，并且 plan_versions.plan_steps 裁剪为仅含第 1 步测量。
 */
@ExtendWith(MockitoExtension.class)
class NormalBaggageBranchStepPruningTest {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    @Mock TaskMapper taskMapper;
    @Mock PlanVersionMapper planVersionMapper;
    @Mock TaskStepAssignmentMapper assignmentMapper;
    @Mock DeviceAgentMapper deviceAgentMapper;
    @Mock DeviceMapper deviceMapper;
    @Mock DeviceCapabilityMapper capabilityMapper;
    @Mock TaskEventService taskEventService;
    @Mock TaskExceptionService taskExceptionService;
    @Mock DeviceAgentMessagingService messagingService;
    @Mock BaselineDryRunLifecycle dryRunLifecycle;
    @Mock DryRunDeviceSelectionMapper dryRunDeviceSelectionMapper;
    @Mock StepParameterResolver parameterResolver;

    @Test
    @DisplayName("DEF-S3-119: 正常行李分支在测量完成后，物理删除下游引导分派并持久化裁剪后的单步计划")
    void normalBaggageBranchPrunesDownstreamAssignmentsAndPlanSteps() throws Exception {
        TaskExecutionOrchestrator orchestrator = new TaskExecutionOrchestrator(
                taskMapper, planVersionMapper, assignmentMapper, deviceAgentMapper, deviceMapper,
                capabilityMapper, taskEventService, taskExceptionService, messagingService,
                dryRunLifecycle, dryRunDeviceSelectionMapper, parameterResolver
        );

        Long taskId = 1001L;
        Long planVersionId = 2001L;

        Task task = new Task();
        task.setId(taskId);
        task.setTaskFamily("OVERSIZE_BAGGAGE_HANDLING");
        task.setStatus(TaskStatus.EXECUTING);
        task.setSceneParams("{\"baggageLocation\":\"T2-A02\",\"dimensionThresholdCm\":158.0,\"weightThresholdKg\":20.0}");
        when(taskMapper.findById(taskId)).thenReturn(Optional.of(task));

        // 初始计划包含 4 步
        List<Map<String, Object>> initialSteps = List.of(
                Map.of("stepSeq", 1, "capabilityType", "CAP_BAGGAGE_MEASURE", "stepGoal", "测量行李"),
                Map.of("stepSeq", 2, "capabilityType", "CAP_OVERSIZE_ALERT", "stepGoal", "超规告警"),
                Map.of("stepSeq", 3, "capabilityType", "CAP_INFO_DISPLAY", "stepGoal", "航显发布"),
                Map.of("stepSeq", 4, "capabilityType", "CAP_NAVIGATION", "stepGoal", "路径引导")
        );
        PlanVersion planVersion = new PlanVersion();
        planVersion.setId(planVersionId);
        planVersion.setTaskId(taskId);
        planVersion.setPlanSteps(MAPPER.writeValueAsString(initialSteps));
        when(planVersionMapper.findById(planVersionId)).thenReturn(Optional.of(planVersion));

        DeviceAgent agent = new DeviceAgent();
        agent.setId(88L);
        agent.setAgentCode("AGT-SCAN-01");
        when(deviceAgentMapper.findByAgentCode("AGT-SCAN-01")).thenReturn(Optional.of(agent));

        // 初始分派包含步骤 1
        TaskStepAssignment step1 = new TaskStepAssignment();
        step1.setId(501L);
        step1.setTaskId(taskId);
        step1.setPlanVersionId(planVersionId);
        step1.setStepSeq(1);
        step1.setStepStatus("EXECUTING");
        step1.setDeviceAgentId(88L);
        step1.setRetryCount(0);
        step1.setCommandId("CMD-MEASURE-001");
        when(assignmentMapper.findByCommandId("CMD-MEASURE-001")).thenReturn(Optional.of(step1));
        when(assignmentMapper.findByPlanVersionIdOrderByStepSeqAsc(planVersionId)).thenReturn(List.of(step1));

        // 模拟测量设备反馈非超规正常数据（三边和 110cm <= 158cm, 重量 10kg <= 20kg, isOversize = false）
        Map<String, Object> outputParams = new HashMap<>();
        outputParams.put("measureStatus", "SUCCESS");
        outputParams.put("length", 50.0);
        outputParams.put("width", 40.0);
        outputParams.put("height", 20.0);
        outputParams.put("weight", 10.0);
        outputParams.put("isOversize", false);

        orchestrator.onExecutionFeedback("AGT-SCAN-01", "CMD-MEASURE-001", 0, "SUCCESS", "DEVICE_SUCCESS", outputParams);

        // 1. 验证任务完成
        assertEquals(TaskStatus.COMPLETED, task.getStatus());
        verify(taskMapper).update(task);

        // 2. 验证调用了物理删除下游引导分派 (stepSeq > 1)
        verify(assignmentMapper).deleteByPlanVersionIdAndStepSeqGreaterThan(planVersionId, 1);

        // 3. 验证调用了 planVersionMapper.updatePlanSteps 持久化裁剪后的单步计划
        ArgumentCaptor<String> planStepsCaptor = ArgumentCaptor.forClass(String.class);
        verify(planVersionMapper).updatePlanSteps(eq(planVersionId), planStepsCaptor.capture());

        String updatedPlanSteps = planStepsCaptor.getValue();
        assertNotNull(updatedPlanSteps);
        List<?> parsedSteps = MAPPER.readValue(updatedPlanSteps, List.class);
        assertEquals(1, parsedSteps.size(), "裁剪后计划必须仅保留第 1 步测量，不得残留引导步骤");

        // 4. 验证留痕记录了 BAGGAGE_WITHIN_LIMIT 事件
        verify(taskEventService).append(eq(taskId), eq("TASK_COMPLETED"), eq("SYSTEM"), eq("BAGGAGE_WITHIN_LIMIT"), contains("行李未超规"));
    }
}
