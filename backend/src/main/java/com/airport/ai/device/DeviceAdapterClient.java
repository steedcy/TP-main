package com.airport.ai.device;

import com.airport.ai.common.BusinessException;
import com.airport.ai.common.ErrorCode;
import com.airport.ai.device.dto.DeviceBindingRequest;
import com.airport.ai.device.dto.DeviceCommandRequest;
import com.airport.ai.device.dto.SimulatorHealthResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.web.client.RestTemplateBuilder;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestTemplate;

import java.net.URI;
import java.time.Duration;
import java.time.OffsetDateTime;
import java.util.UUID;

/** HTTP transport adapter between the platform's single agent gateway and device-side runtimes. */
@Service
public class DeviceAdapterClient {
    private final RestTemplate restTemplate;
    private final DeviceCredentialService credentialService;
    private final String platformBaseUrl;

    public DeviceAdapterClient(RestTemplateBuilder builder,
                               DeviceCredentialService credentialService,
                               @Value("${app.device.adapter-connect-timeout-ms:2000}") int connectTimeoutMs,
                               @Value("${app.device.adapter-read-timeout-ms:3000}") int readTimeoutMs,
                               @Value("${app.device.adapter-public-base-url:http://localhost:8080}") String platformBaseUrl) {
        this.restTemplate = builder
                .setConnectTimeout(Duration.ofMillis(connectTimeoutMs))
                .setReadTimeout(Duration.ofMillis(readTimeoutMs))
                .build();
        this.credentialService = credentialService;
        this.platformBaseUrl = platformBaseUrl.replaceAll("/+$", "");
    }

    public SimulatorHealthResponse testConnection(Device device) {
        String nonce = UUID.randomUUID().toString();
        String url = endpoint(device, "/device-api/v1/health?nonce=" + nonce);
        try {
            ResponseEntity<SimulatorHealthResponse> response = restTemplate.exchange(
                    URI.create(url), HttpMethod.GET, authenticated(device), SimulatorHealthResponse.class);
            SimulatorHealthResponse health = response.getBody();
            if (!response.getStatusCode().is2xxSuccessful() || health == null
                    || !"1.0".equals(health.getProtocolVersion())
                    || !nonce.equals(health.getNonce())
                    || !device.getDeviceCode().equals(health.getDeviceCode())
                    || !"ONLINE".equals(health.getOnlineStatus())
                    || !("IDLE".equals(health.getWorkStatus()) || "BUSY".equals(health.getWorkStatus()))
                    || health.getLocation() == null || health.getLocation().getX() == null || health.getLocation().getY() == null
                    || health.getCapabilities() == null || health.getCapabilities().isEmpty()) {
                throw new DeviceAdapterException("健康握手响应字段无效或设备身份不匹配");
            }
            try {
                OffsetDateTime.parse(health.getReportedAt());
            } catch (Exception ex) {
                throw new DeviceAdapterException("健康握手reportedAt必须为ISO-8601时间");
            }
            String expectedType = Boolean.TRUE.equals(device.getIsSimulator())
                    ? device.getSimulatedDeviceType() : device.getDeviceTypeCode();
            String actualType = Boolean.TRUE.equals(device.getIsSimulator())
                    ? health.getSimulatedDeviceType() : health.getDeviceTypeCode();
            if (expectedType != null && !expectedType.equals(actualType)) {
                throw new DeviceAdapterException("设备类型与档案不匹配");
            }
            return health;
        } catch (RestClientException ex) {
            throw new DeviceAdapterException("设备连接失败: " + describeFailure(ex), ex);
        }
    }

    /**
     * 区分连接失败原因（DEF-S3-014、TC-009.S2）：连接被拒/不可达、连接超时、读取超时、HTTP状态异常、响应格式非法。
     */
    static String describeFailure(Throwable ex) {
        for (Throwable t = ex; t != null; t = t.getCause()) {
            if (t instanceof java.net.SocketTimeoutException) {
                String m = String.valueOf(t.getMessage()).toLowerCase();
                return m.contains("connect") ? "连接超时（建立连接超时）" : "读取超时（设备未在规定时间内响应）";
            }
            if (t instanceof java.net.ConnectException || t instanceof java.net.NoRouteToHostException) {
                return "设备不可达（连接被拒绝或无路由）";
            }
            if (t instanceof java.net.UnknownHostException) {
                return "设备不可达（主机名无法解析）";
            }
        }
        if (ex instanceof org.springframework.web.client.RestClientResponseException r) {
            return "设备接口返回HTTP " + r.getStatusCode().value();
        }
        if (ex instanceof org.springframework.web.client.UnknownContentTypeException
                || (ex.getMessage() != null && ex.getMessage().contains("Error while extracting response"))) {
            return "响应格式非法（无法解析为状态响应）";
        }
        return ex.getClass().getSimpleName();
    }

