#!/usr/bin/env python3
"""交易日报自动生成主脚本。

用法：
    python generate_report.py                    # 生成当日日报
    python generate_report.py --date 20260621    # 指定日期
    python generate_report.py --date 20260621 --output custom.html  # 指定输出路径

输出：
    reports/YYYY-MM-DD-daily.html
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Windows 下强制 UTF-8 输出，避免 GBK 编码错误
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# 确保能导入同目录模块
PROJECT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_DIR))

from api_client import get_config
from data_collector import collect_all, _parse_date, _fmt_display_date
from chart_builder import build_all_charts


def _load_template() -> str:
    """加载 Jinja2 HTML 模板。"""
    template_path = PROJECT_DIR / "report_template.html"
    with open(template_path, "r", encoding="utf-8") as f:
        return f.read()


def render_report(data: dict, charts: dict) -> str:
    """使用 Jinja2 渲染 HTML 报告。"""
    from jinja2 import Template

    template_str = _load_template()
    template = Template(template_str)

    # 合并数据和图表
    context = {**data, "charts": charts}
    return template.render(**context)


def save_report(html_content: str, output_path: Path) -> Path:
    """保存 HTML 报告到文件。"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    return output_path


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(
        description="交易日报自动生成工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  python generate_report.py                  # 生成当日日报
  python generate_report.py --date 20260621  # 生成指定日期日报
  python generate_report.py --output out.html  # 指定输出路径
        """,
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="查询日期，格式 YYYYMMDD（默认当日）",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="输出文件路径（默认 reports/YYYY-MM-DD-daily.html）",
    )
    parser.add_argument(
        "--no-charts",
        action="store_true",
        help="跳过图表生成（加速调试）",
    )
    return parser.parse_args()


def main():
    """主入口。"""
    args = parse_args()

    # 确定日期
    query_date = _parse_date(args.date)
    display_date = _fmt_display_date(query_date)
    weekday_map = {0: "一", 1: "二", 2: "三", 3: "四", 4: "五", 5: "六", 6: "日"}
    weekday = f"周{weekday_map[datetime.strptime(query_date, '%Y%m%d').weekday()]}"

    print(f"═══════════════════════════════════")
    print(f"  交易日报生成")
    print(f"  日期：{display_date}（{weekday}）")
    print(f"═══════════════════════════════════")

    # Step 1: 加载配置
    cfg = get_config()
    print(f"\n[1/4] 配置加载完成")
    print(f"  API: {cfg['api_base_url']}")
    print(f"  输出目录: {cfg.get('output_dir', 'reports')}")

    # Step 2: 采集数据
    print(f"\n[2/4] 正在采集交易数据...")
    data = collect_all(query_date)

    trading_status = "交易日 [OK]" if data["is_trading_day"] else "非交易日 [!]"
    print(f"  交易日判断：{trading_status}")
    print(f"  O32指令数：{len(data.get('_instructions', []))}")
    print(f"  头寸记录数：{len(data.get('_positions', []))}")
    print(f"  交收记录数：{len(data.get('_settlement_rows', []))}")
    print(f"  风险预警数：{len(data.get('risk_warnings', []))}")

    qt = data.get("qt_commentary", {})
    if qt.get("total"):
        print(f"  QT短评总数：{qt['total']}")
        for ch_name, ch_count in qt.get("channels", {}).items():
            print(f"    - {ch_name}: {ch_count} 条")
        for cat_name in ["资金面", "现券", "一级发行"]:
            cat_data = qt.get(cat_name, {})
            print(f"    {cat_name}: {cat_data.get('count', 0)} 条")

    # Step 3: 生成图表
    print(f"\n[3/4] 正在生成图表...")
    if args.no_charts:
        charts = {}
        print(f"  （已跳过）")
    else:
        charts = build_all_charts(data)
        chart_count = sum(1 for v in charts.values() if v)
        print(f"  生成图表：{chart_count} 张")

    # Step 4: 渲染并保存
    print(f"\n[4/4] 正在渲染 HTML 报告...")
    html_content = render_report(data, charts)

    # 确定输出路径
    if args.output:
        output_path = Path(args.output)
    else:
        # 输出到 skill 根目录下的 reports/（scripts 的上级）
        output_dir = PROJECT_DIR.parent / cfg.get("output_dir", "reports")
        output_path = output_dir / f"{display_date}-daily.html"

    save_report(html_content, output_path)
    file_size = output_path.stat().st_size

    print(f"\n{'═' * 40}")
    print(f"  报告生成成功！")
    print(f"  文件：{output_path}")
    print(f"  大小：{file_size / 1024:.1f} KB")
    print(f"{'═' * 40}")

    return output_path


if __name__ == "__main__":
    main()
