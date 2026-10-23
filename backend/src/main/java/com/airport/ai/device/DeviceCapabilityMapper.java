package com.airport.ai.device;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;
import java.util.Optional;

@Mapper
public interface DeviceCapabilityMapper {
    Optional<DeviceCapability> findById(Long id);
    List<DeviceCapability> findByDeviceId(Long deviceId);
    Optional<DeviceCapability> findByDeviceIdAndCapabilityCode(@Param("deviceId") Long deviceId,
                                                                @Param("capabilityCode") String capabilityCode);
    boolean existsByDeviceIdAndCapabilityCode(@Param("deviceId") Long deviceId,
                                               @Param("capabilityCode") String capabilityCode);
    List<DeviceCapability> findByDeviceIdAndCapabilityStatus(@Param("deviceId") Long deviceId,
                                                              @Param("capabilityStatus") String capabilityStatus);
    long countByTemplateId(Long templateId);

    /** 全平台是否存在至少一个已启用的该能力类型（对应5.3.1业务规则4：步骤所需能力必须存在于已启用能力类型中） */
    boolean existsByCapabilityTypeAndCapabilityStatus(@Param("capabilityType") String capabilityType,
                                                        @Param("capabilityStatus") String capabilityStatus);

    /** 指定设备是否具备已启用的该能力类型（对应5.3.2业务规则2：试运行模拟设备能力匹配校验） */
    boolean existsByDeviceIdAndCapabilityTypeAndCapabilityStatus(@Param("deviceId") Long deviceId,
                                                                   @Param("capabilityType") String capabilityType,
                                                                   @Param("capabilityStatus") String capabilityStatus);
    int insert(DeviceCapability capability);
    int update(DeviceCapability capability);
}
