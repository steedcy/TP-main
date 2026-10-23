package com.airport.ai.common;

import org.springframework.http.HttpStatus;

/**
 * 统一错误码，对应附录B第3节错误码定义
 */
public enum ErrorCode {

    // 系统错误 1xxx
    SYSTEM_ERROR(1000, "系统内部错误", HttpStatus.INTERNAL_SERVER_ERROR),
    SERVICE_UNAVAILABLE(1001, "服务不可用", HttpStatus.SERVICE_UNAVAILABLE),

    // 认证授权错误 2xxx
    UNAUTHORIZED(2000, "未授权访问", HttpStatus.UNAUTHORIZED),
    SESSION_EXPIRED(2001, "会话已过期", HttpStatus.UNAUTHORIZED),
    LOGIN_FAILED(2002, "账号或密码错误", HttpStatus.UNAUTHORIZED),
    FORBIDDEN(2003, "无权限访问", HttpStatus.FORBIDDEN),
    ACCOUNT_INACTIVE(2004, "账号或密码错误", HttpStatus.FORBIDDEN),
    ACCOUNT_LOCKED(2005, "账号或密码错误", HttpStatus.FORBIDDEN),
    ACCOUNT_JUST_LOCKED(2006, "连续3次密码输入错误，账号已锁定", HttpStatus.FORBIDDEN),

    // 请求参数错误 3xxx
    PARAM_MISSING(3000, "请求参数缺失", HttpStatus.BAD_REQUEST),
    PARAM_FORMAT_ERROR(3001, "参数格式错误", HttpStatus.BAD_REQUEST),
    PARAM_OUT_OF_RANGE(3002, "参数值超出范围", HttpStatus.BAD_REQUEST),

    // 账号管理错误 40xx
    USER_NOT_FOUND(4001, "用户不存在", HttpStatus.NOT_FOUND),
    USERNAME_TAKEN(4002, "用户名已被占用", HttpStatus.CONFLICT),
    USER_NOT_LOCKED(4003, "用户未锁定，无需解锁", HttpStatus.BAD_REQUEST),
    CANNOT_DISABLE_SELF(4004, "不允许停用当前登录账号", HttpStatus.BAD_REQUEST),

    // 任务规划与执行错误 41xx
    TASK_NOT_FOUND(4101, "任务不存在", HttpStatus.NOT_FOUND),
    TASK_STATUS_NOT_ALLOWED(4102, "任务状态不允许操作", HttpStatus.CONFLICT),
    STRUCTURE_CHECK_FAILED(4103, "结构校验不通过", HttpStatus.BAD_REQUEST),
    CAPABILITY_CHECK_FAILED(4104, "能力校验不通过", HttpStatus.BAD_REQUEST),
    CONSTRAINT_CHECK_FAILED(4105, "约束校验不通过", HttpStatus.BAD_REQUEST),
    MOTION_SAFETY_FIELD_DETECTED(4106, "计划包含运动安全控制字段", HttpStatus.BAD_REQUEST),
    REPLAN_LIMIT_EXCEEDED(4107, "重新规划次数已达上限", HttpStatus.CONFLICT),
    NO_BASELINE_TEMPLATE(4108, "无可用基线模板", HttpStatus.NOT_FOUND),
    SUPERVISION_ON_UNVALIDATED_PLAN(4109, "试图对未通过校验的计划执行监督判定", HttpStatus.BAD_REQUEST),
    FORCE_BYPASS_HARD_CHECK(4110, "试图对硬性校验失败的计划强行放行", HttpStatus.BAD_REQUEST),
    NO_AVAILABLE_DEVICE_AGENT(4111, "当前无启用且在线的设备代理，任务不进入计划生成", HttpStatus.BAD_REQUEST),
    GOAL_UNRELATED_TO_ANY_FAMILY(4112, "任务目标与已定义任务族及能力类型完全无关", HttpStatus.BAD_REQUEST),
    GOAL_UNDERSTANDING_TIMEOUT(4113, "目标理解调用规划模型服务超时或异常", HttpStatus.SERVICE_UNAVAILABLE),
    TASK_INFO_INCOMPLETE(4114, "任务关键信息未补充完整，不得进入计划生成", HttpStatus.BAD_REQUEST),
    TASK_CANNOT_CANCEL_AFTER_PLANNING(4115, "任务已进入计划生成后不可取消，请使用终止流程", HttpStatus.CONFLICT),
    STEP_ASSIGNMENT_NOT_FOUND(4116, "步骤分配记录不存在", HttpStatus.NOT_FOUND),
    STEP_STATUS_NOT_ALLOWED(4117, "步骤当前状态不允许该操作", HttpStatus.CONFLICT),
    TASK_TERMINATE_NOT_ALLOWED(4118, "任务当前状态不可终止", HttpStatus.CONFLICT),
    TERMINATE_REASON_REQUIRED(4119, "终止任务须填写原因并二次确认", HttpStatus.BAD_REQUEST),

