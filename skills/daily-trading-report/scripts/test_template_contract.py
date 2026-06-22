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
    build_equity_market_analysis,
    build_market_forecast,
    build_risk_tips,
    generate_market_commentary,
)
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
        "trade_prices": {},
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
        "positions": [],
        "risk_warnings": [],
        "market_commentary": {
            "funding": "暂无有效消息",
            "bond": "暂无有效消息",
            "primary": "暂无有效消息",
        },
        "primary_market": {"available": False, "reason": "暂无对应 API 数据源"},
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
            "回购·融入": {"笔数": 6, "指令金额": 12_000_000, "成交金额": 10_000_000},
            "现券·买入": {"笔数": 4, "指令金额": 8_000_000, "成交金额": 5_000_000},
        },
    }
    data["trade_prices"] = {
        "R001": {"平均利率": 1.50, "最高利率": 1.70, "最低利率": 1.30, "笔数": 6},
        "R007": {"平均利率": 1.80, "最高利率": 2.00, "最低利率": 1.60, "笔数": 4},
    }
    return render_report(data, charts={})


def render_trade_no_chart_hourly_report() -> str:
    data = build_sample_data()
    data["trade_overview"] = {
        "总笔数": 10,
        "总指令金额": 20_000_000,
        "总成交金额": 15_000_000,
        "分类明细": {
            "回购·融入": {"笔数": 6, "指令金额": 12_000_000, "成交金额": 10_000_000},
            "现券·买入": {"笔数": 4, "指令金额": 8_000_000, "成交金额": 5_000_000},
        },
    }
    data["trade_count_hourly"] = {"09:00": 3, "10:00": 4, "11:00": 3}
    return render_report(data, charts={})


def render_trade_chart_sample_report() -> str:
    data = build_sample_data()
    data["trade_overview"] = {
        "总笔数": 10,
        "总指令金额": 20_000_000,
        "总成交金额": 15_000_000,
        "分类明细": {
            "回购·融入": {"笔数": 6, "指令金额": 12_000_000, "成交金额": 10_000_000},
            "现券·买入": {"笔数": 4, "指令金额": 8_000_000, "成交金额": 5_000_000},
        },
    }
    data["trade_count_hourly"] = {"09:00": 3, "10:00": 4, "11:00": 3}
    data["trade_prices"] = {
        "R001": {"平均利率": 1.50, "最高利率": 1.70, "最低利率": 1.30, "笔数": 6},
        "R007": {"平均利率": 1.80, "最高利率": 2.00, "最低利率": 1.60, "笔数": 4},
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
            {"序号": 1, "产品编号": "产品1", "回购金额万元": 2000.0,
             "期限天": 1, "利率": "R+0BP", "对手方": "上清所",
             "操作时间": "16:15:30", "状态": "有效"},
            {"序号": 2, "产品编号": "产品1", "回购金额万元": 3000.0,
             "期限天": 7, "利率": "2.10", "对手方": "中债登",
             "操作时间": "16:42:10", "状态": "已下达"},
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
        "summary": "一级市场发行情况结构化摘要样例。",
        "structure_summary": "发行结构分析结构化摘要样例。",
    }
    return render_report(data, charts={})


def render_equity_market_sample_report() -> str:
    data = build_sample_data()
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
            "应急回购明细（16:00 后正回购）",
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
        self.assertEqual("暂无相关数据", commentary["primary"])
        self.assertEqual(3, len(tips))
        self.assertIn('<ol class="risk-list">', html)
        self.assertIn('<span class="risk-index">1.</span>', html)
        self.assertNotIn("| safe", template)

    def test_funding_commentary_quotes_daily_report_with_source(self):
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
        # 来源标注
        self.assertIn("吕浩轩", funding)
        self.assertIn("17:00:00", funding)
        self.assertIn("日评", funding)
        # 无机器过程描述（contract 禁止）
        self.assertNotIn("【资金面研判】", funding)
        self.assertNotIn("共 ", funding)
        self.assertNotIn("无高频关键词", funding)
        # bond 无日评降级；一级固定降级
        self.assertEqual("暂无有效消息", commentary["bond"])
        self.assertEqual("暂无相关数据", commentary["primary"])

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

        self.assertIn('<table class="metric-table">', html)
        self.assertIn("笔数占比", html)
        self.assertIn("金额占比", html)
        self.assertIn('<table class="amount-table">', html)
        self.assertNotIn('src="data:image/png;base64,"', html)
        self.assertIn("font-size: 11px", template)
        self.assertIn("padding: 5px 7px", template)

    def test_trade_section_without_charts_uses_tables_not_empty_images(self):
        html = render_trade_no_chart_hourly_report()

        self.assertNotIn('src="data:image/png;base64,"', html)
        self.assertIn("<th>时间</th>", html)
        self.assertIn("<td>09:00</td>", html)
        self.assertIn("<td>3</td>", html)

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

        self.assertIn("应急回购笔数", settlement_html)
        self.assertIn("应急回购金额（万元）", settlement_html)
        self.assertIn("<th>产品编号</th>", settlement_html)
        self.assertIn("<td>产品1</td>", settlement_html)
        self.assertIn("16:15:30", settlement_html)
        self.assertIn("上清所", settlement_html)
        self.assertNotIn("SETTLEMENT_CHART_SHOULD_NOT_RENDER", settlement_html)
        self.assertNotIn("交收进度分布图", settlement_html)
        # 脱敏：真实产品代码/名称不得出现在 02 板块
        self.assertNotIn("003749", settlement_html)
        self.assertNotIn("创金", settlement_html)
        self.assertNotIn("合信", settlement_html)

    def test_forecast_section_contains_rates_and_prediction_contract(self):
        html = render_forecast_sample_report()

        forecast_pos = html.index('<span class="icon">03</span> 市场预测汇总')
        money_pos = html.index('<span class="icon">04</span> 资金市场分析')
        forecast_html = html[forecast_pos:money_pos]

        self.assertIn("REPO_RATE_CHART", forecast_html)
        self.assertIn('alt="回购利率图"', forecast_html)
        self.assertIn("<td><strong>R001</strong></td>", forecast_html)
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
        self.assertIn("一级市场发行情况结构化摘要样例。", primary_html)
        self.assertIn("发行结构分析", primary_html)
        self.assertIn("发行结构分析结构化摘要样例。", primary_html)
        self.assertNotIn("待接入", primary_html)

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
        self.assertIn("一级市场发行情况结构化摘要样例。", available_segment)
        self.assertIn("发行结构分析结构化摘要样例。", available_segment)
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
        self.assertIn("公开市场操作", segment)
        self.assertIn("债券发行与到期", segment)
        self.assertIn("资金面状况", segment)
        self.assertIn("暂无相关数据", segment)

    def test_funding_market_section_renders_data_inside_single_unit(self):
        html = render_money_market_sample_report()

        funding_pos = html.index('<span class="icon">04</span> 资金市场分析')
        section_pos = html.rfind('<div class="section">', 0, funding_pos)
        bond_pos = html.index("现券市场分析")
        segment = html[section_pos:bond_pos]

        self.assertIn("公开市场操作（2026-06-17）", segment)
        self.assertIn("OMO 净投放（亿元）", segment)
        self.assertIn("政府债净缴款（亿元）", segment)
        self.assertIn("<td>7D</td>", segment)
        self.assertIn("债券发行与到期", segment)
        self.assertIn("<strong>国债</strong>", segment)
        self.assertIn("资金面状况", segment)
        self.assertIn("资金面样例短评", segment)
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
