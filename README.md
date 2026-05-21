# my-skills

个人 Skills 开发仓库。用于开发、管理、部署个人 skills 到 Claude Code、QwenPaw、Codex 等 AI 编码助手。

## 这是什么

这个仓库是你个人 skills 的"开发工坊"。你在里面编写、测试、迭代自己的 skills，然后通过一键部署脚本，把它们安装到本机的各个 AI 编码助手上。

Skills 的定义遵循 [Open Agent Skills](https://agentskills.io/) 开放标准，Claude Code、Codex、Gemini CLI、Cursor 等工具都支持。

## 快速开始

### 1. 查看已有 skills

```powershell
.\deploy.ps1 -List
```

### 2. 开发新 skill

在 `skills/` 下创建一个新目录，目录名用短横线命名（kebab-case），比如 `skills/my-new-skill/`。

在里面创建 `SKILL.md`，格式如下：

```yaml
---
name: my-new-skill
description: Use when <什么场景下触发>
---

# 你的 skill 名称

这里是 skill 的核心指令...
```

更详细的编写规范见 [AGENTS.md](AGENTS.md)。

### 3. 部署到本机

```powershell
# 部署单个 skill
.\deploy.ps1 -Skill my-new-skill -Target claude-code

# 部署所有 skills
.\deploy.ps1 -All
```

部署后，下次打开 Claude Code 就能自动发现这个 skill。

## 各平台部署状态

| 平台 | 部署路径 | 自动部署 | 备注 |
|------|----------|----------|------|
| Claude Code | `~/.agents/skills/` | 支持 | Open Agent Skills 跨平台标准目录 |
| Codex | `~/.codex/skills/` | 支持 | SKILL.md 格式兼容 |
| QwenPaw | `~/.qwenpaw/skill_pool/` | 暂不支持 | 使用集中 skill.json 索引，需手动验证自动发现能力 |

## 目录结构

```
my-skills/
├── AGENTS.md               # AI 助手的工作指令和规则
├── README.md               # 本文件 — 人类看的项目概览
├── .gitignore
├── deploy.ps1              # 一键部署脚本
└── skills/                 # 所有 skills 的源码
    └── <skill-slug>/
        ├── SKILL.md        # Skill 定义（必需）
        └── scripts/        # 实现脚本（可选）
```

## 各文件作用

| 文件 | 给谁看 | 用途 |
|------|--------|------|
| `AGENTS.md` | AI 编码助手 | 定义 AI 在此仓库工作时的规则和约定 |
| `README.md` | 人类（你） | 项目概述、快速开始、目录说明 |
| `deploy.ps1` | 工具 | 一键部署 skills 到各平台 |
| `skills/<slug>/SKILL.md` | AI 编码助手 | 每个 skill 的核心定义文件 |

## 定期评估公开 Skills

本仓库中的 skills 会定期与 [skills.sh](https://skills.sh/) 等平台的公开 skills 对比，吸收优秀模式。具体流程见 [AGENTS.md](AGENTS.md) 中的"公开 Skills 评估与吸收流程"章节。

## 开发新 Skill 的完整步骤

1. 在 `skills/` 下创建 kebab-case 目录
2. 编写 `SKILL.md`（frontmatter 必需字段 + 核心指令）
3. 按需添加 `scripts/`、`reference/` 等 Supporting Files
4. 运行 `.\deploy.ps1 -Skill <slug> -Target claude-code` 部署
5. 打开 Claude Code 验证 skill 被正确发现

## 部署问题排查

如果部署失败或 skill 不生效，按以下顺序检查：

1. `SKILL.md` 的 frontmatter 格式是否正确（`name` 和 `description` 必须存在）
2. `name` 是否与目录名完全一致
3. 符号链接是否创建成功（`.\deploy.ps1 -List` 查看状态）
4. 目标平台的全局 skill 目录是否存在

## 文件说明

- 所有 `.md` 文件（除 SKILL.md 外）使用中文
- `SKILL.md` 的 frontmatter 中 `description` 字段必须用英文并以 "Use when..." 开头（这是 AI 工具的标准要求）
- `SKILL.md` 的正文可以用中文写
- PowerShell 脚本（`deploy.ps1`）避免中文，防止编码问题
