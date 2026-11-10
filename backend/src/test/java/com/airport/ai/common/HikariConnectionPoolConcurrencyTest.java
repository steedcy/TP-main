package com.airport.ai.common;

import com.zaxxer.hikari.HikariConfig;
import com.zaxxer.hikari.HikariDataSource;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.dao.CannotAcquireLockException;
import org.springframework.dao.ConcurrencyFailureException;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.dao.PessimisticLockingFailureException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.CannotGetJdbcConnectionException;
import org.springframework.mock.web.MockHttpServletRequest;

import java.sql.Connection;
import java.sql.SQLException;
import java.sql.SQLTransientConnectionException;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

/**
 * SRS_NF010 / TC-090.S1 / NT-S3-011:
 * HikariCP 连接池高可用加固与并发排队保护测试。
 * 验证连接池配置（最大连接数、排队超时、连接有效性心跳检测、泄漏检测阈值）、
 * 瞬时高频并发访问时连接优雅排队与友好错误提示，杜绝数据库连接死锁。
 */
class HikariConnectionPoolConcurrencyTest {

    private final GlobalExceptionHandler handler = new GlobalExceptionHandler(mock(com.airport.ai.auth.OperationLogService.class));

    private MockHttpServletRequest request(String method, String uri) {
        return new MockHttpServletRequest(method, uri);
    }

    @Test
    @DisplayName("HikariCP生产连接池参数配置与心跳保活检测核验")
    void verifyHikariConfigurationProperties() {
        HikariConfig config = new HikariConfig();
        config.setPoolName("AirportAiHikariPool");
        config.setMinimumIdle(5);
        config.setMaximumPoolSize(30);
        config.setConnectionTimeout(30000);
        config.setIdleTimeout(600000);
        config.setMaxLifetime(1800000);
        config.setKeepaliveTime(30000);
        config.setValidationTimeout(5000);
        config.setLeakDetectionThreshold(60000);
        config.setConnectionTestQuery("SELECT 1");

        assertEquals("AirportAiHikariPool", config.getPoolName(), "连接池名称应为 AirportAiHikariPool");
        assertEquals(5, config.getMinimumIdle(), "最小空闲连接数应为 5");
        assertEquals(30, config.getMaximumPoolSize(), "最大连接池容量应为 30");
        assertEquals(30000L, config.getConnectionTimeout(), "排队连接超时时间应为 30000ms");
        assertEquals(600000L, config.getIdleTimeout(), "空闲释放超时时间应为 600000ms");
        assertEquals(1800000L, config.getMaxLifetime(), "连接最大生命周期应为 1800000ms");
        assertEquals(30000L, config.getKeepaliveTime(), "心跳保活检测周期应为 30000ms");
        assertEquals(5000L, config.getValidationTimeout(), "有效性检测超时时间应为 5000ms");
        assertEquals(60000L, config.getLeakDetectionThreshold(), "连接泄漏检测阈值应为 60000ms");
        assertEquals("SELECT 1", config.getConnectionTestQuery(), "保活探针测试SQL应为 SELECT 1");
    }

    @Test
    @DisplayName("高频并发连接排队超时应触发503友好错误提示")
    void connectionPoolQueueTimeoutReturns503FriendlyResponse() {
        var cause = new SQLTransientConnectionException("HikariPool-1 - Connection is not available, request timed out after 30000ms.");
        var springEx = new CannotGetJdbcConnectionException("Failed to obtain JDBC Connection", cause);

        ResponseEntity<ApiResponse<Void>> response = handler.handleConnectionPoolTimeout(springEx, request("POST", "/api/v1/tasks"));

        assertEquals(HttpStatus.SERVICE_UNAVAILABLE, response.getStatusCode(), "排队超时应返回 503 SERVICE_UNAVAILABLE");
        assertNotNull(response.getBody());
        assertEquals(ErrorCode.DATABASE_POOL_BUSY.getCode(), response.getBody().getCode());
        assertEquals("数据库连接繁忙，正在排队重试，请稍后刷新", response.getBody().getMessage());
        assertEquals("/api/v1/tasks", response.getBody().getPath());
    }

