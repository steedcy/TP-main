package com.airport.ai.planning;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.web.client.RestTemplateBuilder;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestTemplate;

import java.time.Duration;

/**
 * 外部规划模型服务的HTTPS调用实现，对应附录A第3.4节。
 * 单次请求60秒超时（对应SRS_NF008）；地址与凭据通过环境变量注入，不写入代码或配置文件明文。
 * 具体接入哪个模型服务/鉴权方式待确认（见开发任务清单"待确认问题"第3项），
 * 当前实现为通用HTTPS POST骨架，字段契约按附录B 5.1节。
 */
@Service
@ConditionalOnProperty(name = "app.planning-model.provider", havingValue = "external", matchIfMissing = true)
public class ExternalPlanningModelServiceImpl implements PlanningModelService {

    private final RestTemplate restTemplate;
    private final String endpoint;
    private final String apiKey;

    public ExternalPlanningModelServiceImpl(RestTemplateBuilder builder,
                                             @Value("${app.planning-model.endpoint:}") String endpoint,
                                             @Value("${app.planning-model.api-key:}") String apiKey,
                                             @Value("${app.planning-model.timeout-ms:60000}") long timeoutMs) {
        this.restTemplate = builder
                .setConnectTimeout(Duration.ofMillis(timeoutMs))
                .setReadTimeout(Duration.ofMillis(timeoutMs))
                .build();
        // 与ExternalGoalUnderstandingServiceImpl共用同一base地址配置（附录B 5.1节"与5.1A共用模型
        // 服务地址和鉴权配置；请求路径固定追加后缀区分端点"），此前直接裸用endpoint未追加路径，
        // 与目标理解端点的拼接约定不一致，是此前从未被validate过的真实缺陷（B3~B8验证时绕开了
        // 目标理解阶段，未触发本类调用路径的不一致）
        this.endpoint = endpoint == null || endpoint.isBlank() ? "" : endpoint + "/v1/planning/generate";
        this.apiKey = apiKey;
    }

    @Override
    public PlanningResponse generatePlan(PlanningRequest request) {
        if (endpoint == null || endpoint.isBlank()) {
            PlanningResponse resp = new PlanningResponse();
            resp.setResultCode("1004");
            resp.setErrorMessage("规划模型服务地址未配置");
            return resp;
        }
        try {
            HttpHeaders headers = new HttpHeaders();
            headers.setBearerAuth(apiKey);
            headers.set("X-Request-ID", request.getRequestId());
            HttpEntity<PlanningRequest> entity = new HttpEntity<>(request, headers);
            return restTemplate.exchange(endpoint, HttpMethod.POST, entity, PlanningResponse.class).getBody();
        } catch (RestClientException ex) {
            // 超时/网络异常统一转失败结果，由调用方（任务规划模块）转5.4.6高风险基线降级，不在此处重试
            PlanningResponse resp = new PlanningResponse();
            resp.setResultCode("1003");
            resp.setErrorMessage("规划模型服务调用超时或不可用: " + ex.getMessage());
            return resp;
        }
    }
}
