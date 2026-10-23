package com.airport.ai.event;

import org.apache.ibatis.annotations.Mapper;

import java.util.List;

/**
 * 仅暴露insert（追加）与查询方法，不提供delete/update场景的方法声明，
 * 从代码层面呼应5.7.1"事件仅可追加"的约束（数据库层已同步撤销UPDATE/DELETE权限）。
 */
@Mapper
public interface TaskEventMapper {
    List<TaskEvent> findByTaskIdOrderByOccurredAtAsc(Long taskId);
    int insert(TaskEvent taskEvent);
}
