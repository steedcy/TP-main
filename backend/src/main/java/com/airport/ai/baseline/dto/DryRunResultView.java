package com.airport.ai.baseline.dto;

import java.util.List;

/**
 * 对应5.3.2界面元素"试运行结果""事件时间线"、附录B 6.6节dry-run响应体
 */
public class DryRunResultView {

    private Long taskId;
    private String taskCode;
    private String result; // SUCCESS / FAILED
    private List<StepResult> stepResults;
    private List<EventView> events;
    private String failureReason;

    public static class StepResult {
        private Integer stepSeq;
        private String result;
        private Integer duration;
        private String failureReason;

        public StepResult(Integer stepSeq, String result, Integer duration, String failureReason) {
            this.stepSeq = stepSeq;
            this.result = result;
            this.duration = duration;
            this.failureReason = failureReason;
        }

        public Integer getStepSeq() { return stepSeq; }
        public String getResult() { return result; }
        public Integer getDuration() { return duration; }
        public String getFailureReason() { return failureReason; }
    }

    public static class EventView {
        private String eventType;
        private String trigger;
        private String detailSummary;
        private String occurredAt;

        public EventView(String eventType, String trigger, String detailSummary, String occurredAt) {
            this.eventType = eventType;
            this.trigger = trigger;
            this.detailSummary = detailSummary;
            this.occurredAt = occurredAt;
        }

        public String getEventType() { return eventType; }
        public String getTrigger() { return trigger; }
        public String getDetailSummary() { return detailSummary; }
        public String getOccurredAt() { return occurredAt; }
    }

    public Long getTaskId() { return taskId; }
    public void setTaskId(Long taskId) { this.taskId = taskId; }
    public String getTaskCode() { return taskCode; }
    public void setTaskCode(String taskCode) { this.taskCode = taskCode; }
    public String getResult() { return result; }
    public void setResult(String result) { this.result = result; }
    public List<StepResult> getStepResults() { return stepResults; }
    public void setStepResults(List<StepResult> stepResults) { this.stepResults = stepResults; }
    public List<EventView> getEvents() { return events; }
    public void setEvents(List<EventView> events) { this.events = events; }
    public String getFailureReason() { return failureReason; }
    public void setFailureReason(String failureReason) { this.failureReason = failureReason; }
}
