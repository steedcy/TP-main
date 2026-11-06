package com.airport.ai.task;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;
import java.util.Optional;

@Mapper
public interface ContextSnapshotMapper {
    Optional<ContextSnapshot> findById(Long id);
    Optional<ContextSnapshot> findBySnapshotCode(String snapshotCode);
    List<ContextSnapshot> findByTaskIdOrderByGeneratedAtDesc(Long taskId);
    long count();
    String findMaxSnapshotCodeByDate(@Param("datePart") String datePart);
    int insert(ContextSnapshot snapshot);
}
