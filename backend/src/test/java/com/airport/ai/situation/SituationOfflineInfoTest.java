package com.airport.ai.situation;

import com.airport.ai.common.PageResult;
import com.airport.ai.device.*;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/** DEF-S3-047：态势快照里离线代理带原因码、离线时间和对任务的影响；在线代理没有这个字段。 */
class SituationOfflineInfoTest {
    private final DeviceAgentService agents = mock(DeviceAgentService.class);
    private final DeviceCapabilityMapper capabilities = mock(DeviceCapabilityMapper.class);
    private final SituationController controller = new SituationController(agents, capabilities);

    private DeviceAgent agent(long id, String code, String online) {
        DeviceAgent a = new DeviceAgent();
        a.setId(id);
        a.setAgentCode(code);
        a.setAgentStatus("ENABLED");
        a.setOnlineStatus(online);
        a.setWorkStatus("IDLE");
        return a;
    }

    private Device device(long id, String code) {
        Device d = new Device();
        d.setId(id);
        d.setDeviceCode(code);
        d.setDeviceName(code);
        d.setPositionX(new BigDecimal("10"));
        d.setPositionY(new BigDecimal("20"));
        return d;
    }

    @Test
    void offlineAgentCarriesReasonCodeAndTaskImpactWhileOnlineOneDoesNot() {
        DeviceAgent off = agent(1, "AGT-OFF", "OFFLINE");
        DeviceAgent on = agent(2, "AGT-ON", "ONLINE");
        PageResult<DeviceAgent> page = PageResult.of(new com.github.pagehelper.PageInfo<>(List.of(off, on)));
        when(agents.list(eq("ENABLED"), any(), anyInt(), anyInt())).thenReturn(page);
        when(agents.getDeviceOf(off)).thenReturn(device(1, "DEV-OFF"));
        when(agents.getDeviceOf(on)).thenReturn(device(2, "DEV-ON"));
        when(capabilities.findByDeviceIdAndCapabilityStatus(anyLong(), eq("ENABLED"))).thenReturn(List.of());
        when(agents.offlineInfo(off)).thenReturn(Map.of("reasonCode", "ERR_HEARTBEAT_TIMEOUT", "affectsTask", true,
                "offlineAt", LocalDateTime.of(2026, 10, 31, 10, 0)));
        when(agents.offlineInfo(on)).thenReturn(null);

        var markers = controller.snapshot().getData().agents();
        var offMarker = markers.stream().filter(m -> "AGT-OFF".equals(m.agentId())).findFirst().orElseThrow();
        var onMarker = markers.stream().filter(m -> "AGT-ON".equals(m.agentId())).findFirst().orElseThrow();
        assertEquals("ERR_HEARTBEAT_TIMEOUT", offMarker.offline().get("reasonCode"));
        assertEquals(true, offMarker.offline().get("affectsTask"));
        assertNull(onMarker.offline());
    }
}
