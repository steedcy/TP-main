package com.airport.ai.baseline;

import com.airport.ai.auth.OperationLogService;
import com.airport.ai.auth.User;
import com.airport.ai.baseline.dto.DryRunRequest;
import com.airport.ai.baseline.dto.DryRunResultView;
import com.airport.ai.common.BusinessException;
import com.airport.ai.common.ErrorCode;
import com.airport.ai.device.DeviceAgent;
import com.airport.ai.device.DeviceAgentMapper;
import com.airport.ai.device.DeviceCapabilityMapper;
import com.airport.ai.event.TaskEvent;
import com.airport.ai.event.TaskEventService;
import com.airport.ai.task.PlanVersion;
import com.airport.ai.task.PlanVersionMapper;
import com.airport.ai.task.Task;
import com.airport.ai.task.TaskCodeGenerator;
import com.airport.ai.task.TaskMapper;
import com.airport.ai.task.TaskStatus;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.*;

/**
 * 对应5.3.2基线模板试运行：试运行结果与自主规划结果使用相同任务和事件结构，
 * 但标记计划来源为BASELINE_TEMPLATE、任务为isDryRun=true（不计入运行总览正式任务统计）。
 * 通过统一消息网关真实下发指令，以异步设备反馈和逐步骤输出判定试运行结果。
 */
@Service
public class BaselineDryRunService {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    @org.springframework.beans.factory.annotation.Autowired private com.airport.ai.task.TaskExecutionOrchestrator execution;
    @org.springframework.beans.factory.annotation.Autowired private com.airport.ai.task.TaskStepAssignmentMapper assignments;
    @org.springframework.beans.factory.annotation.Autowired private com.airport.ai.task.TaskService taskService;
    @org.springframework.beans.factory.annotation.Autowired private BaselineDryRunLifecycle lifecycle;
    @org.springframework.beans.factory.annotation.Autowired private com.airport.ai.device.DeviceMapper devices;
    private final BaselineTemplateMapper templateMapper;
    private final TaskMapper taskMapper;
    private final PlanVersionMapper planVersionMapper;
    private final TaskEventService taskEventService;
    private final DeviceAgentMapper deviceAgentMapper;
    private final DeviceCapabilityMapper deviceCapabilityMapper;
    private final DryRunDeviceSelectionMapper dryRunDeviceSelectionMapper;
    private final OperationLogService operationLogService;
    private final TaskCodeGenerator taskCodeGenerator;

    public BaselineDryRunService(BaselineTemplateMapper templateMapper,
                                  TaskMapper taskMapper,
                                  PlanVersionMapper planVersionMapper,
                                  TaskEventService taskEventService,
                                  DeviceAgentMapper deviceAgentMapper,
                                  DeviceCapabilityMapper deviceCapabilityMapper,
                                  DryRunDeviceSelectionMapper dryRunDeviceSelectionMapper,
                                  OperationLogService operationLogService,
                                  TaskCodeGenerator taskCodeGenerator) {
        this.templateMapper = templateMapper;
        this.taskMapper = taskMapper;
        this.planVersionMapper = planVersionMapper;
        this.taskEventService = taskEventService;
        this.deviceAgentMapper = deviceAgentMapper;
        this.deviceCapabilityMapper = deviceCapabilityMapper;
        this.dryRunDeviceSelectionMapper = dryRunDeviceSelectionMapper;
        this.operationLogService = operationLogService;
        this.taskCodeGenerator = taskCodeGenerator;
    }

