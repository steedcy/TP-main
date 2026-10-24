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
        result.put("impactScope", List.of("六个 SIM_F2_* 仿真设备档案及其能力画像",
                "三套预置基线模板", "超规行李、特殊旅客、航班变更三类预置任务定义"));
        result.put("preservedScope", List.of("历史任务及事件", "用户账号", "设备令牌和凭据标识", "其他设备"));
        result.put("postResetState", "设备连接及能力标记为未测试，基线模板标记为草稿；需要重新连接测试、能力测试和模板试运行后启用");
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
        if (!confirmed || !DemoDataset.CONFIRM_PHRASE.equals(phrase)) {
            throw new BusinessException(ErrorCode.PARAM_FORMAT_ERROR, "确认短语或二次确认不正确，数据未变更");
        }
        long started = System.nanoTime();
        try {
            String digest = worker.restore(operator, injectFailure);
            return Map.of("result", "SUCCESS", "version", DemoDataset.VERSION,
                    "sourceDigest", dataset.sourceDigest(), "contentDigest", digest,
                    "durationMs", (System.nanoTime() - started) / 1_000_000);
        } catch (RuntimeException ex) {
            long duration = (System.nanoTime() - started) / 1_000_000;
            String reason = ex instanceof BusinessException ? ex.getMessage() : ex.getClass().getSimpleName();
            audit.record(operator.getId(), operator.getUsername(), operator.getRole(), "DEMO_DATA_RESET",
                    DemoDataset.VERSION, "FAILED", null,
                    Map.of("sourceDigest", dataset.sourceDigest(), "durationMs", duration, "reason", reason));
            throw ex;
        }
    }
}
