package com.airport.ai.simulator;

import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

/** SRS_F007.R02：承接、执行、取消各用独立指令编号，仿真体按任务+步骤把它们关联到同一业务。 */
class DistinctCommandIdsTest {

    private SimulatorRuntime runtime(String scenario) {
        SimulatorProperties properties = new SimulatorProperties();
        properties.setExecutionDelayMilliseconds(0);
        properties.setScenarioResult(scenario);
        return new SimulatorRuntime(properties, List.of(new SmartDisplayDriver()));
    }

    private SimulatorProtocol.Command cmd(String id, String type, int attempt, String task, Integer step) {
        return new SimulatorProtocol.Command(id, type, attempt, task, step, "CAP_INFO_DISPLAY", Map.of(), null, null);
    }

    @Test
    void cancelWithItsOwnIdReleasesTheStepAcceptedAndExecutedUnderOtherIds() throws Exception {
        SimulatorRuntime r = runtime("NO_FEEDBACK");
        r.accept(cmd("CMD-A", "TASK_ACCEPT", 0, "TASK-1", 1));
        r.accept(cmd("CMD-E", "EXECUTE_CAPABILITY", 0, "TASK-1", 1));
        Thread.sleep(100);
        assertEquals("BUSY", r.health("n1").workStatus());
        r.accept(cmd("CMD-C", "TASK_CANCEL", 0, "TASK-1", 1));
        assertEquals("IDLE", r.health("n2").workStatus());
    }

    @Test
    void cancelForAnotherStepDoesNotReleaseTheRunningOne() throws Exception {
        SimulatorRuntime r = runtime("NO_FEEDBACK");
        r.accept(cmd("CMD-A", "TASK_ACCEPT", 0, "TASK-1", 1));
        r.accept(cmd("CMD-E", "EXECUTE_CAPABILITY", 0, "TASK-1", 1));
        Thread.sleep(100);
        r.accept(cmd("CMD-C", "TASK_CANCEL", 0, "TASK-1", 2));
        assertEquals("BUSY", r.health("n").workStatus());
        r.accept(cmd("CMD-C2", "TASK_CANCEL", 0, "TASK-2", 1));
        assertEquals("BUSY", r.health("n").workStatus());
    }

    @Test
    void wholeTaskCancelWithoutAStepReleasesTheRunningStep() throws Exception {
        SimulatorRuntime r = runtime("NO_FEEDBACK");
        r.accept(cmd("CMD-A", "TASK_ACCEPT", 0, "TASK-1", 1));
        r.accept(cmd("CMD-E", "EXECUTE_CAPABILITY", 0, "TASK-1", 1));
        Thread.sleep(100);
        r.accept(cmd("CMD-C", "TASK_CANCEL", 0, "TASK-1", null));
        assertEquals("IDLE", r.health("n").workStatus());
    }

    @Test
    void aNewAcceptOfTheSameStepAfterACancelStartsFresh() throws Exception {
        SimulatorRuntime r = runtime("NO_FEEDBACK");
        r.accept(cmd("CMD-A", "TASK_ACCEPT", 0, "TASK-1", 1));
        r.accept(cmd("CMD-C", "TASK_CANCEL", 0, "TASK-1", 1));
        assertEquals("IDLE", r.health("n").workStatus());
        r.accept(cmd("CMD-A2", "TASK_ACCEPT", 0, "TASK-1", 1));
        r.accept(cmd("CMD-E2", "EXECUTE_CAPABILITY", 0, "TASK-1", 1));
        Thread.sleep(100);
        assertEquals("BUSY", r.health("n").workStatus(), "旧取消标记不应让新的承接/执行被当作已取消");
    }

    @Test
    void retryOfTheSameExecuteIdAndAttemptIsIdempotent() throws Exception {
        SimulatorRuntime r = runtime("NO_FEEDBACK");
        r.accept(cmd("CMD-A", "TASK_ACCEPT", 0, "TASK-1", 1));
        r.accept(cmd("CMD-E", "EXECUTE_CAPABILITY", 0, "TASK-1", 1));
        r.accept(cmd("CMD-E", "EXECUTE_CAPABILITY", 0, "TASK-1", 1));
        r.accept(cmd("CMD-E", "EXECUTE_CAPABILITY", 1, "TASK-1", 1));
        Thread.sleep(100);
        assertEquals("BUSY", r.health("n").workStatus());
    }
}
