package com.airport.ai.task;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

@Mapper
public interface TaskStepAssignmentMapper {
    Optional<TaskStepAssignment> findById(Long id);
    List<TaskStepAssignment> findByPlanVersionIdOrderByStepSeqAsc(Long planVersionId);
    Optional<TaskStepAssignment> findByPlanVersionIdAndStepSeq(@Param("planVersionId") Long planVersionId,
                                                                @Param("stepSeq") Integer stepSeq);
    Optional<TaskStepAssignment> findByCommandId(String commandId);
    Optional<TaskStepAssignment> findByExecuteCommandId(String executeCommandId);
    List<TaskStepAssignment> findByStepStatusAndDispatchedAtBefore(@Param("stepStatus") String stepStatus,
                                                                    @Param("threshold") LocalDateTime threshold);
    /** 代理在正式任务（待分配/降级执行中/执行中）中尚未结束的步骤关联，不依赖代理current_task_id（DEF-S3-077） */
    List<TaskStepAssignment> findActiveByAgentId(@Param("agentId") Long agentId);
    int insert(TaskStepAssignment assignment);
    int update(TaskStepAssignment assignment);
}
