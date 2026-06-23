#!/usr/bin/env python3
"""交易日报自动生成主脚本。

用法：
    python generate_report.py                    # 生成当日日报
    python generate_report.py --date 20260621    # 指定日期
    python generate_report.py --date 20260621 --output custom.html  # 指定输出路径
    python generate_report.py --learning           # 生成学习模式日报

输出：
    reports/YYYY-MM-DD-daily.html
    reports/YYYY-MM-DD-daily-learning.html
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

from api_client import get_config, clear_api_cache
from data_collector import collect_all, _parse_date, _fmt_display_date, build_equity_market_analysis
from chart_builder import build_all_charts

LEARNING_REFERENCE_EXTENSIONS = {".py", ".md", ".json"}
LEARNING_REFERENCE_MAX_CHARS = 24000


def load_learning_annotations() -> dict:
    """Load learning-mode data source annotations."""
    annotations_path = PROJECT_DIR.parent / "data" / "learning-annotations.json"
    with open(annotations_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _json_for_inline_script(value: dict) -> str:
    """Serialize JSON safely for embedding inside a script tag."""
    return json.dumps(value, ensure_ascii=False).replace("</", "<\\/")


def _reference_values(value) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        refs: list[str] = []
        for item in value:
            refs.extend(_reference_values(item))
        return refs
    if isinstance(value, dict):
        path = value.get("path") or value.get("路径")
        return [str(path)] if path else []
    return []


def _collect_reference_paths(value) -> list[str]:
    if isinstance(value, dict):
        refs: list[str] = []
        for key, item in value.items():
            if key == "引用文件":
                refs.extend(_reference_values(item))
            else:
                refs.extend(_collect_reference_paths(item))
        return refs
    if isinstance(value, list):
        refs: list[str] = []
        for item in value:
            refs.extend(_collect_reference_paths(item))
        return refs
    return []


def _resolve_learning_reference(raw_path: str) -> tuple[str, Path] | None:
    normalized = raw_path.replace("\\", "/").strip().lstrip("/")
    if not normalized:
        return None

    root = PROJECT_DIR.parent.resolve()
    candidate = (root / normalized).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None

    if candidate.suffix.lower() not in LEARNING_REFERENCE_EXTENSIONS:
        return None
    if not candidate.is_file():
        return None

    relative = candidate.relative_to(root).as_posix()
    return relative, candidate


def _language_for_reference(path: str) -> str:
    suffix = Path(path).suffix.lower()
    return {
        ".py": "python",
        ".md": "markdown",
        ".json": "json",
    }.get(suffix, "text")


def load_learning_references(annotations: dict) -> dict:
    """Load safe project text files referenced by learning-mode annotations."""
    references: dict[str, dict] = {}
    for raw_path in _collect_reference_paths(annotations):
        resolved = _resolve_learning_reference(raw_path)
        if not resolved:
            continue
        relative_path, file_path = resolved
        if relative_path in references:
            continue

        content = file_path.read_text(encoding="utf-8", errors="replace")
        truncated = len(content) > LEARNING_REFERENCE_MAX_CHARS
        if truncated:
            content = content[:LEARNING_REFERENCE_MAX_CHARS] + "\n\n...（内容较长，已截断）"
        references[relative_path] = {
            "title": file_path.name,
            "path": relative_path,
            "language": _language_for_reference(relative_path),
            "content": content,
            "truncated": truncated,
        }
    return references


def render_report(
    data: dict,
    charts: dict,
    learning_mode: bool = False,
    learning_annotations: dict | None = None,
) -> str:
    """使用 Jinja2 渲染 HTML 报告。"""
    from jinja2 import Environment, FileSystemLoader

    env = Environment(loader=FileSystemLoader(str(PROJECT_DIR)), autoescape=False)
    template = env.get_template("report_template.html")

    # 合并数据和图表
    context = {**data, "charts": charts, "learning_mode": learning_mode}
    if learning_mode:
        annotations = learning_annotations if learning_annotations is not None else load_learning_annotations()
        references = load_learning_references(annotations)
        context["learning_annotations"] = annotations
        context["learning_annotations_json"] = _json_for_inline_script(annotations)
        context["learning_references"] = references
        context["learning_references_json"] = _json_for_inline_script(references)
    return template.render(**context)


def save_report(html_content: str, output_path: Path) -> Path:
    """保存 HTML 报告到文件。"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    return output_path


