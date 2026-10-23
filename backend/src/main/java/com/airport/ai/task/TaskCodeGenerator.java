package com.airport.ai.task;

import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.concurrent.atomic.AtomicLong;

/**
 * 任务编号生成器（格式TASK-{yyyyMMdd}-{4位序号}），供5.3.2试运行和5.4任务规划链路共用，
 * 避免两处各自"count()+1"在并发下产生重复编号。进程内自增序号，跨天自动归零。
 */
@Component
public class TaskCodeGenerator {

    private static final DateTimeFormatter DATE_FMT = DateTimeFormatter.ofPattern("yyyyMMdd");

    private final TaskMapper taskMapper;
    private volatile String currentDatePart;
    private final AtomicLong sequence = new AtomicLong(0);

    public TaskCodeGenerator(TaskMapper taskMapper) {
        this.taskMapper = taskMapper;
    }

    public synchronized String next() {
        String datePart = DATE_FMT.format(LocalDateTime.now());
        if (!datePart.equals(currentDatePart)) {
            currentDatePart = datePart;
            sequence.set(taskMapper.count());
        }
        long seq = sequence.incrementAndGet();
        return "TASK-" + datePart + "-" + String.format("%04d", seq);
    }
}
