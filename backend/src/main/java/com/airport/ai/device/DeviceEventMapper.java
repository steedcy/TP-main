package com.airport.ai.device;

import org.apache.ibatis.annotations.Mapper;

import java.util.List;

@Mapper
public interface DeviceEventMapper {
    List<DeviceEvent> findByDeviceAgentIdOrderByOccurredAtAsc(Long deviceAgentId);
    int insert(DeviceEvent event);
}
