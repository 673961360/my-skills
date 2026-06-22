"""Oracle 数据库客户端 — 查询 QT 聊天消息数据库。

数据源：ats.t_repo_robot_chatmessage 表
用途：获取资金、现券、一级发行市场的交易员市场短评

Channel 说明：
  1 = 森浦QT
  3 = 通达信QT
  4 = 快确QT

注意：目标数据库为 Oracle 11.2.0.4，需使用 thick 模式（依赖 Oracle Instant Client）。

表结构（关键字段）：
  MSG_DATE      NUMBER   — 消息日期 YYYYMMDD
  MSG_TIME      NUMBER   — 消息时间 HHMMSS
  CHANNEL       NUMBER   — 频道（1/3/4）
  CONTENT       VARCHAR2 — 消息内容
  MSG_SEND_NAME VARCHAR2 — 发送人姓名
  MSG_SEND_CODE VARCHAR2 — 发送人代码
  TRADERIVAL_NAME VARCHAR2 — 交易对手名称
  MSG_GROUP_NAME  VARCHAR2 — 群名称
"""

import os
import sys
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
    conn = oracledb.connect(
        user=cfg["user"],
        password=cfg["password"],
        host=cfg["host"],
        port=cfg["port"],
        service_name=cfg["service_name"],
    )
    return conn


def _row_to_dict(cursor, row) -> dict:
    """将 Oracle 查询结果行转为 dict，处理 LOB 字段。"""
    columns = [col[0] for col in cursor.description]
    record = dict(zip(columns, row))
    for key, val in record.items():
        if hasattr(val, "read"):
            record[key] = val.read()
    return record


def fetch_chat_messages(query_date: str, channel: str | None = None) -> list[dict]:
    """查询 QT 聊天消息。

    Args:
        query_date: 查询日期 YYYYMMDD
        channel: 频道筛选 ("1"=森浦, "3"=通达信, "4"=快确)，None=全部

    Returns:
        消息记录列表
    """
    cfg = _get_config()
    table = cfg.get("comment_table", "ats.t_repo_robot_chatmessage")

    conn = _get_connection()
    try:
        cursor = conn.cursor()

        if channel:
            sql = f"""
                SELECT MSG_DATE, CHANNEL, CONTENT, MSG_TIME,
                       MSG_SEND_NAME, MSG_SEND_CODE, TRADERIVAL_NAME
                FROM {table}
                WHERE MSG_DATE = :p_date AND CHANNEL = :p_channel
                ORDER BY MSG_TIME ASC
            """
            cursor.execute(sql, p_date=int(query_date), p_channel=int(channel))
        else:
            sql = f"""
                SELECT MSG_DATE, CHANNEL, CONTENT, MSG_TIME,
                       MSG_SEND_NAME, MSG_SEND_CODE, TRADERIVAL_NAME
                FROM {table}
                WHERE MSG_DATE = :p_date
                ORDER BY CHANNEL ASC, MSG_TIME ASC
            """
            cursor.execute(sql, p_date=int(query_date))

        return [_row_to_dict(cursor, row) for row in cursor.fetchall()]
    finally:
        conn.close()


def fetch_all_channels(query_date: str) -> dict[str, list[dict]]:
    """按频道分组获取所有 QT 聊天消息。

    Returns:
        {"森浦QT": [...], "通达信QT": [...], "快确QT": [...]}
    """
    cfg = _get_config()
    channels = cfg.get("channels", {"1": "森浦QT", "3": "通达信QT", "4": "快确QT"})

    result: dict[str, list[dict]] = {}
    conn = _get_connection()
    try:
        cursor = conn.cursor()
        table = cfg.get("comment_table", "ats.t_repo_robot_chatmessage")

        sql = f"""
            SELECT MSG_DATE, CHANNEL, CONTENT, MSG_TIME,
                   MSG_SEND_NAME, MSG_SEND_CODE, TRADERIVAL_NAME
            FROM {table}
            WHERE MSG_DATE = :p_date
            ORDER BY CHANNEL ASC, MSG_TIME ASC
        """
        cursor.execute(sql, p_date=int(query_date))

        for row in cursor.fetchall():
            record = _row_to_dict(cursor, row)
            ch_id = str(record.get("CHANNEL", ""))
            ch_name = channels.get(ch_id, f"未知频道({ch_id})")
            if ch_name not in result:
                result[ch_name] = []
            result[ch_name].append(record)
    finally:
        conn.close()

    return result