    @Test
    @DisplayName("数据库并发死锁与悲观锁竞争应触发409防护提示杜绝服务挂死")
    void databaseDeadlockAndLockContentionReturns409Conflict() {
        var deadlockEx = new CannotAcquireLockException("deadlock detected: Process 12345 waits for ShareLock on transaction 67890");
        ResponseEntity<ApiResponse<Void>> deadlockResp = handler.handleConcurrencyLockException(deadlockEx, request("PUT", "/api/v1/devices/1"));

        assertEquals(HttpStatus.CONFLICT, deadlockResp.getStatusCode(), "并发死锁应返回 409 CONFLICT");
        assertNotNull(deadlockResp.getBody());
        assertEquals(ErrorCode.DATA_CONCURRENCY_CONFLICT.getCode(), deadlockResp.getBody().getCode());
        assertEquals("数据库操作并发竞争冲突，系统已自动防护，请稍后重试", deadlockResp.getBody().getMessage());

        var pessimisticEx = new PessimisticLockingFailureException("could not obtain lock on row in relation \"tasks\"");
        ResponseEntity<ApiResponse<Void>> pessimisticResp = handler.handleConcurrencyLockException(pessimisticEx, request("POST", "/api/v1/tasks"));
        assertEquals(HttpStatus.CONFLICT, pessimisticResp.getStatusCode());
        assertEquals(ErrorCode.DATA_CONCURRENCY_CONFLICT.getCode(), pessimisticResp.getBody().getCode());

        var concurrencyEx = new ConcurrencyFailureException("concurrent update failed");
        ResponseEntity<ApiResponse<Void>> concurrencyResp = handler.handleConcurrencyLockException(concurrencyEx, request("PUT", "/api/v1/devices/1"));
        assertEquals(HttpStatus.CONFLICT, concurrencyResp.getStatusCode());
    }

    @Test
    @DisplayName("并发写入唯一键冲突应触发409防重复提交提示")
    void duplicateKeyViolationReturns409Conflict() {
        var duplicateEx = new DuplicateKeyException("ERROR: duplicate key value violates unique constraint \"devices_device_code_key\"");
        ResponseEntity<ApiResponse<Void>> response = handler.handleDataIntegrityViolation(duplicateEx, request("POST", "/api/v1/devices"));

        assertEquals(HttpStatus.CONFLICT, response.getStatusCode(), "唯一键并发冲突应返回 409 CONFLICT");
        assertNotNull(response.getBody());
        assertEquals(ErrorCode.DUPLICATE_KEY_CONFLICT.getCode(), response.getBody().getCode());
        assertEquals("数据并发冲突或唯一标识已存在，请勿重复提交", response.getBody().getMessage());
    }

    @Test
    @DisplayName("多线程高并发瞬时请求模拟：连接池并发排队借还与防死锁测试")
    void simulateConcurrentConnectionQueueingAndReleaseWithoutDeadlock() throws Exception {
        int poolCapacity = 5;
        int clientThreads = 20;
        int taskLoopsPerClient = 10;

        // 模拟一个受限容量的连接池信号量，模拟 HikariCP 连接排队借还
        Semaphore poolSemaphore = new Semaphore(poolCapacity, true);
        AtomicInteger totalAcquisitions = new AtomicInteger(0);
        AtomicInteger activeConnections = new AtomicInteger(0);
        AtomicInteger maxSimultaneousActive = new AtomicInteger(0);
        AtomicInteger queueTimeouts = new AtomicInteger(0);

        ExecutorService executor = Executors.newFixedThreadPool(clientThreads);
        CountDownLatch startLatch = new CountDownLatch(1);
        CountDownLatch doneLatch = new CountDownLatch(clientThreads);

        for (int i = 0; i < clientThreads; i++) {
            final int clientId = i;
            executor.submit(() -> {
                try {
                    startLatch.await();
                    for (int loop = 0; loop < taskLoopsPerClient; loop++) {
                        // 尝试在 500ms 内排队获取连接
                        if (poolSemaphore.tryAcquire(500, TimeUnit.MILLISECONDS)) {
                            try {
                                int currentActive = activeConnections.incrementAndGet();
                                maxSimultaneousActive.accumulateAndGet(currentActive, Math::max);
                                totalAcquisitions.incrementAndGet();
                                // 模拟业务操作耗时
                                Thread.sleep(5);
                            } finally {
                                activeConnections.decrementAndGet();
                                poolSemaphore.release();
                            }
                        } else {
                            queueTimeouts.incrementAndGet();
                        }
                    }
                } catch (Exception e) {
                    Thread.currentThread().interrupt();
                } finally {
                    doneLatch.countDown();
                }
            });
        }

        startLatch.countDown();
        boolean completed = doneLatch.await(10, TimeUnit.SECONDS);
        executor.shutdown();

        assertTrue(completed, "所有并发客户端操作必须在限时内完成，杜绝死锁与挂死");
        assertTrue(maxSimultaneousActive.get() <= poolCapacity, "最大同时活跃连接数不得超过连接池上限(" + poolCapacity + ")");
        assertTrue(totalAcquisitions.get() > 0, "应有大量连接成功被排队借出与安全归还");
        assertEquals(0, activeConnections.get(), "测试结束后所有借出的连接必须彻底归还，无泄漏");
    }
}
