package com.airport.ai.task;

import org.apache.ibatis.annotations.Mapper;

import java.util.List;
import java.util.Optional;

@Mapper
public interface PlanVersionMapper {
    Optional<PlanVersion> findById(Long id);
    List<PlanVersion> findByTaskIdOrderByVersionNoAsc(Long taskId);
    Optional<PlanVersion> findByTaskIdAndVersionNo(Long taskId, Integer versionNo);
    long countByTaskId(Long taskId);
    int insert(PlanVersion planVersion);
    int update(PlanVersion planVersion);
    int updatePlanSteps(@org.apache.ibatis.annotations.Param("id") Long id, @org.apache.ibatis.annotations.Param("planSteps") String planSteps);
}
