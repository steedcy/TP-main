package com.airport.ai.device;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

/** 分页搜索方法（searchPaged）配合PageHelper.startPage()使用，见DeviceAgentService */
@Mapper
public interface DeviceAgentMapper {
    Optional<DeviceAgent> findById(Long id);
    Optional<DeviceAgent> findByDeviceId(Long deviceId);
    Optional<DeviceAgent> findByAgentCode(String agentCode);
    boolean existsByDeviceId(Long deviceId);
    List<DeviceAgent> findByOnlineStatusAndLastReportedAtBefore(@Param("onlineStatus") String onlineStatus,
                                                                 @Param("threshold") LocalDateTime threshold);
    List<DeviceAgent> findByAgentStatusAndOnlineStatus(@Param("agentStatus") String agentStatus,
                                                        @Param("onlineStatus") String onlineStatus);
    List<DeviceAgent> searchPaged(@Param("agentStatus") String agentStatus,
                                   @Param("onlineStatus") String onlineStatus);
    /** 对应5.5.6人工终止业务规则3/4：查出当前任务占用的全部设备代理，逐一发送取消请求并释放占用 */
    List<DeviceAgent> findByCurrentTaskId(Long currentTaskId);
    /** 代理在待分配/降级执行中/执行中的正式任务步骤中的占用数（SRS_F003.R06），不含试运行任务 */
    long countActiveTaskAssignments(@Param("agentId") Long agentId);
    int insert(DeviceAgent agent);
    int update(DeviceAgent agent);
}
