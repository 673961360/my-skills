---
name: skill-evolution-review
description: Use when the user wants to evaluate their complete Skills system against public community patterns for improvement opportunities
---

# Skill Evolution Review

## 职责

评估自有 Skills 体系与公开社区最新模式的差距，输出可执行的改进建议。

## 触发条件

用户运行 `/skill-evolution-review` 时激活。建议每 2-4 周运行一次。

> 本 Skill 是 `AGENTS.md` 中"公开 Skills 评估与吸收流程"的**自动化深度调研版本**。AGENTS.md 定义了手动评估流程，本 Skill 通过自动搜索公开资料、对比分析、生成结构化报告来执行同样的目标，但覆盖范围更广、输出更结构化。两者不冲突——本 Skill 输出建议后，具体的吸收动作仍按 AGENTS.md 流程执行（理解后重写、标注来源、验证正确性）。

## 工作流

### 1. 读取本地 Skills 体系

- 扫描 `skills/` 目录结构
- 读取每个 Skill 的 `SKILL.md` 全文
- 提取关键信息：定位、触发条件、工作流、排除标准、Supporting Files

### 2. 深度搜索公开资料

按以下 4 个来源维度搜索，每维度只保留 1-2 个最有参考价值的发现：

| 维度 | 搜索方向 | 示例 query |
|------|----------|------------|
| 官方一手 | Anthropic Skills 文档、Claude Code Release Notes、OpenAI Codex、MCP 官方文档 | `Claude Code skill best practices`, `MCP server design pattern 2026` |
| 开源实现 | GitHub 高星 Skill/Agent/Rules 仓库 | `github "skill.md" agent workflow`, `github claude-code skills collection` |
| 工程博客 | 真实项目复盘、GitHub Issue/Discussion | `skill design lessons learned`, `agent tool use pattern github` |
| 高信号人物 | Karpathy、Simon Willison、Chip Huyen、Hamel Husain 等 | `simon willison agent design`, `karpathy coding agent workflow` |

**筛选原则**：只保留包含具体实现细节、设计决策、踩坑经验的内容。排除泛泛 AI 新闻、营销稿、纯观点输出。

### 3. 对比分析

#### 3a. 通用模式分析

按 4 个评估维度逐一分析：

1. **定位** — 每个 Skill 是否解决了可重复使用的问题？
2. **边界** — 是否过大、过散、过模糊？与其他 Skill 是否重复？
3. **触发** — 什么时候该用它？是否容易误触发？
4. **工作流** — 是否有稳定、可重复的处理步骤？

同时寻找可吸收的新做法：外部写法、结构、触发方式、工具化方式。

#### 3b. 可比 Skill 逐项对比（按需触发）

当用户提供一个公开 Skill 的 URL 或名称时，将其 SKILL.md 全文与对应自有 Skill 逐项对比：

- **触发条件精准度** — 对方的触发描述是否更具体？
- **工作流完整性** — 对方的步骤是否覆盖了自有 Skill 遗漏的边界情况？
- **输出格式** — 对方的输出是否更适合目标场景？
- **Supporting Files** — 对方是否有值得借鉴的脚本/参考文件组织方式？

如无可比对象，跳过本节。

### 4. 输出报告

严格按以下格式输出，不做长篇审计清单：

```
# Skills 演进建议

## 1. 总体判断（3-5 句话）
- 当前 Skills 体系整体状态
- 最值得改进的问题
- 是否发现值得吸收的公开新思路
- 本次最优先建议改什么

## 2. 值得吸收的新思路

每条格式：
- 新思路：
- 来源：
- 为什么值得参考：
- 适合吸收到哪里：
- 不适合照搬的地方：

如有可比 Skill，标注为"可比 Skill"项，列出：
- 对比对象（对方 Skill 名称/链接）
- 差异点：
- 可吸收点：

## 3. 我的 Skills 应该怎么改（表格）

| Skill | 主要问题 | 建议动作 | 优先级 |
|---|---|---|---|

建议动作只从：保留、精简、拆分、合并、改触发方式、补示例、补边界、补工作流、降级为 Prompt、升级为 Agent/Tool/Workflow、暂不处理

## 4. 不建议跟进的方向

每条格式：
- 不建议方向：
- 原因：
- 继续观察什么：

## 5. 下一步最小动作（1-3 个）

每条格式：
- 动作：
- 修改对象：
- 怎么改：
- 验收标准：
```

## 规则

- 不要为了完整而完整。
- 不要输出长篇审计清单。
- 不要因为某个做法新或流行就建议采用。
- 优先小改动、可维护、可复用。
- 区分公开来源事实和你的建议判断。
- 如果公开资料不足，直接说明，不要猜。

## 变更记录

### 2026-05-22
- 初始创建：从设计文档和实现计划生成
