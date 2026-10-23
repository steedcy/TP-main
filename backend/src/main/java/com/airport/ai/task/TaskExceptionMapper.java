package com.airport.ai.task;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;
import java.util.Optional;

@Mapper
public interface TaskExceptionMapper {
    Optional<TaskException> findById(Long id);
    List<TaskException> findByTaskIdOrderByOccurredAtDesc(Long taskId);
    List<TaskException> searchPaged(@Param("exceptionType") String exceptionType,
                                     @Param("exceptionStatus") String exceptionStatus);
    long countByExceptionStatus(String exceptionStatus);
    int insert(TaskException exception);
    int update(TaskException exception);
}
