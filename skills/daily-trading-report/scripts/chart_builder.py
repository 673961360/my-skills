"""图表生成模块 — 使用 matplotlib 生成报告图表，输出 base64 内嵌 HTML。

所有图表函数返回 base64 编码的 PNG 字符串，可直接用于 HTML 的 <img src="data:image/png;base64,...">。
"""

import base64
import io
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # 非交互式后端
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# 项目根目录
PROJECT_DIR = Path(__file__).resolve().parent

# ─────────────────────────────────────────────
# 字体配置
# ──────────────────────────────────────────────

def _get_chinese_font() -> str:
    """获取可用的中文字体。"""
    # 优先使用常见中文字体
    candidates = ["Microsoft YaHei", "SimHei", "STHeiti", "PingFang SC", "WenQuanYi Micro Hei"]
    available = {f.name for f in fm.fontManager.ttflist}
    for font in candidates:
        if font in available:
            return font
    # 兜底：使用默认字体（中文可能显示为方块）
    return "sans-serif"


_FONT_FAMILY = _get_chinese_font()

# 全局样式配置
plt.rcParams.update({
    "font.family": _FONT_FAMILY,
    "font.size": 10,
    "axes.unicode_minus": False,  # 修复负号显示
    "figure.dpi": 100,
    "savefig.dpi": 100,
    "figure.facecolor": "#f8f9fa",
    "axes.facecolor": "#f8f9fa",
    "axes.edgecolor": "#2d5f8a",
    "axes.linewidth": 0.8,
    "grid.linestyle": "--",
    "grid.alpha": 0.3,
})


def _fig_to_base64(fig: plt.Figure) -> str:
    """将 matplotlib Figure 转为 base64 PNG 字符串。"""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


# ──────────────────────────────────────────────
# 图表函数
# ──────────────────────────────────────────────


def build_trade_overview_chart(overview: dict) -> str:
    """生成交易额度总览饼图。

    Args:
        overview: aggregate_trade_overview 返回的 dict
    """
    categories = overview.get("分类明细", {})
    if not categories:
        return ""

    labels = list(categories.keys())
    amounts = [v["指令金额"] for v in categories.values()]

    fig, ax = plt.subplots(figsize=(8, 5))

    colors = ["#4472C4", "#ED7D31", "#A5A5A5", "#FFC000", "#5B9BD5", "#70AD47"]
    wedges, texts, autotexts = ax.pie(
        amounts,
        labels=labels,
        autopct="%1.1f%%",
        colors=colors[:len(labels)],
        startangle=90,
        textprops={"fontsize": 10},
    )
    for t in autotexts:
        t.set_fontsize(9)
        t.set_color("white")

    ax.set_title("交易额度分布（按业务分类·委托方向）", fontsize=13, fontweight="bold", pad=15)
    fig.tight_layout()
    return _fig_to_base64(fig)


def build_trade_count_chart(hourly_data: dict) -> str:
    """生成交易笔数按小时分布柱状图。

    Args:
        hourly_data: aggregate_trade_count_by_hour 返回的 dict
    """
    if not hourly_data:
        return ""

    hours = list(hourly_data.keys())
    counts = list(hourly_data.values())

    fig, ax = plt.subplots(figsize=(10, 4))

    bars = ax.bar(hours, counts, color="#4472C4", edgecolor="white", width=0.6)

    # 在柱子上方显示数值
    for bar, count in zip(bars, counts):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.3,
            str(count),
            ha="center",
            va="bottom",
            fontsize=9,
        )

    ax.set_xlabel("时间", fontsize=11)
    ax.set_ylabel("笔数", fontsize=11)
    ax.set_title("当日交易笔数分布（按小时）", fontsize=13, fontweight="bold", pad=10)
    ax.grid(axis="y", alpha=0.3)
    ax.set_ylim(0, max(counts) * 1.3 if counts else 10)
    fig.tight_layout()
    return _fig_to_base64(fig)


