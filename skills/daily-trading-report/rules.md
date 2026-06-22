# 稳定规则

> 本文件记录已验证的稳定结论。修改前需确认事实。发现错误时直接修正并注明原因。

## 核心文件

| 文件 | 用途 |
|------|------|
| `scripts/generate_report.py` | 主入口脚本 |
| `scripts/api_client.py` | AI Gateway HTTP 调用 |
| `scripts/db_client.py` | Oracle QT 短评查询 |
| `scripts/data_collector.py` | 数据采集 + 聚合 |
| `scripts/chart_builder.py` | matplotlib 图表生成 |
| `scripts/report_template.html` | Jinja2 HTML 模板 |
| `config.json` | API + Oracle 配置 |
| `reference/API接口接入手册.md` | 完整接口文档 |
| `prompts/funding-commentary.md` | 资金市场分析精炼 prompt |
| `prompts/bond-commentary.md` | 现券市场分析精炼 prompt |
| `prompts/primary-commentary.md` | 一级市场分析精炼 prompt |
| `prompts/stock-commentary.md` | 权益市场分析生成 prompt |

## 数据计算原则

- **数值统计必须代码确定性计算**（`aggregate_*`/SQL），不得大模型推理或编造——LLM 大数求和/百分比/多步运算会漂移，破坏可重复与可审计
- **AI 仅做编排**（跑脚本/展示/WebSearch 取短评）与文字精炼；文字精炼按 `prompts/*.md` 模板执行（围绕业务目标、好/差示例驱动），数值一律引用代码结果，不产出不改写

## API 数据源

### 核心（每日必调）

| API ID | 用途 | 支撑板块 |
|--------|------|---------|
| `cat_sql_trade_0019` | O32 指令查询 | 额度总览、笔数、价格 |
| `cat_api_trade_0002` | 头寸核查表 | 账户头寸 |
| `cat_api_trade_0008` | 实时正回购询价结果 | 应急回购明细（02） |
| `cat_sql_trade_0012` | 银行间回购实时行情 | 市场预测 |
| `cat_sql_trade_0001` | 交易日历 | 流程控制 |

### 补充

| API ID | 用途 |
|--------|------|
| `cat_sql_trade_0005` | 对手基本信息 |
| `cat_api_trade_0022` | 头寸预测 |
| `cat_sql_trade_0013` | 资金事件日历（OMO + 债券发行到期 + 政府债缴款 + 一级市场发行） |
| `cat_sql_trade_0002` | 产品信息 |

**接口规范**：
- SQL → `POST {base_url}/admin/dataquery/execute/{api_id}` + JSON body
- API → `POST {base_url}/admin/apiquery/proxy/{api_id}` + form/json body
- 认证 → `Authorization: Bearer {api_key}`

### 资金事件日历（cat_sql_trade_0013）

- 汇总行：`DATA_TYP=汇总`、`DIM1_NM=OMO净投放` → 净投放额
- 明细行：`DIM3_NM` 为方向（投放/到期/发行）
- **发行识别**：`EVNT_TYP_NM="发行与到期"` 且 `DIM3_NM` 含 `"发行"` → 一级市场发行数据；仅 `DIM3_NM="发行"` 不误判到期
- **日期规则**：`STAT_DT` 是 UTC，+1 天 = 北京日期（查 6/18 → 筛 UTC 6/17）

## Oracle 数据源（QT 短评）

- **连接**：`10.191.0.178:5674` / 服务名 `cjhx` / 用户 `fm`
- **版本**：Oracle 11.2.0.4.0（必须 thick 模式）
- **Instant Client**：环境变量 `ORACLE_LIB_DIR`，默认 `D:\Program Files\oracle_client_x64\instantclient_21_8`
- **表**：`ats.t_repo_robot_chatmessage`

- **字段映射与分类关键词**：见 `findings.md`
- **覆盖范围**：QT 仅覆盖资金面/现券/一级发行，**不覆盖权益市场**（权益需 WebSearch）

## 踩坑表

| 问题 | 根因 | 解决 |
|------|------|------|
| `DPY-3010` thin mode | Oracle 11g 不支持 | 必须 `init_oracle_client()` thick 模式 |
| `ORA-01745` bind variable | `:date` 是保留字 | 用 `:p_date` |
| `ORA-00933` 分页 | 11g 不支持 `FETCH FIRST` | 用 `WHERE ROWNUM <= N` |
| `ORA-00904` 列名 | 列名非预期 | 先 `ALL_TAB_COLUMNS` 查实际列名 |
| MSG_TIME 显示异常 | 9 位整数 HHMMSSfff | `f"{val:09d}"` 补齐取前 6 位 |
| STAT_DT 日期偏移 | UTC 时间 | UTC 日期 + 1 = 北京日期 |
| Windows GBK 编码 | emoji 输出到 cmd | `PYTHONIOENCODING=utf-8` |

## 关键决策

- 输出路径：`reports/YYYY-MM-DD-daily.html`，UTF-8 无 BOM，LF 换行
- 图表 matplotlib base64 内嵌 HTML，无外部 JS 依赖
- 默认使用 AI Gateway 测试环境（`https://aitest.cjhxfund.com/ai-gateway`）
- Python 项目使用 uv 管理依赖，脚本在 `scripts/` 目录

### O32 委托方向业务口径

| 取值 | 含义 | 适用业务分类 |
|------|------|-------------|
| `债券买入` / `债券卖出` | 债券交易 | 交易所业务、银行间业务 |
| `融资` / `融券` | 回购交易（正/逆） | 交易所业务、银行间业务 |
| `买入` / `卖出` | 个股交易 | 仅交易所业务（权益类） |

> 「债券买入/卖出」≠「买入/卖出」。分组统计时保留完整名称，不可简写。

## 测试环境数据特性

- **QT 短评（Oracle）**：历史数据完整，交易日单日可达数万条（如 20260617 约 77,000 条）；非交易日为 0
- **O32 / API（测试环境）**：仅保留当日/近期数据，查**历史日期**通常返回 0 条（非报错、非 403）；查当日或近期才有数据
- **降级**：O32/API 为 0 时按 `template-contract.md` 占位规则降级，不影响其余板块