def categorize_messages(messages: list[dict]) -> dict[str, list[dict]]:
    """将聊天消息按市场类型分类（关键词匹配）。

    分类规则：
    - 资金面：回购、资金、头寸、融出、融入、R001/R007/DR001/DR007、利率、加权等
    - 现券：现券、债券、买券/卖券、收益率、估值、成交、活跃券、国债、政金债等
    - 一级发行：一级、发行、投标、新债、招标、结果、边际、倍率等

    Returns:
        {"资金面": [...], "现券": [...], "一级发行": [...], "其他": [...]}
    """
    categories: dict[str, list[str]] = {
        "资金面": [
            "回购", "资金", "头寸", "融出", "融入", "R001", "R007",
            "DR001", "DR007", "利率", "加权", "平头寸", "借钱", "出钱",
            "紧张", "宽松", "央行", "逆回购", "MLF", "OMO", "投放", "回笼",
        ],
        "现券": [
            "现券", "债券", "买券", "卖券", "收益率", "估值", "成交",
            "活跃券", "国债", "政金债", "信用债", "城投", "地产债",
            "下行", "上行", "BP", "YTM", "久期", "利差",
        ],
        "一级发行": [
            "一级", "发行", "投标", "新债", "招标", "结果", "边际",
            "倍率", "募", "计划发行", "实际发行", "全场倍", "边际倍",
        ],
    }

    result: dict[str, list[dict]] = {
        "资金面": [],
        "现券": [],
        "一级发行": [],
        "其他": [],
    }

    for msg in messages:
        content = str(msg.get("CONTENT", ""))
        if not content.strip():
            continue

        matched = False
        for cat_name, keywords in categories.items():
            for kw in keywords:
                if kw in content:
                    result[cat_name].append(msg)
                    matched = True
                    break
            if matched:
                break

        if not matched:
            result["其他"].append(msg)

    return result


def _format_time(time_val) -> str:
    """将 MSG_TIME 整数转为 HH:MM:SS 字符串。

    MSG_TIME 存储为 9 位整数，格式 HHMMSSfff（fff=毫秒）。
    例如：141704000 → 14:17:04，930150000 → 09:30:15
    """
    if not time_val:
        return ""
    try:
        t = int(time_val)
        s = f"{t:09d}"  # 补齐 9 位
        hour = int(s[0:2])
        minute = int(s[2:4])
        second = int(s[4:6])
        return f"{hour:02d}:{minute:02d}:{second:02d}"
    except (ValueError, TypeError):
        return str(time_val)


def fetch_and_categorize(query_date: str) -> dict[str, Any]:
    """一站式：获取 QT 消息并分类，返回报告所需结构。

    Returns:
        {
            "channels": {"森浦QT": N条, ...},
            "资金面": {"count": N, "messages": [...]},
            "现券": {"count": N, "messages": [...]},
            "一级发行": {"count": N, "messages": [...]},
            "其他": {"count": N, "messages": [...]},
            "total": 总条数,
        }
    """
    all_messages = fetch_all_channels(query_date)

    # 统计各频道数量
    channel_stats = {name: len(msgs) for name, msgs in all_messages.items()}

    # 合并所有消息后分类
    all_msgs_flat: list[dict] = []
    for msgs in all_messages.values():
        all_msgs_flat.extend(msgs)

    categorized = categorize_messages(all_msgs_flat)

    # 提取关键信息（截断过长消息，统一字段名）
    def _extract(msgs: list[dict], max_items: int = 30) -> list[dict]:
        extracted = []
        for msg in msgs[:max_items]:
            content = str(msg.get("CONTENT", ""))
            if len(content) > 500:
                content = content[:500] + "..."
            extracted.append({
                "channel": str(msg.get("CHANNEL", "")),
                "time": _format_time(msg.get("MSG_TIME", "")),
                "sender": msg.get("MSG_SEND_NAME", msg.get("MSG_SEND_CODE", "")),
                "content": content,
            })
        return extracted

    return {
        "channels": channel_stats,
        "资金面": {
            "count": len(categorized["资金面"]),
            "messages": _extract(categorized["资金面"]),
        },
        "现券": {
            "count": len(categorized["现券"]),
            "messages": _extract(categorized["现券"]),
        },
        "一级发行": {
            "count": len(categorized["一级发行"]),
            "messages": _extract(categorized["一级发行"]),
        },
        "其他": {
            "count": len(categorized["其他"]),
            "messages": _extract(categorized["其他"], max_items=10),
        },
        "total": len(all_msgs_flat),
    }