    // 设备与代理错误 42xx
    DEVICE_NOT_FOUND(4201, "设备不存在", HttpStatus.NOT_FOUND),
    DEVICE_CODE_TAKEN(4202, "设备编码已存在", HttpStatus.CONFLICT),
    DEVICE_CONNECTION_TEST_FAILED(4203, "设备连接测试未通过", HttpStatus.BAD_REQUEST),
    DEVICE_AGENT_NOT_FOUND(4204, "设备代理不存在", HttpStatus.NOT_FOUND),
    DEVICE_AGENT_ALREADY_EXISTS(4205, "设备已存在启用代理", HttpStatus.CONFLICT),
    DEVICE_HAS_ACTIVE_TASK(4206, "设备存在进行中任务，不可删除", HttpStatus.CONFLICT),
    DEVICE_OFFLINE(4207, "设备离线", HttpStatus.BAD_REQUEST),
    ACCESS_OBJECT_LIMIT_EXCEEDED(4208, "接入对象数量已达上限", HttpStatus.CONFLICT),
    DEVICE_TOKEN_NOT_CONFIGURED(4209, "设备访问令牌未配置", HttpStatus.CONFLICT),
    DEVICE_CREDENTIAL_KEY_NOT_CONFIGURED(4210, "设备凭据加密密钥未配置", HttpStatus.CONFLICT),

    // 能力管理错误 43xx
    CAPABILITY_CODE_TAKEN(4301, "能力编码已存在", HttpStatus.CONFLICT),
    CAPABILITY_OUT_OF_BOUNDARY(4302, "能力类型超出设备类型边界", HttpStatus.BAD_REQUEST),
    CAPABILITY_NOT_TESTED(4303, "能力未通过模拟调用测试", HttpStatus.BAD_REQUEST),
    CAPABILITY_DISABLED(4304, "能力已停用，不参与规划", HttpStatus.BAD_REQUEST),
    DEVICE_TYPE_NO_CAPABILITY(4305, "设备类型不支持任何能力类型", HttpStatus.BAD_REQUEST),
    CAPABILITY_TEMPLATE_IN_USE(4306, "能力模板已被设备实例使用，不可删除", HttpStatus.CONFLICT),

    // 基线模板错误 44xx
    TEMPLATE_NAME_TAKEN(4401, "模板名称已存在", HttpStatus.CONFLICT),
    TEMPLATE_NOT_DRY_RUN_PASSED(4402, "模板未试运行或试运行未通过", HttpStatus.BAD_REQUEST),
    TEMPLATE_STEP_LIMIT_EXCEEDED(4403, "模板步骤总数超过5", HttpStatus.BAD_REQUEST),
    PRESET_TEMPLATE_CANNOT_DELETE(4404, "预置任务族模板不可删除", HttpStatus.BAD_REQUEST),
    TEMPLATE_VERSION_CHANGED(4405, "模板版本已变更，需重新试运行", HttpStatus.BAD_REQUEST),
    TEMPLATE_CAPABILITY_GAP(4406, "步骤所需能力不存在于已启用能力类型中", HttpStatus.BAD_REQUEST),
    TEMPLATE_PARAM_MAPPING_INVALID(4407, "参数映射引用未定义变量或必填参数无来源", HttpStatus.BAD_REQUEST),
    DRY_RUN_DEVICE_MISMATCH(4408, "模拟设备未选择或能力不匹配", HttpStatus.BAD_REQUEST),
    BASELINE_TEMPLATE_NOT_FOUND(4409, "基线模板不存在", HttpStatus.NOT_FOUND),

    // 风险规则错误 45xx
    RISK_RULE_CODE_TAKEN(4501, "规则编号已存在", HttpStatus.CONFLICT),
    SUPERVISION_SERVICE_UNAVAILABLE(4502, "监督服务不可用或判定超时", HttpStatus.SERVICE_UNAVAILABLE),
    SUPERVISION_UNDETERMINED(4503, "监督智能体输出无法确定", HttpStatus.OK),

    // 任务定义错误 46xx（对应5.6.1旅客服务任务定义管理）
    TASK_DEFINITION_NOT_FOUND(4601, "任务定义不存在", HttpStatus.NOT_FOUND),
    TASK_DEFINITION_NAME_TAKEN(4602, "任务名称已存在", HttpStatus.CONFLICT),
    PRESET_DEFINITION_CANNOT_DELETE(4603, "预置任务族不可删除", HttpStatus.BAD_REQUEST),
    TASK_DEFINITION_CAPABILITY_GAP(4604, "引用的能力类型未启用或不存在", HttpStatus.BAD_REQUEST),
    TASK_FAMILY_INVALID(4605, "任务族不存在或已停用", HttpStatus.BAD_REQUEST),

    // 外部依赖错误 5xxx
    PLANNING_MODEL_CALL_FAILED(5001, "规划模型服务调用失败", HttpStatus.INTERNAL_SERVER_ERROR),
    PLANNING_MODEL_UNAVAILABLE(5002, "规划模型服务不可用", HttpStatus.SERVICE_UNAVAILABLE),
    DEVICE_API_TIMEOUT(5003, "设备接口调用超时", HttpStatus.INTERNAL_SERVER_ERROR);

    private final int code;
    private final String message;
    private final HttpStatus httpStatus;

    ErrorCode(int code, String message, HttpStatus httpStatus) {
        this.code = code;
        this.message = message;
        this.httpStatus = httpStatus;
    }

    public int getCode() { return code; }
    public String getMessage() { return message; }
    public HttpStatus getHttpStatus() { return httpStatus; }
}
