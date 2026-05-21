# AGENTS.md

本文件面向 AI 编码助手，定义在此仓库中工作时应遵循的规则和约定。

## 仓库用途

这是个人 skills 开发仓库。Skills 在此开发后通过符号链接部署到本机 AI 编码助手（Claude Code、QwenPaw、Codex 等）。不用于公开发布。

## 项目结构

```
my-skills/
├── AGENTS.md                          # 本文件 — AI 助手指令
├── README.md                          # 人类可读的项目概述
├── .gitignore
├── deploy.ps1                         # 通过符号链接部署 skills 到目标平台
└── skills/
    └── <skill-slug>/
        ├── SKILL.md                   # Skill 定义文件（必需）
        └── scripts/                   # 实现脚本（可选）
```

## SKILL.md 规范

每个 skill 必须包含 `SKILL.md` 文件，遵循 Open Agent Skills 标准格式。

### 必需 Frontmatter

```yaml
---
name: <skill-slug>
description: Use when <触发条件描述>
---
```

- `name`：仅小写字母、数字、短横线，最长 64 字符，必须与父目录名一致
- `description`：最长 1024 字符，**必须以 "Use when..." 开头**，只描述触发条件，不总结 workflow

### 正文编写原则

- **简洁优先**：高频 skill 正文控制在 200 字以内，其他不超过 500 字
- **结构化**：用标题分层，用列表/表格展示流程，用 Graphviz 流程图展示复杂逻辑
- **按需引用**：大段 API 文档、参考代码等放入 `scripts/` 或 `reference/` 目录，正文只保留引用路径
- **避免猜测性开发**：只写解决当前问题的最小指令集
- **不写显而易见代码的注释**：良好的命名已经足够

### 可选 Supporting Files

```
skill-slug/
├── SKILL.md              # 核心定义（必需）
├── scripts/              # 可执行脚本
├── reference/            # 重型参考文档
└── docs/                 # 补充文档
```

## 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| skill 目录名 | kebab-case | `follow-ai-coding-builders` |
| SKILL.md `name` 字段 | 必须与目录名一致 | `follow-ai-coding-builders` |
| 脚本文件 | 语言后缀 | `main.py`, `deploy.sh` |
| 引用文档 | 描述性名称 | `api-reference.md` |

## 部署方式

Skills 通过创建符号链接（Windows Junction）部署到各平台的全局 skill 目录。

### 目标目录

| 平台 | 路径 | 自动部署 |
|------|------|----------|
| Claude Code | `%USERPROFILE%\.agents\skills\` | 支持 |
| Codex | `%USERPROFILE%\.codex\skills\` | 支持 |
| QwenPaw | `%USERPROFILE%\.qwenpaw\skill_pool\` | 暂不支持（使用集中 skill.json 索引，需手动验证自动发现能力） |

### 使用 deploy.ps1

统一使用 `deploy.ps1` 进行部署和卸载，不要手动创建符号链接。

```powershell
.\deploy.ps1 -List                                        # 列出所有 skills
.\deploy.ps1 -Skill <slug> -Target claude-code            # 部署单个 skill
.\deploy.ps1 -All                                         # 部署所有到所有平台
.\deploy.ps1 -Skill <slug> -Uninstall                     # 移除符号链接
```

## 公开 Skills 评估与吸收流程

本仓库中的 skills 应定期与公开 skills 对比，吸收优秀模式。

### 流程

1. **发现**：浏览 [skills.sh](https://skills.sh/)、GitHub 上的 `skill.md` 仓库、社区推荐
2. **评估**：对比自有 skill 与公开 skill：
   - 触发条件是否更精准
   - 指令组织是否更清晰
   - 是否处理了自有 skill 遗漏的边界情况
   - 是否有可借鉴的 Supporting Files 组织方式
   - 是否有减少 token 消耗的技巧
3. **吸收**：将验证有效的模式合并到自有 skill 中
   - **不要直接复制**，理解后用自己的话重写
   - 在 SKILL.md 末尾添加 `## 参考来源` 记录来源
   - 合并后验证行为正确性
4. **记录**：在对应 skill 的 SKILL.md 末尾追加变更记录

### 频率

建议每 2-4 周进行一次评估。

## AI 行为规则

- 遵循现有 skill 模式，不要自创新结构
- 添加新 skill 时，严格按照 SKILL.md 模板
- 修改已有 skill 时，只改必要的行，不要"顺手改进"相邻代码
- 吸收公开 skill 模式时，必须标注来源
- 不要伪造"已成功"结论。验证不通过的，如实报告状态
