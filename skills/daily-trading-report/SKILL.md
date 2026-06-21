---
name: daily-trading-report
description: Use when generating daily trading work reports from AI Gateway API data, git/svn/Claude Code sessions, or manual input. Supports both automated HTML trading reports and manual work summaries.
---

# Daily-Trading-Report

交易部工作日报自动生成技能：
- **自动模式**：调用 Python 脚本从 AI Gateway API 采集真实交易数据，生成专业 HTML 交易日报


## 触发条件

用户提到以下关键词时激活：
- "写日报"、"生成交易日报"、"daily report"
- "今日总结"、"今天做了什么"
- "交易日报"、"trading daily"

## 工作流程

### 模式一：自动生成交易日报（推荐）

适用于需要完整交易数据的日报。

#### Step 1: 确定日期

默认生成当日日报。用户可指定日期，如"昨天的日报"、"上周五的日报"。

确认日期后向用户确认：
> "日报日期：{date}（周X），是否正确？"

#### Step 2: 运行生成脚本

```bash
cd "D:\代码\git_public\my-skills\skills\daily-trading-report\scripts"
uv run python generate_report.py --date {YYYYMMDD}
```

可选参数：
- `--no-charts`：跳过图表生成，加速调试（QT 短评采集仍需 20-30 秒）
- `--output custom.html`：指定输出路径（默认 `reports/YYYY-MM-DD-daily.html`）

首次运行或未安装依赖时：
```bash
uv sync
```

> **环境依赖**：脚本依赖 Oracle Instant Client（thick 模式），路径通过环境变量 `ORACLE_LIB_DIR` 配置，默认 `D:\Program Files\oracle_client_x64\instantclient_21_8`。若换机器运行，需先安装 Instant Client 并配置路径。

#### Step 3: 检查结果

- 脚本输出成功 → 读取生成的 HTML 文件，向用户展示报告摘要
- 脚本报错 → 根据错误信息排查（API 连接、数据缺失等）

> **注意**：测试环境下查询**历史日期**时，O32 指令、头寸、交收、回购行情等数据通常为 **0 条**，这是正常现象（测试环境仅保留当日/近期数据）。QT 聊天短评（Oracle 数据库）历史数据完整，不受此影响。具体预期数据量见 `state.md` "已验证数据" 章节。

#### Step 4: 人工审核

展示报告摘要后，询问用户：
> "日报已生成，是否需要调整？（最多 3 轮）"

可调整项：
- 数据筛选（排除特定产品/业务类型）
- 风险提示文本
- 格式调整

#### Step 5: 交付

- 确认无误后，告知用户文件路径：`reports/YYYY-MM-DD-daily.html`
- 询问是否创建飞书文档版本
- 可建议用浏览器打开预览

---

## 配置

### 仓库列表

复用 weekly-report 的仓库配置，见 `../weekly-report/SKILL.md` 中的 `git_repos` 和 `svn_repos`。

### API 配置

见 `config.json`：
- `api_base_url`：API 网关地址（默认测试环境）
- `api_key`：认证密钥
- `output_dir`：输出目录

### 接口文档

完整 API 接口文档见 `reference/API接口接入手册.md`。

## 错误处理

见 `runbook.md` "错误排查" 章节。
