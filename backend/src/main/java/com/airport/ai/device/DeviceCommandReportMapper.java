package com.airport.ai.device;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

@Mapper
public interface DeviceCommandReportMapper {
    int insertIfAbsent(@Param("agentCode") String agentCode,
                       @Param("commandId") String commandId,
                       @Param("reportType") String reportType,
                       @Param("attemptNo") Integer attemptNo,
                       @Param("payloadHash") String payloadHash);
    String findPayloadHash(@Param("agentCode") String agentCode,
                           @Param("commandId") String commandId,
                           @Param("reportType") String reportType,
                           @Param("attemptNo") Integer attemptNo);
}
