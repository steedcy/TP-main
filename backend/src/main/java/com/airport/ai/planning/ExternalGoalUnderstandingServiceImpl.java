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
 * 外部目标理解服务的HTTPS调用实现，对应附录A第3.4节、附录B 5.2节（方案A新增端点）。
 * 与ExternalPlanningModelServiceImpl共用同一模型服务地址与鉴权配置（app.planning-model.*），
 * 但请求路径追加固定后缀"/v1/goal/understand"，与候选计划生成端点"/v1/planning/generate"区分。
 * 单次请求60秒超时（对应5.4.1业务规则7）；超时或模型异常时不得触发设备指令，
 * 由调用方（TaskService）转为"不进入计划生成，提示稍后重试"，本类内部不做业务降级判断。
 */
@Service
@ConditionalOnProperty(name = "app.planning-model.provider", havingValue = "external", matchIfMissing = true)
public class ExternalGoalUnderstandingServiceImpl implements GoalUnderstandingService {

    private final RestTemplate restTemplate;
    private final String endpoint;
    private final String apiKey;

    public ExternalGoalUnderstandingServiceImpl(RestTemplateBuilder builder,
                                                 @Value("${app.planning-model.endpoint:}") String endpoint,
                                                 @Value("${app.planning-model.api-key:}") String apiKey,
                                                 @Value("${app.planning-model.timeout-ms:60000}") long timeoutMs) {
        this.restTemplate = builder
                .setConnectTimeout(Duration.ofMillis(timeoutMs))
                .setReadTimeout(Duration.ofMillis(timeoutMs))
                .build();
        this.endpoint = endpoint == null || endpoint.isBlank() ? "" : endpoint + "/v1/goal/understand";
        this.apiKey = apiKey;
    }

    @Override
    public GoalUnderstandingResponse understand(GoalUnderstandingRequest request) {
        if (endpoint.isBlank()) {
            GoalUnderstandingResponse resp = new GoalUnderstandingResponse();
            resp.setResultCode("1004");
            resp.setErrorMessage("规划模型服务地址未配置");
            return resp;
        }
        try {
            HttpHeaders headers = new HttpHeaders();
            headers.setBearerAuth(apiKey);
            headers.set("X-Request-ID", request.getRequestId());
            HttpEntity<GoalUnderstandingRequest> entity = new HttpEntity<>(request, headers);
            return restTemplate.exchange(endpoint, HttpMethod.POST, entity, GoalUnderstandingResponse.class).getBody();
        } catch (RestClientException ex) {
            // 超时/网络异常统一转失败结果，由调用方转"不进入计划生成"，不在此处重试
            GoalUnderstandingResponse resp = new GoalUnderstandingResponse();
            resp.setResultCode("1003");
            resp.setErrorMessage("目标理解服务调用超时或不可用: " + ex.getMessage());
            return resp;
        }
    }
}