def build_trade_price_chart(prices: dict) -> str:
    """生成交易价格（利率）折线图。

    Args:
        prices: aggregate_trade_prices 返回的 dict
    """
    if not prices:
        return ""

    fig, ax = plt.subplots(figsize=(10, 4))

    labels = list(prices.keys())
    avg_rates = [v["平均利率"] for v in prices.values()]
    max_rates = [v["最高利率"] for v in prices.values()]
    min_rates = [v["最低利率"] for v in prices.values()]

    x = range(len(labels))

    ax.plot(x, avg_rates, "o-", color="#4472C4", label="平均利率", linewidth=2, markersize=8)
    ax.plot(x, max_rates, "s--", color="#ED7D31", label="最高利率", linewidth=1.5, markersize=6)
    ax.plot(x, min_rates, "^--", color="#70AD47", label="最低利率", linewidth=1.5, markersize=6)

    # 填充区间
    ax.fill_between(x, min_rates, max_rates, alpha=0.1, color="#4472C4")

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=11)
    ax.set_ylabel("利率（%）", fontsize=11)
    ax.set_title("当日回购利率分布", fontsize=13, fontweight="bold", pad=10)
    ax.legend(loc="best", fontsize=10)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    return _fig_to_base64(fig)


def build_repo_rate_gauge(repo_rates: list[dict]) -> str:
    """生成回购利率仪表盘（R001/R007 对比）。

    Args:
        repo_rates: 银行间回购实时行情数据
    """
    if not repo_rates:
        return ""

    # 提取 R001 和 R007 的利率
    r001_rates = []
    r007_rates = []
    for rate in repo_rates:
        code = rate.get("SECURITY_CODE", "")
        price = rate.get("LAST_PRICE", 0) or rate.get("LATEST_PRICE", 0)
        if price:
            if "R001" in code or "R-1" in code:
                r001_rates.append(float(price))
            elif "R007" in code or "R-7" in code:
                r007_rates.append(float(price))

    if not r001_rates and not r007_rates:
        return ""

    fig, ax = plt.subplots(figsize=(8, 4))

    categories = []
    values = []
    colors_list = []

    if r001_rates:
        categories.append("R001")
        values.append(round(sum(r001_rates) / len(r001_rates), 4))
        colors_list.append("#4472C4")
    if r007_rates:
        categories.append("R007")
        values.append(round(sum(r007_rates) / len(r007_rates), 4))
        colors_list.append("#ED7D31")

    bars = ax.bar(categories, values, color=colors_list, width=0.5, edgecolor="white")
    for bar, val in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.001,
            f"{val:.4f}%",
            ha="center",
            va="bottom",
            fontsize=12,
            fontweight="bold",
        )

    ax.set_ylabel("利率（%）", fontsize=11)
    ax.set_title("银行间回购实时利率", fontsize=13, fontweight="bold", pad=10)
    ax.grid(axis="y", alpha=0.3)
    ax.set_ylim(0, max(values) * 1.5 if values else 5)
    fig.tight_layout()
    return _fig_to_base64(fig)


def build_settlement_chart(forecast: dict) -> str:
    """生成交收预测柱状图。

    Args:
        forecast: aggregate_settlement_forecast 返回的 dict
    """
    status_map = forecast.get("状态明细", {})
    if not status_map:
        return ""

    labels = list(status_map.keys())
    counts = [v["笔数"] for v in status_map.values()]

    fig, ax = plt.subplots(figsize=(8, 4))

    color_map = {
        "成功": "#70AD47",
        "进行中": "#FFC000",
        "待处理": "#FFC000",
        "失败": "#ED7D31",
    }
    colors = [color_map.get(l, "#4472C4") for l in labels]

    bars = ax.bar(labels, counts, color=colors, width=0.5, edgecolor="white")
    for bar, count in zip(bars, counts):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.3,
            str(count),
            ha="center",
            va="bottom",
            fontsize=10,
        )

    ax.set_ylabel("笔数", fontsize=11)
    ax.set_title("交收进度分布", fontsize=13, fontweight="bold", pad=10)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    return _fig_to_base64(fig)


def build_all_charts(data: dict) -> dict:
    """批量生成所有图表，返回 {图表名: base64字符串} dict。

    Args:
        data: collect_all 返回的完整数据 dict
    """
    charts: dict[str, str] = {}

    # 板块 1：交易额度分布饼图
    overview = data.get("trade_overview", {})
    charts["trade_overview"] = build_trade_overview_chart(overview)

    # 板块 2：交易笔数柱状图
    hourly = data.get("trade_count_hourly", {})
    charts["trade_count"] = build_trade_count_chart(hourly)

    # 板块 3：交易价格折线图
    prices = data.get("trade_prices", {})
    charts["trade_price"] = build_trade_price_chart(prices)

    # 板块 4：交收预测柱状图
    settlement = data.get("settlement_forecast", {})
    charts["settlement"] = build_settlement_chart(settlement)

    # 板块 5：回购利率仪表盘
    repo_rates = data.get("_repo_rates", [])
    charts["repo_rate"] = build_repo_rate_gauge(repo_rates)

    return charts
