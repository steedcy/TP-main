package com.airport.ai.task;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

@Mapper
public interface TaskMapper {
    Optional<Task> findById(Long id);
    Optional<Task> findByTaskCode(String taskCode);
    long countByStatus(TaskStatus status);
    long count();
    int insert(Task task);
    int update(Task task);
    int claimReplan(@Param("taskId") Long taskId,@Param("reason") String reason);

    /**
     * 对应5.7.1界面元素：任务编号（精确查询）、时间范围（按创建时间）、任务族/状态任意组合筛选，
     * 全部为null时返回全量，配合PageHelper.startPage()使用。取代此前按单一维度硬编码的
     * findByStatusPaged/findByTaskFamilyPaged/findAllPaged三个方法。
     */
    List<Task> searchPaged(@Param("taskCode") String taskCode,
                            @Param("status") TaskStatus status,
                            @Param("taskFamily") String taskFamily,
                            @Param("createdFrom") LocalDateTime createdFrom,
                            @Param("createdTo") LocalDateTime createdTo);
}
