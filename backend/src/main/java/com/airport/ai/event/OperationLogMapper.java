package com.airport.ai.event;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.time.LocalDateTime;
import java.util.List;

/**
 * 对应5.7.2界面元素：按操作人、操作类型、时间范围、操作结果任意组合筛选，配合
 * PageHelper.startPage()使用，见OperationLogService。全部筛选参数为null时返回全量。
 */
@Mapper
public interface OperationLogMapper {
    List<OperationLog> searchPaged(@Param("username") String username,
                                    @Param("operationType") String operationType,
                                    @Param("operationResult") String operationResult,
                                    @Param("startTime") LocalDateTime startTime,
                                    @Param("endTime") LocalDateTime endTime);
    int insert(OperationLog operationLog);
}
