---
name: daily-trading-report
description: 生成交易部每日交易日报（HTML 窄幅长图）。触发：写日报、生成交易日报、daily report、交易日报、今日总结、trading daily。
---

# Daily-Trading-Report

从 AI Gateway（O32 指令/头寸/交收/回购行情/资金事件）+ Oracle QT 短评采集当日数据，渲染为窄幅长图式 HTML 日报。

## 触发条件

用户提到：写日报 / 生成交易日报 / daily report / 今日总结 / 交易日报 / trading daily。

## 生成命令

```bash
cd "<本 skill 目录>/scripts"
uv run python generate_report.py --date {YYYYMMDD}
```

- **培训/口径讲解模式**：用户要求讲解口径、培训分享时加 `--learning`（输出含数据来源/加工方式/可信度标注）
- **产出物**：默认 `reports/YYYY-MM-DD-daily.html`（learning 模式为 `*-learning.html`），可用 `--output` 覆盖

## 详细参考

- **完整流程**（日期确认、`--no-charts`/`--output` 参数、首次 `uv sync`、Oracle Instant Client 依赖、结果检查、错误排查）：见 `runbook.md`
- **API / Oracle 配置**：见 `config.json`（脱敏模板 `config.example.json`）
- **接口文档**：`reference/API接口接入手册.md`

> 本 skill 仅生成交易日报，不做 git/svn 工作总结；工作周报请用 weekly-report skill。
