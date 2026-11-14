package com.airport.ai.device;

import org.junit.jupiter.api.Test;
import java.net.ServerSocket;
import java.net.Socket;
import java.nio.file.Path;
import java.nio.file.Files;
import java.util.List;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class ManagedSimulatorServiceTest {
    @org.junit.jupiter.api.io.TempDir Path temporary;

    @Test void occupiedListenerRemainsAliveWhenRestartIsRejected() throws Exception {
        Path jar = Files.writeString(temporary.resolve("runtime.jar"), "not launched");
        try (ServerSocket listener = new ServerSocket(0);
             ManagedSimulatorService service = new ManagedSimulatorService(mock(DeviceMapper.class), true, jar.toString())) {
            Device device = new Device(); device.setDeviceCode("EXTERNAL");
            device.setAccessEndpoint("http://127.0.0.1:" + listener.getLocalPort());
            assertThrows(IllegalStateException.class, () -> service.restart(device, "unused-test-token"));
            try (Socket connection = new Socket("127.0.0.1", listener.getLocalPort())) {
                assertTrue(connection.isConnected());
            }
            assertFalse(listener.isClosed());
        }
    }
    @Test void limitsManagementToLocalHttpRootWithExplicitUnprivilegedPort() {
        assertEquals(18100, ManagedSimulatorService.localPort("http://localhost:18100/"));
        for (String endpoint : List.of("http://example.com:18100", "https://127.0.0.1:18100", "http://127.0.0.1",
                "http://127.0.0.1:80", "http://u:p@127.0.0.1:18100", "http://127.0.0.1:18100/path", "file:///tmp"))
            assertThrows(IllegalArgumentException.class, () -> ManagedSimulatorService.localPort(endpoint), endpoint);
    }

    @Test void skipsDatabaseEndpointsAndKeepsConcurrentReservationsDistinct() {
        DeviceMapper mapper = mock(DeviceMapper.class);
        when(mapper.findActiveSimulatorEndpoints()).thenReturn(List.of("http://localhost:18100"));
        try (ManagedSimulatorService service = new ManagedSimulatorService(mapper, true, "missing.jar")) {
            String first = service.allocateEndpoint("A"); String second = service.allocateEndpoint("B");
            assertNotEquals(first, second); assertNotEquals("http://127.0.0.1:18100", first);
        }
    }
}
