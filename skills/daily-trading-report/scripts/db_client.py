"""Oracle 数据库客户端 — 查询 QT 聊天消息数据库。

数据源：ats.t_repo_robot_chatmessage 表
用途：召回当日市场日评（资金/现券），供日报市场分析栏目整段引用。

QT 表本质是交易报价/询价聊天流（单日 13 万+条），真正的市场日评
（机构收盘研报）只占其中几十条。本模块用「日评/早评/午评」关键词
召回、按原文去重、按标题分主题、选代表篇。详见 findings.md「QT 短评」一节。

Channel 说明：
  1 = 森浦QT
  3 = 通达信QT
  4 = 快确QT

注意：目标数据库为 Oracle 11.2.0.4，需使用 thick 模式（依赖 Oracle Instant Client）。
"""

import os
from typing import Any

from config_loader import load_config

# Oracle Client 库路径（thick 模式需要）
_ORACLE_LIB_DIR = os.environ.get(
    "ORACLE_LIB_DIR",
    r"D:\Program Files\oracle_client_x64\instantclient_21_8",
)

# 全局初始化标记
_oracle_initialized = False


def _init_oracle():
    """初始化 Oracle thick 模式（只需调用一次）。"""
    global _oracle_initialized
    if _oracle_initialized:
        return

    import oracledb

    lib_dir = _ORACLE_LIB_DIR
    if not os.path.isdir(lib_dir):
        raise FileNotFoundError(
            f"Oracle Instant Client 未找到: {lib_dir}\n"
            f"请设置环境变量 ORACLE_LIB_DIR 指向正确的路径"
        )

    oracledb.init_oracle_client(lib_dir=lib_dir)
    _oracle_initialized = True


def _get_config() -> dict:
    """获取配置中的 Oracle 部分（已按 DTR_ENV 合并环境差异）。"""
    return load_config().get("oracle", {})


def _get_connection():
    """创建 Oracle 数据库连接（thick 模式，需要 Oracle Instant Client）。"""
    import oracledb

    _init_oracle()

    cfg = _get_config()
    return oracledb.connect(
        user=cfg["user"],
        password=cfg["password"],
        host=cfg["host"],
        port=cfg["port"],
        service_name=cfg["service_name"],
    )


def _row_to_dict(cursor, row) -> dict:
    """将 Oracle 查询结果行转为 dict，处理 LOB 字段。"""
    columns = [col[0] for col in cursor.description]
    record = dict(zip(columns, row))
    for key, val in record.items():
        if hasattr(val, "read"):
            record[key] = val.read()
    return record


def _format_time(time_val) -> str:
    """将 MSG_TIME 整数转为 HH:MM:SS 字符串。

    MSG_TIME 存储为 9 位整数 HHMMSSfff（fff=毫秒），不足 9 位时无前导 0。
    例如：141704000 → 14:17:04，93015000 → 09:30:15。
    """
    if not time_val:
        return ""
    try:
        t = int(time_val)
        s = f"{t:09d}"  # 补齐 9 位
        return f"{int(s[0:2]):02d}:{int(s[2:4]):02d}:{int(s[4:6]):02d}"
    except (ValueError, TypeError):
        return str(time_val)


# 日评召回关键词（findings.md 验证：日评/早评/午评 已穷尽；禁用 %评% 会命中「评级」噪音）
_RECALL_KEYWORDS = ("日评", "早评", "午评")


def _extract_title(content: str) -> str:
    """取日评标题：首个换行前的内容，截前 40 字。"""
    first = content.strip().split("\n", 1)[0].strip()
    return first[:40]


def _classify_theme(title: str) -> str:
    """按日评标题分主题（标题是机构写的明确分类，比正文关键词可靠）。"""
    if any(w in title for w in ("资金", "货币市场", "存单")):
        return "资金"
    if any(w in title for w in ("利率债", "国债", "现券", "信用债")):
        return "现券"
    if any(w in title for w in ("一级", "发行", "新债")):
        return "一级"
    return "其他"


def _detect_session(content: str) -> str:
    """判定时段：早评/午评/日评。"""
    if "早评" in content:
        return "早评"
    if "午评" in content:
        return "午评"
    return "日评"


def fetch_daily_commentary(query_date: str) -> dict[str, Any]:
    """召回当日市场日评，按原文去重，按标题分主题，选代表篇。

    流程：SQL 层 LIKE 召回（日评/早评/午评）→ 按 CONTENT 原文完全相同去重
    （跨频道同篇逐字一致）→ 按标题分主题 → 每主题选最长（最全）作代表篇。

    Returns:
        {
            "total": 去重后独立日评数,
            "total_raw": 召回原始命中（含跨频道重复）,
            "reports": [ {content, sender, time, channel, title, theme, session}, ... ],
            "representative": { "资金": report|None, "现券": report|None },
        }
    """
    cfg = _get_config()
    table = cfg.get("comment_table", "ats.t_repo_robot_chatmessage")

    like_clause = " OR ".join(
        f"CONTENT LIKE :kw{i}" for i in range(len(_RECALL_KEYWORDS))
    )
    binds = {f"kw{i}": f"%{kw}%" for i, kw in enumerate(_RECALL_KEYWORDS)}

    conn = _get_connection()
    try:
        cursor = conn.cursor()
        sql = (
            f"SELECT CONTENT, MSG_SEND_NAME, MSG_TIME, CHANNEL FROM {table} "
            f"WHERE MSG_DATE = :p_date AND ({like_clause}) ORDER BY MSG_TIME"
        )
        cursor.execute(sql, p_date=int(query_date), **binds)
        rows = [_row_to_dict(cursor, row) for row in cursor.fetchall()]
    finally:
        conn.close()

    total_raw = len(rows)

    # 按 CONTENT 原文完全相同去重（跨频道同篇逐字一致）
    seen: set[str] = set()
    reports: list[dict[str, Any]] = []
    for row in rows:
        content = str(row.get("CONTENT") or "").strip()
        if not content or content in seen:
            continue
        seen.add(content)
        title = _extract_title(content)
        reports.append({
            "content": content,
            "sender": str(row.get("MSG_SEND_NAME") or "").strip(),
            "time": _format_time(row.get("MSG_TIME")),
            "channel": str(row.get("CHANNEL") or ""),
            "title": title,
            "theme": _classify_theme(title),
            "session": _detect_session(content),
        })

    # 每主题选最长（最全）作代表篇
    representative: dict[str, dict[str, Any] | None] = {"资金": None, "现券": None}
    for theme in representative:
        candidates = [r for r in reports if r["theme"] == theme]
        if candidates:
            representative[theme] = max(candidates, key=lambda r: len(r["content"]))

    return {
        "total": len(reports),
        "total_raw": total_raw,
        "reports": reports,
        "representative": representative,
    }
