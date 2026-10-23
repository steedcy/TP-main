package com.airport.ai.task;

import org.apache.ibatis.annotations.Mapper;

import java.util.List;
import java.util.Optional;

@Mapper
public interface ContextSnapshotMapper {
    Optional<ContextSnapshot> findById(Long id);
    Optional<ContextSnapshot> findBySnapshotCode(String snapshotCode);
    List<ContextSnapshot> findByTaskIdOrderByGeneratedAtDesc(Long taskId);
    long count();
    int insert(ContextSnapshot snapshot);
}
