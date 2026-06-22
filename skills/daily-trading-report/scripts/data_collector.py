"""数据采集模块 — 从 AI Gateway API 采集并聚合交易数据。

采集流程：
  Phase 1（并行基础数据）：O32指令、头寸、应急回购、回购行情、交易日历
  Phase 2（补充数据）：对手信息、头寸预测、资金事件
"""

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Any

from api_client import call_sql_api, call_api, call_form_api
from desensitize import mask_product_fields
from external_market import collect_external_market_indicators


def _parse_date(date_str: str | None) -> str:
    """解析日期字符串，返回 YYYYMMDD 格式。"""
    if date_str:
        return date_str.replace("-", "")
    return datetime.now().strftime("%Y%m%d")


def _fmt_display_date(date_str: str) -> str:
    """将 YYYYMMDD 转为 YYYY-MM-DD 显示格式。"""
    return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"


def _fmt_template_date(date_str: str) -> str:
    """将 YYYYMMDD 转为参考模板标题区日期格式。"""
    dt = datetime.strptime(date_str, "%Y%m%d")
    return f"{dt.year}年{dt.month}月{dt.day}日"


def _weekday_name(date_str: str) -> str:
    """返回星期几的中文名。"""
    days = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    dt = datetime.strptime(date_str, "%Y%m%d")
    return days[dt.weekday()]


