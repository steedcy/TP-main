"""Publish final F021 documentation only after verified evidence push."""
from pathlib import Path
import subprocess,json
R=Path(__file__).resolve().parents[2]
EVIDENCE='1c597f7aafb854e464e884e252f2fe9c80e22368'
def git(*args):return subprocess.check_output(['git',*args],cwd=R,encoding='utf8').strip()
assert git('rev-parse','origin/ai/gpt-test')==EVIDENCE
assert git('rev-parse','origin/main')=='a8d6409964085e4a500bd399bb1a6b4f6bfb2918'
assert git('rev-parse','V1.173^{commit}')=='761bd0b51af380c19b06357f815acda751905a3b'
def write(path,text):(R/path).write_bytes(text.encode('utf8'))
def replace_line(t,prefix,new):
 lines=t.splitlines();ix=next(i for i,x in enumerate(lines) if x.startswith(prefix));lines[ix]=new;return '\n'.join(lines)+'\n'
p='docs/HANDOFF.md';t=(R/p).read_text(encoding='utf8')
t=replace_line(t,'- 状态：','- 状态：`READY_FOR_CLAUDE`（F021 V1.173整轮未通过：8规则7P/1F/0NT、5步骤4P/1F/0NT；DEF-S3-059仅事件整体JSON残留，完整证据已先推送`'+EVIDENCE+'`；main未合本轮）')
t=replace_line(t,'- 当前代码 SHA：','- 当前代码 SHA：`761bd0b51af380c19b06357f815acda751905a3b`，唯一递增版本标签：`V1.173`（远端精确指向固定产品提交，不移动）')
t=replace_line(t,'- 当前进度：','- 当前进度：F001～F020已验收合main，main保持`a8d6409964085e4a500bd399bb1a6b4f6bfb2918`。F021全部适用项当前实测，059事件detail整体非JSON统一交修；无NT、不合main/无PR、不推进F022。')
t+=f'''
## 2026-11-07 GPT → Claude：SRS_F021 V1.173 整轮完成，统一交修059残留

- **READY_FOR_CLAUDE**：8规则**7P/1F/0NT**（仅R08 F），TC-066/TC-067正式五步骤**4P/1F/0NT**（仅TC-066.S3 F）。当前需求全部适用项本轮实测，历史业务P复用0；未以首F提前结束，未修改产品代替独立测试，未改变业务基线。
- **完整证据已先提交推送 `{EVIDENCE}`**，分支`ai/gpt-test`；首个最小反例检查点`fb44f7a`。本专节所在提交为正式交接SHA，以最终回复/远端实际提交核对；不要把证据SHA或产品标签误作交接文档SHA。
- 固定产品 **`761bd0b51af380c19b06357f815acda751905a3b` / `V1.173`**，Claude实际文档 **`f00536c595d291a495a5f7e55561dbf08823ac8c`**；远端分支、精确标签及上一个F020 main均已核对，消息与Git一致。测试worktree`C:/Users/savy/Desktop/TIP-main/tip-gpt-f013` / `ai/gpt-test`，日期2026-11-07、Asia/Shanghai，执行基线V2.4及已有BL006。
- **059原缺陷残留，不新建重复编号**：真实任务923（TASK-20261107-0913）完成步骤1、步骤2执行时人工终止。操作日志`TASK_TERMINATE.detail`已非空且为完整对象，945双设备映射`deviceCode/agentId/cancelCommandId/cancelStatus`与两取消持久记录逐项对应并最终确认空闲，属于当前子范围P。但`GET /api/v1/tasks/923/events`的`TASK_TERMINATED.detail`仍为中文说明文字拼接JSON数组，整体`json.loads`首字符失败，无法取得对象级`deviceCancelResults`；SQL持久事件同为说明文字，`TaskEvent.getDetail()`只是`detailSummary`别名，未满足本轮明确的完整JSON交接断言。原F和截图/HTTP/SQL原始数据均保留。
- **Claude下一步**：先fetch并接收本测试分支完整证据与正式交接；仅修059事件详情JSON及直接影响，保留独立的人类可读时间线摘要，核对事件持久化与REST整体可解析（reason、previousStatus、operator、deviceCancelResults及设备/取消编号/状态），不要仅增加别名或只修操作日志。保持已通过的安全释放门禁/终态/多设备/离线恢复/界面行为，提交并推送下一唯一递增V1.N标签后，F021重新整轮独立复测。
- **当前通过范围**：918原因省略/null/空/空白/201字/缺确认/false均400、业务完整快照不变；919精确200字与1字trim实际持久；936实际IAB弹窗空白或未确认禁用、201输入限200、取消不变、明确安全边界，真实终止首步COMPLETED/后二步FROZEN。923重试规划/转基线/置失败均409，澄清/取消/重复终止拒绝、迟到接受/反馈不恢复下发；其他禁止绕过动作按既有F013规则400/4110并保留拦截留痕。
- 六合法状态920及937～941终止200；三终态942～944终止409且完整业务快照不变；927～935真实UI六入口有/三终态无。921正常两步执行、948另一任务完成、949配置角色403（含缺参）/匿名401通过。状态SQL夹具不冒充自然瞬态生命周期。
- 925真实默认60秒取消未确认→TIMED_OUT，事件含设备/指令号和DEVICE_CANCEL_NO_CONFIRMATION，UI明确“保留占用待核查”，按已有BL006保留执行设备安全占用；OFFLINE IDLE/ONLINE BUSY不释放，相关ONLINE IDLE才CONFIRMED_IDLE并释放，重复确认幂等、任务不恢复。TC067旧“超时释放”须与此前已生效BL006合并解读，不为立即释放而取消物理运动安全门。历史DEF-R04-001无响应监控缺口本轮关联闭环，原F不追溯删除。
- 945多设备两独立取消均确认空闲；第二设备同任务占用明确SQL播种，不宣称自然并行规划。946离线实际执行设备DELIVERY_FAILED→CONFIRMED_IDLE、全部占用释放；离线触发另一预选候选的取消SENT不误当实际执行确认。947自然预选任务终止不撤销另一任务948当前占用，948正常完成。
- **数量及证据层级**：32持久任务=11实际协议/生命周期+21显式SQL状态夹具；20去重HTTP/SQL/合成设备组19P/1F、86断言85P/1F；4真实IAB Chromium界面组当前P、9状态入口、6截图。936同一真实UI终止与HTTP共证不重复计业务执行次数。433后端报告431通过/2原有跳过、0失败/错误；前后端生产构建和实际打包JAR健康/认证/业务HTTP通过，不扩大为物理设备或商业模型验证。
- 原始探针五次dict重复loads诊断、两处错误的终态断言、946误假定只一条取消/全部确认及两处UI包装器/异步文本断言全部保留并有独立更正。924/926部分取证不冒充完整通过，缺失断言补在945/946；不重复制造已充分同版观察、不把探针错误交Claude。
- 报告`acceptance/stage3/SRS_F021-V1.173-整轮独立复测与统一交修.md`；总索引`acceptance/stage3/evidence/SRS_F021-V1.173-complete-verification-20261107.json`及SHA256 manifest；原台账快照、原始HTTP两文件、UI JSON/截图/DOM、最小反例、离线断言更正、433项报告/构建、版本和清理证据已全部推送。台账只更新F021八规则/五步骤与059，不改其他需求历史结果；暂存4ec6695相应产品代码已实际纳入，事件残留仍F。
- **清理完毕**：GPT自有schema`tip_gpt_f006_v118_20261030`、Redis10；2定义DISABLED、3设备INACTIVE、活跃分配0、占用0、注入触发器0，无规则/模板修改。任务/版本/失败全部保留；核对命令归属后3自有进程树停止，18129/18117/18132～18134/15179六端口释放，Claude与共享PG/Redis未动。提交前扫描无本机密码/密钥/JWT、无原Office/DPAPI/JAR/无关用户文件。
- **main保持`a8d6409964085e4a500bd399bb1a6b4f6bfb2918`，本轮未合入，无PR**。主工作区既有文件未动，产品标签不移动。下一仅继续F021修复与整轮复测，不提前推进F022，不代表三核心场景或95项整体验收通过。正式交接推送核对后，HANDOFF单写入权顺序交Claude。

| 时间（Asia/Shanghai） | 需求 | 交接 | 状态 | 产品SHA/标签 | 完整证据SHA | main |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-11-07 | SRS_F021 | GPT → Claude | READY_FOR_CLAUDE，7P/1F/0NT，4P/1F/0NT | 761bd0b51af380c19b06357f815acda751905a3b / V1.173 | {EVIDENCE} | a8d6409964085e4a500bd399bb1a6b4f6bfb2918，未合本轮/无PR |
''';write(p,t)
p='docs/ROADMAP.md';t=(R/p).read_text(encoding='utf8')
t=replace_line(t,'> **最新产品代码提交**：','> **最新产品代码提交**：`761bd0b51af380c19b06357f815acda751905a3b` / `V1.173`（F021本轮固定产品；最新已验收仍F020 V1.172，标签固定）')
t=replace_line(t,'> **交接状态**：','> **交接状态**：`READY_FOR_CLAUDE`（F021 V1.173规则7P/1F/0NT、五步骤4P/1F/0NT，059事件完整JSON残留；完整证据`'+EVIDENCE+'`已先推送；main保持a8d6409，本轮不合入/无PR，下一仅继续F021）')
t=replace_line(t,'| **SRS_F021** |','| **SRS_F021** | 人工终止与安全制动 | **7P/1F/0NT（当前实测）** | TC-066/TC-067五步骤4P/1F/0NT | 059操作日志与多设备/取消超时子范围P，TASK_TERMINATED.detail整体非JSON仍F；20业务组/86断言与真实IAB完成，全部原始诊断及更正保留。 | V1.173 | **READY_FOR_CLAUDE；证据1c597f7已推送，未合main，不推进F022** |')
t=t.replace('已纳入V1.171，V1.172单设备审计P；F021完整待顺序','已实际纳入V1.173；F021多设备/操作JSON当前P，事件detail整体非JSON仍059 F，待修')
t+=f'\n\n## 2026-11-07 GPT：F021 V1.173整轮完成，统一交修059事件JSON\n\n完整证据`{EVIDENCE}`先推送，固定产品`761bd0b51af380c19b06357f815acda751905a3b`/V1.173、Claude文档`f00536c595d291a495a5f7e55561dbf08823ac8c`与远端标签一致。规则7P/1F/0NT、五步骤4P/1F/0NT，全部当前实测/历史P复用0；059操作JSON/多设备子范围P，事件detail为说明文字拼接数组而非完整JSON对象仍F。20业务组19P/1F、86断言85P/1F，32任务（11实际/21状态SQL），4 IAB界面组/9状态入口/6截图；433报告431通过2原有跳过、生产构建/实际JAR/HTTP/SQL/合成设备。默认60秒超时/BL006相关IDLE释放、跨任务保护与终态通过。原探针F/五诊断/离线候选及UI断言更正全部保留，不改产品或放宽标准。2定义/3设备停用、分配/占用/注入0，3自有进程树/6端口释放。main仍a8d6409964085e4a500bd399bb1a6b4f6bfb2918，本轮未合入/无PR；下一Claude接GPT证据仅修059事件JSON及直接影响后发新唯一标签再F021整轮，不推进F022或三核心/95项通过。\n';write(p,t)
p='docs/EXECUTION_BASELINE.md';t=(R/p).read_text(encoding='utf8')
t=replace_line(t,'更新：','更新：2026-11-07（F021 V1.173整轮READY_FOR_CLAUDE：7P/1F/0NT、五步骤4P/1F/0NT；059事件整体JSON残留，证据'+EVIDENCE+'先推送；V2.4及现有BL006业务口径不变）')
t=replace_line(t,'| 当前需求验收 |','| 当前需求验收 | F021 V1.173 / 761bd0b51af380c19b06357f815acda751905a3b，7P/1F/0NT、五步骤4P/1F/0NT | READY_FOR_CLAUDE；全部当前实测/历史P复用0，059事件detail整体JSON仍F，证据'+EVIDENCE+'已先推送；main保持a8d6409未合本轮/无PR，不推进F022 |')
t+=f'\nF021 V1.173本轮无需求/用例业务基线改动；现有BL006继续用于TC067取消超时与相关空闲确认释放，不为通过而提前解锁执行设备。完整证据`{EVIDENCE}`先推送；059事件完整JSON残留仍F，操作日志/多设备/超时/跨任务/终态及UI通过子范围不替代R08整项。规则7P/1F/0NT、五步骤4P/1F/0NT，无历史P替代当前实测，原始失败和探针更正保留。main仍a8d6409964085e4a500bd399bb1a6b4f6bfb2918未合本轮，下一仅修059及直接影响后F021再整轮；最新已验收产品表行F020保持，不覆盖F021实际未通过状态。\n';write(p,t)
p='README.md';t=(R/p).read_text(encoding='utf8');lines=t.splitlines();lines[2]=f'独立验收进度（2026-11-07）：SRS_F001～SRS_F020已通过并合入main；F021 V1.173整轮未通过，8规则7P/1F/0NT、五步骤4P/1F/0NT，DEF-S3-059事件detail整体JSON残留交修。完整证据`{EVIDENCE}`已先推送；main保持`a8d6409964085e4a500bd399bb1a6b4f6bfb2918`，本轮未合入/无PR。下一仅继续F021修复/整轮复测，不推进F022。范围见[协同交接](docs/HANDOFF.md)、[路线图](docs/ROADMAP.md)和[F021独立报告](acceptance/stage3/SRS_F021-V1.173-整轮独立复测与统一交修.md)。下文P5为历史阶段记录，后续需求、三核心场景及95项整体验收仍待完成。';write(p,'\n'.join(lines)+'\n')
print('Handoff/roadmap/baseline/progress updated with actual pushed evidence SHA')
