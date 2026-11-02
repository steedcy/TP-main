package com.airport.ai.task;

import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDateTime;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/** DEF-S3-006 / SRS_F020.R06：任务列表按目标关键字筛选；LIKE 通配符按字面处理，空白不筛选。 */
class TaskGoalKeywordF020Test {

    @Test
    void blankAndNullKeywordsMeanNoFilter() {
        assertNull(TaskService.escapeLike(null));
        assertNull(TaskService.escapeLike(""));
        assertNull(TaskService.escapeLike("   "));
    }

    @Test
    void ordinaryKeywordIsTrimmedAndKeptAsIs() {
        assertEquals("超规行李", TaskService.escapeLike("  超规行李 "));
        assertEquals("F2_TEST", TaskService.escapeLike("F2_TEST").replace("\\", ""), "下划线被转义但字符保留");
    }

    @Test
    void likeWildcardsAndEscapeCharacterAreTreatedAsLiterals() {
        assertEquals("100\\%", TaskService.escapeLike("100%"));
        assertEquals("a\\_b", TaskService.escapeLike("a_b"));
        assertEquals("a\\\\b", TaskService.escapeLike("a\\b"));
        assertEquals("\\%\\_\\\\", TaskService.escapeLike("%_\\"));
        // 只有通配符的输入不会变成“匹配全部”
        assertNotEquals("%", TaskService.escapeLike("%"));
        assertNotEquals("_", TaskService.escapeLike("_"));
    }

    @Test
    void overlongKeywordIsCutToOneHundredCharacters() {
        assertEquals(100, TaskService.escapeLike("x".repeat(500)).length());
    }

    @Test
    void keywordIsPassedToTheMapperAndTheOldSignatureStillMeansNoKeyword() {
        TaskMapper mapper = mock(TaskMapper.class);
        when(mapper.searchPaged(any(), any(), any(), any(), any(), any())).thenReturn(List.of());
        TaskService service = new TaskService(mapper, mock(PlanVersionMapper.class), mock(ContextSnapshotMapper.class),
                mock(com.airport.ai.device.DeviceAgentMapper.class), mock(com.airport.ai.planning.GoalUnderstandingService.class),
                mock(TaskCodeGenerator.class), mock(com.airport.ai.event.TaskEventService.class),
                mock(com.airport.ai.auth.OperationLogService.class), mock(TaskPlanningOrchestrator.class),
                mock(TaskStepAssignmentMapper.class), mock(com.airport.ai.taskdef.TaskDefinitionService.class),
                mock(com.airport.ai.device.DeviceAgentMessagingService.class));
        service.list(null, null, null, "航班", null, null, 1, 20);
        ArgumentCaptor<String> keyword = ArgumentCaptor.forClass(String.class);
        verify(mapper).searchPaged(isNull(), isNull(), isNull(), keyword.capture(), isNull(), isNull());
        assertEquals("航班", keyword.getValue());

        reset(mapper);
        when(mapper.searchPaged(any(), any(), any(), any(), any(), any())).thenReturn(List.of());
        service.list(null, null, null, LocalDateTime.now().minusDays(1), null, 1, 20);
        verify(mapper).searchPaged(isNull(), isNull(), isNull(), isNull(), any(), isNull());
    }

    @Test
    void mapperSqlFiltersGoalCaseInsensitivelyWithAnExplicitEscapeCharacter() throws Exception {
        String xml = Files.readString(Path.of("src/main/resources/mapper/TaskMapper.xml"), StandardCharsets.UTF_8);
        String select = xml.substring(xml.indexOf("id=\"searchPaged\""), xml.indexOf("id=\"countByStatus\""));
        assertTrue(select.contains("goalKeyword != null"));
        assertTrue(select.contains("task_goal ILIKE"));
        assertTrue(select.contains("ESCAPE '\\'"), "转义字符必须显式声明，否则转义后的通配符在不同库里含义不一致");
        assertTrue(select.contains("is_dry_run = FALSE"), "试运行任务仍不进入任务列表");
    }
}
