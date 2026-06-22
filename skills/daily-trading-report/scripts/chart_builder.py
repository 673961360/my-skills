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


def build_trade_count_chart(count_data: dict) -> str:
    """生成当日交易笔数分类柱状图。

    Args:
        count_data: aggregate_trade_count_by_hour 返回的 dict
    """
    if not count_data:
        return ""

    categories = count_data.get("categories", [])
    counts_by_category = count_data.get("counts", {})
    categories = [category for category in categories if counts_by_category.get(category, 0)]
    if not categories:
        return ""
    counts = [counts_by_category[category] for category in categories]

    fig, ax = plt.subplots(figsize=(10, 4.8))

    colors = {
        "现券买入": "#76b7e5",
        "现券卖出": "#2f73c9",
        "正回购": "#61d1d4",
        "逆回购": "#94e2de",
        "权益买入": "#d9473f",
        "权益卖出": "#c51f28",
        "分销买入": "#f2a13a",
        "分销卖出": "#f6c56f",
    }
    bars = ax.bar(categories, counts, color=[colors.get(category, "#4472C4") for category in categories], edgecolor="white", width=0.62)

    # 在柱子上方显示数值
    for bar, count in zip(bars, counts):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + max(counts) * 0.015,
            str(count),
            ha="center",
            va="bottom",
            fontsize=8,
        )

    ax.set_xlabel("交易方向", fontsize=11)
    ax.set_ylabel("笔数", fontsize=11)
    ax.set_title("交易笔数（当日分类）", fontsize=13, fontweight="bold", pad=10)
    ax.tick_params(axis="x", labelrotation=28, labelsize=9)
    ax.grid(axis="y", alpha=0.3)
    ax.set_ylim(0, max(counts) * 1.3 if counts else 10)
    fig.tight_layout()
    return _fig_to_base64(fig)


def build_trade_amount_chart(amount_data: dict) -> str:
    """生成当日交易金额分类柱状图。"""
    if not amount_data:
        return ""

    categories = amount_data.get("categories", [])
    amounts_by_category = amount_data.get("amounts", {})
    categories = [category for category in categories if amounts_by_category.get(category, 0)]
    if not categories:
        return ""
    amounts = [amounts_by_category[category] / 100000000 for category in categories]

    fig, ax = plt.subplots(figsize=(10, 4.8))
    colors = {
        "现券买入": "#76b7e5",
        "现券卖出": "#2f73c9",
        "正回购": "#61d1d4",
        "逆回购": "#94e2de",
        "权益买入": "#d9473f",
        "权益卖出": "#c51f28",
        "分销买入": "#f2a13a",
        "分销卖出": "#f6c56f",
    }
    bars = ax.bar(categories, amounts, color=[colors.get(category, "#4472C4") for category in categories], edgecolor="white", width=0.62)

    for bar, amount in zip(bars, amounts):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + max(amounts) * 0.015,
            f"{amount:.2f}",
            ha="center",
            va="bottom",
            fontsize=8,
        )

    ax.set_xlabel("交易方向", fontsize=11)
    ax.set_ylabel("金额（亿元）", fontsize=11)
    ax.set_title("交易金额（当日分类）", fontsize=13, fontweight="bold", pad=10)
    ax.tick_params(axis="x", labelrotation=28, labelsize=9)
    ax.grid(axis="y", alpha=0.3)
    ax.set_ylim(0, max(amounts) * 1.3 if amounts else 1)
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


def build_all_charts(data: dict) -> dict:
    """批量生成所有图表，返回 {图表名: base64字符串} dict。

    Args:
        data: collect_all 返回的完整数据 dict
    """
    charts: dict[str, str] = {}

    # 01 交易笔数柱状图
    hourly = data.get("trade_count_hourly", {})
    charts["trade_count"] = build_trade_count_chart(hourly)

    # 01 交易金额图
    charts["trade_price"] = build_trade_amount_chart(data.get("trade_amount_by_direction", {}))

    # 03 市场预测汇总回购利率图
    repo_rates = data.get("_repo_rates", [])
    charts["repo_rate"] = build_repo_rate_gauge(repo_rates)

    return charts
