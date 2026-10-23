package com.airport.ai.device.dto;

import com.airport.ai.device.DeviceCommandRecord;

import java.time.LocalDateTime;

public record DeviceCommandView(Long id, String commandId, String commandType, Integer attemptNo, Long taskId,
                                Integer stepSeq, String capabilityType, String commandStatus,
                                LocalDateTime createdAt, LocalDateTime updatedAt) {
    public static DeviceCommandView from(DeviceCommandRecord command) {
        return new DeviceCommandView(command.getId(), command.getCommandId(), command.getCommandType(), command.getAttemptNo(),
                command.getTaskId(), command.getStepSeq(), command.getCapabilityType(), command.getCommandStatus(),
                command.getCreatedAt(), command.getUpdatedAt());
    }
}
