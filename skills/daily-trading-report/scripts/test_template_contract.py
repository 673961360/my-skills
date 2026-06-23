#!/usr/bin/env python3
"""Contract tests for the daily trading report template."""

import sys
import unittest
from html.parser import HTMLParser
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from data_collector import (
    _fmt_template_date,
    _funding_condition,
    _is_invalid_instruction,
    build_funding_market_status,
    aggregate_trade_amount_by_direction,
    aggregate_trade_count_by_hour,
    aggregate_emergency_repo,
    aggregate_trade_overview,
    build_equity_market_analysis,
    build_market_forecast,
    build_risk_tips,
    generate_market_commentary,
)
from chart_builder import build_all_charts
from generate_report import render_report


class ReportTitleParser(HTMLParser):
    """Extract visible titles that define the report's main reading order."""

    TITLE_TAGS = {"h1", "h2", "h3", "h4"}
    TITLE_CLASSES = {"section-title", "template-subtitle"}

    def __init__(self):
        super().__init__()
        self._capture_depth = 0
        self._parts = []
        self.titles = []

    def handle_starttag(self, tag, attrs):
        class_names = set(dict(attrs).get("class", "").split())
        should_capture = tag in self.TITLE_TAGS or bool(class_names & self.TITLE_CLASSES)
        if should_capture:
            self._capture_depth += 1
            if self._capture_depth == 1:
                self._parts = []
        elif self._capture_depth:
            self._capture_depth += 1

    def handle_endtag(self, tag):
        if not self._capture_depth:
            return

        self._capture_depth -= 1
        if self._capture_depth == 0:
            text = " ".join("".join(self._parts).split())
            if text:
                self.titles.append(text)

    def handle_data(self, data):
        if self._capture_depth:
            self._parts.append(data)


def build_sample_data() -> dict:
    return {
        "display_date": "2026-06-17",
        "template_date": "2026年6月17日",
        "weekday": "周三",
        "generated_at": "2026-06-17 18:00:00",
        "is_trading_day": True,
        "trade_overview": {"总笔数": 0, "总指令金额": 0, "总成交金额": 0, "分类明细": {}},
        "trade_count_hourly": [],
        "trade_amount_by_direction": {},
        "emergency_repo": {"has_data": False, "明细": [], "总笔数": 0, "总金额万元": 0.0},
        "repo_rates": [],
        "market_forecast": {
            "available": False,
            "conclusion": "预测指标来源尚未确认",
            "rows": [],
            "indicators": [],
            "methodology": "资金利率、公开市场操作、债券收益率曲线和 QT 情绪等预测指标尚未完成来源确认，暂不生成方向性预测。",
            "sources": [],
            "reason": "当前预测指标数据源尚未完成映射，暂不生成方向性预测。",
        },
        "money_market": {"has_data": False},
        "funding_market_status": {"available": False, "writer": "自动", "overall": "", "summary": "", "fallback": "暂无有效消息"},
        "positions": [],
        "risk_warnings": [],
        "market_commentary": {
            "funding": "暂无有效消息",
            "bond": "暂无有效消息",
            "primary": "暂无有效消息",
        },
        "primary_market": {"available": False, "reason": "今日无一级市场发行数据"},
        "equity_indices": {"available": False, "indices": [], "source": ""},
        "equity_market": build_equity_market_analysis(),
        "risk_tips": build_risk_tips([]),
        "qt_commentary": {
            "total": 0,
            "total_raw": 0,
            "reports": [],
            "representative": {"资金": None, "现券": None},
        },
    }


def render_sample_report() -> str:
    return render_report(build_sample_data(), charts={})


def render_trade_sample_report() -> str:
    data = build_sample_data()
    data["trade_overview"] = {
        "总笔数": 10,
        "总指令金额": 20_000_000,
        "总成交金额": 15_000_000,
        "分类明细": {
            "现券": {"买入金额": 8_000_000, "卖出金额": 5_000_000, "买入笔数": 4, "卖出笔数": 2},
            "资金": {"买入金额": 7_000_000, "卖出金额": 0, "买入笔数": 3, "卖出笔数": 0},
            "权益": {"买入金额": 3_000_000, "卖出金额": 2_000_000, "买入笔数": 2, "卖出笔数": 1},
            "一级": {"买入金额": 2_000_000, "卖出金额": 0, "买入笔数": 1, "卖出笔数": 0},
        },
    }
    data["trade_amount_by_direction"] = {
        "total": 20_000_000,
        "year_total": None,
        "categories": ["现券买入", "现券卖出", "正回购", "逆回购", "权益买入", "权益卖出", "分销买入", "分销卖出"],
        "amounts": {"现券买入": 8_000_000, "现券卖出": 5_000_000, "正回购": 7_000_000, "逆回购": 0, "权益买入": 0, "权益卖出": 0, "分销买入": 0, "分销卖出": 0},
    }
    return render_report(data, charts={})


def render_trade_no_chart_hourly_report() -> str:
    data = build_sample_data()
    data["trade_overview"] = {
        "总笔数": 10,
        "总指令金额": 20_000_000,
        "总成交金额": 15_000_000,
        "分类明细": {
            "现券": {"买入金额": 8_000_000, "卖出金额": 5_000_000, "买入笔数": 4, "卖出笔数": 2},
            "资金": {"买入金额": 7_000_000, "卖出金额": 0, "买入笔数": 3, "卖出笔数": 0},
            "权益": {"买入金额": 3_000_000, "卖出金额": 2_000_000, "买入笔数": 2, "卖出笔数": 1},
            "一级": {"买入金额": 2_000_000, "卖出金额": 0, "买入笔数": 1, "卖出笔数": 0},
        },
    }
    data["trade_count_hourly"] = {
        "total": 10,
        "year_total": None,
        "categories": ["现券买入", "现券卖出", "正回购", "逆回购", "权益买入", "权益卖出", "分销买入", "分销卖出"],
        "counts": {"现券买入": 4, "现券卖出": 2, "正回购": 3, "逆回购": 0, "权益买入": 1, "权益卖出": 0, "分销买入": 0, "分销卖出": 0},
    }
    data["trade_amount_by_direction"] = {
        "total": 20_000_000,
        "year_total": None,
        "categories": ["现券买入", "现券卖出", "正回购", "逆回购", "权益买入", "权益卖出", "分销买入", "分销卖出"],
        "amounts": {"现券买入": 8_000_000, "现券卖出": 5_000_000, "正回购": 7_000_000, "逆回购": 0, "权益买入": 0, "权益卖出": 0, "分销买入": 0, "分销卖出": 0},
    }
    return render_report(data, charts={})


