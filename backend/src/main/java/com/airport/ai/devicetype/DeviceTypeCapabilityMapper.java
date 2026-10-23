package com.airport.ai.devicetype;

import org.apache.ibatis.annotations.Mapper;

import java.util.List;
import java.util.Optional;

@Mapper
public interface DeviceTypeCapabilityMapper {
    List<DeviceTypeCapability> findAll();
    Optional<DeviceTypeCapability> findByDeviceTypeCode(String deviceTypeCode);
    int insert(DeviceTypeCapability entity);
    int update(DeviceTypeCapability entity);
}
