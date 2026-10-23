package com.airport.ai.baseline;

import org.apache.ibatis.annotations.Mapper;

import java.util.List;

@Mapper
public interface DryRunDeviceSelectionMapper {
    List<DryRunDeviceSelection> findByTaskId(Long taskId);
    int insert(DryRunDeviceSelection selection);
}