    public void bind(Device device, DeviceAgent agent, int heartbeatTimeoutSeconds) {
        DeviceBindingRequest request = new DeviceBindingRequest(device.getDeviceCode(), agent.getAgentCode(),
                platformBaseUrl + "/device-api/v1/agents/" + agent.getAgentCode() + "/report",
                device.getStatusReportInterval(), heartbeatTimeoutSeconds);
        exchange(device, "/device-api/v1/agents/" + agent.getAgentCode() + "/binding", HttpMethod.POST,
                request, Void.class);
    }

    public void sendCommand(Device device, String agentCode, DeviceCommandRequest command) {
        if (command.getIssuedAt() == null) command.setIssuedAt(OffsetDateTime.now());
        exchange(device, "/device-api/v1/agents/" + agentCode + "/commands", HttpMethod.POST,
                command, Void.class);
    }

    public void setSimulatorOnline(Device device, boolean online) {
        exchange(device, "/device-api/v1/control/online?value=" + online, HttpMethod.POST, null,
                java.util.Map.class);
    }

    @SuppressWarnings("unchecked")
    public java.util.Map<String, Object> testCapability(Device device, String agentCode, String commandId,
                                                        String capabilityType, java.util.Map<String, Object> params) {
        return exchange(device, "/device-api/v1/agents/" + agentCode + "/capability-test", HttpMethod.POST,
                java.util.Map.of("commandId", commandId, "capabilityType", capabilityType, "inputParams", params),
                java.util.Map.class);
    }

    public void setSimulatorScenario(Device device, String scenarioResult) {
        exchange(device, "/device-api/v1/control/scenario", HttpMethod.POST,
                java.util.Map.of("scenarioResult", scenarioResult), java.util.Map.class);
    }

    private <T> T exchange(Device device, String path, HttpMethod method, Object body, Class<T> responseType) {
        try {
            ResponseEntity<T> response = restTemplate.exchange(URI.create(endpoint(device, path)), method,
                    authenticated(device, body), responseType);
            if (!response.getStatusCode().is2xxSuccessful()) {
                throw new DeviceAdapterException("设备接口返回HTTP " + response.getStatusCode().value());
            }
            return response.getBody();
        } catch (RestClientException ex) {
            throw new DeviceAdapterException("设备接口调用失败: " + describeFailure(ex), ex);
        }
    }

    private HttpEntity<?> authenticated(Device device) { return authenticated(device, null); }

    private HttpEntity<?> authenticated(Device device, Object body) {
        String token;
        try {
            token = credentialService.tokenFor(device);
        } catch (BusinessException ex) {
            throw ex;
        } catch (RuntimeException ex) {
            throw new DeviceAdapterException("设备访问令牌不可用", ex);
        }
        HttpHeaders headers = new HttpHeaders();
        headers.setBearerAuth(token);
        headers.setContentType(MediaType.APPLICATION_JSON);
        return new HttpEntity<>(body, headers);
    }

    private String endpoint(Device device, String path) {
        String base = device.getAccessEndpoint();
        if (base == null || base.isBlank()) throw new DeviceAdapterException("设备接口地址未配置");
        URI uri;
        try {
            uri = URI.create(base);
        } catch (IllegalArgumentException ex) {
            throw new DeviceAdapterException("设备接口地址格式错误", ex);
        }
        if (!("http".equalsIgnoreCase(uri.getScheme()) || "https".equalsIgnoreCase(uri.getScheme()))
                || uri.getHost() == null || uri.getUserInfo() != null) {
            throw new DeviceAdapterException("设备接口地址仅支持合法HTTP/HTTPS基址");
        }
        return base.replaceAll("/+$", "") + path;
    }
}
