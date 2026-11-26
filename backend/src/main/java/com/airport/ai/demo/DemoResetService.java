package com.airport.ai.demo;

import com.airport.ai.auth.OperationLogService;
import com.airport.ai.auth.User;
import com.airport.ai.common.BusinessException;
import com.airport.ai.common.ErrorCode;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@Service
public class DemoResetService {
    private final DemoDataset dataset;
    private final DemoResetWorker worker;
    private final OperationLogService audit;
    private final boolean enabled;

    public DemoResetService(DemoDataset dataset, DemoResetWorker worker, OperationLogService audit,
                            @Value("${app.demo-reset.enabled:false}") boolean enabled) {
        this.dataset = dataset;
        this.worker = worker;
        this.audit = audit;
        this.enabled = enabled;
    }

    public Map<String, Object> preview() {
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("enabled", enabled);
        result.put("version", DemoDataset.VERSION);
        result.put("generatedAt", DemoDataset.GENERATED_AT);
        result.put("sourceDigest", dataset.sourceDigest());
        result.put("currentContentDigest", worker.contentDigest());
        result.put("confirmationPhrase", DemoDataset.CONFIRM_PHRASE);
        result.put("impactScope", List.of(
                "2000×600 室内地图区域（18 条）与设施点位（68 个）",
                "20 台标准仿真体设备档案及其对齐附录 F 的能力画像与设备代理",
                "三套预置基线模板（V1.5 已启用）",
                "超规行李、特殊旅客、航班变更、通用协同服务四类预置场景规则",
                "三条风险规则与空间/距离校验规则基线参数"));
        result.put("preservedScope", List.of("历史任务及事件", "用户账号", "设备令牌和凭据标识", "非预置演示设备"));
        result.put("postResetState", "地图点位、20台仿真体设备及能力（已测试通过并启用）、三套基线模板（已启用）、四类预置场景与风险/校验规则均恢复至 V1.5 最新标准版本");
        result.put("blockingTasks", worker.blockingTasks());
        result.put("busyDemoAgents", worker.busyDemoAgents());
        return result;
    }

    public Map<String, Object> restore(String phrase, boolean confirmed, User operator) {
        return restoreInternal(phrase, confirmed, operator, false);
    }

    /** Package scope permits a controlled mid-transaction fault in the isolated integration test. */
    Map<String, Object> restoreWithInjectedFailureForTest(String phrase, boolean confirmed, User operator) {
        return restoreInternal(phrase, confirmed, operator, true);
    }

    private Map<String, Object> restoreInternal(String phrase, boolean confirmed, User operator, boolean injectFailure) {
        if (!enabled) throw new BusinessException(ErrorCode.SERVICE_UNAVAILABLE, "标准演示数据复位仅在隔离演示环境启用");
        String requestId = UUID.randomUUID().toString();
        String beforeDatasetVersion = worker.currentDatasetVersion();
        String beforeContentDigest = worker.contentDigest();
        if (!confirmed || !DemoDataset.CONFIRM_PHRASE.equals(phrase)) {
            recordFailure(operator, requestId, beforeDatasetVersion, beforeContentDigest,
                    "确认短语或二次确认不正确，数据未变更");
            throw new BusinessException(ErrorCode.PARAM_FORMAT_ERROR,
                    "确认短语或二次确认不正确，数据未变更；请求标识: " + requestId);
        }
        long started = System.nanoTime();
        try {
            DemoResetWorker.ResetOutcome outcome = worker.restore(operator, injectFailure, requestId,
                    beforeDatasetVersion, beforeContentDigest);
            return Map.of("result", "SUCCESS", "requestId", requestId,
                    "version", outcome.afterDatasetVersion(),
                    "beforeDatasetVersion", outcome.beforeDatasetVersion(),
                    "afterDatasetVersion", outcome.afterDatasetVersion(),
                    "beforeContentDigest", outcome.beforeContentDigest(),
                    "sourceDigest", dataset.sourceDigest(), "contentDigest", outcome.afterContentDigest(),
                    "durationMs", (System.nanoTime() - started) / 1_000_000);
        } catch (RuntimeException ex) {
            long duration = (System.nanoTime() - started) / 1_000_000;
            String reason = ex instanceof BusinessException ? ex.getMessage() : ex.getClass().getSimpleName();
            recordFailure(operator, requestId, beforeDatasetVersion, beforeContentDigest, reason, duration);
            if (ex instanceof BusinessException business) {
                throw new BusinessException(business.getErrorCode(), business.getMessage()
                        + "；请求标识: " + requestId);
            }
            throw ex;
        }
    }

    private void recordFailure(User operator, String requestId, String beforeDatasetVersion,
                               String beforeContentDigest, String reason) {
        recordFailure(operator, requestId, beforeDatasetVersion, beforeContentDigest, reason, null);
    }

    private void recordFailure(User operator, String requestId, String beforeDatasetVersion,
                               String beforeContentDigest, String reason, Long durationMs) {
        Map<String, Object> detail = new LinkedHashMap<>();
        detail.put("requestId", requestId);
        detail.put("beforeDatasetVersion", beforeDatasetVersion);
        detail.put("afterDatasetVersion", beforeDatasetVersion);
        detail.put("beforeContentDigest", beforeContentDigest);
        detail.put("afterContentDigest", beforeContentDigest);
        detail.put("attemptedDatasetVersion", DemoDataset.VERSION);
        detail.put("sourceDigest", dataset.sourceDigest());
        detail.put("reason", reason);
        if (durationMs != null) detail.put("durationMs", durationMs);
        audit.record(operator.getId(), operator.getUsername(), operator.getRole(), "DEMO_DATA_RESET",
                DemoDataset.VERSION, "FAILED", null, detail);
    }
}
