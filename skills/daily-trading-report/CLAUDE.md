# Daily Trading Report

交易日报/周报自动生成：从 AI Gateway API + Oracle QT 短评采集数据，生成 HTML 报告。

## 任务路由

**开始工作前，先判断任务类型，只读对应文件：**

| 任务类型 | 读取文件 |
|---------|---------|
| `/goal` 迭代 | `goal.md` → `template-contract.md` → `state.md`（涉及字段/API 时再读 `findings.md`、`rules.md`） |
| 日常生成日报/周报 | `runbook.md` |
| 探索新数据源/新功能 | `state.md` |
| 排查报错 | `rules.md`（踩坑表）+ `runbook.md` |

## 原则

- 只读当前任务必要材料，不要一次性读取所有文件
- 始终围绕"准确、贴近模板、可重复生成"推进
- 只沉淀稳定结论到 `rules.md`，不记录过程废话
- 缺失数据不得编造，发现旧规则错误时可以修正并说明原因
- `state.md` 是工作台，goal 完成后重置为最新快照