def _as_float(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _fmt_point(value: float | None, digits: int = 2) -> str:
    if value is None:
        return "暂无相关数据"
    return f"{value:.{digits}f}"


def _trend_from_score(score: float, up_label: str = "上行", down_label: str = "下行") -> str:
    if score >= 1.0:
        return up_label
    if score <= -1.0:
        return down_label
    return "持平"


def _funding_condition(text: str) -> str:
    if not text or text == "暂无有效消息":
        return "暂无有效消息"
    if any(word in text for word in ["不松", "偏紧", "紧张", "资金难借", "融入需求"]):
        return "不松"
    if any(word in text for word in ["偏松", "宽松", "融出意愿较强"]):
        return "偏松"
    if any(word in text for word in ["平稳", "均衡"]):
        return "均衡"
    return "不松"


def _forecast_point(current: float | None, trend: str, step: float, digits: int = 2) -> str:
    if current is None:
        return "\\"
    if trend == "上行":
        return _fmt_point(current + step, digits)
    if trend == "下行":
        return _fmt_point(max(current - step, 0), digits)
    return _fmt_point(current, digits)


def build_market_forecast(
    repo_rates: list[dict],
    money_market: dict,
    market_commentary: dict,
    external_market: dict | None = None,
) -> dict:
    """Build the forecast table shown in the reference report."""
    indicators: list[dict[str, str]] = []
    rows: list[dict[str, str]] = []
    funding_score = 0.0
    bond_score = 0.0
    external_market = external_market or {}

    for rate in repo_rates[:6]:
        name = str(rate.get("SECURITY_NAME") or rate.get("SECURITY_CODE") or "").strip()
        latest = _as_float(rate.get("LAST_PRICE", rate.get("LATEST_PRICE")))
        high = _as_float(rate.get("HIGH_PRICE"))
        low = _as_float(rate.get("LOW_PRICE"))
        if not name or latest is None:
            continue

        indicators.append({
            "name": f"{name} 最新利率",
            "value": f"{latest:.2f}%",
            "source": str(rate.get("SOURCE") or "O32 回购行情 cat_sql_trade_0012"),
        })
        if name in {"R001", "DR001"}:
            if latest >= 2.0:
                funding_score += 1.0
            elif latest <= 1.5:
                funding_score -= 1.0
        elif name in {"R007", "DR007"}:
            if latest >= 2.2:
                funding_score += 1.0
            elif latest <= 1.7:
                funding_score -= 1.0

        if high is not None and low is not None and high - low >= 0.3:
            funding_score += 0.5

    if money_market.get("has_data"):
        omo_net = _as_float(money_market.get("omo_net_inject")) or 0.0
        gov_pay = _as_float(money_market.get("gov_bond_payment")) or 0.0
        indicators.append({
            "name": "OMO 净投放",
            "value": f"{omo_net:.2f} 亿元",
            "source": "资金事件日历 cat_sql_trade_0013",
        })
        indicators.append({
            "name": "政府债缴款",
            "value": f"{gov_pay:.2f} 亿元",
            "source": "资金事件日历 cat_sql_trade_0013",
        })
        if omo_net > 0:
            funding_score -= 1.0
        elif omo_net < 0:
            funding_score += 1.0
        if gov_pay > 0:
            funding_score += 1.0
        elif gov_pay < 0:
            funding_score -= 0.5

    funding_text = str(market_commentary.get("funding", ""))
    funding_condition = _funding_condition(funding_text)
    if funding_text and funding_text != "暂无有效消息":
        if funding_condition in {"不松", "偏紧"}:
            funding_score += 1.0
        elif funding_condition == "偏松":
            funding_score -= 1.0
        indicators.append({
            "name": "QT 资金面情绪",
            "value": funding_condition,
            "source": "QT 资金面短评",
        })

    bond_text = str(market_commentary.get("bond", ""))
    if bond_text and bond_text != "暂无有效消息":
        if any(word in bond_text for word in ["收益率上行", "走弱", "卖方", "OFR"]):
            bond_score += 1.0
            bond_sentiment = "偏弱"
        elif any(word in bond_text for word in ["收益率下行", "走强", "买方", "BID"]):
            bond_score -= 1.0
            bond_sentiment = "偏强"
        else:
            bond_sentiment = "中性"
        indicators.append({
            "name": "QT 现券情绪",
            "value": bond_sentiment,
            "source": "QT 现券短评",
        })

    curve = external_market.get("treasury_curve", {})
    if curve.get("available"):
        for point in curve.get("points", []):
            term = str(point.get("term", ""))
            yield_value = _as_float(point.get("yield"))
            if yield_value is None:
                continue
            if term in {"1", "10"}:
                indicators.append({
                    "name": f"国债 {term}Y 收盘收益率",
                    "value": f"{yield_value:.4f}%",
                    "source": "中国货币网债券收盘收益率曲线",
                })
            if term == "10":
                if yield_value >= 2.2:
                    bond_score += 0.5
                elif yield_value <= 1.8:
                    bond_score -= 0.5

    funding_trend = funding_condition if funding_condition != "暂无有效消息" else "暂无判断"
    rows.append({
        "asset_type": "资金",
        "core_type": "资金面",
        "indicator": "资金面判断",
        "current": funding_condition,
        "forecast_point": "\\",
        "trend": funding_trend,
    })

    treasury_10y = None
    if curve.get("available"):
        for point in curve.get("points", []):
            if str(point.get("term")) == "10":
                treasury_10y = _as_float(point.get("yield"))
                break
    bond_score += max(min(funding_score / 2, 1.0), -1.0)
    bond_trend = _trend_from_score(bond_score)
    rows.append({
        "asset_type": "现券",
        "core_type": "10年国债",
        "indicator": "10Y国债收益率",
        "current": _fmt_point(treasury_10y, 4),
        "forecast_point": _forecast_point(treasury_10y, bond_trend, 0.01, 4),
        "trend": bond_trend if treasury_10y is not None else "暂无判断",
    })

    equity_indices = {
        row.get("name"): row for row in external_market.get("equity_indices", {}).get("indices", [])
    }
    equity_source = external_market.get("equity_indices", {}).get("source", "新浪财经")
    for display_name, source_name in [
        ("上证指数", "上证指数"),
        ("深证成指", "深证成指"),
        ("创业板", "创业板指"),
        ("科创50", "科创50"),
    ]:
        quote = equity_indices.get(source_name, {})
        latest = _as_float(quote.get("latest"))
        pct_change = _as_float(quote.get("pct_change")) or 0.0
        trend = "上行" if pct_change > 0 else "下行" if pct_change < 0 else "持平"
        if latest is not None:
            indicators.append({
                "name": display_name,
                "value": _fmt_point(latest, 2),
                "source": equity_source,
            })
        rows.append({
            "asset_type": "权益",
            "core_type": "行情指数",
            "indicator": display_name,
            "current": _fmt_point(latest, 2),
            "forecast_point": _forecast_point(latest, trend, (latest or 0) * 0.002, 2),
            "trend": trend if latest is not None else "暂无判断",
        })

    primary_text = str(market_commentary.get("primary", ""))
    cd_rate = None
    for token in primary_text.replace("%", " ").replace("，", " ").split():
        parsed = _as_float(token)
        if parsed is not None and 0.5 <= parsed <= 5:
            cd_rate = parsed
            break
    spread_direction = "正" if any(word in primary_text for word in ["正", "走阔", "利差"]) else "暂无判断"
    rows.extend([
        {
            "asset_type": "一级",
            "core_type": "行情指数",
            "indicator": "1Y大行CD发行",
            "current": _fmt_point(cd_rate, 3),
            "forecast_point": _fmt_point(cd_rate, 3) if cd_rate is not None else "\\",
            "trend": "持平" if cd_rate is not None else "暂无判断",
        },
        {
            "asset_type": "一级",
            "core_type": "行情指数",
            "indicator": "1Y大行CD二级利差",
            "current": spread_direction,
            "forecast_point": "\\",
            "trend": spread_direction,
        },
    ])

    available = any(row["current"] not in {"暂无相关数据", "暂无有效消息", "暂无判断"} for row in rows)
    if not available and not indicators:
        return {
            "available": False,
            "conclusion": "预测指标来源尚未确认",
            "rows": rows,
            "indicators": [],
            "methodology": "资金利率、公开市场操作、债券收益率曲线和 QT 情绪等预测指标尚未完成来源确认，暂不生成方向性预测。",
            "sources": [],
            "reason": "当前预测指标数据源尚未完成映射，暂不生成方向性预测。",
        }

    methodology = (
        "资金面当日行情来自 17 点后 QT 资金短评中的情绪判断；OMO 净投放和政府债缴款继续使用 cat_sql_trade_0013 作为资金扰动校验。"
        "现券行使用中国货币网国债收盘收益率曲线，权益行使用外部指数行情并做短线动量外推。"
        "一级 CD 行优先从一级发行短评中抽取发行利率和利差方向；缺少对应短评时明确降级，不编造点位。"
    )
    return {
        "available": True,
        "conclusion": "市场预测汇总表",
        "rows": rows,
        "indicators": indicators,
        "methodology": methodology,
        "sources": sorted({indicator["source"] for indicator in indicators}),
        "reason": "",
    }


def build_risk_tips(risk_warnings: list[dict]) -> list[str]:
    """Build fixed compliance tips plus a lightweight dynamic risk summary."""
    tips = [
        "请密切关注明日到期回购资金的安排，提前做好头寸准备。",
        "关注央行公开市场操作动向，合理安排资金交易节奏。",
        "注意交易对手集中度风险，分散交易对手以降低信用风险。",
    ]
    if risk_warnings:
        tips.insert(0, f"今日规则引擎识别到 {len(risk_warnings)} 条风险线索，请优先复核高等级事项。")
    return tips


def build_equity_market_analysis(commentary: str | None = None) -> dict:
    """Build equity market analysis from external input or the contract fallback."""
    text = (commentary or "").strip()
    if text:
        return {
            "available": True,
            "commentary": text,
            "source": "external",
        }
    return {
        "available": False,
        "commentary": "外部短评暂未获取",
        "source": "fallback",
    }


def _deduplicate_instructions(records: list[dict]) -> list[dict]:
    """按指令编号去重，保留修改序号最大的记录。

    O32 接口对同一指令的每次修改都会返回一条新记录（修改序号递增）。
    聚合前必须去重，否则已修改/已撤销的旧版本会被重复计入统计。
    """
    best: dict = {}
    for r in records:
        instr_id = r.get("指令编号")
        mod_seq = r.get("修改序号", 1)
        if instr_id is None:
            continue
        if instr_id not in best or mod_seq > best[instr_id][1]:
            best[instr_id] = (r, mod_seq)
    return [v[0] for v in best.values()]


def collect_trade_instructions(query_date: str) -> list[dict]:
    """采集 O32 交易指令数据（cat_sql_trade_0019）。

    返回指令列表（已按指令编号去重保留最新修改序号，产品代码/名称已脱敏）。
    """
    result = call_sql_api("cat_sql_trade_0019", {"queryDate": int(query_date)})
    records = result.get("body", [])
    records = _deduplicate_instructions(records)
    return [mask_product_fields(r) for r in records]


def collect_position_data() -> list[dict]:
    """采集头寸核查表数据（cat_api_trade_0002）。"""
    result = call_form_api("cat_api_trade_0002", {
        "page": 1,
        "size": 2000,
        "exchangeSettlementMode": 1,
        "positionSortingType": 1,
        "liquidationStatus": 2,
        "positionAzyllsType": 3,
        "totalPositionAzylls": 3,
        "floorFinancingDiagnosis": 0,
        "redemptionModeList": 0,
        "isNotOtherPlace": 1,
        "totalManagerLevel": 1,
        "totalPositionStatusTypeList": "2,3,4,5,16,6",
        "totalPositionStatus": 1,
    })
    body = result.get("data", {}).get("body", {})
    return body.get("rows", [])


def _direct_time_hhmmss(text) -> str:
    """从 repoInsDirectTimeText（如 '谢创 2026-06-22 10:14:28'）提取 HH:MM:SS。

    格式：'<人名> <YYYY-MM-DD> <HH:MM:SS>'。解析失败返回 ''。
    """
    if not isinstance(text, str):
        return ""
    parts = text.strip().split()
    if len(parts) < 2:
        return ""
    segs = parts[-1].split(":")
    if len(segs) == 3 and all(len(s) == 2 for s in segs):
        return f"{segs[0]}:{segs[1]}:{segs[2]}"
    return ""


def collect_emergency_repo(query_date: str) -> list[dict]:
    """采集应急回购明细（cat_api_trade_0008 实时正回购询价结果）。

    应急判定：当日（opDate == query_date）且指令下达时间（repoInsDirectTimeText）
    在 16:00 及以后。0008 服务端不支持按日期/时间过滤，需客户端二次筛选。
    返回原始行（含真实 productName，外流前需脱敏）。
    """
    result = call_api("cat_api_trade_0008", {
        "rows": 2000,
        "page": 1,
        "rivalIdList": [],
        "inqResStatusList": [1, 3, 9],  # 有效 / 草稿 / 已下达
        "sideCodeList": ["7"],          # 正回购
    })
    # 响应结构：data._embedded.vos[].inqResultMgrQueryInfos[]
    embedded = result.get("data", {}).get("_embedded", {})
    rows: list[dict] = []
    for vo in embedded.get("vos", []) or []:
        rows.extend(vo.get("inqResultMgrQueryInfos", []) or [])

    return [
        r for r in rows
        if r.get("opDate") == query_date
        and _direct_time_hhmmss(r.get("repoInsDirectTimeText", ""))[:5] >= "16:00"
    ]


def collect_repo_rates() -> list[dict]:
    """采集银行间回购实时行情（cat_sql_trade_0012）。"""
    result = call_sql_api("cat_sql_trade_0012", {})
    return result.get("body", [])


def collect_trading_calendar() -> list[dict]:
    """采集交易日历（cat_sql_trade_0001）。"""
    result = call_sql_api("cat_sql_trade_0001", {})
    return result.get("body", [])


def collect_fund_events(begin_date: str, end_date: str) -> list[dict]:
    """采集资金事件日历（cat_sql_trade_0013）。"""
    result = call_sql_api("cat_sql_trade_0013", {
        "beginDate": int(begin_date),
        "endDate": int(end_date),
    })
    return result.get("body", [])


def collect_rival_info(last_rival_id: int = 0) -> list[dict]:
    """采集对手基本信息（cat_sql_trade_0005）。"""
    result = call_sql_api("cat_sql_trade_0005", {"lastRivalId": str(last_rival_id)})
    return result.get("body", [])


def collect_position_forecast(end_date: str) -> list[dict]:
    """采集头寸预测（cat_api_trade_0022）。"""
    result = call_form_api("cat_api_trade_0022", {
        "fundList": "",
        "page": 1,
        "size": 2000,
        "endDate": end_date,
        "containTreatConfirmApply": 0,
        "containConfirmedRedeemFundBal": 0,
        "productLevel": 0,
        "managerLevel": 0,
        "positionStatus": "",
        "positionFlatDays": -1,
    })
    body = result.get("data", {}).get("body", {})
    return body.get("rows", [])


def is_trading_day(query_date: str, calendar_data: list[dict] | None = None) -> bool:
    """判断是否为交易日。"""
    if calendar_data is None:
        calendar_data = collect_trading_calendar()
    date_int = int(query_date)
    for entry in calendar_data:
        if entry.get("SYS_DATE") == date_int:
            return entry.get("TRADEDAY_FLAG", 0) == 1
    # 如果不在日历范围内，默认周一到周五为交易日
    dt = datetime.strptime(query_date, "%Y%m%d")
    return dt.weekday() < 5


# ──────────────────────────────────────────────
# 数据聚合计算
# ──────────────────────────────────────────────


def aggregate_trade_overview(instructions: list[dict]) -> dict:
    """聚合交易额度总览数据。

    按「业务分类」+「委托方向」分组，统计：
    - 总笔数
    - 指令总金额
    - 成交总金额
    """
    overview: dict[str, dict[str, Any]] = {}

    for inst in instructions:
        biz_type = inst.get("业务分类", "未知")
        direction = inst.get("委托方向", "未知")
        status = inst.get("指令状态", "")

        # 过滤已撤销指令
        if "撤销" in status:
            continue

        key = f"{biz_type}·{direction}"
        if key not in overview:
            overview[key] = {"笔数": 0, "指令金额": 0.0, "成交金额": 0.0}

        overview[key]["笔数"] += 1
        overview[key]["指令金额"] += float(inst.get("指令金额", 0) or 0)
        overview[key]["成交金额"] += float(inst.get("成交金额", 0) or 0)

    # 汇总
    total_count = sum(v["笔数"] for v in overview.values())
    total_amount = sum(v["指令金额"] for v in overview.values())
    total_deal = sum(v["成交金额"] for v in overview.values())

    return {
        "分类明细": overview,
        "总笔数": total_count,
        "总指令金额": total_amount,
        "总成交金额": total_deal,
    }


def aggregate_trade_count_by_hour(instructions: list[dict]) -> dict:
    """按小时聚合交易笔数（日内分布）。"""
    hourly: dict[str, int] = {}

    for inst in instructions:
        time_val = inst.get("指令下达时间", 0)
        if not time_val:
            continue
        # 时间格式 HHMMSS（整数），提取小时
        hour = int(time_val) // 10000
        hour_str = f"{hour:02d}:00"
        hourly[hour_str] = hourly.get(hour_str, 0) + 1

    # 按时间排序
    return dict(sorted(hourly.items()))


def aggregate_trade_prices(instructions: list[dict]) -> dict:
    """按回购天数聚合交易价格（利率）。

    只统计融资回购类指令。
    """
    prices: dict[str, list[float]] = {}

    for inst in instructions:
        direction = inst.get("委托方向", "")
        if "回购" not in direction:
            continue

        price = inst.get("指令价格(回购为利率)", 0)
        if not price or price < 0:
            continue

        repo_days = inst.get("回购天数", 0)
        if not repo_days or repo_days < 0:
            continue

        # 按品种分类：1天=R001, 7天=R007, 14天=R014
        if repo_days == 1:
            label = "R001"
        elif repo_days == 7:
            label = "R007"
        elif repo_days == 14:
            label = "R014"
        else:
            label = f"R{repo_days:03d}"

        if label not in prices:
            prices[label] = []
        prices[label].append(float(price))

    # 计算每个品种的均值和笔数
    result = {}
    for label, vals in sorted(prices.items()):
        result[label] = {
            "平均利率": round(sum(vals) / len(vals), 4),
            "最高利率": round(max(vals), 4),
            "最低利率": round(min(vals), 4),
            "笔数": len(vals),
        }
    return result


def aggregate_emergency_repo(rows: list[dict]) -> dict:
    """聚合应急回购明细，供 02 板块渲染。

    按指令下达时间升序排列；同一 productId 多笔记录映射到同一「产品N」编号。
    """
    if not rows:
        return {"has_data": False, "明细": [], "总笔数": 0, "总金额万元": 0.0}

    sorted_rows = sorted(
        rows, key=lambda r: _direct_time_hhmmss(r.get("repoInsDirectTimeText", ""))
    )

    product_index: dict[str, str] = {}
    counter = 0
    items: list[dict] = []
    for row in sorted_rows:
        pid = str(row.get("productId") or row.get("productCode") or "")
        if pid not in product_index:
            counter += 1
            product_index[pid] = f"产品{counter}"

        # 利率：优先 repoPriceText（如 'R+0BP'），为空回退 repurRate
        rate_text = (row.get("repoPriceText") or "").strip()
        利率 = rate_text if rate_text else str(row.get("repurRate", "0") or "0")

        items.append({
            "序号": len(items) + 1,
            "产品编号": product_index[pid],
            "回购金额万元": round(float(row.get("repurAmt", 0) or 0) / 10000, 2),
            "期限天": int(row.get("repurDay", 0) or 0),
            "利率": 利率,
            "对手方": row.get("rivalName", "") or "",
            "操作时间": _direct_time_hhmmss(row.get("repoInsDirectTimeText", "")),
            "状态": row.get("inqResStatusText", "") or "",
        })

    return {
        "has_data": True,
        "明细": items,
        "总笔数": len(items),
        "总金额万元": round(sum(x["回购金额万元"] for x in items), 2),
    }


def aggregate_money_market(events: list[dict], query_date: str = "") -> dict:
    """聚合货币市场数据（资金事件日历 cat_sql_trade_0013）。

    事件类型：
    - 公开市场操作：央行 OMO（逆回购/MLF/买断式回购/国库定存等），含汇总行（OMO净投放）
    - 发行与到期：NCD/地方债/政金债等发行与到期明细
    - 政府债缴款：政府债券净缴款

    STAT_DT 格式为 ISO 字符串（如 "2026-06-17T16:00:00.000+0000"），
    UTC 日期 + 1 天 = 北京时间日期。
    """
    if not events:
        return {
            "omo_operations": [],
            "omo_net_inject": 0.0,
            "bond_maturities": [],
            "gov_bond_payment": 0.0,
            "has_data": False,
        }

    # 将 query_date（YYYYMMDD）转为对应的 UTC 日期（减 1 天）
    target_utc_date = ""
    if query_date:
        dt = datetime.strptime(query_date, "%Y%m%d")
        utc_dt = dt - timedelta(days=1)
        target_utc_date = utc_dt.strftime("%Y-%m-%d")

    # 按日期分类
    by_date: dict[str, list[dict]] = {}
    for evt in events:
        dt_raw = evt.get("STAT_DT", "")
        if isinstance(dt_raw, str) and len(dt_raw) >= 10:
            date_key = dt_raw[:10]
            by_date.setdefault(date_key, []).append(evt)

    # 优先取目标日期，否则取最新日期
    day_events = by_date.get(target_utc_date)
    data_date = target_utc_date
    if day_events is None:
        sorted_dates = sorted(by_date.keys(), reverse=True)
        data_date = sorted_dates[0] if sorted_dates else ""
        day_events = by_date.get(data_date, [])

    # 将 data_date（UTC）转为北京时间显示
    if data_date:
        display_date = (datetime.strptime(data_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        display_date = ""

    # 按事件类型分组
    omo_summary = []
    omo_net = 0.0
    bond_mat = []
    gov_pay = 0.0

    for evt in day_events:
        evnt_type = evt.get("EVNT_TYP_NM", "")
        data_typ = evt.get("DATA_TYP", "")
        dim1 = evt.get("DIM1_NM", "")
        dim2 = evt.get("DIM2_NM", "")
        dim3 = evt.get("DIM3_NM", "")
        val = float(evt.get("INDX_VAL", 0) or 0)

        if evnt_type == "公开市场操作":
            if data_typ == "汇总" and "净投放" in dim1:
                omo_net = val
            else:
                direction = dim3
                omo_summary.append({
                    "操作": dim1,
                    "期限": dim2 if dim2 != "ALL" else "—",
                    "方向": direction,
                    "金额(亿)": round(val, 2),
                })
        elif evnt_type == "发行与到期":
            if data_typ == "明细":
                bond_mat.append({
                    "品种": dim1,
                    "期限": dim2,
                    "方向": dim3,
                    "金额(亿)": round(val, 2),
                })
        elif evnt_type == "政府债缴款":
            if data_typ == "汇总":
                gov_pay = val

    # 按品种汇总
    bond_by_type: dict[str, dict[str, Any]] = {}
    for item in bond_mat:
        key = item["品种"]
        if key not in bond_by_type:
            bond_by_type[key] = {"品种": key, "到期(亿)": 0.0, "发行(亿)": 0.0}
        if item["方向"] == "到期":
            bond_by_type[key]["到期(亿)"] += item["金额(亿)"]
        elif item["方向"] in ("发行", "缴款"):
            bond_by_type[key]["发行(亿)"] += item["金额(亿)"]

    return {
        "data_date": display_date,
        "omo_operations": omo_summary,
        "omo_net_inject": round(omo_net, 2),
        "bond_maturities": sorted(bond_by_type.values(), key=lambda x: x["到期(亿)"], reverse=True),
        "gov_bond_payment": round(gov_pay, 2),
        "has_data": bool(day_events),
    }


def aggregate_primary_market(events: list[dict], query_date: str = "") -> dict:
    """从资金事件日历中提取一级市场发行数据。

    识别逻辑（不会被 DIM3 中的「到期」噪音干扰）：
    - 汇总行：EVNT_TYP_NM="发行与到期" AND DATA_TYP="汇总" AND DIM3_NM 包含"发行"
      → 利率债发行 / 地方债发行 / NCD发行（每日最多各一条）
    - 明细行：EVNT_TYP_NM="发行与到期" AND DATA_TYP="明细" AND DIM3_NM="发行"
      → 国债/政金债/地方债/NCD × 期限（到期行 DIM3="到期"，不会被误识）
    - 汇总行缺失时，从明细行汇总推算 totals。
    - 当日无任何发行数据时 available=False。

    STAT_DT 日期映射同 aggregate_money_market（UTC+1天=北京时间）。
    """
    if not events:
        return {"available": False, "reason": "暂无一级市场发行数据"}

    # UTC 日期映射
    target_utc_date = ""
    if query_date:
        dt = datetime.strptime(query_date, "%Y%m%d")
        utc_dt = dt - timedelta(days=1)
        target_utc_date = utc_dt.strftime("%Y-%m-%d")

    # 按日期筛选
    day_events: list[dict] = []
    for e in events:
        raw = e.get("STAT_DT", "")
        if isinstance(raw, str) and raw[:10] == target_utc_date:
            day_events.append(e)

    # 目标日期无数据时取最新日期
    data_date = target_utc_date
    if not day_events and events:
        dates = sorted(
            {str(e.get("STAT_DT", ""))[:10] for e in events if e.get("STAT_DT")},
            reverse=True,
        )
        if dates:
            data_date = dates[0]
            day_events = [e for e in events if str(e.get("STAT_DT", ""))[:10] == data_date]

    # 北京时间显示
    if data_date:
        display_date = (datetime.strptime(data_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        display_date = ""

    # 提取发行数据
    issuance_summary: dict[str, float] = {}   # 品种名→金额（汇总行）
    issuance_detail: list[dict] = []          # [{品种, 期限, 金额(亿)}]

    for e in day_events:
        if e.get("EVNT_TYP_NM") != "发行与到期":
            continue
        dim3 = e.get("DIM3_NM", "")
        if "发行" not in dim3:                # 到期/其他行全部跳过
            continue
        val = float(e.get("INDX_VAL", 0) or 0)
        if e.get("DATA_TYP") == "汇总":
            # 利率债发行 / 地方债发行 / NCD发行
            issuance_summary[dim3] = val
        elif dim3 == "发行":                   # 明细行，精确匹配"发行"二字
            issuance_detail.append({
                "品种": e.get("DIM1_NM", ""),
                "期限": e.get("DIM2_NM", ""),
                "金额(亿)": round(val, 2),
            })

    has_data = bool(issuance_summary) or bool(issuance_detail)
    if not has_data:
        return {"available": False, "reason": "今日无一级市场发行数据"}

    # 汇总行缺失时从明细推算
    def _get_total(category: str) -> float:
        if category in issuance_summary:
            return issuance_summary[category]
        # 从明细汇总
        cat_map = {"利率债发行": ("国债", "政金债"), "地方债发行": ("地方债",), "NCD发行": ("NCD",)}
        names = cat_map.get(category, ())
        return round(sum(d["金额(亿)"] for d in issuance_detail if d["品种"] in names), 2)

    totals = {
        "利率债": _get_total("利率债发行"),
        "地方债": _get_total("地方债发行"),
        "NCD": _get_total("NCD发行"),
    }

    # 生成文字摘要
    parts = []
    for label, cat in [("利率债", "利率债"), ("地方债", "地方债"), ("NCD", "NCD")]:
        if totals[cat] > 0:
            parts.append(f"{label} {totals[cat]:.0f}亿")
    summary = "今日一级市场发行：" + "，".join(parts) if parts else "今日一级市场发行数据"

    # 按品种分组
    by_type: dict[str, dict] = {}
    for d in issuance_detail:
        t = d["品种"]
        if t not in by_type:
            by_type[t] = {"品种": t, "发行(亿)": 0.0, "明细": []}
        by_type[t]["发行(亿)"] += d["金额(亿)"]
        by_type[t]["明细"].append(d)

    structure_parts = []
    for t, info in sorted(by_type.items()):
        d_str = ", ".join(f"{d['期限']} {d['金额(亿)']:.0f}亿" for d in info["明细"])
        structure_parts.append(f"{t}（{d_str}），合计 {info['发行(亿)']:.0f}亿")
    structure_summary = "；".join(structure_parts) + "。"

    return {
        "available": True,
        "data_date": display_date,
        "summary": summary,
        "totals": totals,
        "structure": sorted(by_type.values(), key=lambda x: x["发行(亿)"], reverse=True),
        "structure_detail": issuance_detail,
        "structure_summary": structure_summary,
    }


def aggregate_risk_warnings(
    instructions: list[dict],
    positions: list[dict],
) -> list[dict]:
    """风险预警规则引擎。

    规则：
    1. 头寸不足：总头寸可用 < 阈值
    2. 指令质量：指令错误率偏高

    注：原「交收异常」规则随 cat_api_trade_0021 弃用而移除（0008 无交收进度字段）。
    """
    warnings: list[dict] = []

    # 规则 1：检查头寸
    for pos in positions:
        pos_type = pos.get("positionType", "")
        usable = pos.get("totalPositionT1Usable", 0)
        if usable is not None and float(usable or 0) < 0:
            warnings.append({
                "风险类型": "头寸不足",
                "产品": pos.get("fundName", pos.get("fundCode", "未知")),
                "详情": f"T+1可用头寸为 {usable}",
                "等级": "高",
            })

    # 规则 2：指令质量
    error_count = 0
    total_count = len(instructions)
    for inst in instructions:
        correctness = inst.get("o32InstructCorrectnessDesc", "")
        if "错误" in correctness:
            error_count += 1

    if total_count > 0 and error_count / total_count > 0.1:
        warnings.append({
            "风险类型": "指令质量",
            "产品": "全局",
            "详情": f"指令错误率 {error_count}/{total_count} ({error_count/total_count:.1%})",
            "等级": "中",
        })

    return warnings


def _clean_commentary_body(content: str) -> str:
    """无损清洗日评正文：去纯 URL 行、合并多余空行、去行尾空格。

    只删格式噪音，不改任何文字判断。
    """
    lines = []
    for line in content.splitlines():
        s = line.strip()
        if not s:
            continue
        if "http://" in s or "https://" in s:
            continue
        lines.append(s)
    return "\n".join(lines)


def generate_market_commentary(daily_commentary: dict) -> dict[str, str]:
    """基于日评代表篇生成资金/现券/一级市场分析文字。

    输入 fetch_daily_commentary 返回的结构（含 representative）。每主题整段
    引用代表篇原文（无损清洗）+ 来源标注；无日评时降级占位。一级无独立
    日评（见 findings），固定降级。不综合、不摘要、不枚举小节关键词。

    Returns:
        {"funding": str, "bond": str, "primary": str}
    """
    rep = (daily_commentary or {}).get("representative") or {}

    def _render(theme_report: dict | None) -> str:
        if not theme_report:
            return "暂无有效消息"
        body = _clean_commentary_body(str(theme_report.get("content", "")))
        source = str(theme_report.get("sender", "")).strip()
        time_val = str(theme_report.get("time", "")).strip()
        session = str(theme_report.get("session", "")).strip()
        parts = [p for p in (source, f"{time_val} {session}".strip()) if p]
        if parts:
            return f"{body}\n\n（来源：{' · '.join(parts)}）"
        return body

    return {
        "funding": _render(rep.get("资金")),
        "bond": _render(rep.get("现券")),
        "primary": "暂无相关数据",
    }


# ──────────────────────────────────────────────
# 主采集入口
# ──────────────────────────────────────────────


def collect_all(query_date: str | None = None) -> dict:
    """采集所有数据并聚合，返回报告所需的完整数据 dict。

    Args:
        query_date: 查询日期 YYYYMMDD，默认当日

    Returns:
        包含所有板块数据的 dict，可直接传给 Jinja2 模板
    """
    date_str = _parse_date(query_date)
    display_date = _fmt_display_date(date_str)
    weekday = _weekday_name(date_str)

    # Phase 1：并行采集基础数据
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(collect_trade_instructions, date_str): "instructions",
            executor.submit(collect_position_data): "positions",
            executor.submit(collect_emergency_repo, date_str): "emergency_repo",
            executor.submit(collect_repo_rates): "repo_rates",
            executor.submit(collect_trading_calendar): "calendar",
        }

        data: dict[str, Any] = {}
        for future in as_completed(futures):
            key = futures[future]
            try:
                data[key] = future.result()
            except Exception as e:
                print(f"[警告] {key} 数据采集失败: {e}")
                data[key] = [] if key != "calendar" else []

    instructions = data.get("instructions", [])
    positions = data.get("positions", [])
    emergency_rows = data.get("emergency_repo", [])
    repo_rates = data.get("repo_rates", [])
    calendar = data.get("calendar", [])

    # 检查是否为交易日
    trading_day = is_trading_day(date_str, calendar)

    # Phase 2：补充数据
    fund_events = []
    position_forecast = []
    try:
        # 资金事件：查近 7 天
        begin = (datetime.strptime(date_str, "%Y%m%d") - timedelta(days=3)).strftime("%Y%m%d")
        end = (datetime.strptime(date_str, "%Y%m%d") + timedelta(days=3)).strftime("%Y%m%d")
        fund_events = collect_fund_events(begin, end)
    except Exception as e:
        print(f"[警告] 资金事件采集失败: {e}")

    try:
        position_forecast = collect_position_forecast(date_str)
    except Exception as e:
        print(f"[警告] 头寸预测采集失败: {e}")

    # Phase 3：QT 日评（Oracle）——召回日评/早评/午评，按原文去重，选代表篇
    qt_commentary: dict[str, Any] = {}
    try:
        from db_client import fetch_daily_commentary
        qt_commentary = fetch_daily_commentary(date_str)
        print(f"  QT日评采集完成：召回 {qt_commentary.get('total_raw', 0)} 条 → 去重 {qt_commentary.get('total', 0)} 篇")
    except Exception as e:
        print(f"[警告] QT日评采集失败（非关键，继续）: {e}")
        qt_commentary = {
            "total": 0, "total_raw": 0, "reports": [],
            "representative": {"资金": None, "现券": None},
        }

    external_market = {}
    try:
        external_market = collect_external_market_indicators()
    except Exception as e:
        print(f"[警告] 外部市场指标采集失败（非关键，继续）: {e}")
        external_market = {}

    # 数据聚合
    trade_overview = aggregate_trade_overview(instructions)
    trade_count_hourly = aggregate_trade_count_by_hour(instructions)
    trade_prices = aggregate_trade_prices(instructions)
    emergency_repo = aggregate_emergency_repo(emergency_rows)
    money_market = aggregate_money_market(fund_events, date_str)
    primary_market = aggregate_primary_market(fund_events, date_str)
    risk_warnings = aggregate_risk_warnings(instructions, positions)
    market_commentary = generate_market_commentary(qt_commentary)

    forecast_repo_rates = repo_rates or external_market.get("repo_rates", {}).get("repo_rates", [])

    return {
        # 基础信息
        "query_date": date_str,
        "display_date": display_date,
        "template_date": _fmt_template_date(date_str),
        "weekday": weekday,
        "is_trading_day": trading_day,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),

        # 板块 1：交易额度总览
        "trade_overview": trade_overview,

        # 板块 2：交易笔数（按小时）
        "trade_count_hourly": trade_count_hourly,

        # 01 交易数据汇总：交易金额仍由 O32 分类金额填充，价格数据保留给后续明细扩展
        "trade_prices": trade_prices,

        # 02 交收数据汇总
        "emergency_repo": emergency_repo,

        # 03 市场预测汇总（回购行情 + 预测方法）
        "repo_rates": forecast_repo_rates,
        "market_forecast": build_market_forecast(forecast_repo_rates, money_market, market_commentary, external_market),

        # 04 资金市场分析
        "money_market": money_market,

        # 头寸附录数据，默认不进入主模板流
        "positions": positions,

        # 规则引擎风险附录数据，默认不进入主模板流
        "risk_warnings": risk_warnings,

        # 资金、现券、一级市场分析文字（基于 QT 短评）
        "market_commentary": market_commentary,

        # 板块 11：一级市场（发行数据来自资金事件日历）
        "primary_market": primary_market,

        # 权益指数行情（新浪/腾讯双源）
        "equity_indices": external_market.get("equity_indices", {}),

        # 权益市场分析：由 AI 执行期外部短评输入，纯脚本运行时降级
        "equity_market": build_equity_market_analysis(),

        # 风险提示
        "risk_tips": build_risk_tips(risk_warnings),

        # QT 聊天消息分类（资金面/现券/一级发行）
        "qt_commentary": qt_commentary,

        # 原始数据（供图表生成使用）
        "_instructions": instructions,
        "_positions": positions,
        "_emergency_rows": emergency_rows,
        "_repo_rates": forecast_repo_rates,
        "_fund_events": fund_events,
        "_external_market": external_market,
    }
