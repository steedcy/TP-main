package com.airport.ai.device;

import org.apache.ibatis.annotations.Mapper;

import java.util.List;

@Mapper
public interface DeviceEventMapper {
    List<DeviceEvent> findByDeviceAgentIdOrderByOccurredAtAsc(Long deviceAgentId);
    /** 最近一次离线事件（心跳超时或主动上报离线），用于页面展示离线时间与原因码 */
    DeviceEvent findLatestOffline(Long deviceAgentId);
    int insert(DeviceEvent event);
}
