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
    build_forecast_accuracy_sections,
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
        "settlement_forecast": {"总笔数": 0, "总金额": 0, "状态明细": {}},
        "repo_rates": [],
        "trend_forecast": {
            "available": False,
            "data": {},
            "reason": "历史预测数据不足，暂无法计算准确率",
        },
        "interval_forecast": {
            "available": False,
            "data": {},
            "reason": "历史预测数据不足，暂无法计算准确率",
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
            "channels": {},
            "资金面": {"count": 0, "messages": []},
            "现券": {"count": 0, "messages": []},
            "一级发行": {"count": 0, "messages": []},
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
    data["settlement_forecast"] = {
        "总笔数": 8,
        "总金额": 32_000_000,
        "状态明细": {
            "成功": {"笔数": 5, "金额": 20_000_000},
            "进行中": {"笔数": 2, "金额": 8_000_000},
            "失败": {"笔数": 1, "金额": 4_000_000},
        },
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
            "趋势预测准确率",
            "区间预测准确率",
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

    def test_forecast_accuracy_uses_placeholder_without_history(self):
        trade_prices = {
            "质押式回购": {"最低利率": 1.2, "最高利率": 1.8, "平均利率": 1.5, "笔数": 12}
        }

        forecasts = build_forecast_accuracy_sections(trade_prices)

        self.assertFalse(forecasts["trend_forecast"]["available"])
        self.assertFalse(forecasts["interval_forecast"]["available"])
        self.assertEqual("历史预测数据不足，暂无法计算准确率", forecasts["trend_forecast"]["reason"])
        self.assertEqual("历史预测数据不足，暂无法计算准确率", forecasts["interval_forecast"]["reason"])

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
        self.assertEqual(2, html.count("历史预测数据不足，暂无法计算准确率"))

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

        self.assertIn("交收总笔数", settlement_html)
        self.assertIn("交收总金额（万元）", settlement_html)
        self.assertIn("<th>交收状态</th>", settlement_html)
        self.assertIn("<td>成功</td>", settlement_html)
        self.assertIn("<td>进行中</td>", settlement_html)
        self.assertIn("<td>失败</td>", settlement_html)
        self.assertNotIn("SETTLEMENT_CHART_SHOULD_NOT_RENDER", settlement_html)
        self.assertNotIn("交收进度分布图", settlement_html)

    def test_forecast_section_contains_rates_and_accuracy_placeholders(self):
        html = render_forecast_sample_report()

        forecast_pos = html.index('<span class="icon">03</span> 市场预测汇总')
        money_pos = html.index('<span class="icon">04</span> 资金市场分析')
        forecast_html = html[forecast_pos:money_pos]

        self.assertIn("REPO_RATE_CHART", forecast_html)
        self.assertIn('alt="回购利率图"', forecast_html)
        self.assertIn("<td><strong>R001</strong></td>", forecast_html)
        self.assertIn("趋势预测准确率", forecast_html)
        self.assertIn("区间预测准确率", forecast_html)
        self.assertEqual(2, forecast_html.count("历史预测数据不足，暂无法计算准确率"))
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

        self.assertIn("发行情况", html)
        self.assertIn("一级市场发行情况结构化摘要样例。", html)
        self.assertIn("发行结构分析", html)
        self.assertIn("发行结构分析结构化摘要样例。", html)
        self.assertNotIn("待接入", html)

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


if __name__ == "__main__":
    unittest.main()