    /**
     * 对应业务规则1：只有静态校验通过的草稿方可试运行（DRAFT/DRY_RUN_PASSED均可重新试运行，
     * ENABLED/DISABLED不可直接试运行——已启用模板需先编辑产生新版本草稿才能再次试运行）。
     * 业务规则2：每个步骤须选择具备对应能力的模拟设备，未选择或能力不匹配时拒绝执行。
     * 业务规则7：试运行同样受五步限制（模板保存时已校验，此处按模板当前steps执行即受限）与运动安全边界约束
     * （步骤完成条件为业务语义描述，不含运动安全控制字段，由静态校验环节保证，本执行器不下发任何控制指令）。
     */
    @SuppressWarnings("unchecked")
    @Transactional
    public DryRunResultView dryRun(Long templateId, DryRunRequest request, User operator) {
        BaselineTemplate template = templateMapper.findById(templateId)
                .orElseThrow(() -> new BusinessException(ErrorCode.BASELINE_TEMPLATE_NOT_FOUND));
        if ("ENABLED".equals(template.getTemplateStatus()) || "DISABLED".equals(template.getTemplateStatus())) {
            throw new BusinessException(ErrorCode.TEMPLATE_NOT_DRY_RUN_PASSED, "仅草稿状态的模板可试运行，请先编辑模板生成新版本");
        }

        List<Map<String, Object>> steps = fromJson(template.getSteps());
        if (steps.isEmpty() || steps.size()>5) throw new BusinessException(ErrorCode.DRY_RUN_DEVICE_MISMATCH, "模板必须有1至5个步骤");
        Map<String,Object> inputs;
        try { inputs=com.airport.ai.device.ParameterValues.materialize(template.getInputParams(), request.getInputParams()); }
        catch (IllegalArgumentException ex) { throw new BusinessException(ErrorCode.PARAM_FORMAT_ERROR, ex.getMessage()); }
        Map<Integer, String> stepAgentCode = new HashMap<>();
        for (DryRunRequest.StepDeviceSelection sel : request.getSimulatedDevices()) {
            stepAgentCode.put(sel.getStepSeq(), sel.getAgentId());
        }
        if (stepAgentCode.size() < steps.size()) {
            throw new BusinessException(ErrorCode.DRY_RUN_DEVICE_MISMATCH, "请为每个步骤选择模拟设备");
        }

        // 能力匹配校验：每个步骤选择的设备必须具备该步骤所需能力类型的已启用能力（对应业务规则2、异常路径2a）
        Map<Integer, DeviceAgent> stepAgents = new HashMap<>();
        for (Map<String, Object> step : steps) {
            Integer stepSeq = (Integer) step.get("stepSeq");
            String capabilityType = (String) step.get("capabilityType");
            String agentCode = stepAgentCode.get(stepSeq);
            if (agentCode == null) {
                throw new BusinessException(ErrorCode.DRY_RUN_DEVICE_MISMATCH, "步骤" + stepSeq + "未选择模拟设备");
            }
            DeviceAgent agent = deviceAgentMapper.findByAgentCode(agentCode)
                    .orElseThrow(() -> new BusinessException(ErrorCode.DRY_RUN_DEVICE_MISMATCH, "设备代理不存在: " + agentCode));
            var device=devices.findById(agent.getDeviceId()).orElseThrow();
            if (!Boolean.TRUE.equals(device.getIsSimulator()) || !"ENABLED".equals(agent.getAgentStatus())
                    || !"ONLINE".equals(agent.getOnlineStatus()) || !"IDLE".equals(agent.getWorkStatus()))
                throw new BusinessException(ErrorCode.DRY_RUN_DEVICE_MISMATCH, "试运行必须选择在线空闲的仿真体代理");
            boolean matched = deviceCapabilityMapper.existsByDeviceIdAndCapabilityTypeAndCapabilityStatus(
                    agent.getDeviceId(), capabilityType, "ENABLED");
            if (!matched) {
                throw new BusinessException(ErrorCode.DRY_RUN_DEVICE_MISMATCH,
                        "步骤" + stepSeq + "选择的设备不具备已启用的" + capabilityType + "能力");
            }
            stepAgents.put(stepSeq, agent);
        }

        Task task = new Task();
        task.setTaskCode(taskCodeGenerator.next());
        task.setTaskGoal("基线模板试运行: " + template.getTemplateName());
        task.setTaskFamily(template.getTaskFamily());
        task.setSceneParams(toJson(inputs));
        task.setStatus(TaskStatus.PENDING_ASSIGNMENT);
        task.setIsDryRun(true);
        task.setCreatedBy(operator.getUsername());
        taskMapper.insert(task);
        Task savedTask = task;

        for (Map.Entry<Integer, DeviceAgent> entry : stepAgents.entrySet()) {
            DryRunDeviceSelection selection = new DryRunDeviceSelection();
            selection.setTaskId(savedTask.getId());
            selection.setStepSeq(entry.getKey());
            selection.setDeviceAgentId(entry.getValue().getId());
            dryRunDeviceSelectionMapper.insert(selection);
        }

        PlanVersion planVersion = new PlanVersion();
        planVersion.setTaskId(savedTask.getId());
        planVersion.setVersionNo(1);
        planVersion.setSource("BASELINE_TEMPLATE");
        planVersion.setBaselineTemplateId(template.getId());
        planVersion.setSnapshotId(template.getTemplateVersion());
        planVersion.setPlanSteps(toJson(steps));
        planVersion.setFrozenAt(LocalDateTime.now());
        planVersionMapper.insert(planVersion);
        savedTask.setCurrentPlanVersionId(planVersion.getId());
        taskMapper.update(savedTask);

        taskEventService.append(savedTask.getId(), "DRY_RUN_STARTED", "OPERATOR", null,
                "配置管理员" + operator.getUsername() + "对模板" + template.getTemplateName()
                        + "(" + template.getTemplateVersion() + ")发起试运行");

        operationLogService.record(operator.getId(), operator.getUsername(), operator.getRole(),
                "BASELINE_TEMPLATE_DRY_RUN", template.getTemplateName() + " -> RUNNING", "SUCCESS", null);
        execution.startExecution(task.getId(), planVersion.getId());
        return result(templateId, task.getId());
    }

