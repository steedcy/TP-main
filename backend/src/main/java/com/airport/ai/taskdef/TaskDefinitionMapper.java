package com.airport.ai.taskdef;

import org.apache.ibatis.annotations.Mapper;

import java.util.List;
import java.util.Optional;

@Mapper
public interface TaskDefinitionMapper {
    Optional<TaskDefinition> findById(Long id);
    Optional<TaskDefinition> findByDefinitionCode(String definitionCode);
    List<TaskDefinition> findAll();
    List<TaskDefinition> findByDefinitionStatus(String definitionStatus);
    boolean existsByTaskName(String taskName);
    boolean existsByDefinitionCode(String definitionCode);
    int insert(TaskDefinition taskDefinition);
    int update(TaskDefinition taskDefinition);
    int deleteById(Long id);
}