def render_trade_chart_sample_report() -> str:
    data = build_sample_data()
    data["trade_overview"] = {
        "总笔数": 10,
        "总指令金额": 20_000_000,
        "总成交金额": 15_000_000,
        "分类明细": {
            "现券": {"买入金额": 8_000_000, "卖出金额": 5_000_000, "买入笔数": 4, "卖出笔数": 2},
            "资金": {"买入金额": 7_000_000, "卖出金额": 0, "买入笔数": 3, "卖出笔数": 0},
            "权益": {"买入金额": 3_000_000, "卖出金额": 2_000_000, "买入笔数": 2, "卖出笔数": 1},
            "一级": {"买入金额": 2_000_000, "卖出金额": 0, "买入笔数": 1, "卖出笔数": 0},
        },
    }
    data["trade_count_hourly"] = {
        "total": 10,
        "year_total": None,
        "categories": ["现券买入", "现券卖出", "正回购", "逆回购", "权益买入", "权益卖出", "分销买入", "分销卖出"],
        "counts": {"现券买入": 4, "现券卖出": 2, "正回购": 3, "逆回购": 0, "权益买入": 1, "权益卖出": 0, "分销买入": 0, "分销卖出": 0},
    }
    data["trade_amount_by_direction"] = {
        "total": 20_000_000,
        "year_total": None,
        "categories": ["现券买入", "现券卖出", "正回购", "逆回购", "权益买入", "权益卖出", "分销买入", "分销卖出"],
        "amounts": {"现券买入": 8_000_000, "现券卖出": 5_000_000, "正回购": 7_000_000, "逆回购": 0, "权益买入": 0, "权益卖出": 0, "分销买入": 0, "分销卖出": 0},
    }
    charts = {
        "trade_overview": "OVERVIEW_CHART_SHOULD_NOT_RENDER",
        "trade_count": "COUNT_CHART",
        "trade_price": "PRICE_CHART",
    }
    return render_report(data, charts=charts)


def render_settlement_sample_report() -> str:
    data = build_sample_data()
    data["emergency_repo"] = {
        "has_data": True,
        "明细": [
            {"序号": 1, "应急产品": "**鼎泰135号(*)", "应急金额万元": 2000.0,
             "应收业务类型": "正回购到期", "应收交易对手": "上清所",
             "应急原因": "16点15分未到账"},
            {"序号": 2, "应急产品": "**创盈6号（*）", "应急金额万元": 3000.0,
             "应收业务类型": "正回购到期", "应收交易对手": "中债登",
             "应急原因": "16点42分未到账"},
        ],
        "总笔数": 2,
        "总金额万元": 5000.0,
    }
    charts = {"settlement": "SETTLEMENT_CHART_SHOULD_NOT_RENDER"}
    return render_report(data, charts=charts)


def render_forecast_sample_report() -> str:
    data = build_sample_data()
    data["repo_rates"] = [
        {
            "SECURITY_NAME": "R001",
            "LAST_PRICE": "1.75",
            "HIGH_PRICE": "1.90",
            "LOW_PRICE": "1.60",
            "VOLUME": "1200",
        },
        {
            "SECURITY_NAME": "R007",
            "LAST_PRICE": "1.88",
            "HIGH_PRICE": "2.05",
            "LOW_PRICE": "1.72",
            "VOLUME": "800",
        },
    ]
    data["market_forecast"] = build_market_forecast(data["repo_rates"], {}, data["market_commentary"])
    charts = {"repo_rate": "REPO_RATE_CHART"}
    return render_report(data, charts=charts)


def render_primary_market_sample_report() -> str:
    data = build_sample_data()
    data["market_commentary"]["primary"] = "【关注焦点】发行、投标\n\n【代表性信息】样例摘要"
    data["qt_commentary"]["total"] = 2
    data["qt_commentary"]["一级发行"] = {
        "count": 2,
        "messages": [
            {"sender": "交易员A", "time": "09:30", "content": "一级发行样例消息一"},
            {"sender": "交易员B", "time": "10:15", "content": "一级发行样例消息二"},
        ],
    }
    return render_report(data, charts={})


def render_primary_market_available_report() -> str:
    data = build_sample_data()
    data["primary_market"] = {
        "available": True,
        "data_date": "2026-06-22",
        "ncd_next_day_pre": 2082.5,
        "totals": {"利率债": 260, "地方债": 235, "NCD": 0},
        "structure_detail": [
            {"品种": "国债", "期限": "10Y", "金额(亿)": 90.00},
            {"品种": "政金债", "期限": "5Y", "金额(亿)": 70.00},
            {"品种": "地方债", "期限": "30Y", "金额(亿)": 50.50},
        ],
    }
    return render_report(data, charts={})


def render_equity_market_sample_report() -> str:
    data = build_sample_data()
    data["equity_indices"] = {
        "available": True,
        "source": "新浪财经",
        "indices": [
            {"name": "上证指数", "latest": "4163.10", "pct_change": "1.78"},
            {"name": "深证成指", "latest": "16372.50", "pct_change": "2.13"},
            {"name": "创业板指", "latest": "4359.39", "pct_change": "2.52"},
            {"name": "科创50", "latest": "1948.93", "pct_change": "1.96"},
        ],
    }
    data["equity_market"] = build_equity_market_analysis("A股市场收盘后外部短评样例。")
    return render_report(data, charts={})


def render_bond_market_sample_report() -> str:
    data = build_sample_data()
    data["market_commentary"]["bond"] = "现券样例短评：长端收益率小幅下行，成交集中在活跃券。"
    return render_report(data, charts={})


def render_non_trading_sample_report() -> str:
    data = build_sample_data()
    data["is_trading_day"] = False
    return render_report(data, charts={})


def render_money_market_detail_missing_report() -> str:
    data = build_sample_data()
    data["money_market"] = {
        "has_data": True,
        "data_date": "2026-06-17",
        "omo_net_inject": 0,
        "gov_bond_payment": 0,
        "omo_operations": [],
        "bond_maturities": [],
    }
    return render_report(data, charts={})


