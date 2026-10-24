package com.airport.ai.device;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.Optional;

@Mapper
public interface DeviceCommandMapper {
    java.util.List<DeviceCommandRecord> findRecentByAgentCode(@Param("agentCode") String agentCode,
                                                               @Param("limit") int limit);
    int insertIfAbsent(DeviceCommandRecord command);
    java.util.List<DeviceCommandRecord> findUnconfirmedCancelBefore(@Param("threshold") java.time.LocalDateTime threshold);
    Optional<DeviceCommandRecord> findByKey(@Param("agentCode") String agentCode,
                                             @Param("commandId") String commandId,
                                             @Param("commandType") String commandType,
                                             @Param("attemptNo") Integer attemptNo);
    int updateStatus(@Param("agentCode") String agentCode,
                     @Param("commandId") String commandId,
                     @Param("commandType") String commandType,
                     @Param("attemptNo") Integer attemptNo,
                     @Param("status") String status,
                     @Param("responsePayload") String responsePayload);
}
