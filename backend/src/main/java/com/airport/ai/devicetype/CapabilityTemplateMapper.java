package com.airport.ai.devicetype;

import org.apache.ibatis.annotations.Mapper;

import java.util.List;
import java.util.Optional;

@Mapper
public interface CapabilityTemplateMapper {
    Optional<CapabilityTemplate> findById(Long id);
    List<CapabilityTemplate> findByDeviceTypeCode(String deviceTypeCode);
    Optional<CapabilityTemplate> findByDeviceTypeCodeAndTemplateCode(String deviceTypeCode, String templateCode);
    boolean existsByDeviceTypeCodeAndTemplateCode(String deviceTypeCode, String templateCode);
    long countByDeviceTypeCode(String deviceTypeCode);
    int insert(CapabilityTemplate entity);
    int update(CapabilityTemplate entity);
    int deleteById(Long id);
}
