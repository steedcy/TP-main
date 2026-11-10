package com.airport.ai.config;

import com.zaxxer.hikari.HikariConfig;
import com.zaxxer.hikari.HikariDataSource;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.jdbc.DataSourceProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Primary;

import javax.sql.DataSource;

/**
 * Hardened HikariCP DataSource Configuration for SRS_NF010 / NT-S3-011.
 * Explicitly constructs HikariDataSource from HikariConfig prior to pool startup,
 * ensuring all production pool parameters (pool-name, pool sizes, keepalive, leak detection)
 * are cleanly sealed without late property-binding race conditions.
 */
@Configuration(proxyBeanMethods = false)
public class DataSourceConfig {

    @Bean
    @Primary
    public DataSource dataSource(
            DataSourceProperties properties,
            @Value("${spring.datasource.hikari.minimum-idle:5}") int minIdle,
            @Value("${spring.datasource.hikari.maximum-pool-size:30}") int maxPoolSize,
            @Value("${spring.datasource.hikari.connection-timeout:30000}") long connTimeout,
            @Value("${spring.datasource.hikari.idle-timeout:600000}") long idleTimeout,
            @Value("${spring.datasource.hikari.max-lifetime:1800000}") long maxLifetime,
            @Value("${spring.datasource.hikari.keepalive-time:30000}") long keepaliveTime,
            @Value("${spring.datasource.hikari.validation-timeout:5000}") long validationTimeout,
            @Value("${spring.datasource.hikari.leak-detection-threshold:60000}") long leakThreshold) {

        HikariConfig config = new HikariConfig();
        config.setPoolName("AirportAiHikariPool");
        config.setJdbcUrl(properties.getUrl());
        config.setUsername(properties.getUsername());
        config.setPassword(properties.getPassword());
        config.setDriverClassName(properties.getDriverClassName());
        config.setMinimumIdle(minIdle);
        config.setMaximumPoolSize(maxPoolSize);
        config.setConnectionTimeout(connTimeout);
        config.setIdleTimeout(idleTimeout);
        config.setMaxLifetime(maxLifetime);
        config.setKeepaliveTime(keepaliveTime);
        config.setValidationTimeout(validationTimeout);
        config.setLeakDetectionThreshold(leakThreshold);
        return new HikariDataSource(config);
    }
}