def render_money_market_sample_report() -> str:
    data = build_sample_data()
    data["money_market"] = {
        "has_data": True,
        "data_date": "2026-06-17",
        "omo_net_inject": 120.0,
        "gov_bond_payment": -35.0,
        "omo_summary_rows": [
            {"项目": "7天逆回购", "规模（亿元）": 500.0, "利率": "1.40%", "到期量（亿元）": 380.0, "净投放（亿元）": 120.0},
        ],
        "omo_operations": [
            {"操作": "7天逆回购", "期限": "7D", "方向": "投放", "金额(亿)": 500.0},
            {"操作": "逆回购到期", "期限": "7D", "方向": "回笼", "金额(亿)": 380.0},
        ],
        "bond_maturities": [
            {"品种": "国债", "到期(亿)": 80.0, "发行(亿)": 120.0},
            {"品种": "地方债", "到期(亿)": 160.0, "发行(亿)": 90.0},
        ],
    }
    data["market_commentary"]["funding"] = "资金面样例短评：隔夜供给平稳，跨月资金价格保持关注。"
    data["funding_market_status"] = {
        "available": True,
        "writer": "自动",
        "overall": "",  # 留空待 Claude 生成
        "summary": "",  # 留空待 Claude 生成
        "rows": [
            {"时段": "早盘（开盘）", "隔夜": "非银ofr 1.50%-1.51%", "7天": "押利率/存单 1.47%-1.48%", "14天跨月": "1.50%-1.52%", "市场状态": "银行收敛"},
            {"时段": "午前", "隔夜": "押利率 1.46%-1.48%", "7天": "7d押存单成交 ~1.46%", "14天跨月": "成交寥寥", "市场状态": "均衡"},
            {"时段": "尾盘", "隔夜": "最低押利率 1.45% / 存单 1.46%", "7天": "—", "14天跨月": "—", "市场状态": "均衡收盘"},
        ],
        "raw_text": "资金面样例短评：隔夜供给平稳，跨月资金价格保持关注。",
        "sentiment_index": "",
        "fallback": "资金面样例短评：隔夜供给平稳，跨月资金价格保持关注。",
    }
    return render_report(data, charts={})


def render_risk_tips_sample_report() -> str:
    data = build_sample_data()
    warnings = [
        {"风险类型": "集中度", "产品": "产品A", "详情": "交易对手集中度偏高", "等级": "高"},
        {"风险类型": "流动性", "产品": "产品B", "详情": "明日到期资金较集中", "等级": "中"},
    ]
    data["risk_warnings"] = warnings
    data["risk_tips"] = build_risk_tips(warnings)
    return render_report(data, charts={})


