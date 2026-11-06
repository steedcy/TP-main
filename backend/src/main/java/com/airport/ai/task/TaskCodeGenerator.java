package com.airport.ai.task;

import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.concurrent.atomic.AtomicLong;

/**
 * 任务编号生成器（格式TASK-{yyyyMMdd}-{4位序号}），供5.3.2试运行和5.4任务规划链路共用，
 * 避免两处各自"count()+1"在并发下产生重复编号。基于库中当天最大序号初始化，并在自增中校验唯一性，
 * 免疫重启后序号碰撞与事务回滚留下的编号间隙（DEF-S3-114）。
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
            long maxSeq = 0L;
            try {
                String maxCode = taskMapper.findMaxTaskCodeByDate(datePart);
                if (maxCode != null && maxCode.startsWith("TASK-" + datePart + "-")) {
                    String seqPart = maxCode.substring(("TASK-" + datePart + "-").length());
                    maxSeq = Long.parseLong(seqPart);
                }
            } catch (Exception ignored) {
            }
            sequence.set(Math.max(taskMapper.count(), maxSeq));
        }
        while (true) {
            long seq = sequence.incrementAndGet();
            String candidateCode = "TASK-" + datePart + "-" + String.format("%04d", seq);
            if (taskMapper.findByTaskCode(candidateCode).isEmpty()) {
                return candidateCode;
            }
        }
    }
}
