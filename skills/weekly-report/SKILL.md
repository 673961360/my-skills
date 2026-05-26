---
name: weekly-report
description: Use when generating weekly or monthly work reports from git/svn/Claude Code/WeCom data sources. Trigger when the user asks to write a weekly report, monthly report, work summary, or generates a report.
---

# Weekly-Report

从多个数据源（git 提交、svn 提交、Claude Code 会话、企微手工总结）采集数据，智能归纳为工作汇报风格的周报/月报。

## 触发条件

用户提到以下关键词时激活：
- "写周报"、"生成本周总结"、"weekly report"
- "写月报"、"生成本月总结"、"monthly report"
- "生成报告"、"工作汇报"

## 配置 - 仓库列表

以下为 Git 仓库路径和对应的项目名称（用于报告分组标题）。**按需修改为你实际的路径**：

```yaml
git_repos:
  - path: "D:\\代码\\repo-a"
    name: "C端交易系统"
  - path: "D:\\代码\\repo-b"
    name: "资金AI"
  - path: "D:\\代码\\git_public\\my-skills"
    name: "IT基础设施"
```

以下为 SVN 仓库路径和对应的项目名称：

```yaml
svn_repos:
  - path: "svn://your-server/repo-c"
    name: "柜台债"
  - path: "svn://your-server/repo-d"
    name: "柜台债工程化"
```

**配置说明：**
- `path`：仓库在本机的绝对路径（Windows 路径用双反斜杠 `\\`）
- `name`：报告中显示的项目分组名称（中文）
- 增删仓库时，直接编辑 SKILL.md 中的配置区
- 某项目本周无动静的，不显示该分组标题

## 工作流程

### Step 1: 确定时间范围

询问用户："周报还是月报？"

- **周报**：最近 7 天，从本周一起至今天
- **月报**：最近 30 天
- 用户也可手动指定起止日期，如"从上周五到这周三"

确定时间后，计算具体的 `start_date` 和 `end_date`（YYYY-MM-DD 格式），向用户确认：
> "时间范围确认：{start_date} ~ {end_date}，是否正确？"

### Step 2: 采集数据

确认时间范围后，并行采集以下数据源。

#### 2.1 Git 提交采集

遍历配置中的每个 `git_repos`，对每个仓库执行：

```bash
cd "仓库path" && git log --after="start_date" --before="end_date +1天" --author="当前git用户名" --pretty=format:"%H|%ai|%s" --name-status
```

如果仓库路径不存在，跳过并在末尾汇总中记录"未找到：路径"。
如果返回为空（无提交），记录"该仓库本周无提交"，继续下一个。

#### 2.2 SVN 提交采集

遍历配置中的每个 `svn_repos`，对每个仓库执行：

```bash
svn log -r "{start_date}:{end_date +1天}" "仓库path"
```

如果路径不存在或无权限，跳过并记录"未找到/无权限：路径"。

#### 2.3 Claude Code 会话采集

读取 `~/.claude/sessions/` 目录下的 JSON 文件，筛选 `startedAt` 时间在目标范围内的会话。

```bash
# 列出 sessions 目录
ls ~/.claude/sessions/
```

对每个 session JSON 文件，读取 `startedAt`（毫秒时间戳）、`cwd`（工作目录）、`sessionId`。
按 `cwd` 判断该会话属于哪个项目分组（匹配 git_repos 中的 path）。

汇总格式：
| 日期 | 会话主题（从首条 prompt 概括） | 工作目录 | 关联项目 |

如果 sessions 目录不存在或为空，跳过 CC 分析，不影响其他数据源。
