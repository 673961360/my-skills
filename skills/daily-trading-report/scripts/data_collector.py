"""数据采集模块 — 从 AI Gateway API 采集并聚合交易数据。

采集流程：
  Phase 1（并行基础数据）：O32指令、头寸、应急回购、回购行情、交易日历
  Phase 2（补充数据）：对手信息、头寸预测、资金事件
"""

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Any

from api_client import call_sql_api, call_api, call_form_api
from desensitize import mask_product_fields, mask_product_name
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


def _beijing_to_utc_date_key(query_date: str) -> str:
    """北京业务日期(YYYYMMDD) → 0013 STAT_DT 的 UTC 日期 key(YYYY-MM-DD)。

    STAT_DT 是 UTC 时间戳，+8h 才转北京时间，故 UTC 日期 = 北京日期 − 1 天。
    """
    beijing_dt = datetime.strptime(query_date, "%Y%m%d")
    return (beijing_dt - timedelta(days=1)).strftime("%Y-%m-%d")


def _utc_date_key_to_beijing(utc_key: str) -> str:
    """UTC 日期 key(YYYY-MM-DD) → 北京业务日期(YYYY-MM-DD)，用于展示标题。"""
    return (datetime.strptime(utc_key, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")


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
    if any(word in text for word in ["不松", "偏紧", "紧张", "转紧", "资金难借", "融入需求"]):
        return "不松"
    if any(word in text for word in ["偏松", "宽松", "融出意愿较强"]):
        return "偏松"
    if any(word in text for word in ["平稳", "均衡", "收敛"]):
        return "均衡"
    return "均衡"


def _fmt_money_amount(value: float | None) -> str:
    if value is None:
        return "\\"
    if abs(value - round(value)) < 0.005:
        return f"{value:.0f}"
    return f"{value:.2f}"


def _fmt_net_inject(value: float | None) -> str:
    if value is None:
        return "\\"
    sign = "+" if value > 0 else ""
    if abs(value - round(value)) < 0.005:
        return f"{sign}{value:.0f}"
    return f"{sign}{value:.2f}"


def _normalize_omo_project(name: str, term: str) -> str:
    text = f"{name}{term}"
    if "逆回购" in text:
        if "7" in text:
            return "7天逆回购"
        return "逆回购"
    if "MLF" in text.upper():
        return "MLF"
    if "买断式" in text:
        return "买断式逆回购"
    if "国库" in text:
        return "国库定存"
    return name or term or "公开市场操作"


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
    daily_commentary: dict | None = None,
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

    # 资金面判断：优先扫描所有资金日评去重篇，取多数判断
    # 无 daily_commentary 或无资金篇时退回到 market_commentary.funding（历史兼容）
    funding_texts = [
        str(r.get("content", "")) for r in (daily_commentary or {}).get("reports", [])
        if r.get("theme") == "资金"
    ]
    if funding_texts:
        # 去重后每篇独立判断，紧 > 均衡 > 松（悲观优先，避免午评偏松覆盖日评偏紧）
        conditions = [_funding_condition(t) for t in funding_texts if t]
        if any(c == "不松" for c in conditions):
            funding_condition = "不松"
        elif any(c == "均衡" for c in conditions):
            funding_condition = "均衡"
        elif any(c == "偏松" for c in conditions):
            funding_condition = "偏松"
        else:
            funding_condition = "暂无有效消息"
    else:
        funding_condition = _funding_condition(str(market_commentary.get("funding", "")))
    if funding_texts and funding_condition != "暂无有效消息":
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
        ("创业板", "创业板指"),
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
        and _direct_time_hhmmss(r.get("repoInsDirectTimeText", ""))[:5] >= "16:30"
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


def _is_invalid_instruction(inst: dict) -> bool:
    """判断指令是否无效：已撤销且无实际成交（未成交/缺失）才视为无效；有部分/全部成交的仍需统计。"""
    if str(inst.get("指令状态", "")) != "已撤销":
        return False
    # 成交状态缺失/空串视为未成交（已撤销的挂单无成交，应过滤）
    return str(inst.get("成交状态", "")).strip() not in ("全部成交", "部分成交")


def aggregate_trade_overview(instructions: list[dict]) -> dict:
    """聚合交易数据汇总。

    汇总口径固定为日报模板中的四类：现券、资金、权益、一级。
    金额按指令金额统计，单位在模板中换算为亿元。
    """
    categories = ("现券", "资金", "权益", "一级")
    overview: dict[str, dict[str, Any]] = {
        category: {"买入金额": 0.0, "卖出金额": 0.0, "买入笔数": 0, "卖出笔数": 0}
        for category in categories
    }

    def classify_trade(direction: str) -> str | None:
        if direction in {"分销买入", "分销卖出"}:
            return "一级"
        if direction in {"债券买入", "债券卖出"}:
            return "现券"
        if direction in {"融资回购", "融券回购"}:
            return "资金"
        if direction in {"买入", "卖出"}:
            return "权益"
        return None

    def classify_side(direction: str) -> str | None:
        # 融资回购=正回购(融入资金)→买入；融券回购=逆回购(融出资金)→卖出
        if direction in {"买入", "债券买入", "分销买入", "融资回购"}:
            return "买入"
        if direction in {"卖出", "债券卖出", "分销卖出", "融券回购"}:
            return "卖出"
        return None

    total_instruct_amount = 0.0  # 指令金额汇总（参考口径）
    for inst in instructions:
        direction = str(inst.get("委托方向", ""))
        status = inst.get("指令状态", "")

        # 过滤无效指令：已撤销且未成交
        if _is_invalid_instruction(inst):
            continue

        category = classify_trade(direction)
        side = classify_side(direction)
        if category is None or side is None:
            continue
        # 资金类(回购)仅统计银行间，对齐交易员手工口径
        if category == "资金" and str(inst.get("市场", "")) != "银行间":
            continue

        overview[category][f"{side}笔数"] += 1
        overview[category][f"{side}金额"] += float(inst.get("成交金额", 0) or 0)
        total_instruct_amount += float(inst.get("指令金额", 0) or 0)

    total_count = sum(v["买入笔数"] + v["卖出笔数"] for v in overview.values())
    total_deal_amount = sum(v["买入金额"] + v["卖出金额"] for v in overview.values())

    return {
        "分类明细": overview,
        "总笔数": total_count,
        "总指令金额": total_instruct_amount,
        "总成交金额": total_deal_amount,
    }


def aggregate_trade_count_by_hour(instructions: list[dict]) -> dict:
    """聚合当日交易笔数。

    0019 目前只能查单日，因此交易笔数先按当日方向分类展示，不生成历史序列。
    """
    categories = ["现券买入", "现券卖出", "正回购", "逆回购", "权益买入", "权益卖出", "分销买入", "分销卖出"]
    counts = {category: 0 for category in categories}
    total = 0

    for inst in instructions:
        if _is_invalid_instruction(inst):
            continue
        bucket = _trade_count_bucket(str(inst.get("委托方向", "")))
        if bucket:
            # 回购(正/逆)仅统计银行间，对齐交易员手工口径
            if bucket in {"正回购", "逆回购"} and str(inst.get("市场", "")) != "银行间":
                continue
            total += 1
            counts[bucket] += 1

    return {
        "total": total,
        "year_total": None,
        "categories": categories,
        "counts": counts,
    }


def _trade_count_bucket(direction: str) -> str | None:
    mapping = {
        "债券买入": "现券买入",
        "债券卖出": "现券卖出",
        "融资回购": "正回购",
        "融券回购": "逆回购",
        "买入": "权益买入",
        "卖出": "权益卖出",
        "分销买入": "分销买入",
        "分销卖出": "分销卖出",
    }
    return mapping.get(direction)


def aggregate_trade_amount_by_direction(instructions: list[dict]) -> dict:
    """聚合当日交易金额。

    与交易笔数使用同一组方向分类。金额单位在模板/图表中换算为亿元。
    """
    categories = ["现券买入", "现券卖出", "正回购", "逆回购", "权益买入", "权益卖出", "分销买入", "分销卖出"]
    amounts = {category: 0.0 for category in categories}
    total = 0.0

    for inst in instructions:
        if _is_invalid_instruction(inst):
            continue
        bucket = _trade_count_bucket(str(inst.get("委托方向", "")))
        if not bucket:
            continue
        # 回购(正/逆)仅统计银行间，对齐交易员手工口径
        if bucket in {"正回购", "逆回购"} and str(inst.get("市场", "")) != "银行间":
            continue
        amount = float(inst.get("成交金额", 0) or 0)
        amounts[bucket] += amount
        total += amount

    return {
        "total": total,
        "year_total": None,
        "categories": categories,
        "amounts": amounts,
    }


def aggregate_emergency_repo(rows: list[dict]) -> dict:
    """聚合应急回购明细，供 02 板块渲染。

    按指令下达时间升序排列，产品名称按规则脱敏展示。
    """
    if not rows:
        return {"has_data": False, "明细": [], "总笔数": 0, "总金额万元": 0.0}

    sorted_rows = sorted(
        rows, key=lambda r: _direct_time_hhmmss(r.get("repoInsDirectTimeText", ""))
    )

    items: list[dict] = []
    for row in sorted_rows:
        direct_time = _direct_time_hhmmss(row.get("repoInsDirectTimeText", ""))
        if direct_time:
            hour, minute = direct_time.split(":")[:2]
            reason = f"{int(hour)}点{int(minute):02d}分未到账"
        else:
            reason = "16点后未到账"

        items.append({
            "序号": len(items) + 1,
            "应急产品": mask_product_name(row.get("productName", "") or row.get("productCode", "") or ""),
            "应急金额万元": round(float(row.get("repurAmt", 0) or 0) / 10000, 2),
            "应收业务类型": f"{row.get('sideCodeText', '') or '正回购'}到期",
            "应收交易对手": row.get("rivalName", "") or "",
            "应急原因": reason,
        })

    return {
        "has_data": True,
        "明细": items,
        "总笔数": len(items),
        "总金额万元": round(sum(x["应急金额万元"] for x in items), 2),
    }


def aggregate_money_market(events: list[dict], query_date: str = "") -> dict:
    """聚合货币市场数据（资金事件日历 cat_sql_trade_0013）。

    事件类型：
    - 公开市场操作：央行 OMO（逆回购/MLF/买断式回购/国库定存等），含汇总行（OMO净投放）
    - 发行与到期：NCD/地方债/政金债等发行与到期明细
    - 政府债缴款：政府债券净缴款

    STAT_DT 格式为 ISO 字符串（如 "2026-06-21T16:00:00.000+0000"）。
    STAT_DT 是 UTC 时间，+8 小时才转成北京时间——因此 **UTC 日期部分 = 北京业务日期 − 1 天**。
    查北京 6/22 → 在缓存里匹配 UTC 日期 "2026-06-21"。
    """
    if not events:
        return {
            "omo_operations": [],
            "omo_summary_rows": [],
            "omo_net_inject": 0.0,
            "bond_maturities": [],
            "gov_bond_payment": 0.0,
            "has_data": False,
        }

    # query_date 是北京业务日期（YYYYMMDD）；0013 的 STAT_DT 是 UTC，UTC 日期 = 北京日期 − 1
    utc_date_key = _beijing_to_utc_date_key(query_date) if query_date else ""

    # 按 UTC 日期分类（缓存 STAT_DT 的日期部分是 UTC）
    by_date: dict[str, list[dict]] = {}
    for evt in events:
        dt_raw = evt.get("STAT_DT", "")
        if isinstance(dt_raw, str) and len(dt_raw) >= 10:
            date_key = dt_raw[:10]
            by_date.setdefault(date_key, []).append(evt)

    # 优先用 utc_date_key 命中北京当日数据
    day_events = by_date.get(utc_date_key)
    data_utc_date = utc_date_key
    if day_events is None:
        # fallback：取最新可用 UTC 日期
        sorted_dates = sorted(by_date.keys(), reverse=True)
        data_utc_date = sorted_dates[0] if sorted_dates else ""
        day_events = by_date.get(data_utc_date, [])

    # 显示日期用北京时间：把 UTC 日期 +1 天还原为北京日期
    display_date = _utc_date_key_to_beijing(data_utc_date) if data_utc_date else ""

    # 按事件类型分组
    omo_summary = []
    omo_by_project: dict[str, dict[str, Any]] = {}
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
                project = _normalize_omo_project(dim1, dim2)
                row = omo_by_project.setdefault(
                    project,
                    {"项目": project, "规模（亿元）": 0.0, "利率": "\\", "到期量（亿元）": 0.0},
                )
                rate = evt.get("RATE") or evt.get("INT_RATE") or evt.get("利率")
                if rate not in (None, "", "ALL"):
                    try:
                        rate_val = float(rate)
                        row["利率"] = f"{rate_val:.2f}%"
                    except (TypeError, ValueError):
                        row["利率"] = str(rate)
                if direction in ("投放", "发行", "缴款"):
                    row["规模（亿元）"] += val
                elif direction in ("回笼", "到期"):
                    row["到期量（亿元）"] += val
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

    omo_summary_rows = []
    derived_omo_net = 0.0
    for row in omo_by_project.values():
        net = row["规模（亿元）"] - row["到期量（亿元）"]
        derived_omo_net += net
        omo_summary_rows.append({
            "项目": row["项目"],
            "规模（亿元）": round(row["规模（亿元）"], 2),
            "利率": row["利率"],
            "到期量（亿元）": round(row["到期量（亿元）"], 2),
            "净投放（亿元）": round(net, 2),
        })
    if not omo_net and derived_omo_net:
        omo_net = derived_omo_net

    return {
        "data_date": display_date,
        "omo_operations": omo_summary,
        "omo_summary_rows": sorted(omo_summary_rows, key=lambda x: abs(x["净投放（亿元）"]), reverse=True),
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

    STAT_DT 是 UTC 时间，UTC 日期部分 = 北京业务日期 − 1 天（实测 2026-06-21T16:00:00+0000 = 北京 6/22 的发行数据）。
    """
    if not events:
        return {"available": False, "reason": "暂无一级市场发行数据"}

    # query_date 是北京业务日期（YYYYMMDD）；0013 的 STAT_DT 是 UTC，UTC 日期 = 北京日期 − 1
    utc_date_key = _beijing_to_utc_date_key(query_date) if query_date else ""

    # 按 UTC 日期筛选
    day_events: list[dict] = []
    for e in events:
        raw = e.get("STAT_DT", "")
        if isinstance(raw, str) and raw[:10] == utc_date_key:
            day_events.append(e)

    # 目标日期无数据时取最新 UTC 日期
    data_utc_date = utc_date_key
    if not day_events and events:
        dates = sorted(
            {str(e.get("STAT_DT", ""))[:10] for e in events if e.get("STAT_DT")},
            reverse=True,
        )
        if dates:
            data_utc_date = dates[0]
            day_events = [e for e in events if str(e.get("STAT_DT", ""))[:10] == data_utc_date]

    # 显示日期用北京时间：把 UTC 日期 +1 天还原为北京日期
    display_date = _utc_date_key_to_beijing(data_utc_date) if data_utc_date else ""

    # 次日 NCD 预发行：一级市场分析的"总募集量"用次日预发行数据（更具前瞻性）。
    # 北京日期 +1 天 → 跳过周末 → 转 UTC 日期 → 在 events 里找 NCD发行 汇总行。
    # 周五查的是周一（跳过周六日），缓存无数据时为 0.0。
    ncd_next_day_pre = 0.0
    if query_date:
        beijing_dt = datetime.strptime(query_date, "%Y%m%d")
        search_dt = beijing_dt + timedelta(days=1)
        while search_dt.weekday() >= 5:   # 5=六, 6=日
            search_dt += timedelta(days=1)
        search_utc_key = (search_dt - timedelta(days=1)).strftime("%Y-%m-%d")
        for e in events:
            raw = e.get("STAT_DT", "")
            if (isinstance(raw, str) and raw[:10] == search_utc_key
                    and e.get("DATA_TYP") == "汇总"
                    and e.get("EVNT_TYP_NM") == "发行与到期"):
                dim3 = str(e.get("DIM3_NM", ""))
                if dim3 == "NCD发行":
                    ncd_next_day_pre = float(e.get("INDX_VAL", 0) or 0)
                    break

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
        return {"available": False, "reason": "今日无一级市场发行数据",
                "ncd_next_day_pre": round(ncd_next_day_pre, 1)}

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

    # 按品种分组
    by_type: dict[str, dict] = {}
    for d in issuance_detail:
        t = d["品种"]
        if t not in by_type:
            by_type[t] = {"品种": t, "发行(亿)": 0.0, "明细": []}
        by_type[t]["发行(亿)"] += d["金额(亿)"]
        by_type[t]["明细"].append(d)

    # 明细按品种（国债→政金债→地方债→NCD）+ 期限长短排序
    _product_order = {"国债": 0, "政金债": 1, "地方债": 2, "NCD": 3}
    def _term_months(term: str) -> int:
        t = str(term).strip()
        if t.endswith("M"):
            return int(t[:-1])
        if t.endswith("Y"):
            return int(t[:-1]) * 12
        try:
            return int(t)
        except ValueError:
            return 9999
    issuance_detail = sorted(
        issuance_detail,
        key=lambda d: (_product_order.get(d["品种"], 99), _term_months(d["期限"])),
    )

    return {
        "available": True,
        "data_date": display_date,
        "totals": totals,
        "ncd_next_day_pre": round(ncd_next_day_pre, 1),
        "structure": sorted(by_type.values(), key=lambda x: x["发行(亿)"], reverse=True),
        "structure_detail": issuance_detail,
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


def _compact_sentence(text: str, max_len: int = 42) -> str:
    text = re.sub(r"\s+", "", text or "")
    if not text:
        return "—"
    return text if len(text) <= max_len else text[: max_len - 1] + "…"


def _split_commentary_sentences(text: str) -> list[str]:
    cleaned = _clean_commentary_body(text)
    parts = re.split(r"[。；;！!？?\n]+", cleaned)
    return [p.strip(" ：:，,、") for p in parts if p.strip(" ：:，,、")]


def _pick_sentence(sentences: list[str], keywords: tuple[str, ...]) -> str:
    for sentence in sentences:
        if re.search(r"(资金|存单).{0,8}(早评|午评|日评)", sentence):
            continue
        if ("央行" in sentence or "逆回购操作" in sentence) and not any(
            word in sentence for word in ("资金面", "隔夜", "质押", "成交")
        ):
            continue
        if any(word in sentence for word in keywords):
            return _compact_sentence(sentence)
    return "—"


_ALL_TERMS = ("隔夜", "O/N", "7天", "7D", "7d", "七天", "14天", "14D", "14d", "跨月")


def _rate_fragment(sentences: list[str], keywords: tuple[str, ...]) -> str:
    """利率列：选含关键词的句子，从关键词处截取，并在下一个其他期限词前截断。"""
    sentence = _pick_sentence(sentences, keywords)
    if sentence == "—":
        return sentence
    positions = [sentence.find(kw) for kw in keywords if kw in sentence]
    if positions:
        sentence = sentence[min(positions):]
    other_terms = [t for t in _ALL_TERMS if t not in keywords]
    cut = min((sentence.find(t) for t in other_terms if sentence.find(t) > 0), default=-1)
    if cut > 0:
        sentence = sentence[:cut].rstrip("，,。；; ")
    return _compact_sentence(sentence)


def _session_rank(report: dict) -> int:
    session = str(report.get("session", ""))
    title = str(report.get("title", ""))
    time_val = str(report.get("time", ""))
    content = str(report.get("content", ""))
    text = f"{session}{title}{content}"
    if "早评" in text or ("早" in title and "评" in title):
        return 0
    if "午评" in text or "午前" in text or "午间" in text:
        return 2
    if "日评" in text or "尾盘" in text or "收盘" in text:
        return 4
    if time_val:
        hour_match = re.search(r"(\d{1,2}):", time_val)
        if hour_match:
            hour = int(hour_match.group(1))
            if hour < 10:
                return 0
            if hour < 12:
                return 2
            if hour < 15:
                return 3
            return 4
    return 4


def _period_name(rank: int) -> str:
    return {
        0: "早盘（开盘）",
        1: "OMO操作后",
        2: "午前",
        3: "午后（初）",
        4: "尾盘",
    }.get(rank, "尾盘")


def _period_from_sentence(sentence: str) -> str | None:
    if "公开市场操作后" in sentence or "OMO操作后" in sentence or "OMO后" in sentence:
        return "OMO操作后"
    if "早盘" in sentence or "开盘" in sentence:
        return "早盘（开盘）"
    if "临近午盘" in sentence or "午前" in sentence or "午盘" in sentence:
        return "午前"
    if "午后" in sentence:
        return "午后（初）"
    if "尾盘" in sentence or "收盘" in sentence:
        return "尾盘"
    return None


def _market_status_from_text(text: str) -> str:
    if any(word in text for word in ("偏紧", "收紧", "转紧", "紧张", "融出减少", "融入困难")):
        return "偏紧"
    if any(word in text for word in ("偏松", "转松", "宽松", "融出充足")):
        return "偏松"
    if "收敛" in text:
        return "收敛"
    if any(word in text for word in ("均衡", "平稳", "稳定")):
        return "均衡"
    return "—"


def enrich_omo_rates_from_commentary(money_market: dict, daily_commentary: dict) -> dict:
    rows = money_market.get("omo_summary_rows") or []
    if not rows or all(row.get("利率") not in ("", "\\", "—") for row in rows):
        return money_market

    text = "\n".join(str(r.get("content", "")) for r in (daily_commentary or {}).get("reports", []))
    rate_match = re.search(r"(?:操作利率|中标利率)[为]?\s*([0-9]+(?:\.[0-9]+)?)%", text)
    if not rate_match:
        return money_market
    rate = f"{float(rate_match.group(1)):.2f}%"
    for row in rows:
        if row.get("利率") in ("", "\\", "—"):
            row["利率"] = rate
    return money_market


def _extract_sentiment_index(text: str) -> str:
    """从 QT 资金日评中提取情绪指数。

    格式：「今日全天的资金面情绪指数：52-54-52-52」
    未找到时返回空字符串。
    """
    if not text:
        return ""
    match = re.search(r"今日全天的资金面情绪指数[:：]\s*([\d\-—–]+)", text)
    if match:
        return match.group(1).strip()
    return ""


def build_funding_market_status(daily_commentary: dict, fallback_text: str = "") -> dict[str, Any]:
    """将 QT 资金短评整理成资金市场分析表。

    能识别早/午/尾盘时输出结构化表；否则保留原短评降级展示。
    新增：raw_text（QT 原文 dump，供 Claude 精炼）、sentiment_index（情绪指数，条件展示）。
    """
    reports = [
        r for r in (daily_commentary or {}).get("reports", [])
        if str(r.get("theme", "")) == "资金" and str(r.get("content", "")).strip()
    ]
    if not reports:
        return {"available": False, "writer": "自动", "fallback": fallback_text or "暂无有效消息"}

    period_buckets: dict[str, list[str]] = {
        "早盘（开盘）": [],
        "OMO操作后": [],
        "午前": [],
        "午后（初）": [],
        "尾盘": [],
    }
    for report in reports:
        active_period = None
        for sentence in _split_commentary_sentences(str(report.get("content", ""))):
            period = _period_from_sentence(sentence)
            if period:
                active_period = period
            else:
                period = active_period
            if not period:
                continue
            if not any(word in sentence for word in ("资金面", "隔夜", "7D", "7d", "7天", "14D", "14d", "14天", "跨月", "成交", "融出", "利率")):
                continue
            period_buckets[period].append(sentence)

    rows = []
    for period, sentences in period_buckets.items():
        if not sentences:
            continue
        joined = "。".join(sentences)
        row = {
            "时段": period,
            "隔夜": _rate_fragment(sentences, ("隔夜", "O/N", "ofr", "OFR", "押利率")),
            "7天": _rate_fragment(sentences, ("7天", "7D", "7d", "七天")),
            "14天跨月": _rate_fragment(sentences, ("14天", "14D", "14d", "跨月")),
            "市场状态": _market_status_from_text(joined),
        }
        meaningful = sum(1 for key in ("隔夜", "7天", "14天跨月", "市场状态") if row[key] != "—")
        if meaningful >= 2:
            rows.append(row)

    by_rank: dict[int, dict[str, Any]] = {}
    for report in reports:
        rank = _session_rank(report)
        current = by_rank.get(rank)
        if current is None or len(str(report.get("content", ""))) > len(str(current.get("content", ""))):
            by_rank[rank] = report

    all_text_parts = []
    existing_periods = {row["时段"] for row in rows}
    for rank in sorted(by_rank):
        content = str(by_rank[rank].get("content", ""))
        all_text_parts.append(content)
        if rows and _period_name(rank) in existing_periods:
            continue
        sentences = _split_commentary_sentences(content)
        row = {
            "时段": _period_name(rank),
            "隔夜": _rate_fragment(sentences, ("隔夜", "O/N", "ofr", "OFR", "押利率")),
            "7天": _rate_fragment(sentences, ("7天", "7D", "7d", "七天")),
            "14天跨月": _rate_fragment(sentences, ("14天", "14D", "14d", "跨月")),
            "市场状态": _market_status_from_text(content),
        }
        meaningful = sum(1 for key in ("隔夜", "7天", "14天跨月", "市场状态") if row[key] != "—")
        if meaningful >= 2:
            rows.append(row)

    period_order = {"早盘（开盘）": 0, "OMO操作后": 1, "午前": 2, "午后（初）": 3, "尾盘": 4}
    rows.sort(key=lambda row: period_order.get(row["时段"], 99))
    period_count = len({row["时段"] for row in rows})
    if period_count < 2:
        return {"available": False, "writer": "自动", "fallback": fallback_text or "暂无有效消息"}

    # 拼接全部 QT 原文作为 raw_text（供 Claude 精炼）
    all_text = "\n".join(str(report.get("content", "")) for report in reports) or "\n".join(all_text_parts)
    # 提取情绪指数（条件展示）
    sentiment_index = _extract_sentiment_index(all_text)

    return {
        "available": True,
        "writer": "自动",
        "overall": "",   # 留空，待 Claude 按 funding-commentary.md 精炼后填入
        "summary": "",   # 留空，待 Claude 按 funding-commentary.md 精炼后填入
        "rows": rows,
        "raw_text": _clean_commentary_body(all_text),  # 原文 dump（中间态，Claude 精炼后删除）
        "sentiment_index": sentiment_index,
        "fallback": fallback_text or "暂无有效消息",
    }


def _extract_primary_section(content: str) -> str:
    """从资金日评正文中提取【一级简评】小节。

    QT 无独立一级日评，一级存单评述嵌在资金日评的【一级简评】小节中。
    返回清洗后的小节正文（去 URL/空行），无匹配时返回空字符串。
    """
    if not content:
        return ""
    match = re.search(r"【一级简评】(.*?)(?=【|$)", content, re.DOTALL)
    if match:
        return _clean_commentary_body(match.group(1).strip())
    return ""


def generate_market_commentary(daily_commentary: dict) -> dict[str, str]:
    """基于日评代表篇生成资金/现券/一级市场分析文字。

    输入 fetch_daily_commentary 返回的结构（含 representative）。每主题整段
    引用代表篇原文（无损清洗）+ 来源标注；无日评时降级占位。一级无独立
    日评（见 findings），从资金日评的【一级简评】小节提取。
    不综合、不摘要、不枚举小节关键词。

    Returns:
        {"funding": str, "bond": str, "primary": str}
    """
    rep = (daily_commentary or {}).get("representative") or {}

    def _render(theme_report: dict | None) -> str:
        if not theme_report:
            return "暂无有效消息"
        body = _clean_commentary_body(str(theme_report.get("content", "")))
        return f"<!-- ⚠️ 中间态：以下为 QT 日评原文 dump，待 Claude 精炼 → 禁止直接交付 -->\n[待精炼]\n{body}"

    # 一级：从资金日评的【一级简评】小节提取
    # 代表篇不一定含【一级简评】（如午评无此小节），回退搜索所有资金类去重篇
    all_reports = (daily_commentary or {}).get("reports") or []
    funding_candidates = [r for r in all_reports if r.get("theme") == "资金"]

    primary_body = ""
    primary_source_report = None
    for candidate in funding_candidates:
        body = _extract_primary_section(str(candidate.get("content", "")))
        if body:
            primary_body = body
            primary_source_report = candidate
            break

    if primary_body and primary_source_report:
        primary = f"<!-- ⚠️ 中间态：以下为【一级简评】原文 dump，待 Claude 精炼 -->\n[待精炼]\n{primary_body}"
    else:
        primary = "暂无有效消息"

    return {
        "funding": _render(rep.get("资金")),
        "bond": _render(rep.get("现券")),
        "primary": primary,
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
    try:
        # 资金事件：查近 7 天
        begin = (datetime.strptime(date_str, "%Y%m%d") - timedelta(days=3)).strftime("%Y%m%d")
        end = (datetime.strptime(date_str, "%Y%m%d") + timedelta(days=3)).strftime("%Y%m%d")
        fund_events = collect_fund_events(begin, end)
    except Exception as e:
        print(f"[警告] 资金事件采集失败: {e}")

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
    trade_amount_by_direction = aggregate_trade_amount_by_direction(instructions)
    emergency_repo = aggregate_emergency_repo(emergency_rows)
    money_market = aggregate_money_market(fund_events, date_str)
    primary_market = aggregate_primary_market(fund_events, date_str)
    risk_warnings = aggregate_risk_warnings(instructions, positions)
    market_commentary = generate_market_commentary(qt_commentary)
    money_market = enrich_omo_rates_from_commentary(money_market, qt_commentary)
    funding_market_status = build_funding_market_status(qt_commentary, market_commentary.get("funding", ""))

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

        # 01 交易数据汇总：交易金额按当日方向分类展示
        "trade_amount_by_direction": trade_amount_by_direction,

        # 02 交收数据汇总
        "emergency_repo": emergency_repo,

        # 03 市场预测汇总（回购行情 + 预测方法）
        "repo_rates": forecast_repo_rates,
        "market_forecast": build_market_forecast(forecast_repo_rates, money_market, market_commentary, external_market, qt_commentary),

        # 04 资金市场分析
        "money_market": money_market,
        "funding_market_status": funding_market_status,

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
