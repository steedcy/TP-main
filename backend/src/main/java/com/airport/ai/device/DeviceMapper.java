package com.airport.ai.device;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;
import java.util.Optional;

/** 分页搜索方法（searchPaged）配合PageHelper.startPage()使用，见DeviceService */
@Mapper
public interface DeviceMapper {
    Optional<Device> findById(Long id);
    Optional<Device> findByDeviceCode(String deviceCode);
    boolean existsByDeviceCode(String deviceCode);
    List<Device> findByIds(@Param("ids") List<Long> ids);
    long countByDeviceStatusNot(String deviceStatus);
    long countByDeviceTypeCodeAndDeviceStatusNot(@Param("deviceTypeCode") String deviceTypeCode,
                                                  @Param("deviceStatus") String deviceStatus);
    int updateDeviceToken(@Param("deviceId") Long deviceId,
                          @Param("tokenHash") String tokenHash,
                          @Param("tokenCiphertext") String tokenCiphertext,
                          @Param("issuedAt") java.time.LocalDateTime issuedAt);
    List<Device> searchPaged(@Param("deviceTypeCode") String deviceTypeCode,
                              @Param("keyword") String keyword);
    int insert(Device device);
    int update(Device device);
}
