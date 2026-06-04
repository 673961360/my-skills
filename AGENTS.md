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

| 平台 | 路径 | 自动部署 | 备注 |
|------|------|----------|------|
| Claude Code | `%USERPROFILE%\.agents\skills\` | 支持 | Open Agent Skills 跨平台标准目录 |
| Codex | `%USERPROFILE%\.codex\skills\` | 支持 | SKILL.md 格式兼容 |
| QwenPaw | `%USERPROFILE%\.qwenpaw\workspaces\<id>\skills\` | 支持 | 复制文件 + 注册 workspace skill.json，所有工作区 |

### QwenPaw 特殊说明

QwenPaw 通过 `deploy.ps1` 部署，机制与 Claude Code/Codex 不同：
- **不走 skill_pool**，直接部署到所有 workspace 的 `skills/` 目录
- 每次部署遍历 `~/.qwenpaw/workspaces/` 下所有工作区，复制文件并注册到 workspace 的 `skill.json`
- 自动跳过 builtin skill，不会覆盖

两种来源的 skill 都可部署到 QwenPaw：
- **自研 skill**：从 `skills/` 目录（默认，`-Source self`）
- **全局开源 skill**：从 `~/.agents/skills/` 目录（`-Source global`）

`skill.json` 中的 `description` 字段应包含中文关键词以优化发现机制。首次部署时如未指定 `-Description`，会使用 SKILL.md 中的英文 description 作为兜底；后续更新时保留已有描述。

#### SKILL.md 格式兼容性

QwenPaw 的 customized skill 与 Claude Code 使用**完全相同的 SKILL.md 格式**（仅 `name` + `description` frontmatter + 正文指令）。QwenPaw 内置 skill 会额外带 `metadata.qwenpaw` 字段（emoji、requires 等），但自部署 skill 不需要。

迁移可行性按 skill 类型分：

| 类型 | 兼容性 | 说明 |
|------|--------|------|
| 纯文本指导型（brainstorming、grill-me 等） | 高 | 直接复制即可，不依赖任何平台特有功能 |
| 引用工具名的 skill（TDD、debugging 等） | 中 | 需逐个评估工具名映射（如 Claude 的 `Bash` → QwenPaw 的 `execute_command`） |
| 使用 hooks 的 skill（verification-before-completion 等） | 低 | QwenPaw 无 hooks 机制，需改写为纯指令引导 |
| 第三方 GitHub 源 skill | 需评估 | 多数面向 Claude Code 编写，按上述类型逐个判断 |

结论：本仓库自开发的纯指导型 skill 可以直接通过 `deploy.ps1 -Target qwenpaw` 部署到 QwenPaw 所有工作区。

### 使用 deploy.ps1

统一使用 `deploy.ps1` 进行部署和卸载，不要手动创建符号链接。

```powershell
.\deploy.ps1 -List                                        # 列出所有 skills
.\deploy.ps1 -Skill <slug> -Target claude-code            # 部署单个 skill
.\deploy.ps1 -Skill <slug> -Target qwenpaw                # 部署到 QwenPaw（自研）
.\deploy.ps1 -Skill <slug> -Target qwenpaw -Source global # 部署全局开源 skill 到 QwenPaw
.\deploy.ps1 -Skill <slug> -Target qwenpaw -Description "中文描述"  # 指定中文发现描述
.\deploy.ps1 -All                                         # 部署所有到所有平台
.\deploy.ps1 -Skill <slug> -Uninstall                     # 移除符号链接
```

## 第三方 Skills 更新

本机安装了两类第三方 skills，更新方式不同。

### GitHub 源 Skills（通过 npx skills 管理）

由 `skills-lock.json` 追踪来源和版本，来自 obra/superpowers、mattpocock/skills、upstash/context7 等仓库。

```bash
npx skills update                          # 更新所有
npx skills update -g                       # 仅全局
npx skills update -p                       # 仅项目
npx skills list -g                         # 列出已安装的全局 skills
npx skills add <owner/repo> -g             # 安装新 skill
npx skills remove <name> -g                # 移除 skill
```

实际安装位置为 `.agents/skills/`，`.claude/skills/` 下是对应的符号链接。

### 插件源 Skills（通过 claude plugins 管理）

```bash
claude plugins update <plugin@source>      # 更新指定插件
# 示例：claude plugins update frontend-design@claude-plugins-official
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
- 部署/卸载 skills 一律通过 `deploy.ps1`，不要手动复制文件或操作 skill.json
- 部署到 QwenPaw 时注意区分来源：自研 skill 用默认 `-Source self`，全局开源 skill 用 `-Source global`
