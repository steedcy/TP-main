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
    List<TaskStepAssignment> findByStepStatusAndDispatchedAtBefore(@Param("stepStatus") String stepStatus,
                                                                    @Param("threshold") LocalDateTime threshold);
    int insert(TaskStepAssignment assignment);
    int update(TaskStepAssignment assignment);
}
