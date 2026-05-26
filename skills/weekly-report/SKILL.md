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
