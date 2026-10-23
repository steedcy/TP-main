package com.airport.ai.task.dto;

import jakarta.validation.constraints.NotEmpty;

import java.util.Map;

/**
 * 对应5.4.1界面元素"待补充问题""提交补充信息"。answers以问题原文为key，
 * 运行操作员填写的补充内容为value；补充后系统重新执行目标理解（对应业务规则）。
 */
public class ClarifyTaskRequest {

    @NotEmpty(message = "请填写待补充问题的答案")
    private Map<String, String> answers;

    public Map<String, String> getAnswers() { return answers; }
    public void setAnswers(Map<String, String> answers) { this.answers = answers; }
}
