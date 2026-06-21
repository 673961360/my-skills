# 操作手册

> 日常生成日报/周报时读取本文件。

## 生成日报

```bash
cd "D:\代码\git_public\my-skills\skills\daily-trading-report\scripts"
uv run python generate_report.py --date {YYYYMMDD}
```

可选参数：
- `--no-charts`：跳过图表生成（加速调试，QT 采集仍需 20-30 秒）
- `--output custom.html`：指定输出路径（默认 `reports/YYYY-MM-DD-daily.html`）

首次运行或依赖变更时：
```bash
cd scripts && uv sync
```

## 环境依赖

| 依赖 | 说明 |
|------|------|
| Python 3.10+ | 通过 uv 管理 |
| uv | Python 包管理 |
| Oracle Instant Client 21.8 | thick 模式连接 Oracle 11g |
| `ORACLE_LIB_DIR` 环境变量 | 指向 Instant Client 路径 |

默认 Instant Client 路径：`D:\Program Files\oracle_client_x64\instantclient_21_8`

## 工作流程

1. **确认日期**：默认当日，用户可指定。向用户确认日期和星期
2. **运行脚本**：`uv run python generate_report.py --date YYYYMMDD`
3. **检查结果**：
   - 成功 → 读取 HTML，向用户展示摘要
   - 失败 → 根据错误信息排查（见下方错误表）
4. **用户审核**：最多 3 轮调整
5. **交付**：告知文件路径，询问是否创建飞书文档

## 错误排查

| 错误信息 | 原因 | 处理 |
|---------|------|------|
| `API 请求失败` | 网络不通或 API Key 过期 | 检查 config.json，确认测试环境可访问 |
| `无交易数据` | 非交易日或当日无交易 | 正常，报告标注"无数据" |
| `依赖未安装` | 首次运行 | `cd scripts && uv sync` |
| `图表生成失败` | matplotlib 中文字体缺失 | 不影响报告，图表区域显示空 |
| `DPY-3010` | Oracle 11g 不支持 thin 模式 | 检查 ORACLE_LIB_DIR 配置 |
| `ORA-01745` | 绑定变量用了保留字 | 代码中用 `:p_date` 等非保留名 |
| `ORA-00904` | 列名拼写错误 | 用 `ALL_TAB_COLUMNS` 查实际列名 |
| `FileNotFoundError: oracle_client` | Instant Client 未安装 | 安装并配置 ORACLE_LIB_DIR |
| `UnicodeEncodeError: 'gbk'` | Windows 输出 emoji | 脚本已处理；新脚本加 `PYTHONIOENCODING=utf-8` |
| `QT短评采集失败` | Oracle 不可达 | 非关键，报告其余部分正常 |

## 配置文件

`config.json` 关键字段：

```json
{
  "api_base_url": "https://aitest.cjhxfund.com/ai-gateway",
  "api_key": "sk-...",
  "output_dir": "reports",
  "oracle": {
    "host": "10.191.0.178",
    "port": 5674,
    "service_name": "cjhx",
    "user": "fm",
    "password": "fm"
  }
}
```

## 触发关键词

用户说以下关键词时激活本技能：
- "写日报"、"生成交易日报"、"daily report"
- "今日总结"、"交易日报"、"trading daily"
