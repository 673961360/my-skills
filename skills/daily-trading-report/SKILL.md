---
name: daily-trading-report
description: 生成交易部每日交易日报（HTML）。从 AI Gateway API 采集 O32 指令/头寸/交收/回购行情/资金事件，从 Oracle 采集 QT 短评，渲染窄幅长图日报。触发：写日报、生成交易日报、daily report、交易日报、今日总结。
---

# Daily-Trading-Report

生成交易部每日交易日报 HTML：AI Gateway API（O32 指令 / 头寸 / 交收 / 回购行情 / 资金事件）+ Oracle QT 短评 → 窄幅长图式日报。

## 触发条件

用户提到："写日报"、"生成交易日报"、"daily report"、"今日总结"、"交易日报"、"trading daily"。

## 生成

```bash
cd "D:\代码\git_public\my-skills\skills\daily-trading-report\scripts"
uv run python generate_report.py --date {YYYYMMDD}
```

- 完整流程（日期确认、可选参数 `--no-charts` / `--output`、首次 `uv sync`、Oracle Instant Client 环境依赖、结果检查、错误排查）：见 `runbook.md`。
- API / Oracle 配置：见 `config.json`（脱敏模板 `config.example.json`）。
- 接口文档：`reference/API接口接入手册.md`。

> 本 skill 仅生成交易日报，不做 git/svn 工作总结；工作周报请用 weekly-report skill。