class TemplateContractTest(unittest.TestCase):
    def test_visible_titles_follow_template_contract_order(self):
        html = render_sample_report()
        parser = ReportTitleParser()
        parser.feed(html)

        expected_titles = [
            "创金合信基金交易部",
            "交易日报",
            "01 交易数据汇总",
            "交易数据汇总",
            "交易笔数",
            "交易金额",
            "02 交收数据汇总",
            "03 市场预测汇总",
            "预测结论",
            "04 资金市场分析",
            "现券市场分析",
            "权益市场分析",
            "一级市场分析",
            "风险提示",
        ]

        self.assertEqual(expected_titles, parser.titles[: len(expected_titles)])
        second_section_title = html.index('<span class="icon">02</span> 交收数据汇总')
        segment_end = html.rfind('<div class="section">', 0, second_section_title)
        self.assertEqual(1, html[:segment_end].count('<div class="section">'))
        forbidden_main_titles = {
            "交易额度总览",
            "交易笔数分布",
            "交易价格汇总",
            "交收预测汇总",
            "货币市场情况",
            "市场综合分析",
            "账户头寸情况",
            "风险预警分析",
            "一级市场情况",
        }
        self.assertFalse(forbidden_main_titles & set(parser.titles))

    def test_market_forecast_requires_indicators_and_methodology(self):
        forecast = build_market_forecast([], {}, {})

        self.assertFalse(forecast["available"])
        self.assertEqual("预测指标来源尚未确认", forecast["conclusion"])
        self.assertEqual(6, len(forecast["rows"]))
        self.assertEqual("暂无有效消息", forecast["rows"][0]["current"])
        self.assertEqual([], forecast["indicators"])
        self.assertIn("资金利率", forecast["methodology"])
        self.assertIn("债券收益率曲线", forecast["methodology"])

    def test_market_forecast_builds_explainable_prediction_from_repo_rates(self):
        forecast = build_market_forecast(
            [
                {"SECURITY_NAME": "R001", "LAST_PRICE": "2.05", "HIGH_PRICE": "2.25", "LOW_PRICE": "1.85"},
                {"SECURITY_NAME": "R007", "LAST_PRICE": "2.30", "HIGH_PRICE": "2.45", "LOW_PRICE": "2.10"},
            ],
            {"has_data": True, "omo_net_inject": -200, "gov_bond_payment": 300},
            {"funding": "资金面偏紧，融入需求较多。", "bond": "现券收益率上行，OFR 增多。"},
            {
                "treasury_curve": {
                    "available": True,
                    "points": [{"term": "10", "yield": "1.7275"}],
                },
                "equity_indices": {
                    "available": True,
                    "indices": [
                        {"name": "上证指数", "latest": "4108", "pct_change": "0.2"},
                        {"name": "创业板指", "latest": "4167", "pct_change": "0.5"},
                    ],
                },
            },
        )

        self.assertTrue(forecast["available"])
        self.assertEqual("市场预测汇总表", forecast["conclusion"])
        self.assertIn("资金面当日行情", forecast["methodology"])
        self.assertEqual(6, len(forecast["rows"]))
        self.assertEqual("资金", forecast["rows"][0]["asset_type"])
        self.assertEqual("不松", forecast["rows"][0]["current"])
        self.assertEqual("现券", forecast["rows"][1]["asset_type"])
        self.assertEqual("1.7275", forecast["rows"][1]["current"])
        self.assertEqual("上证指数", forecast["rows"][2]["indicator"])
        self.assertGreaterEqual(len(forecast["indicators"]), 5)
        self.assertIn("O32 回购行情 cat_sql_trade_0012", forecast["sources"])

    def test_header_uses_reference_date_format(self):
        html = render_sample_report()

        self.assertIn("2026年6月17日（周三）", html)
        self.assertEqual("2026年6月17日", _fmt_template_date("20260617"))

    def test_template_has_narrow_timeline_skeleton(self):
        template = (SCRIPT_DIR / "report_template.html").read_text(encoding="utf-8")

        self.assertIn("max-width: 680px", template)
        self.assertIn(".report-container::before", template)
        self.assertIn(".section::before", template)
        self.assertIn("body::before", template)
        self.assertIn("linear-gradient(115deg", template)
        self.assertIn("linear-gradient(70deg", template)
        self.assertNotIn("radial-gradient", template)

    def test_commentary_and_risk_tips_use_contract_fallbacks(self):
        commentary = generate_market_commentary({})
        tips = build_risk_tips([])
        html = render_sample_report()
        template = (SCRIPT_DIR / "report_template.html").read_text(encoding="utf-8")

        self.assertEqual("暂无有效消息", commentary["funding"])
        self.assertEqual("暂无有效消息", commentary["bond"])
        self.assertEqual("暂无有效消息", commentary["primary"])
        self.assertEqual(3, len(tips))
        self.assertIn('<ol class="risk-list">', html)
        self.assertIn('<span class="risk-index">1.</span>', html)
        self.assertNotIn("| safe", template)

    def test_funding_commentary_quotes_daily_report(self):
        commentary = generate_market_commentary({
            "representative": {
                "资金": {
                    "content": "6.18资金日评 今日资金面整体呈均衡态势。早盘资金充裕，隔夜成交在加权-1.46%区间。",
                    "sender": "吕浩轩",
                    "time": "17:00:00",
                    "session": "日评",
                    "title": "6.18资金日评",
                    "theme": "资金",
                },
                "现券": None,
            },
        })

        funding = commentary["funding"]
        # 整段引用日评原文（含情绪与数据，非机器拼接）
        self.assertIn("资金面整体呈均衡态势", funding)
        self.assertIn("隔夜成交在加权-1.46%区间", funding)
        # 不再附加机器来源标注（中间态标记，精炼前应丢弃）
        self.assertNotIn("（来源：", funding)
        # 无机器过程描述（contract 禁止）
        self.assertNotIn("【资金面研判】", funding)
        self.assertNotIn("共 ", funding)
        self.assertNotIn("无高频关键词", funding)
        # bond 无日评降级；一级固定降级
        self.assertEqual("暂无有效消息", commentary["bond"])
        self.assertEqual("暂无有效消息", commentary["primary"])

    def test_commentary_strips_url_noise_preserving_text(self):
        commentary = generate_market_commentary({
            "representative": {
                "资金": {
                    "content": "资金面均衡偏松。\n发行汇总：http://test.idbhost.com/x\n隔夜1.46%。",
                    "sender": "测试机构",
                    "time": "17:00:00",
                    "session": "日评",
                },
                "现券": None,
            },
        })
        funding = commentary["funding"]
        self.assertIn("资金面均衡偏松", funding)
        self.assertIn("隔夜1.46%", funding)
        self.assertNotIn("http://", funding)

    def test_funding_market_status_extracts_intraday_table_from_qt_reports(self):
        status = build_funding_market_status(
            {
                "reports": [
                    {
                        "theme": "资金",
                        "session": "早评",
                        "title": "资金早评",
                        "time": "09:20:00",
                        "content": "资金面早盘均衡。隔夜ofr 1.50%-1.51%，7天押利率1.47%-1.48%，14天跨月1.50%-1.52%。",
                    },
                    {
                        "theme": "资金",
                        "session": "午评",
                        "title": "资金午评",
                        "time": "11:40:00",
                        "content": "午前资金面平稳。隔夜押利率1.46%-1.48%，7d押存单成交约1.46%，14天成交寥寥。",
                    },
                    {
                        "theme": "资金",
                        "session": "日评",
                        "title": "资金日评",
                        "time": "16:50:00",
                        "content": "全天资金面整体均衡。尾盘隔夜最低押利率1.45%，存单1.46%，利率走势稳定。",
                    },
                ]
            },
            "原始短评",
        )

        self.assertTrue(status["available"])
        self.assertEqual("自动", status["writer"])
        self.assertEqual(["早盘（开盘）", "午前", "尾盘"], [row["时段"] for row in status["rows"]])
        self.assertIn("隔夜ofr", status["rows"][0]["隔夜"])
        self.assertIn("7天押利率", status["rows"][0]["7天"])
        self.assertIn("14天跨月", status["rows"][0]["14天跨月"])
        self.assertEqual("", status["overall"])  # 留空待 Claude 生成
        self.assertEqual("", status["summary"])  # 留空待 Claude 生成

    def test_visible_missing_data_uses_contract_fallback_texts(self):
        html = render_sample_report()
        money_detail_html = render_money_market_detail_missing_report()
        combined = html + money_detail_html
        forbidden_texts = [
            "当日无交易指令数据",
            "当日无交易笔数数据",
            "当日无交收数据",
            "测试环境历史日期",
            "暂无银行间回购实时行情数据",
            "该板块需积累历史时序数据后方可启用",
            "当日无公开市场操作明细",
            "当日无债券到期数据",
            "暂无头寸数据",
            "需接入 ChinaBond/Wind 或当日无相关 QT 短评",
        ]

        for text in forbidden_texts:
            self.assertNotIn(text, combined)

        self.assertIn("暂无成交", html)
        self.assertIn("暂无相关数据", html)
        self.assertIn("预测指标来源尚未确认", html)
        self.assertNotIn("历史预测数据不足，暂无法计算准确率", html)

    def test_visible_report_avoids_internal_implementation_notes(self):
        combined = (
            render_sample_report()
            + render_primary_market_sample_report()
            + render_equity_market_sample_report()
            + render_non_trading_sample_report()
        )
        forbidden_texts = [
            "AI 执行期",
            "AI Gateway 测试环境",
            "需接入",
            "可能为非交易日",
            "如有疑问请联系 IT 支持",
            "自动生成",
            "生成时间：",
            "O32 指令数据 / QT 市场短评 / 授权外部短评",
            "待接入",
        ]

        for text in forbidden_texts:
            self.assertNotIn(text, combined)

        self.assertIn("今日休市，无交易数据", combined)
        self.assertIn("数据来源：外部市场短评", combined)

    def test_template_source_has_no_disabled_appendix_sections(self):
        template = (SCRIPT_DIR / "report_template.html").read_text(encoding="utf-8")
        forbidden_fragments = [
            "{% if false",
            "附录",
            "qt-tab",
            "qt-panel",
            "qt-msg",
            "risk-tag",
            "头寸数据",
            "规则引擎风险",
        ]

        for fragment in forbidden_fragments:
            self.assertNotIn(fragment, template)

    def test_template_and_chart_labels_use_contract_names(self):
        template = (SCRIPT_DIR / "report_template.html").read_text(encoding="utf-8")
        chart_builder = (SCRIPT_DIR / "chart_builder.py").read_text(encoding="utf-8")
        combined = template + chart_builder
        forbidden_fragments = [
            "交易额度",
            "交易笔数分布",
            "交收预测",
            "货币市场情况",
            "账户头寸",
            "风险预警",
            "一级市场情况",
        ]

        for fragment in forbidden_fragments:
            self.assertNotIn(fragment, combined)

        self.assertNotIn("交易数据汇总图", template)
        self.assertIn("交易金额图", template)
        self.assertNotIn("交易数据汇总（按业务分类·委托方向）", chart_builder)
        self.assertNotIn("交收进度分布图", template)

    def test_trade_section_uses_split_compact_tables(self):
        html = render_trade_sample_report()
        template = (SCRIPT_DIR / "report_template.html").read_text(encoding="utf-8")

        self.assertIn('<table class="trade-summary-table">', html)
        self.assertIn("<th rowspan=\"2\">业务类型</th>", html)
        self.assertIn("<th colspan=\"2\">金额（亿元）</th>", html)
        self.assertIn("<td>现券</td>", html)
        self.assertIn("<td>资金</td>", html)
        self.assertIn("<td>权益</td>", html)
        self.assertIn("<td>一级</td>", html)
        self.assertIn("笔数占比", html)
        self.assertIn("金额占比", html)
        self.assertIn('<table class="amount-table">', html)
        self.assertNotIn('src="data:image/png;base64,"', html)
        self.assertIn("font-size: 11px", template)
        self.assertIn("padding: 5px 7px", template)

    def test_trade_summary_block_contains_category_amount_rows_before_count_chart(self):
        html = render_trade_chart_sample_report()

        summary_pos = html.index('<div class="template-subtitle">交易数据汇总</div>')
        count_pos = html.index('<div class="template-subtitle">交易笔数</div>')
        summary_html = html[summary_pos:count_pos]

        self.assertIn('<table class="trade-summary-table">', summary_html)
        self.assertIn("<th rowspan=\"2\">业务类型</th>", summary_html)
        self.assertIn("<th colspan=\"2\">金额（亿元）</th>", summary_html)
        self.assertIn("<th colspan=\"2\">笔数</th>", summary_html)
        self.assertIn("<th>买入</th>", summary_html)
        self.assertIn("<th>卖出</th>", summary_html)
        for category in ["现券", "资金", "权益", "一级"]:
            self.assertIn(f"<td>{category}</td>", summary_html)
        self.assertNotIn("银行间业务", summary_html)
        self.assertNotIn("交易所业务", summary_html)

    def test_trade_amount_chart_uses_amount_overview_not_repo_rate_prices(self):
        data = build_sample_data()
        data["trade_amount_by_direction"] = {
            "total": 20_000_000,
            "year_total": None,
            "categories": ["现券买入", "现券卖出", "正回购", "逆回购", "权益买入", "权益卖出", "分销买入", "分销卖出"],
            "amounts": {"现券买入": 8_000_000, "现券卖出": 5_000_000, "正回购": 7_000_000, "逆回购": 0, "权益买入": 0, "权益卖出": 0, "分销买入": 0, "分销卖出": 0},
        }
        data["trade_count_hourly"] = {}

        charts = build_all_charts(data)

        self.assertEqual("", charts["trade_count"])
        self.assertTrue(charts["trade_price"])

    def test_trade_amount_uses_current_day_direction_categories(self):
        amount_data = aggregate_trade_amount_by_direction([
            {"委托方向": "债券买入", "指令金额": 100_000_000, "成交金额": 100_000_000, "指令状态": "有效指令"},
            {"委托方向": "债券卖出", "指令金额": 200_000_000, "成交金额": 200_000_000, "指令状态": "有效指令"},
            {"委托方向": "融资回购", "指令金额": 300_000_000, "成交金额": 300_000_000, "指令状态": "有效指令", "市场": "银行间"},
            {"委托方向": "融券回购", "指令金额": 400_000_000, "成交金额": 400_000_000, "指令状态": "有效指令", "市场": "银行间"},
            {"委托方向": "买入", "指令金额": 500_000_000, "成交金额": 500_000_000, "指令状态": "有效指令"},
            {"委托方向": "卖出", "指令金额": 600_000_000, "成交金额": 600_000_000, "指令状态": "有效指令"},
            {"委托方向": "分销买入", "指令金额": 700_000_000, "成交金额": 700_000_000, "指令状态": "有效指令"},
            {"委托方向": "分销卖出", "指令金额": 800_000_000, "成交金额": 800_000_000, "指令状态": "有效指令"},
            {"委托方向": "混合", "指令金额": 900_000_000, "成交金额": 900_000_000, "指令状态": "有效指令"},
            {"委托方向": "买入", "指令金额": 900_000_000, "指令状态": "已撤销", "成交状态": "未成交"},
        ])

        self.assertIsNone(amount_data["year_total"])
        self.assertEqual(3_600_000_000, amount_data["total"])
        self.assertEqual(100_000_000, amount_data["amounts"]["现券买入"])
        self.assertEqual(200_000_000, amount_data["amounts"]["现券卖出"])
        self.assertEqual(300_000_000, amount_data["amounts"]["正回购"])
        self.assertEqual(400_000_000, amount_data["amounts"]["逆回购"])
        self.assertEqual(500_000_000, amount_data["amounts"]["权益买入"])
        self.assertEqual(600_000_000, amount_data["amounts"]["权益卖出"])
        self.assertEqual(700_000_000, amount_data["amounts"]["分销买入"])
        self.assertEqual(800_000_000, amount_data["amounts"]["分销卖出"])

    def test_trade_overview_uses_four_fixed_business_types(self):
        overview = aggregate_trade_overview([
            {"委托方向": "债券买入", "指令金额": 100_000_000, "成交金额": 100_000_000, "指令状态": "有效指令"},
            {"委托方向": "债券卖出", "指令金额": 200_000_000, "成交金额": 200_000_000, "指令状态": "有效指令"},
            {"委托方向": "融券回购", "指令金额": 300_000_000, "成交金额": 300_000_000, "指令状态": "有效指令", "市场": "银行间"},
            {"委托方向": "融资回购", "指令金额": 400_000_000, "成交金额": 400_000_000, "指令状态": "有效指令", "市场": "银行间"},
            {"委托方向": "买入", "指令金额": 500_000_000, "成交金额": 500_000_000, "指令状态": "有效指令"},
            {"委托方向": "卖出", "指令金额": 600_000_000, "成交金额": 600_000_000, "指令状态": "有效指令"},
            {"委托方向": "分销买入", "指令金额": 700_000_000, "成交金额": 700_000_000, "指令状态": "有效指令"},
            {"委托方向": "分销卖出", "指令金额": 800_000_000, "成交金额": 800_000_000, "指令状态": "有效指令"},
            {"委托方向": "正回购", "指令金额": 900_000_000, "成交金额": 900_000_000, "指令状态": "有效指令"},  # 无效委托方向，被跳过
            {"委托方向": "债券买入", "指令金额": 900_000_000, "指令状态": "已撤销", "成交状态": "未成交"},
        ])

        self.assertEqual(["现券", "资金", "权益", "一级"], list(overview["分类明细"].keys()))
        self.assertEqual(100_000_000, overview["分类明细"]["现券"]["买入金额"])
        self.assertEqual(200_000_000, overview["分类明细"]["现券"]["卖出金额"])
        self.assertEqual(400_000_000, overview["分类明细"]["资金"]["买入金额"])
        self.assertEqual(300_000_000, overview["分类明细"]["资金"]["卖出金额"])
        self.assertEqual(500_000_000, overview["分类明细"]["权益"]["买入金额"])
        self.assertEqual(600_000_000, overview["分类明细"]["权益"]["卖出金额"])
        self.assertEqual(700_000_000, overview["分类明细"]["一级"]["买入金额"])
        self.assertEqual(800_000_000, overview["分类明细"]["一级"]["卖出金额"])
        self.assertEqual(8, overview["总笔数"])
        self.assertEqual(3_600_000_000, overview["总指令金额"])
        self.assertEqual(3_600_000_000, overview["总成交金额"])

    def test_invalid_instruction_filters_cancelled_without_fill(self):
        # 已撤销 + 未成交 / 成交状态缺失 / 空串 → 无效（不计入）
        self.assertTrue(_is_invalid_instruction({"指令状态": "已撤销", "成交状态": "未成交"}))
        self.assertTrue(_is_invalid_instruction({"指令状态": "已撤销"}))  # 成交状态缺失视为未成交
        self.assertTrue(_is_invalid_instruction({"指令状态": "已撤销", "成交状态": ""}))  # 空串同理
        # 已撤销 + 有实际成交（部分/全部）→ 有效，仍计入（符合"部分成交算笔数"）
        self.assertFalse(_is_invalid_instruction({"指令状态": "已撤销", "成交状态": "部分成交"}))
        self.assertFalse(_is_invalid_instruction({"指令状态": "已撤销", "成交状态": "全部成交"}))
        # 非撤销指令一律有效
        self.assertFalse(_is_invalid_instruction({"指令状态": "有效指令", "成交状态": "未成交"}))
        self.assertFalse(_is_invalid_instruction({"指令状态": "已修改", "成交状态": "未成交"}))

    def test_funding_condition_treats_unknown_and_converge_as_neutral(self):
        # 含明确紧/松关键词 → 对应档
        self.assertEqual("不松", _funding_condition("资金面偏紧，融入需求旺盛"))
        self.assertEqual("偏松", _funding_condition("资金面偏松，融出意愿较强"))
        # "收敛"归中性均衡（与 _market_status_from_text 一致，不触发 funding_score+1.0）
        self.assertEqual("均衡", _funding_condition("资金面收敛，利率向中性回落"))
        # 无情绪词的纯数据描述 → 兜底均衡（中性，不无依据偏向紧）
        self.assertEqual("均衡", _funding_condition("隔夜成交在加权-1.46%区间，7天押存单1.46%"))
        # 空文本 / 占位 → 暂无有效消息
        self.assertEqual("暂无有效消息", _funding_condition(""))
        self.assertEqual("暂无有效消息", _funding_condition("暂无有效消息"))

    def test_trade_count_uses_current_day_direction_categories(self):
        count_data = aggregate_trade_count_by_hour([
            {"委托方向": "债券买入", "指令状态": "有效指令"},
            {"委托方向": "债券卖出", "指令状态": "有效指令"},
            {"委托方向": "融资回购", "指令状态": "有效指令", "市场": "银行间"},
            {"委托方向": "融券回购", "指令状态": "有效指令", "市场": "银行间"},
            {"委托方向": "买入", "指令状态": "有效指令"},
            {"委托方向": "卖出", "指令状态": "有效指令"},
            {"委托方向": "分销买入", "指令状态": "有效指令"},
            {"委托方向": "分销卖出", "指令状态": "有效指令"},
            {"委托方向": "混合", "指令状态": "有效指令"},
            {"委托方向": "买入", "指令状态": "已撤销", "成交状态": "未成交"},
        ])

        self.assertEqual(8, count_data["total"])
        self.assertIsNone(count_data["year_total"])
        self.assertEqual(1, count_data["counts"]["现券买入"])
        self.assertEqual(1, count_data["counts"]["现券卖出"])
        self.assertEqual(1, count_data["counts"]["正回购"])
        self.assertEqual(1, count_data["counts"]["逆回购"])
        self.assertEqual(1, count_data["counts"]["权益买入"])
        self.assertEqual(1, count_data["counts"]["权益卖出"])
        self.assertEqual(1, count_data["counts"]["分销买入"])
        self.assertEqual(1, count_data["counts"]["分销卖出"])

    def test_trade_section_without_charts_uses_tables_not_empty_images(self):
        html = render_trade_no_chart_hourly_report()

        self.assertNotIn('src="data:image/png;base64,"', html)
        self.assertIn("今日交易笔数合计10笔。", html)
        self.assertIn("<th>交易方向</th>", html)
        self.assertIn("<td>现券买入</td>", html)
        self.assertIn("<td>4</td>", html)
        self.assertNotIn("2026年以来", html)

    def test_trade_section_chart_order_matches_reference_unit(self):
        html = render_trade_chart_sample_report()

        summary_pos = html.index('<div class="template-subtitle">交易数据汇总</div>')
        count_pos = html.index('<div class="template-subtitle">交易笔数</div>')
        count_chart_pos = html.index("COUNT_CHART")
        amount_pos = html.index('<div class="template-subtitle">交易金额</div>')
        amount_chart_pos = html.index("PRICE_CHART")
        amount_table_pos = html.index('<table class="amount-table">')

        self.assertLess(summary_pos, count_pos)
        self.assertLess(count_pos, count_chart_pos)
        self.assertLess(count_chart_pos, amount_pos)
        self.assertLess(amount_pos, amount_chart_pos)
        self.assertLess(amount_chart_pos, amount_table_pos)
        self.assertIn('alt="交易笔数图"', html)
        self.assertIn('alt="交易金额图"', html)
        self.assertNotIn("OVERVIEW_CHART_SHOULD_NOT_RENDER", html)

    def test_settlement_section_uses_compact_table_without_extra_chart(self):
        html = render_settlement_sample_report()

        settlement_pos = html.index('<span class="icon">02</span> 交收数据汇总')
        forecast_pos = html.index('<span class="icon">03</span> 市场预测汇总')
        settlement_html = html[settlement_pos:forecast_pos]

        self.assertIn("今日应急金额为5000万元", settlement_html)
        self.assertIn("<th>应急产品</th>", settlement_html)
        self.assertIn("<th>应急金额（万元）</th>", settlement_html)
        self.assertIn("<th>应收业务类型</th>", settlement_html)
        self.assertIn("<th>应收交易对手</th>", settlement_html)
        self.assertIn("<th>应急原因</th>", settlement_html)
        self.assertIn("<td>**鼎泰135号(*)</td>", settlement_html)
        self.assertNotIn("<td>产品1</td>", settlement_html)
        self.assertNotIn("创金", settlement_html)
        self.assertNotIn("合信", settlement_html)
        self.assertNotIn("中国银行上海", settlement_html)
        self.assertIn("16点15分未到账", settlement_html)
        self.assertIn("上清所", settlement_html)
        self.assertNotIn("SETTLEMENT_CHART_SHOULD_NOT_RENDER", settlement_html)
        self.assertNotIn("交收进度分布图", settlement_html)

    def test_emergency_repo_masks_product_names_without_generic_numbering(self):
        repo = aggregate_emergency_repo([
            {
                "productName": "创金合信鼎泰135号(中国银行上海)",
                "repurAmt": "180000000",
                "sideCodeText": "正回购",
                "rivalName": "中信信托日享套利1号",
                "repoInsDirectTimeText": "交易员 2026-06-22 16:43:12",
            }
        ])

        self.assertEqual("**鼎泰135号(*)", repo["明细"][0]["应急产品"])
        self.assertNotEqual("产品1", repo["明细"][0]["应急产品"])
        self.assertEqual("16点43分未到账", repo["明细"][0]["应急原因"])

    def test_forecast_section_contains_rates_and_prediction_contract(self):
        html = render_forecast_sample_report()

        forecast_pos = html.index('<span class="icon">03</span> 市场预测汇总')
        money_pos = html.index('<span class="icon">04</span> 资金市场分析')
        forecast_html = html[forecast_pos:money_pos]

        self.assertNotIn("REPO_RATE_CHART", forecast_html)
        self.assertNotIn('alt="回购利率图"', forecast_html)
        self.assertNotIn("<td><strong>R001</strong></td>", forecast_html)
        self.assertNotIn("最新利率（%）", forecast_html)
        self.assertIn("预测结论", forecast_html)
        self.assertIn("资产类型", forecast_html)
        self.assertIn("明日预测点位区间", forecast_html)
        self.assertIn("方法说明", forecast_html)
        self.assertIn("资金面判断", forecast_html)
        self.assertNotIn("预测指标来源尚未确认", forecast_html)
        self.assertNotIn("趋势预测准确率", forecast_html)
        self.assertNotIn("区间预测准确率", forecast_html)
        self.assertEqual(1, forecast_html.count('<div class="section">'))

    def test_primary_market_section_uses_analysis_then_evidence(self):
        html = render_primary_market_sample_report()

        analysis_pos = html.index("【关注焦点】发行、投标")
        list_pos = html.index('<div class="commentary-list">')
        structure_pos = html.index("发行结构分析")
        self.assertLess(analysis_pos, list_pos)
        self.assertLess(list_pos, structure_pos)
        self.assertIn("一级发行样例消息一", html)

    def test_primary_market_available_branch_renders_both_subsections(self):
        html = render_primary_market_available_report()
        primary_start = html.rfind(
            '<div class="section">',
            0,
            html.index('<div class="section-title">一级市场分析</div>'),
        )
        primary_end = html.rfind(
            '<div class="section">',
            0,
            html.index('<div class="section-title">风险提示</div>'),
        )
        primary_html = html[primary_start:primary_end]

        self.assertIn("发行情况", primary_html)
        self.assertIn("发行结构分析", primary_html)
        self.assertNotIn("待接入", primary_html)
        # 新结构：汇总卡片 + 明细表
        self.assertIn("利率债发行", primary_html)
        self.assertIn("260", primary_html)
        self.assertIn("地方债发行", primary_html)
        self.assertIn("235", primary_html)
        self.assertNotIn("NCD 发行", primary_html)  # NCD=0 不渲染卡片
        self.assertIn("<th>品种</th>", primary_html)
        self.assertIn("<td>国债</td>", primary_html)
        self.assertIn("<td>10Y</td>", primary_html)

    def test_primary_market_section_renders_all_branches_inside_single_unit(self):
        fallback_html = render_sample_report()
        qt_html = render_primary_market_sample_report()
        available_html = render_primary_market_available_report()

        def primary_segment(html: str) -> str:
            title = html.index('<div class="section-title">一级市场分析</div>')
            start = html.rfind('<div class="section">', 0, title)
            next_title = html.index('<div class="section-title">风险提示</div>')
            end = html.rfind('<div class="section">', 0, next_title)
            return html[start:end]

        fallback_segment = primary_segment(fallback_html)
        qt_segment = primary_segment(qt_html)
        available_segment = primary_segment(available_html)

        self.assertIn("发行情况", fallback_segment)
        self.assertIn("发行结构分析", fallback_segment)
        self.assertIn("暂无相关数据", fallback_segment)
        self.assertIn("一级发行样例消息一", qt_segment)
        self.assertIn("发行结构分析", qt_segment)
        self.assertIn("利率债发行", available_segment)  # 汇总卡片
        self.assertEqual(1, available_segment.count('<div class="section">'))

    def test_risk_tips_section_renders_numbered_list_as_final_unit(self):
        html = render_risk_tips_sample_report()

        risk_title = html.index('<div class="section-title">风险提示</div>')
        risk_start = html.rfind('<div class="section">', 0, risk_title)
        risk_segment = html[risk_start:]

        self.assertIn('<ol class="risk-list">', risk_segment)
        self.assertIn('<span class="risk-index">1.</span>', risk_segment)
        self.assertIn("今日规则引擎识别到 2 条风险线索", risk_segment)
        self.assertIn("请密切关注明日到期回购资金的安排", risk_segment)
        self.assertEqual(1, risk_segment.count('<div class="section">'))
        self.assertNotIn("规则引擎风险", risk_segment)

    def test_equity_market_uses_external_input_or_contract_fallback(self):
        fallback = build_equity_market_analysis()
        provided = build_equity_market_analysis("A股市场收盘后外部短评样例。")
        fallback_html = render_sample_report()
        provided_html = render_equity_market_sample_report()

        self.assertFalse(fallback["available"])
        self.assertEqual("外部短评暂未获取", fallback["commentary"])
        self.assertTrue(provided["available"])
        self.assertIn("外部短评暂未获取", fallback_html)
        self.assertIn("A股市场收盘后外部短评样例。", provided_html)

    def test_equity_market_section_renders_input_or_fallback_inside_single_unit(self):
        fallback_html = render_sample_report()
        provided_html = render_equity_market_sample_report()

        fallback_pos = fallback_html.index('<div class="section-title">权益市场分析</div>')
        fallback_next = fallback_html.index('<div class="section-title">一级市场分析</div>')
        fallback_segment = fallback_html[fallback_pos:fallback_next]

        provided_pos = provided_html.index('<div class="section-title">权益市场分析</div>')
        provided_start = provided_html.rfind('<div class="section">', 0, provided_pos)
        provided_next_title = provided_html.index('<div class="section-title">一级市场分析</div>')
        provided_next = provided_html.rfind('<div class="section">', 0, provided_next_title)
        provided_segment = provided_html[provided_start:provided_next]

        self.assertIn("外部短评暂未获取", fallback_segment)
        self.assertIn("A股市场收盘后外部短评样例。", provided_segment)
        self.assertIn("数据来源：外部市场短评", provided_segment)
        self.assertIn('<div class="analysis-box">', provided_segment)
        self.assertEqual(1, provided_segment.count('<div class="section">'))

    def test_funding_market_structure_is_stable_without_money_data(self):
        html = render_sample_report()

        funding_pos = html.index('<span class="icon">04</span> 资金市场分析')
        bond_pos = html.index("现券市场分析")
        segment = html[funding_pos:bond_pos]
        self.assertIn("填写人：自动", segment)
        self.assertIn("▶公开市场操作", segment)
        self.assertIn("▶资金面状况", segment)
        self.assertNotIn("债券发行与到期", segment)
        self.assertIn("暂无相关数据", segment)

    def test_funding_market_section_renders_data_inside_single_unit(self):
        html = render_money_market_sample_report()

        funding_pos = html.index('<span class="icon">04</span> 资金市场分析')
        section_pos = html.rfind('<div class="section">', 0, funding_pos)
        bond_pos = html.index("现券市场分析")
        segment = html[section_pos:bond_pos]

        self.assertIn("填写人：自动", segment)
        self.assertIn("▶公开市场操作（2026-06-17）", segment)
        self.assertIn("规模（亿元）", segment)
        self.assertIn("到期量（亿元）", segment)
        self.assertIn("净投放（亿元）", segment)
        self.assertIn("<strong>7天逆回购</strong>", segment)
        self.assertIn("+120.00", segment)
        self.assertNotIn("债券发行与到期", segment)
        self.assertIn("▶资金面状况", segment)
        # 整体状态由 Claude 生成，脚本不产出
        self.assertNotIn("整体状态：", segment)
        self.assertIn("隔夜（押利率/存单）", segment)
        self.assertIn("7天（押利率/存单/信用）", segment)
        self.assertIn("14天跨月", segment)
        self.assertEqual(1, segment.count('<div class="section">'))

    def test_bond_market_section_renders_commentary_or_fallback(self):
        fallback_html = render_sample_report()
        provided_html = render_bond_market_sample_report()

        fallback_pos = fallback_html.index('<div class="section-title">现券市场分析</div>')
        fallback_next = fallback_html.index('<div class="section-title">权益市场分析</div>')
        fallback_segment = fallback_html[fallback_pos:fallback_next]

        provided_pos = provided_html.index('<div class="section-title">现券市场分析</div>')
        provided_start = provided_html.rfind('<div class="section">', 0, provided_pos)
        provided_next_title = provided_html.index('<div class="section-title">权益市场分析</div>')
        provided_next = provided_html.rfind('<div class="section">', 0, provided_next_title)
        provided_segment = provided_html[provided_start:provided_next]

        self.assertIn("暂无有效消息", fallback_segment)
        self.assertIn("现券样例短评", provided_segment)
        self.assertIn('<div class="analysis-box">', provided_segment)
        self.assertEqual(1, provided_segment.count('<div class="section">'))


if __name__ == "__main__":
    unittest.main()
