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

## API 数据源

### 核心（每日必调）

| API ID | 用途 | 支撑板块 |
|--------|------|---------|
| `cat_sql_trade_0019` | O32 指令查询 | 额度总览、笔数、价格 |
| `cat_api_trade_0002` | 头寸核查表 | 账户头寸 |
| `cat_api_trade_0021` | 进度汇总 | 交收预测 |
| `cat_sql_trade_0012` | 银行间回购实时行情 | 市场预测 |
| `cat_sql_trade_0001` | 交易日历 | 流程控制 |

### 补充

| API ID | 用途 |
|--------|------|
| `cat_sql_trade_0005` | 对手基本信息 |
| `cat_api_trade_0022` | 头寸预测 |
| `cat_sql_trade_0013` | 资金事件日历（OMO + 债券发行到期 + 政府债缴款） |
| `cat_sql_trade_0002` | 产品信息 |

**接口规范**：
- SQL → `POST {base_url}/admin/dataquery/execute/{api_id}` + JSON body
- API → `POST {base_url}/admin/apiquery/proxy/{api_id}` + form/json body
- 认证 → `Authorization: Bearer {api_key}`

### 资金事件日历（cat_sql_trade_0013）

- 汇总行：`DATA_TYP=汇总`、`DIM1_NM=OMO净投放` → 净投放额
- 明细行：`DIM3_NM` 为方向（投放/到期）
- **日期规则**：`STAT_DT` 是 UTC，+1 天 = 北京日期（查 6/18 → 筛 UTC 6/17）

## Oracle 数据源（QT 短评）

- **连接**：`10.191.0.178:5674` / 服务名 `cjhx` / 用户 `fm`
- **版本**：Oracle 11.2.0.4.0（必须 thick 模式）
- **Instant Client**：环境变量 `ORACLE_LIB_DIR`，默认 `D:\Program Files\oracle_client_x64\instantclient_21_8`
- **表**：`ats.t_repo_robot_chatmessage`

| 字段 | 类型 | 说明 |
|------|------|------|
| `MSG_DATE` | NUMBER | 消息日期（YYYYMMDD） |
| `MSG_TIME` | NUMBER | 9 位整数：HHMMSSfff（fff=毫秒） |
| `CHANNEL` | NUMBER | 频道（1=森浦QT, 3=通达信QT, 4=快确QT） |
| `CONTENT` | VARCHAR2 | 消息内容 |
| `MSG_SEND_NAME` | VARCHAR2 | 发送人姓名 |
| `MSG_GROUP_NAME` | VARCHAR2 | 群名称 |

### QT 分类关键词

定义在 `scripts/db_client.py::categorize_messages()`，按顺序匹配（命中即停）：
- **资金面**：回购、资金、头寸、融出、融入、R001/R007/DR001/DR007、利率、加权、央行、逆回购、MLF、OMO、投放、回笼
- **现券**：现券、债券、收益率、估值、成交、活跃券、国债、政金债、信用债、BP、YTM、利差
- **一级发行**：一级、发行、投标、新债、招标、边际、倍率、募
- **其他**：未命中

> **注意**：QT 数据源**不覆盖权益市场**。权益市场分析需通过 WebSearch 获取外部闭市总评。

## 当前实现板块（非模板合同）

> 本表记录当前代码中可复用的数据块。参考图目标结构以 `template-contract.md` 为准；本表不得作为“已对齐参考图”的证据。

| # | 当前实现/素材板块 | 数据源 | 图表 |
|---|------------------|--------|------|
| 1 | 交易额度汇总 | O32 | 表格+饼图 |
| 2 | 交易笔数 | O32 | 柱状图 |
| 3 | 交易价格汇总 | O32 利率 | 折线图 |
| 4 | 交收数据汇总 | 进度汇总 API | 表格 |
| 5 | 市场预测汇总 | 回购行情 | 利率表格 |
| 5b | 市场短评 | QT 聊天 | Tab 消息列表 |
| 6 | 趋势预测及偏离率 | 当日 O32 利率 | 简化版 |
| 7 | 区间预测及偏离率 | 当日 O32 利率 | 简化版 |
| 8 | 资金市场分析 | QT 短评 + 资金事件日历 | 文字分析+表格 |
| 9 | 现券市场分析 | QT 短评 | 文字分析+表格 |
| 10 | 权益市场分析 | WebSearch（A 股闭市总评） | 文字分析 |
| 11 | 一级市场分析 | QT 一级短评（暂代） | 待外部数据源 |
| 12 | 账户头寸 | 头寸核查表 | 表格 |
| 13 | 风险预警 | 规则引擎 | 风险表格 |
| 14 | 风险提示 | AI 综合分析 | 文字说明 |

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
- 复用 weekly-report 仓库配置（`../weekly-report/SKILL.md`）
- 默认使用 AI Gateway 测试环境（`https://aitest.cjhxfund.com/ai-gateway`）
- Python 项目使用 uv 管理依赖，脚本在 `scripts/` 目录

### O32 委托方向业务口径

| 取值 | 含义 | 适用业务分类 |
|------|------|-------------|
| `债券买入` / `债券卖出` | 债券交易 | 交易所业务、银行间业务 |
| `融资` / `融券` | 回购交易（正/逆） | 交易所业务、银行间业务 |
| `买入` / `卖出` | 个股交易 | 仅交易所业务（权益类） |

> 「债券买入/卖出」≠「买入/卖出」。分组统计时保留完整名称，不可简写。
