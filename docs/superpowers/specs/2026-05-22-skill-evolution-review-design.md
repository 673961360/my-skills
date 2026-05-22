---
date: 2026-05-22
topic: skill-evolution-review
type: skill-design
---

# Skill Evolution Review — 设计文档

## 概述

开发一个手动触发的 Skill，用于定期评估自有 Skills 体系与公开社区最新模式的差距，输出结构化改进建议。

## 触发方式

用户手动运行 `/skill-evolution-review`，无参数。每次运行覆盖全部已部署 Skills 的全局评估。

## 工作流

### Step 1: 读取本地 Skills 体系

- 扫描 `skills/` 目录结构
- 读取每个 Skill 的 `SKILL.md` 全文
- 提取关键信息：定位、触发条件、工作流、排除标准、Supporting Files

### Step 2: 深度搜索公开资料

按以下 4 个来源维度并行搜索，每维度只保留 1-2 个最有参考价值的发现：

| 维度 | 搜索方向 | 示例 query |
|------|----------|------------|
| 官方一手 | Anthropic Skills 文档、Claude Code Release Notes、OpenAI Codex、MCP 官方文档 | `Claude Code skill best practices`, `MCP server design pattern 2026` |
| 开源实现 | GitHub 高星 Skill/Agent/Rules 仓库 | `github "skill.md" agent workflow`, `github claude-code skills collection` |
| 工程博客 | 真实项目复盘、GitHub Issue/Discussion | `skill design lessons learned`, `agent tool use pattern github` |
| 高信号人物 | Karpathy、Simon Willison、Chip Huyen、Hamel Husain 等 | `simon willison agent design`, `karpathy coding agent workflow` |

**筛选原则**：只保留包含具体实现细节、设计决策、踩坑经验的内容。排除泛泛 AI 新闻、营销稿、纯观点输出。

### Step 3: 对比分析

#### 3a. 通用模式分析

按 5 个评估维度逐一分析：

1. **定位** — 每个 Skill 是否解决了可重复使用的问题？
2. **边界** — 是否过大、过散、过模糊？与其他 Skill 是否重复？
3. **触发** — 什么时候该用它？是否容易误触发？
4. **工作流** — 是否有稳定、可重复的处理步骤？
5. **可吸收新做法** — 外部写法、结构、触发方式、工具化方式

#### 3b. 可比 Skill 逐项对比

在 Step 2 搜索时，如果发现与自有 Skill **功能类似**的公开 Skill（如另一个"AI 动态追踪" Skill），执行逐项对比：

- **触发条件精准度** — 对方的触发描述是否更具体？
- **工作流完整性** — 对方的步骤是否覆盖了自有 Skill 遗漏的边界情况？
- **输出格式** — 对方的输出是否更适合目标场景？
- **Supporting Files** — 对方是否有值得借鉴的脚本/参考文件组织方式？

对比结果在报告第 2 节标注为"可比 Skill"项，列出具体差异和可吸收点。

### Step 4: 终端输出结构化报告

严格按以下格式输出，不做长篇审计清单：

```
# Skills 演进建议

## 1. 总体判断（3-5 句话）
## 2. 值得吸收的新思路（只列真正有价值的，不凑数）
## 3. 我的 Skills 应该怎么改（表格：Skill | 主要问题 | 建议动作 | 优先级）
## 4. 不建议跟进的方向（只列容易误导的）
## 5. 下一步最小动作（1-3 个）
```

## SKILL.md 结构

```yaml
---
name: skill-evolution-review
description: Use when evaluating your complete Skills system against public patterns for improvement opportunities — runs deep research and outputs structured evolution report
---

# Skill Evolution Review

## Purpose
评估自有 Skills 体系与公开社区模式的差距，输出可执行的改进建议。

## When to Use
用户手动触发 /skill-evolution-review 时运行。
建议每 2-4 周运行一次。

## Workflow
### 1. 读取本地 Skills
### 2. 深度搜索公开资料（4 维度 + 筛选原则）
### 3. 对比分析（5 维度）
### 4. 输出报告（固定格式）

## Output Format
[固定模板]

## Rules
- 不凑数，只输出真正有价值的内容
- 区分公开来源事实和自己的建议判断
- 如果公开资料不足，直接说明，不要猜
- 优先小改动、可维护、可复用
- 不因为某个做法新或流行就建议采用
```

## 设计决策

1. **单次运行** — 不拆分阶段，一次完成读取、搜索、分析、输出
2. **搜索即筛选** — Step 2 搜索时就做筛选，不把原始结果全部带进分析
3. **固定输出格式** — 报告格式固定，保证多次运行的结果可对比
4. **无文件输出** — 直接终端输出，不生成报告文件（用户要求）

## 验收标准

- [ ] `skills/skill-evolution-review/SKILL.md` 存在且格式正确
- [ ] `name` 与目录名一致
- [ ] `description` 以 "Use when..." 开头
- [ ] 运行后能输出包含 5 个章节的结构化报告
- [ ] 搜索覆盖至少 3 个来源维度
- [ ] 输出长度适中，不做长篇审计清单
