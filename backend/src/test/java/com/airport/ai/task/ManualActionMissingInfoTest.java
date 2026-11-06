package com.airport.ai.task;

import com.airport.ai.auth.OperationLogService;
import com.airport.ai.auth.User;
import com.airport.ai.common.BusinessException;
import com.airport.ai.common.ErrorCode;
import com.airport.ai.device.DeviceAgentMapper;
import com.airport.ai.device.DeviceAgentMessagingService;
import com.airport.ai.event.TaskEventService;
import com.airport.ai.planning.GoalUnderstandingService;
import com.airport.ai.taskdef.TaskDefinitionService;
import org.junit.jupiter.api.Test;

import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/** DEF-S3-063：关键信息仍缺失的待人工任务，不得转基线/重试规划让模板默认值顶替未确认的内容。 */
class ManualActionMissingInfoTest {
    private final TaskMapper tasks = mock(TaskMapper.class);
    private final TaskPlanningOrchestrator planning = mock(TaskPlanningOrchestrator.class);
    private final TaskService service = new TaskService(tasks, mock(PlanVersionMapper.class),
            mock(ContextSnapshotMapper.class), mock(DeviceAgentMapper.class), mock(GoalUnderstandingService.class),
            mock(TaskCodeGenerator.class), mock(TaskEventService.class), mock(OperationLogService.class), planning,
            mock(TaskStepAssignmentMapper.class), mock(TaskDefinitionService.class), mock(DeviceAgentMessagingService.class));

    private Task pendingManual(String missingInfo) {
        Task task = new Task();
        task.setId(7L);
        task.setTaskCode("TASK-7");
        task.setStatus(TaskStatus.PENDING_MANUAL);
        task.setMissingInfoQuestions(missingInfo);
        when(tasks.findById(7L)).thenReturn(Optional.of(task));
        return task;
    }

    private User operator() {
        User u = new User();
        u.setId(4L);
        u.setUsername("op");
        u.setRole("OPERATOR");
        return u;
    }

    @Test
    void baselineAndRetryAreRejectedWhileKeyInformationIsStillMissing() {
        for (String action : new String[]{"SWITCH_TO_BASELINE", "RETRY_PLANNING"}) {
            Task task = pendingManual("[\"请提供协助类型\",\"请提供起点\",\"请提供终点\"]");
            BusinessException ex = assertThrows(BusinessException.class, () -> service.manualAction(7L, action, "提供原因测试", operator()));
            assertEquals(ErrorCode.PARAM_MISSING, ex.getErrorCode());
            assertTrue(ex.getMessage().contains("请提供起点"));
            assertEquals(TaskStatus.PENDING_MANUAL, task.getStatus(), "被拒绝时状态不变");
        }
        verifyNoInteractions(planning);
        verify(tasks, never()).update(any());
    }

    @Test
    void markFailedIsStillAllowedWhileInformationIsMissing() {
        Task task = pendingManual("[\"请提供起点\"]");
        service.manualAction(7L, "MARK_FAILED", "现场确认旅客已离开", operator());
        assertEquals(TaskStatus.FAILED, task.getStatus());
    }

    @Test
    void baselineAndRetryStillWorkWhenNothingIsMissing() {
        for (String missing : new String[]{null, "", "[]"}) {
            reset(planning);
            pendingManual(missing);
            service.manualAction(7L, "SWITCH_TO_BASELINE", "转基线正常原因", operator());
            verify(planning).switchToBaseline(7L);
            pendingManual(missing); // 上一步把任务置为PLANNING，重新置为待人工再验证另一动作
            service.manualAction(7L, "RETRY_PLANNING", "重试规划正常原因", operator());
            verify(planning).advance(7L);
        }
    }
}
