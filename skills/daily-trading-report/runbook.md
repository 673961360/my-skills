# 操作手册

> 生成交易日报的权威操作入口（`SKILL.md` 为薄入口，细节以本文件为准）。

## 生成日报

```bash
cd "<本 skill 目录>/scripts"
uv run python generate_report.py --date {YYYYMMDD}
```

可选参数：
- `--no-charts`：跳过图表生成（加速调试，QT 采集仍需 20-30 秒）
- `--output custom.html`：指定输出路径（默认 `reports/YYYY-MM-DD-daily.html`）
- `--learning`：生成分享模式日报，输出 `reports/YYYY-MM-DD-daily-learning.html`，每个主板块标题可点击查看数据来源、加工方式、可信度和注意事项

首次运行或依赖变更时：
```bash
cd scripts && uv sync
```

## 缓存调试

调试时不想每次等 API 实时采集（30-60 秒），可启用缓存：

```bash
# 首次：不带缓存跑一次，自动写入 cache/
uv run python scripts/generate_report.py --env prod

# 后续调试：用缓存秒启动（6 秒）
uv run python scripts/generate_report.py --env prod --use-cache
uv run python scripts/export_data.py --use-cache
```

- 开关：`--use-cache` 或环境变量 `DTR_USE_CACHE=true`
- 缓存目录：`cache/`（已 gitignore）
- **只缓存 AI Gateway API 响应**，Oracle QT 和外部行情仍实时请求
- 参数变了（如换日期）会自动调 API 补缓存

### 生成历史日报

测试环境 O32/API 接口**不支持查询历史日期数据**（返回 0 条，非报错），因此生成历史日报必须使用 `cache/` 中已有的缓存文件：

```bash
uv run python scripts/generate_report.py --date {YYYYMMDD} --use-cache
```

- **缓存来源**：当日首次运行（不带 `--use-cache`）时，API 响应自动落盘到 `cache/`；后续同日期查询直接读缓存
- **限制**：`cache/` 中无对应日期的缓存时，历史日期无法生成有效数据（接口不返回历史）
- Oracle QT 短评不受此限制（历史数据完整），但仍需 `--use-cache` 避免重复请求

## 环境依赖

| 依赖 | 说明 |
|------|------|
| Python 3.10+ | 通过 uv 管理 |
| uv | Python 包管理 |
| Oracle Instant Client 21.8 | thick 模式连接 Oracle 11g |
| `ORACLE_LIB_DIR` 环境变量 | 指向 Instant Client 路径 |

默认 Instant Client 路径：由 `ORACLE_LIB_DIR` 环境变量指定（需自行安装 Oracle Instant Client 21.8）

## 工作流程

1. **确认日期**：默认当日，用户可指定。向用户确认日期和星期
2. **运行脚本**：`uv run python generate_report.py --date YYYYMMDD`
   - 若用于培训或口径讲解：`uv run python generate_report.py --date YYYYMMDD --learning`
3. **AI 注入短评（必须执行，不可跳过）**：
   脚本输出的 HTML 中现券/权益栏为占位文本。AI 必须通过 WebSearch 获取当日市场信息并注入：
   - **现券市场分析**：QT 现券日评原文 dump 由脚本填入（**中间态**），按 `prompts/现券交易员短评角色.md` 精炼为 3-5 句，剔除 OMO/资金面/一级（他栏已有）；QT 无现券日评才 WebSearch "YYYY年M月D日 债券 利率债 收盘"
   - **权益市场分析**：按 `prompts/权益交易员短评角色.md` 的查询策略（域名限定优先，非精确日期长句）WebSearch 当日 A 股收盘，整合为成交额/板块/驱动的**增量判断**（指数点位引用上方表格，不复述）
   - **资金市场分析**：QT 资金日评原文 dump 已由脚本填入，按 `prompts/资金交易员短评角色.md` 精炼为 3-5 句判断性总结（若模板已含 QT 原文则无需额外搜索）
   - **一级市场分析**：发行卡 + 明细表由脚本自动填充（`aggregate_primary_market`）；若资金日评含【一级简评】→ 按 `prompts/一级交易员短评角色.md` 精炼为 3-5 句判断性总结
   - 注入方式：直接 `Edit` HTML 文件替换占位文本
   - **注入后逐栏检查（中间态→成品，每栏必过）**：
     - [ ] 资金面状况：两个 HTML 注释占位（`<!-- 整体状态占位 -->` / `<!-- 市场特征总结占位 -->`）→ 按 `prompts/资金交易员短评角色.md` 分别精炼，每个注释替换为 `<div class="inline-heading">▶整体状态/市场特征总结</div><div>精炼内容</div>`；已是 `inline-heading` + 内容 → 过
     - [ ] 现券市场分析：不得留 QT 原文 dump（含日评标题/逐条成交/OMO/Shibor/一级）→ 按 `prompts/现券交易员短评角色.md` 精炼
     - [ ] 权益市场分析：不得是"外部短评暂未获取"（`empty-data` 占位），也不得复述指数表点位 → 按 `prompts/权益交易员短评角色.md` 补成交额/板块/驱动，整段 `<div class="empty-data">` 替换为 `<div class="analysis-box">` 包裹的精炼文字
     - [ ] 一级市场分析：有【一级简评】原文 dump → 按 `prompts/一级交易员短评角色.md` 精炼；仅表格无文字 → 过
4. **检查结果**：
   - 成功 → 读取 HTML，向用户展示摘要
   - 失败 → 根据错误信息排查（见下方错误表）
5. **用户审核**：最多 3 轮调整
6. **交付**：告知文件路径，询问是否通过企微群机器人发送日报（使用 `send-wecom-group-message` skill）

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

`config/config.json` 关键字段（完整脱敏模板见 `config/config.example.json`）：

```json
{
  "env": "test",
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
