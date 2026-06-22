# Daily Trading Report

交易日报自动生成：从 AI Gateway API + Oracle QT 短评采集数据，生成 HTML 报告。

## 任务路由

**开始工作前，先判断任务类型，只读对应文件：**

| 任务类型 | 读取文件 |
|---------|---------|
| `/goal` 迭代 | `goal.md` → `template-contract.md` → `state.md`（涉及字段/API 时再读 `findings.md`、`rules.md`） |
| 日常生成日报 | `runbook.md`（脚本出骨架后 Claude 必须 WebSearch 注入现券/权益短评，见 `rules.md`"Claude 注入短评"） |
| 探索新数据源/新功能 | `findings.md`（数据源能力/缺口） |
| 排查报错 | `rules.md`（踩坑表）+ `runbook.md` |
| 追溯数据来源/加工血缘 | `data-sources.md`（每板块数据源→采集→加工→脱敏→降级） |

## 原则

- 只读当前任务必要材料，不要一次性读取所有文件
- 始终围绕"准确、贴近模板、可重复生成"推进
- 缺失数据不得编造，发现旧规则错误时可以修正并说明原因
- 写 5 份迭代 md（state/contract/rules/findings/goal）前，对照 `conventions.md` 自检角色与去重