def load_equity_commentary(args: argparse.Namespace) -> str:
    """Load optional externally supplied equity market commentary."""
    if args.equity_commentary_file:
        path = Path(args.equity_commentary_file)
        return path.read_text(encoding="utf-8").strip()
    return (args.equity_commentary or "").strip()


def resolve_output_path(output_arg: str | None, cfg: dict, display_date: str, learning_mode: bool) -> Path:
    """Resolve report output path for normal and learning modes."""
    if output_arg:
        return Path(output_arg)

    output_dir = PROJECT_DIR.parent / cfg.get("output_dir", "reports")
    suffix = "daily-learning" if learning_mode else "daily"
    return output_dir / f"{display_date}-{suffix}.html"


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
    parser.add_argument(
        "--learning",
        action="store_true",
        help="输出学习模式日报（含数据来源标注面板）",
    )
    parser.add_argument(
        "--equity-commentary",
        type=str,
        default="",
        help="权益市场外部短评文本；未提供时显示固定降级文案",
    )
    parser.add_argument(
        "--equity-commentary-file",
        type=str,
        default="",
        help="读取权益市场外部短评的 UTF-8 文本文件；优先级高于 --equity-commentary",
    )
    parser.add_argument(
        "--env",
        type=str,
        default=None,
        choices=["test", "prod"],
        help="目标环境；优先级高于环境变量 DTR_ENV 和 config.json 的 env 字段",
    )
    parser.add_argument(
        "--use-cache",
        action="store_true",
        default=False,
        help="使用缓存的 API 响应（调试模式，跳过实时采集）",
    )
    parser.add_argument(
        "--refresh-cache",
        action="store_true",
        default=False,
        help="清除旧缓存后重新拉取并缓存",
    )
    return parser.parse_args()


def main():
    """主入口。"""
    args = parse_args()

    # 设定目标环境（供 api_client / db_client 的配置加载读取）
    # 仅在命令行显式指定时才覆盖环境变量，否则让 config_loader 按优先级解析
    if args.env is not None:
        os.environ["DTR_ENV"] = args.env

    # 缓存模式
    if args.use_cache or args.refresh_cache:
        os.environ["DTR_USE_CACHE"] = "true"
    if args.refresh_cache:
        removed = clear_api_cache()
        for name in removed:
            print(f"  🗑️  已删除缓存: {name}")
    if args.use_cache:
        print(f"  🗄️  缓存模式：ON（跳过实时 API 调用）")

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
    print(f"  环境: {cfg['_env']}")
    print(f"  API: {cfg['api_base_url']}")
    print(f"  输出目录: {cfg.get('output_dir', 'reports')}")

    # Step 2: 采集数据
    print(f"\n[2/4] 正在采集交易数据...")
    data = collect_all(query_date)
    equity_commentary = load_equity_commentary(args)
    data["equity_market"] = build_equity_market_analysis(equity_commentary)

    trading_status = "交易日 [OK]" if data["is_trading_day"] else "非交易日 [!]"
    print(f"  交易日判断：{trading_status}")
    print(f"  O32指令数：{len(data.get('_instructions', []))}")
    print(f"  头寸记录数：{len(data.get('_positions', []))}")
    print(f"  应急回购数：{len(data.get('_emergency_rows', []))}")
    print(f"  风险预警数：{len(data.get('risk_warnings', []))}")
    print(f"  权益短评：{'外部输入' if data['equity_market']['available'] else data['equity_market']['commentary']}")

    qt = data.get("qt_commentary", {})
    if qt.get("total"):
        print(f"  QT日评：召回 {qt.get('total_raw', 0)} 条 → 去重 {qt['total']} 篇")
        for theme in ("资金", "现券"):
            rep = qt.get("representative", {}).get(theme)
            if rep:
                print(f"    {theme}代表篇：{rep.get('sender', '')} · {rep.get('time', '')} · {rep.get('title', '')[:30]}")
            else:
                print(f"    {theme}代表篇：无")

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
    html_content = render_report(data, charts, learning_mode=args.learning)

    # 确定输出路径
    output_path = resolve_output_path(args.output, cfg, display_date, args.learning)

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
