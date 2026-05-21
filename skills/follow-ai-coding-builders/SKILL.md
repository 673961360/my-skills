---
name: follow-ai-coding-builders
description: Use when you want to track, evaluate, and absorb patterns from public AI coding skills and builders
---

# Follow AI Coding Builders

## 目标

定期发现、评估、吸收公开 AI coding skills 中的优秀模式，持续迭代自有 skills。

## 触发条件

用户提到以下关键词时激活：
- "follow builders"
- "evaluate public skills"
- "absorb skill patterns"
- "检查有没有新的公开 skill"

## 工作流程

### 1. 发现

- 浏览 [skills.sh](https://skills.sh/) 的 trending 和 recently updated
- 搜索 GitHub 上 `skill.md` + `claude-code` 相关的仓库
- 关注社区推荐的 skill 实现（如 Agensi 等聚合站点）

### 2. 评估

对比当前仓库中的 skills 与发现到的公开 skills，逐项评估：

| 评估维度 | 问题 |
|----------|------|
| 触发精准度 | 对方的 description 是否更精准地命中场景？ |
| 指令清晰度 | 指令组织是否更易于理解？ |
| 边界案例 | 是否处理了自有 skill 遗漏的边界情况？ |
| 文件结构 | 是否有可借鉴的 Supporting Files 组织方式？ |
| 性能/效率 | 是否有减少 token 消耗的技巧？ |

### 3. 吸收

1. 确定值得吸收的模式
2. 理解其原理后用自己的话重写（不直接复制）
3. 在 SKILL.md 末尾添加 `## 参考来源` 记录来源
4. 合并后验证行为正确性

### 4. 迭代记录

每次吸收后，在本文件末尾追加变更记录：

```markdown
## 变更记录

### YYYY-MM-DD
- 吸收了 [skill-name](source-url) 的 [具体模式/技巧]
```
