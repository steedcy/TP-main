import json, pathlib, shutil
ROOT=pathlib.Path(__file__).resolve().parents[1]; E=ROOT/"document/formal-test-evidence"
p=E/"R06-results.json"; data=json.loads(p.read_text(encoding="utf-8"))
tc37=next(x for x in data["results"] if x["id"]=="TC-037");tc37["conclusion"]="F"
data["summary"]={k:sum(1 for x in data["results"] if x["conclusion"]==k) for k in ("P","F","NT")}
p.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
detail='''# R06 正式测试补测明细

- 执行日期：2026-10-23（Asia/Shanghai）。
- 范围：复测 TC-035、TC-036、TC-037、TC-041、TC-045、TC-046、TC-047、TC-061，并定向更正 TC-052 步骤备注。依据为 2026-09-10 SRS V1.0、桌面《测试用例V2.xls》原用例步骤/预期及正式批次规则。
- 本批合并结论：P 0，F 1，NT 8。TC-037 自主候选计划违反原用例硬约束，实测 F；其余用例仍至少有未覆盖步骤或分支，记 NT。TC-052结论及步骤结果不变，仅校正证据措辞。
- 所有新增任务均使用虚构航班和脱敏场景；没有记录或输出密钥、密码或设备令牌。本批未执行 TC-091，未关机。

## 执行证据与裁定

- **真实 Moonshot/Kimi**：任务200使用完整虚构场景，未要求补充信息，目标理解 reasonCode 为空；生成两个上下文快照和自主计划V1。候选计划含5个动作步骤及目标、能力、参数、前置、完成、失败处理信息，但触发运动安全字段及任务族能力约束失败；平台转入已校验基线，完成两步业务任务。原始请求、计划版本、事件、快照、分配及设备反馈保存在 `R06-TC037-live-kimi.json`。
- **目标理解澄清复核**：任务201的真实Kimi首轮事件为 `GOAL_CLARIFIED.reasonCode=INFO_INCOMPLETE`，并返回待补充问题。按问题原文提交逐项答案；之后目标理解事件 reasonCode 为空，流程进入快照和计划。受控机器人离线注入未保持为离线状态，第二个快照来自基线降级，不是首次上下文变化后的自主局部重规划。证据见 `R06-TC035-replan-context.json`。因此旧批次187/188/189/190的PLANNING且无快照/计划，依据 `INFO_INCOMPLETE` 应理解为等待澄清的正常流程，不是规划故障。
- **TC-035**：真实快照展示原六代理能力、在线状态、位置、负载、可用时间及生成时间；禁用/归档及未测试/失败能力完整过滤仍缺。首次快照—事实变化—局部重规划及模型请求仅使用新快照的预期时序未建立，两个步骤均NT。
- **TC-036**：保留B05全部所需能力缺失时转人工且不调规划模型的P证据；单代理状态查询失败及快照失败清单仍无可控注入，步骤2 NT。
- **TC-037**：步骤1未完成计划解释、候选设备、参数来源及前台展示逐项核验，NT。步骤2实测自主V1第3步含“路径点”安全控制字段，第5步使用任务族未声明的 `CAP_ESCORT`；校验事件记录 `ERR_MOTION_SAFETY_FIELD` 和 `ERR_CAPABILITY_NOT_IN_TASK_DEFINITION`，约束校验失败，且该版本未冻结/执行。原预期要求仅引用已启用能力并通过校验后冻结，故步骤2 F、整条F。五动作的数量达到上限，但条件节点及分支计数没有实测。
- **TC-041**：沿用已测能力缺失及部分参数/安全/能力约束失败；资源冲突、无效完成条件未齐，步骤2 NT。失败版本未进入监督/设备分配，但没有对失败版本尝试监督或人工强行放行，步骤3 NT。
- **TC-045**：继续保留低置信度单信号记录及自动流转证据。0.8/60秒边界、超60秒、候选差异信号及组合仍未测，步骤1 NT，步骤2 P。
- **TC-046**：监督无法确定/不可用/超时未注入，步骤1 NT；未校验版本未进入监督且未尝试该判定入口，步骤2 NT。所有曾被误称“全局停滞”的187/188/189/190任务，原始事件 `INFO_INCOMPLETE` 表示等待补充信息，不构成监督或规划故障证据。
- **TC-047**：保留B06高风险、规划失败、模型不可用三个自动基线分支。R06新增自主候选约束失败后转入基线的真实任务证据；校验页主动切换仍未覆盖，步骤1 NT。同族多模板排序组未构造，步骤2 NT。
- **TC-061**：保留B08剩余额度3而返回4步的超额拒绝证据；额度0、剩余步骤计数、条件节点及分支动作总额仍缺，两个步骤均NT。
- **TC-052措辞更正**：保持原结论NT、第一步P、第二步NT。修订后的第二步备注明确：B07任务103在分配前被能力校验拦截，R04任务190为 `INFO_INCOMPLETE` 的目标理解等待补充信息；均未覆盖分配阶段全部候选主动拒绝。没有把离线或等待澄清称为模型停滞/全拒绝。

## 环境恢复

- 最终提供方仍为真实 Moonshot/Kimi；新增任务200、201均为COMPLETED。
- 六个原代理均为ONLINE/IDLE，三个原预置基线均ENABLED；本批将SIM_F2_ROBOT及SIM_F2_ROBOT_B置离线的注入均已发送恢复ONLINE并核实最终在线。
- SIM_F2_ROBOT_B仍报告已完成任务200的历史 `currentTaskId`，但工作状态为IDLE、无运行任务。这一观察已原样保留在 `R06-final-environment.json`，没有直接改数据库。
- TC-091未执行；没有关机。

## 结果簿与留档

- 更新前复制备份：`正式测试用例V2-执行结果.pre-R06-20261023.xls`。
- 更新只针对上述9条的结论、执行日期、逐步结果和备注。完成后核对95条总数、86条非目标用例结果字段、全部工作表单元格与样式。
- 原始 `R03-results.json` 保留不改；R06结果中更正TC-046/047旧措辞。TC-052维持既有结论和步骤判定，只更新措辞。

## 证据索引

- `R06-results.json`：R06逐步判定及amend输入。
- `R06-TC037-live-kimi.json`：真实Kimi任务200请求、目标理解、上下文、两个计划版本、校验、事件、设备分配与反馈。
- `R06-TC035-replan-context.json`：真实Kimi任务201原始澄清问题/答案、受控离线操作、上下文快照、计划、事件和恢复结果。
- `R06-final-environment.json`：提供方、六代理、三个基线及任务终态。
- `R06-book-verification.json`：amend后逐格值/格式核验。
- `正式测试用例V2-执行结果.pre-R06-20261023.xls`：写前备份。
'''
(E/"R06-detail.md").write_text(detail,encoding="utf-8")

# Preserve the pre-amend workbook before the only authorized write.
book=ROOT/"document/正式测试用例V2-执行结果.xls"
backup=ROOT/"document/正式测试用例V2-执行结果.pre-R06-20261023.xls"
if backup.exists(): raise SystemExit("R06 backup already exists; refusing to overwrite")
shutil.copy2(book,backup)
print(json.dumps({"summary":data["summary"],"backup":str(backup),"results":str(p),"detail":str(E/"R06-detail.md")},ensure_ascii=False))