    public DryRunResultView result(Long templateId, Long taskId) {
        Task task=taskMapper.findById(taskId).orElseThrow(() -> new BusinessException(ErrorCode.TASK_NOT_FOUND));
        PlanVersion plan=planVersionMapper.findById(task.getCurrentPlanVersionId()).orElseThrow();
        if (!Boolean.TRUE.equals(task.getIsDryRun()) || !templateId.equals(plan.getBaselineTemplateId()))
            throw new BusinessException(ErrorCode.DRY_RUN_DEVICE_MISMATCH, "试运行与模板不匹配");
        DryRunResultView view=new DryRunResultView();
        view.setTaskId(taskId); view.setTaskCode(task.getTaskCode());
        view.setResult(task.getStatus()==TaskStatus.COMPLETED ? "SUCCESS"
                : task.getStatus()==TaskStatus.MANUAL_TERMINATED ? "CANCELLED"
                : task.getStatus()==TaskStatus.FAILED || task.getStatus()==TaskStatus.PENDING_MANUAL ? "FAILED" : "RUNNING");
        view.setFailureReason(task.getFailureReason());
        view.setStepResults(assignments.findByPlanVersionIdOrderByStepSeqAsc(plan.getId()).stream().map(a -> {
            int duration=a.getDispatchedAt()!=null && a.getFeedbackAt()!=null
                    ? (int)java.time.Duration.between(a.getDispatchedAt(),a.getFeedbackAt()).toSeconds() : 0;
            return new DryRunResultView.StepResult(a.getStepSeq(), a.getStepStatus(), duration, a.getReasonCode());
        }).toList());
        view.setEvents(taskEventService.listByTask(taskId).stream().map(this::toEventView).toList());
        return view;
    }

    @Transactional
    public DryRunResultView cancel(Long templateId, Long taskId, User operator) {
        result(templateId,taskId);
        taskService.terminate(taskId,"配置管理员取消模板试运行",operator);
        lifecycle.finish(taskId,false,"配置管理员取消模板试运行");
        Task task=taskMapper.findById(taskId).orElseThrow();
        task.setStatus(TaskStatus.MANUAL_TERMINATED); taskMapper.update(task);
        return result(templateId,taskId);
    }

    private DryRunResultView.EventView toEventView(TaskEvent event) {
        return new DryRunResultView.EventView(event.getEventType(), event.getTrigger(),
                event.getDetailSummary(), String.valueOf(event.getOccurredAt()));
    }

    private String toJson(Object value) {
        try {
            return MAPPER.writeValueAsString(value);
        } catch (Exception e) {
            throw new BusinessException(ErrorCode.DRY_RUN_DEVICE_MISMATCH, "序列化失败: " + e.getMessage());
        }
    }

    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> fromJson(String json) {
        if (json == null || json.isBlank()) {
            return Collections.emptyList();
        }
        try {
            return MAPPER.readValue(json, List.class);
        } catch (Exception e) {
            throw new BusinessException(ErrorCode.DRY_RUN_DEVICE_MISMATCH, "反序列化失败: " + e.getMessage());
        }
    }
}
