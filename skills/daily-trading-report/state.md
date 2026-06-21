# 当前状态

> 本文件是当前快照，goal 迭代时更新。每次 goal 完成后重置为最新状态。

## 当前快照（2026-06-22）

| 项目 | 状态 | 证据 |
|------|------|------|
| 完整报告级验收 | 已验证 | `$env:PYTHONIOENCODING='utf-8'; uv run python scripts/generate_report.py --date 20260617` 成功生成 `reports/2026-06-17-daily.html`；生成过程中 O32/API 403 被降级处理，未阻断报告输出 |
| 主模板栏目顺序与命名 | 已验证 | `uv run python test_template_contract.py` 通过；可见标题顺序符合 `template-contract.md` |
| 标题区与输出命名 | 已验证 | HTML 显示 `2026年6月17日（周三）`；文件名保持 `reports/2026-06-17-daily.html` |
| `01 交易数据汇总` | 已验证（样例截图） | `reports/01-trade-unit-sample.html` 与 `reports/01-trade-unit-sample.png` 显示 `交易数据汇总`、`交易笔数`、`交易金额` 位于同一 `01` section；截图中 `交易笔数图`→`交易金额图` 顺序正确，后接 `02 交收数据汇总`；文本检查确认无 `交易数据汇总图` 旧饼图、无空 `data:image/png;base64,` 图片 |
| `02 交收数据汇总` | 已验证（样例截图） | `reports/02-settlement-unit-sample.html` 与 `reports/02-settlement-unit-sample.png` 显示交收总笔数、交收总金额和交收状态表；`02` 后直接进入 `03 市场预测汇总`，不再渲染参考图没有的交收柱状图；文本检查确认无 `交收进度分布图` 和未使用图表占位 |
| `03 市场预测汇总` | 已验证（样例截图） | `reports/03-forecast-unit-sample.html` 与 `reports/03-forecast-unit-sample-full.png` 显示回购利率图、回购行情表、`趋势预测准确率`、`区间预测准确率` 同处 `03` section；无历史预测数据时两个准确率子块均显示 `历史预测数据不足，暂无法计算准确率`，随后进入 `04 资金市场分析` |
| `04 资金市场分析` | 已验证（样例截图） | `reports/04-money-market-unit-sample.html` 与 `reports/04-money-market-unit-sample.png` 显示 `公开市场操作`、`债券发行与到期`、`资金面状况` 同处 `04` section；有数据分支渲染 OMO 汇总、操作明细、债券发行/到期表和资金面短评，随后进入 `现券市场分析`；无数据分支仍使用 `暂无相关数据` |
| `现券市场分析` | 已验证（样例截图） | `reports/bond-market-unit-sample.html` 与 `reports/bond-market-unit-sample.png` 显示现券短评作为独立 section 渲染为 `analysis-box`，随后进入 `权益市场分析`；合同测试覆盖有短评分支和缺失时 `暂无有效消息` 降级 |
| `权益市场分析` | 已验证（样例截图） | `reports/equity-market-unit-sample.html` 与 `reports/equity-market-unit-sample.png` 显示外部权益短评作为独立 section 渲染为 `analysis-box`，并标注 `数据来源：外部市场短评`，随后进入 `一级市场分析`；合同测试覆盖外部输入分支和缺失时 `外部短评暂未获取` 降级 |
| `一级市场分析` | 已验证（样例截图） | `reports/primary-market-unit-sample.html` 与 `reports/primary-market-unit-sample.png` 显示 `发行情况`、`发行结构分析` 同处 `一级市场分析` section，随后进入 `风险提示`；合同测试覆盖结构化可用分支、QT 短评分支和完全缺失时 `暂无相关数据` 降级 |
| 缺失数据占位 | 已验证 | 可见空状态统一使用合同占位；合同测试禁止旧空状态文案，`rg` 搜索模板无命中 |
| 可见实现痕迹 | 已验证 | 渲染结果不再出现 `AI 执行期`、`AI Gateway 测试环境`、`需接入`、`可能为非交易日`、`生成时间` 等内部说明；非交易日使用 `今日休市，无交易数据` |
| 旧模板残留 | 已验证 | `report_template.html` 不再保留禁用附录死代码；模板和图表源码不再出现 `交易额度`、`交收预测`、`账户头寸`、`风险预警` 等旧栏目命名 |
| `风险提示` | 已验证（样例截图） | `reports/risk-tips-unit-sample.html` 与 `reports/risk-tips-unit-sample.png` 显示风险提示作为末尾独立 section 渲染为红色编号列表；合同测试覆盖固定合规提示和动态风险摘要，规则引擎风险表不进入主模板流 |
| 视觉骨架 | 已验证（完整长图） | `reports/2026-06-17-daily-full.png` 显示完整窄幅长图：蓝色背景、左侧时间线、白色内容块、蓝色标题标签；浏览器可正常打开，无明显文本重叠 |

## 当前阻塞

- 无 goal 阻塞。主模板栏目、生成路径、缺失数据占位和完整长图视觉骨架均已有当前证据。

## 后续非阻塞事项

- 真实 O32/API 测试环境返回 403 时，报告按合同占位降级；待权限恢复后可复核真实字段口径和真实图表位置。
- 权益市场真实短评需由调用方在 AI 执行期 WebSearch 后通过参数传入；脚本本身保留降级占位。
- 历史预测数据源、一级发行结构化外部数据源尚未接入，当前按合同占位。
