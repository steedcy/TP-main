package com.airport.ai.event;

import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Set;
import java.util.TreeSet;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Stream;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

/** DEF-S3-057 / SRS_F027.R02：每条任务事件都有原因码；显式给出的保留，缺失的按事件类型补。 */
class EventReasonCodesTest {

    @Test
    void anExplicitReasonCodeIsAlwaysKept() {
        assertEquals("ERR_GOAL_UNRELATED", EventReasonCodes.resolve("GOAL_CLARIFIED", "ERR_GOAL_UNRELATED"));
        assertEquals("CUSTOM", EventReasonCodes.resolve("NOT_REGISTERED", "  CUSTOM  "));
    }

    @Test
    void aMissingReasonCodeIsFilledFromTheEventType() {
        for (String missing : new String[]{null, "", "   "}) {
            assertEquals("NORMAL_GOAL_SUBMITTED", EventReasonCodes.resolve("GOAL_SUBMITTED", missing));
            assertEquals("NORMAL_STEP_COMPLETED", EventReasonCodes.resolve("STEP_COMPLETED", missing));
            assertEquals("NORMAL_TASK_COMPLETED", EventReasonCodes.resolve("TASK_COMPLETED", missing));
            assertEquals("ERR_STEP_FAILED", EventReasonCodes.resolve("STEP_FAILED", missing));
        }
    }

    @Test
    void unknownOrNullEventTypesStillGetACode() {
        assertEquals(EventReasonCodes.FALLBACK, EventReasonCodes.resolve("SOME_NEW_EVENT", null));
        assertEquals(EventReasonCodes.FALLBACK, EventReasonCodes.resolve(null, null));
        assertEquals(EventReasonCodes.FALLBACK, EventReasonCodes.resolve(null, " "));
    }

    @Test
    void defaultsDistinguishNormalFlowFromErrorsAndWarnings() {
        for (var e : EventReasonCodes.defaults().entrySet()) {
            assertTrue(e.getValue().matches("(NORMAL|ERR|WARN)_[A-Z_]+"), e.getKey() + " -> " + e.getValue());
        }
        assertTrue(EventReasonCodes.defaults().get("TASK_FAILED").startsWith("ERR_"));
        assertTrue(EventReasonCodes.defaults().get("TASK_COMPLETED").startsWith("NORMAL_"));
    }

    @Test
    void appendNeverStoresAnEmptyReasonCode() {
        TaskEventMapper mapper = mock(TaskEventMapper.class);
        TaskEventService service = new TaskEventService(mapper);
        service.append(1L, "STEP_DISPATCHED", "SYSTEM", null, "已下发");
        service.append(1L, "STEP_FAILED", "SYSTEM", "DEVICE_API_ERROR", "设备失败");
        service.append(1L, "BRAND_NEW_EVENT", "SYSTEM", "", "x");
        ArgumentCaptor<TaskEvent> c = ArgumentCaptor.forClass(TaskEvent.class);
        verify(mapper, times(3)).insert(c.capture());
        assertEquals("NORMAL_STEP_DISPATCHED", c.getAllValues().get(0).getReasonCode());
        assertEquals("DEVICE_API_ERROR", c.getAllValues().get(1).getReasonCode());
        assertEquals(EventReasonCodes.FALLBACK, c.getAllValues().get(2).getReasonCode());
    }

    /**
     * 代码里写死事件类型字面量的 append 调用，其事件类型都应登记过默认码；
     * 否则它在不带原因码时只会拿到笼统的 NORMAL_EVENT，追溯页看不出是哪一步。
     * 新增事件类型时这条测试会提醒同步登记。
     */
    @Test
    void everyEventTypeAppendedInTheCodebaseHasARegisteredDefault() throws IOException {
        Pattern p = Pattern.compile("(?:taskEventService|events|eventService|taskEvents)\\s*\\.append\\([^,]+,\\s*\"([A-Z_]+)\"");
        Set<String> found = new TreeSet<>();
        try (Stream<Path> files = Files.walk(Path.of("src/main/java"))) {
            for (Path f : (Iterable<Path>) files.filter(x -> x.toString().endsWith(".java"))::iterator) {
                Matcher m = p.matcher(Files.readString(f, StandardCharsets.UTF_8));
                while (m.find()) found.add(m.group(1));
            }
        }
        assertFalse(found.isEmpty(), "没有扫描到任何事件类型，正则可能失效");
        Set<String> unregistered = new TreeSet<>(found);
        unregistered.removeAll(EventReasonCodes.defaults().keySet());
        // 这几类不属于任务事件时间线，或调用方一定会显式给出原因码，可以不登记
        unregistered.removeAll(Set.of("SWITCH_TO_BASELINE", "AGENT_ONLINE_RECOVERED", "AGENT_OFFLINE_DETECTED", "AGENT_REJECTED",
                "AGENT_STALE_TASK_REFERENCE_CLEARED", "STATUS_REPORT_FORMAT_INVALID", "REPLAN_DUPLICATE_IGNORED",
                "BASELINE_INPUT_BOUND", "BASELINE_INPUT_DEFAULTED", "TASK_MANUAL_ACTION_FAILED",
                "AGENT_BIND_FAILED", "AGENT_BOUND_TO_RUNTIME", "STATUS_REPORT_REJECTED"));
        assertTrue(unregistered.isEmpty(), "这些事件类型还没有登记默认原因码: " + unregistered);
    }
}
