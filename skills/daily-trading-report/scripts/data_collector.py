"""数据采集模块 — 从 AI Gateway API 采集并聚合交易数据。

采集流程：
  Phase 1（并行基础数据）：O32指令、头寸、交收进度、回购行情、交易日历
  Phase 2（补充数据）：对手信息、头寸预测、资金事件
"""

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Any

from api_client import call_sql_api, call_api, call_form_api


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


def build_forecast_accuracy_sections(trade_prices: dict) -> dict:
    """Build forecast accuracy sections without inventing history-based metrics."""
    placeholder = "历史预测数据不足，暂无法计算准确率"
    return {
        "trend_forecast": {
            "available": False,
            "data": {},
            "reason": placeholder,
        },
        "interval_forecast": {
            "available": False,
            "data": {},
            "reason": placeholder,
        },
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


def collect_trade_instructions(query_date: str) -> list[dict]:
    """采集 O32 交易指令数据（cat_sql_trade_0019）。

    返回原始指令列表。
    """
    result = call_sql_api("cat_sql_trade_0019", {"queryDate": int(query_date)})
    return result.get("body", [])


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


def collect_settlement_progress(query_date: str) -> list[dict]:
    """采集交收进度汇总数据（cat_api_trade_0021）。"""
    result = call_api("cat_api_trade_0021", {
        "page": 1,
        "size": 2000,
        "productIdList": [],
        "businDateStart": query_date,
        "businDateEnd": query_date,
        "businTypeList": [],
        "hideTgProductData": True,
        "hideInvalid": True,
        "showUnDeal": False,
        "hideSettleSuccess": False,
        "hideSettleByHandSuccess": False,
    })
    body = result.get("data", {}).get("body", {})
    return body.get("rows", [])


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


def aggregate_settlement_forecast(rows: list[dict]) -> dict:
    """聚合交收预测数据。"""
    status_map: dict[str, dict[str, Any]] = {}

    for row in rows:
        progress = row.get("settleProgressDesc", "未知")
        if progress not in status_map:
            status_map[progress] = {"笔数": 0, "金额": 0.0}

        status_map[progress]["笔数"] += 1
        status_map[progress]["金额"] += float(row.get("settleAmt", 0) or 0)

    total = sum(v["笔数"] for v in status_map.values())
    total_amt = sum(v["金额"] for v in status_map.values())

    return {
        "状态明细": status_map,
        "总笔数": total,
        "总金额": total_amt,
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


def aggregate_risk_warnings(
    instructions: list[dict],
    positions: list[dict],
    settlement_rows: list[dict],
) -> list[dict]:
    """风险预警规则引擎。

    规则：
    1. 头寸不足：总头寸可用 < 阈值
    2. 交收异常：存在交收失败/指令错误的记录
    3. 大额到期：单笔回购到期金额过大
    4. 指令质量：指令错误率偏高
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

    # 规则 2：检查交收异常
    error_states = {"交收失败", "指令错误", "等调款"}
    for row in settlement_rows:
        progress = row.get("settleProgressDesc", "")
        if progress in error_states or "失败" in progress or "错误" in progress:
            warnings.append({
                "风险类型": "交收异常",
                "产品": row.get("productName", "未知"),
                "详情": f"{row.get('tradeTypeDesc', '')} - {progress}",
                "等级": "中",
            })

    # 规则 3：指令质量
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


def generate_market_commentary(qt_commentary: dict) -> dict:
    """基于 QT 短评数据生成资金、现券和一级市场分析文字。

    从资金面/现券/一级发行三个分类的短评中提取关键信息，
    生成结构化的市场分析文字。

    Returns:
        {
            "funding": "资金面分析文字",
            "bond": "现券分析文字",
            "primary": "一级发行分析文字",
        }
    """
    if not qt_commentary or qt_commentary.get("total", 0) == 0:
        return {
            "funding": "暂无有效消息",
            "bond": "暂无有效消息",
            "primary": "暂无有效消息",
        }

    def _analyze_funding(messages: list[dict]) -> str:
        """资金面分析。"""
        if not messages:
            return "暂无有效消息"

        # 统计关键词
        kw_freq: dict[str, int] = {}
        sentiment_keywords = {"紧张": 0, "宽松": 0, "平稳": 0, "均衡": 0}
        rate_keywords = {"R001": 0, "R007": 0, "DR001": 0, "DR007": 0, "隔夜": 0, "7 天": 0, "14 天": 0}
        for msg in messages[:200]:
            content = str(msg.get("content", ""))
            for kw in ["回购", "资金", "头寸", "融出", "融入", "利率", "加权", "央行", "逆回购", "MLF", "OMO", "投放", "回笼"]:
                if kw in content:
                    kw_freq[kw] = kw_freq.get(kw, 0) + 1
            for sent_kw in sentiment_keywords:
                if sent_kw in content:
                    sentiment_keywords[sent_kw] += 1
            for rate_kw in rate_keywords:
                if rate_kw in content:
                    rate_keywords[rate_kw] += 1

        # 判断资金面情绪
        tight = sentiment_keywords["紧张"]
        loose = sentiment_keywords["宽松"]
        if tight > loose * 1.5:
            sentiment = "偏紧，交易员普遍反映资金难借"
        elif tight > loose:
            sentiment = "略偏紧，部分期限资金需求旺盛"
        elif loose > tight * 1.5:
            sentiment = "偏宽松，资金融出意愿较强"
        elif loose > tight:
            sentiment = "略偏宽松，资金面整体均衡"
        else:
            sentiment = "平稳均衡，供需基本匹配"

        top_kws = sorted(kw_freq.items(), key=lambda x: x[1], reverse=True)[:6]
        kw_str = "、".join(f"{kw}" for kw, _ in top_kws) if top_kws else "无高频关键词"

        # 利率期限关注
        rate_strs = [f"{k}({v}次)" for k, v in sorted(rate_keywords.items(), key=lambda x: x[1], reverse=True) if v > 0][:5]
        rate_focus = "、".join(rate_strs) if rate_strs else "无特定利率品种关注"

        # 选取代表性消息（早/中/晚各取 2 条，共 6 条）
        samples = []
        if len(messages) >= 6:
            step = len(messages) // 6
            samples = [messages[i * step] for i in range(6)]
        elif len(messages) >= 3:
            samples = [messages[0], messages[len(messages)//2], messages[-1]]
        else:
            samples = messages[:min(3, len(messages))]

        sample_strs = []
        for msg in samples:
            sender = msg.get("sender", "未知")
            time_val = msg.get("time", "")
            content = msg.get("content", "")[:120]
            sample_strs.append(f"{time_val} {sender}: {content}")

        return f"【资金面情绪】{sentiment}\n\n【关注焦点】{kw_str}\n\n【利率期限】{rate_focus}\n\n【代表性报价】（共 {len(messages)} 条短评）\n" + "\n".join(f"  • {s}" for s in sample_strs)

    def _analyze_bond(messages: list[dict]) -> str:
        """现券分析。"""
        if not messages:
            return "暂无有效消息"

        kw_freq: dict[str, int] = {}
        direction_keywords = {"买券": 0, "卖券": 0, "OFR": 0, "BID": 0}
        for msg in messages[:200]:
            content = str(msg.get("content", ""))
            for kw in ["现券", "债券", "收益率", "估值", "成交", "活跃券", "国债", "政金债", "信用债", "城投", "地产债", "BP", "YTM", "久期", "利差"]:
                if kw in content:
                    kw_freq[kw] = kw_freq.get(kw, 0) + 1
            for dir_kw in direction_keywords:
                if dir_kw in content.upper():
                    direction_keywords[dir_kw] += 1

        top_kws = sorted(kw_freq.items(), key=lambda x: x[1], reverse=True)[:6]
        kw_str = "、".join(f"{kw}" for kw, _ in top_kws) if top_kws else "无高频关键词"

        # 买卖方向
        buy = direction_keywords["买券"] + direction_keywords["BID"]
        sell = direction_keywords["卖券"] + direction_keywords["OFR"]
        if buy > sell * 1.5:
            direction = "买方力量较强，市场需求旺盛"
        elif sell > buy * 1.5:
            direction = "卖方力量较强，市场供给充足"
        else:
            direction = "买卖双方力量相对均衡"

        samples = []
        if len(messages) >= 6:
            step = len(messages) // 6
            samples = [messages[i * step] for i in range(6)]
        elif len(messages) >= 3:
            samples = [messages[0], messages[len(messages)//2], messages[-1]]
        else:
            samples = messages[:min(3, len(messages))]

        sample_strs = []
        for msg in samples:
            sender = msg.get("sender", "未知")
            time_val = msg.get("time", "")
            content = msg.get("content", "")[:120]
            sample_strs.append(f"{time_val} {sender}: {content}")

        return f"【市场情绪】{direction}\n\n【关注焦点】{kw_str}\n\n【代表性成交】（共 {len(messages)} 条短评）\n" + "\n".join(f"  • {s}" for s in sample_strs)

    def _analyze_primary(messages: list[dict]) -> str:
        """一级发行分析。"""
        if not messages:
            return "暂无有效消息"

        kw_freq: dict[str, int] = {}
        for msg in messages[:200]:
            content = str(msg.get("content", ""))
            for kw in ["一级", "发行", "投标", "新债", "招标", "结果", "边际", "倍率", "募", "全场倍", "边际倍"]:
                if kw in content:
                    kw_freq[kw] = kw_freq.get(kw, 0) + 1

        top_kws = sorted(kw_freq.items(), key=lambda x: x[1], reverse=True)[:6]
        kw_str = "、".join(f"{kw}" for kw, _ in top_kws) if top_kws else "无高频关键词"

        samples = []
        if len(messages) >= 6:
            step = len(messages) // 6
            samples = [messages[i * step] for i in range(6)]
        elif len(messages) >= 3:
            samples = [messages[0], messages[len(messages)//2], messages[-1]]
        else:
            samples = messages[:min(3, len(messages))]

        sample_strs = []
        for msg in samples:
            sender = msg.get("sender", "未知")
            time_val = msg.get("time", "")
            content = msg.get("content", "")[:120]
            sample_strs.append(f"{time_val} {sender}: {content}")

        return f"【关注焦点】{kw_str}\n\n【代表性信息】（共 {len(messages)} 条短评）\n" + "\n".join(f"  • {s}" for s in sample_strs)

    return {
        "funding": _analyze_funding(qt_commentary.get("资金面", {}).get("messages", [])),
        "bond": _analyze_bond(qt_commentary.get("现券", {}).get("messages", [])),
        "primary": _analyze_primary(qt_commentary.get("一级发行", {}).get("messages", [])),
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
            executor.submit(collect_settlement_progress, date_str): "settlement",
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
    settlement_rows = data.get("settlement", [])
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

    # Phase 3：QT 聊天短评（Oracle）
    qt_commentary: dict[str, Any] = {}
    try:
        from db_client import fetch_and_categorize
        qt_commentary = fetch_and_categorize(date_str)
        print(f"  QT短评采集完成：{qt_commentary.get('total', 0)} 条")
    except Exception as e:
        print(f"[警告] QT短评采集失败（非关键，继续）: {e}")
        qt_commentary = {"total": 0, "channels": {}, "资金面": {"count": 0, "messages": []},
                         "现券": {"count": 0, "messages": []}, "一级发行": {"count": 0, "messages": []},
                         "其他": {"count": 0, "messages": []}}

    # 数据聚合
    trade_overview = aggregate_trade_overview(instructions)
    trade_count_hourly = aggregate_trade_count_by_hour(instructions)
    trade_prices = aggregate_trade_prices(instructions)
    settlement_forecast = aggregate_settlement_forecast(settlement_rows)
    money_market = aggregate_money_market(fund_events, date_str)
    risk_warnings = aggregate_risk_warnings(instructions, positions, settlement_rows)
    market_commentary = generate_market_commentary(qt_commentary)

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
        "settlement_forecast": settlement_forecast,

        # 03 市场预测汇总（回购行情）
        "repo_rates": repo_rates,

        # 板块 6-7：趋势/区间预测准确率（没有历史预测数据时不使用当日价格替代）
        **build_forecast_accuracy_sections(trade_prices),

        # 04 资金市场分析
        "money_market": money_market,

        # 头寸附录数据，默认不进入主模板流
        "positions": positions,

        # 规则引擎风险附录数据，默认不进入主模板流
        "risk_warnings": risk_warnings,

        # 资金、现券、一级市场分析文字（基于 QT 短评）
        "market_commentary": market_commentary,

        # 板块 11：一级市场（无数据源）
        "primary_market": {
            "available": False,
            "reason": "暂无对应 API 数据源",
        },

        # 权益市场分析：由 AI 执行期外部短评输入，纯脚本运行时降级
        "equity_market": build_equity_market_analysis(),

        # 风险提示
        "risk_tips": build_risk_tips(risk_warnings),

        # QT 聊天消息分类（资金面/现券/一级发行）
        "qt_commentary": qt_commentary,

        # 原始数据（供图表生成使用）
        "_instructions": instructions,
        "_positions": positions,
        "_settlement_rows": settlement_rows,
        "_repo_rates": repo_rates,
        "_fund_events": fund_events,
    }
