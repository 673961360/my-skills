# 操作手册

> 生成交易日报的权威操作入口（`SKILL.md` 为薄入口，细节以本文件为准）。

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
3. **精炼短评**：脚本输出的 HTML 中资金/现券栏为原文 dump。Claude 读取原文，按 `prompts/funding-commentary.md` 和 `prompts/bond-commentary.md` 精炼为 3-5 句判断性总结；权益栏按 `prompts/stock-commentary.md` 通过 WebSearch 获取行情并生成总结；一级栏按 `prompts/primary-commentary.md` 尝试从资金日评「一级简评」提取，无则降级。精炼结果直接编辑 HTML 替换。
4. **检查结果**：
   - 成功 → 读取 HTML，向用户展示摘要
   - 失败 → 根据错误信息排查（见下方错误表）
5. **用户审核**：最多 3 轮调整
6. **交付**：告知文件路径，询问是否创建飞书文档

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

`config.json` 关键字段（完整脱敏模板见 `config.example.json`）：

```json
{
  "api_base_url": "https://aitest.cjhxfund.com/ai-gateway",
  "api_key": "sk-...",
  "output_dir": "reports",
  "oracle": {
    "host": "10.191.0.178",
    "port": 5674,
    "service_name": "cjhx",
    "user": "<oracle_user>",
    "password": "<oracle_password>"
  }
}
```

## 触发关键词

用户说以下关键词时激活本技能：
- "写日报"、"生成交易日报"、"daily report"
- "今日总结"、"交易日报"、"trading daily"
