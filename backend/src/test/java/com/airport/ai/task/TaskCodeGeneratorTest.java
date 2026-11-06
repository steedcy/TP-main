package com.airport.ai.task;

import org.junit.jupiter.api.Test;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Optional;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class TaskCodeGeneratorTest {

    private static final DateTimeFormatter DATE_FMT = DateTimeFormatter.ofPattern("yyyyMMdd");

    @Test
    void handlesRestartAndGapsWithoutCollision() {
        TaskMapper taskMapper = mock(TaskMapper.class);
        String today = DATE_FMT.format(LocalDateTime.now());

        // 模拟 DEF-S3-114 场景：数据库总行数为 656，但最大序号为 0681（存在历史回滚间隙）
        when(taskMapper.count()).thenReturn(656L);
        when(taskMapper.findMaxTaskCodeByDate(today)).thenReturn("TASK-" + today + "-0681");

        // 模拟 TASK-yyyyMMdd-0682 碰撞已存在，0683 可用
        Task existing = new Task();
        existing.setTaskCode("TASK-" + today + "-0682");
        when(taskMapper.findByTaskCode("TASK-" + today + "-0682")).thenReturn(Optional.of(existing));
        when(taskMapper.findByTaskCode("TASK-" + today + "-0683")).thenReturn(Optional.empty());

        TaskCodeGenerator generator = new TaskCodeGenerator(taskMapper);
        String code = generator.next();

        assertEquals("TASK-" + today + "-0683", code,
                "重启后应从当天最大序号(0681)后继续分配并跳过已存在的0682，杜绝主键唯一索引冲突500");
    }

    @Test
    void normalInitializationWithEmptyDatabase() {
        TaskMapper taskMapper = mock(TaskMapper.class);
        String today = DATE_FMT.format(LocalDateTime.now());

        when(taskMapper.count()).thenReturn(0L);
        when(taskMapper.findMaxTaskCodeByDate(today)).thenReturn(null);
        when(taskMapper.findByTaskCode(anyString())).thenReturn(Optional.empty());

        TaskCodeGenerator generator = new TaskCodeGenerator(taskMapper);
        assertEquals("TASK-" + today + "-0001", generator.next());
        assertEquals("TASK-" + today + "-0002", generator.next());
    }

    @Test
    void handlesCountGreaterThanMaxSeqSafely() {
        TaskMapper taskMapper = mock(TaskMapper.class);
        String today = DATE_FMT.format(LocalDateTime.now());

        when(taskMapper.count()).thenReturn(10L);
        when(taskMapper.findMaxTaskCodeByDate(today)).thenReturn("TASK-" + today + "-0005");
        when(taskMapper.findByTaskCode(anyString())).thenReturn(Optional.empty());

        TaskCodeGenerator generator = new TaskCodeGenerator(taskMapper);
        assertEquals("TASK-" + today + "-0011", generator.next());
    }

    @Test
    void handlesConcurrencyWithoutDuplicate() throws InterruptedException {
        TaskMapper taskMapper = mock(TaskMapper.class);
        String today = DATE_FMT.format(LocalDateTime.now());

        when(taskMapper.count()).thenReturn(100L);
        when(taskMapper.findMaxTaskCodeByDate(today)).thenReturn("TASK-" + today + "-0100");
        when(taskMapper.findByTaskCode(anyString())).thenReturn(Optional.empty());

        TaskCodeGenerator generator = new TaskCodeGenerator(taskMapper);

        int threadCount = 20;
        ExecutorService executor = Executors.newFixedThreadPool(threadCount);
        CountDownLatch latch = new CountDownLatch(threadCount);
        Set<String> generatedCodes = ConcurrentHashMap.newKeySet();

        for (int i = 0; i < threadCount; i++) {
            executor.submit(() -> {
                try {
                    generatedCodes.add(generator.next());
                } finally {
                    latch.countDown();
                }
            });
        }

        latch.await();
        executor.shutdown();

        assertEquals(threadCount, generatedCodes.size(), "并发调用生成的任务编号必须全局唯一无重复");
    }
}
